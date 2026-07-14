from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median

import pandas as pd
import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.importer.xes import importer as xes_importer

from crpm.pipeline import csv_to_event_log

BOUNDARY = datetime(2023, 7, 1, tzinfo=timezone.utc)


def _load_screening_demo():
    return xes_importer.apply("examples/screening_conformance_demo.xes")


def test_idealized_reference_log_uses_1200_case_sample() -> None:
    log = xes_importer.apply("examples/idealized_event_log.xes")
    variants = Counter(_variant(trace) for trace in log)

    assert len(log) == 1200
    assert sum(len(trace) for trace in log) == 4126
    assert len({trace.attributes["concept:name"] for trace in log}) == 1200
    assert sorted(variants.values()) == [34, 405, 761]


def _variant(trace) -> tuple[str, ...]:
    return tuple(event["concept:name"] for event in trace)


def _duration_days(trace) -> float:
    return (trace[-1]["time:timestamp"] - trace[0]["time:timestamp"]).total_seconds() / 86400


def _transitions(log):
    return Counter((start["concept:name"], end["concept:name"]) for trace in log for start, end in zip(trace, trace[1:]))


def test_screening_conformance_demo_is_rich_enough_for_ui_storytelling() -> None:
    log = _load_screening_demo()
    variants = Counter(_variant(trace) for trace in log)
    activities = {event["concept:name"] for trace in log for event in trace}

    assert len(log) == 30_000
    assert len(variants) >= 18
    assert 30 <= (variants.most_common(1)[0][1] / len(log) * 100) <= 40
    assert {
        "Admin_review",
        "Colonoscopy_no_show",
        "PCC_FIT_rejection",
        "Lab_rejection",
        "Reminder_mail",
    }.issubset(activities)


def test_screening_conformance_demo_contains_conformant_and_deviating_paths() -> None:
    log = _load_screening_demo()
    variants = Counter(_variant(trace) for trace in log)
    dominant_variant = (
        "Invitation_mail",
        "FIT_mail",
        "FIT_return",
        "Lab_return",
        "Lab_result",
        "PCC_fwd",
        "PCC_observation",
        "Colonoscopy_center",
    )

    assert dominant_variant in variants
    assert variants[dominant_variant] >= 9_300
    assert (
        "Invitation_mail",
        "Reminder_mail",
        "FIT_mail",
        "FIT_return",
        "Lab_return",
        "Lab_result",
        "PCC_fwd",
        "PCC_observation",
        "Colonoscopy_center",
    ) in variants
    assert any(
        "Admin_review" in variant or "Colonoscopy_no_show" in variant or "Lab_rejection" in variant
        for variant in variants
        if variant != dominant_variant
    )


def test_screening_conformance_demo_has_clear_pre_post_shift_and_dfg_spread() -> None:
    log = _load_screening_demo()
    pre = [trace for trace in log if trace.attributes["phase"] == "PRE"]
    post = [trace for trace in log if trace.attributes["phase"] == "POST"]
    transitions = _transitions(log)

    assert len(pre) == len(post) == 15_000
    assert max(trace[0]["time:timestamp"] for trace in pre) < BOUNDARY
    assert min(trace[0]["time:timestamp"] for trace in post) > BOUNDARY
    assert max(trace[-1]["time:timestamp"] for trace in log) - min(trace[0]["time:timestamp"] for trace in log) >= timedelta(days=365 * 3)
    assert median(_duration_days(trace) for trace in post) >= median(_duration_days(trace) for trace in pre) * 2
    assert transitions[("FIT_mail", "FIT_return")] == 30_000
    assert transitions[("Lab_result", "Colonoscopy_center")] >= 750
    assert transitions[("Reminder_mail", "Reminder_mail")] >= 2_500


def test_screening_conformance_demo_csv_is_rich_enough_for_onboarding() -> None:
    dataframe = pd.read_csv("examples/screening_conformance_demo.csv")
    log = csv_to_event_log(dataframe.copy(), "case_id", "activity", "timestamp")
    variants = Counter(_variant(trace) for trace in log)
    case_phase = dataframe.groupby("case_id")["phase"].first()
    case_durations = (
        dataframe.assign(timestamp=pd.to_datetime(dataframe["timestamp"]))
        .groupby("case_id")["timestamp"]
        .agg(lambda series: (series.max() - series.min()).total_seconds() / 86400)
    )

    assert len(log) == 30_000
    assert dataframe["case_id"].nunique() == 30_000
    assert set(dataframe["phase"]) == {"PRE", "POST"}
    assert dataframe[dataframe["phase"] == "PRE"]["case_id"].nunique() == 15_000
    assert dataframe[dataframe["phase"] == "POST"]["case_id"].nunique() == 15_000
    assert dataframe["timestamp"].pipe(pd.to_datetime).max() - dataframe["timestamp"].pipe(pd.to_datetime).min() >= timedelta(days=365 * 3)
    assert len(variants) >= 18
    assert {"variant_hint", "manual_review_flag", "no_show_flag", "followup_breach_days"}.issubset(dataframe.columns)
    assert {"Admin_review", "Colonoscopy_no_show", "Lab_rejection", "Reminder_mail"}.issubset(set(dataframe["activity"]))
    assert median(case_durations[case_phase == "POST"]) > median(case_durations[case_phase == "PRE"]) * 1.8
