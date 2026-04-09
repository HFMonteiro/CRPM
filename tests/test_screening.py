from __future__ import annotations

from datetime import datetime, date

import pandas as pd
import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.obj import EventLog, Trace

from crpm.screening import (
    PeriodDefinition,
    build_normative_pathway_model,
    filter_log_by_incident_period,
    split_log_by_periods,
    summarize_transition_benchmarks,
)


def make_trace(case_id: str, events: list[tuple[str, datetime]]) -> Trace:
    trace = Trace(attributes={"concept:name": case_id})
    for activity, timestamp in events:
        trace.append({"concept:name": activity, "time:timestamp": timestamp})
    return trace


def test_followup_window_censors_late_events() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("Invitation_mail", datetime(2024, 1, 1)),
                    ("FIT_return", datetime(2024, 1, 10)),
                    ("Colonoscopy_center", datetime(2025, 2, 1)),
                ],
            )
        ]
    )

    filtered = filter_log_by_incident_period(
        log,
        anchor_activity="Invitation_mail",
        followup_days=365,
    )

    assert len(filtered) == 1
    assert [event["concept:name"] for event in filtered[0]] == [
        "Invitation_mail",
        "FIT_return",
    ]


def test_period_split_uses_anchor_date() -> None:
    log = EventLog(
        [
            make_trace("a", [("Invitation_mail", datetime(2023, 6, 1)), ("FIT_return", datetime(2023, 6, 8))]),
            make_trace("b", [("Invitation_mail", datetime(2024, 7, 1)), ("FIT_return", datetime(2024, 7, 8))]),
        ]
    )

    periods = split_log_by_periods(
        log,
        anchor_activity="Invitation_mail",
        period_a=PeriodDefinition("PRE", date(2023, 1, 1), date(2023, 12, 31)),
        period_b=PeriodDefinition("POST", date(2024, 1, 1), date(2024, 12, 31)),
    )

    assert len(periods["PRE"]) == 1
    assert len(periods["POST"]) == 1
    assert periods["PRE"][0].attributes["concept:name"] == "a"
    assert periods["POST"][0].attributes["concept:name"] == "b"


def test_normative_model_keeps_ordered_steps() -> None:
    model = build_normative_pathway_model(
        {
            "invitation": "Invitation_mail",
            "fit_mail": "FIT_mail",
            "fit_return": "FIT_return",
            "lab_result": "Lab_result",
            "pcc_observation": "PCC_observation",
            "colonoscopy": "Colonoscopy_center",
        }
    )

    assert model is not None
    _, _, _, steps = model
    assert steps == [
        "Invitation_mail",
        "FIT_mail",
        "FIT_return",
        "Lab_result",
        "PCC_observation",
        "Colonoscopy_center",
    ]


def test_transition_benchmarks_flag_breaches() -> None:
    transition_stats = pd.DataFrame(
        [
            {
                "activity": "PCC_observation",
                "next_activity": "Colonoscopy_center",
                "transition": "PCC_observation → Colonoscopy_center",
                "frequency": 10,
                "median_duration_s": 60 * 86400,
                "p90_duration_s": 90 * 86400,
            }
        ]
    )

    benchmark_df = summarize_transition_benchmarks(
        transition_stats,
        {("PCC_observation", "Colonoscopy_center"): 45.0},
    )

    assert benchmark_df.iloc[0]["benchmark_status"] == "Breached"
    assert benchmark_df.iloc[0]["breach_days"] == pytest.approx(15.0)
