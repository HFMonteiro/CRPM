from datetime import datetime, timedelta, timezone
import warnings

import pandas as pd
from pm4py.objects.log.obj import EventLog, Trace

from crpm.process_intelligence import (
    build_cohort_lenses,
    build_conformance_root_cause_summary,
    build_resource_perspective,
    build_time_series_monitoring,
)


def _trace(case_id: str, activities: list[str], start: datetime, *, step_days: int = 1) -> Trace:
    trace = Trace(attributes={"concept:name": case_id})
    for index, activity in enumerate(activities):
        trace.append({"concept:name": activity, "time:timestamp": start + timedelta(days=index * step_days)})
    return trace


def test_build_cohort_lenses_counts_dominant_rare_slow_deviation_and_rework() -> None:
    log = EventLog(
        [
            _trace("case-1", ["A", "B", "C"], datetime(2024, 1, 1)),
            _trace("case-2", ["A", "B", "C"], datetime(2024, 1, 2)),
            _trace("case-3", ["A", "A", "C"], datetime(2024, 1, 3)),
            _trace("case-4", ["A", "D", "C"], datetime(2024, 1, 4), step_days=10),
        ]
    )
    workflow = {"trace_profiles": pd.DataFrame([{"has_deviation": False}, {"has_deviation": True}, {"has_deviation": False}])}

    lenses = build_cohort_lenses(log, workflow=workflow, loop_rework_metrics={"rework_cases": 1}, rare_variant_pct=25)

    summary = lenses["summary"]
    assert summary["case_count"] == 4
    assert summary["dominant_path_cases"] == 2
    assert summary["rare_path_cases"] == 2
    assert summary["deviation_cases"] == 1
    assert summary["rework_cases"] == 1
    assert summary["slow_cases"] >= 1
    assert {row["label"] for row in lenses["rows"]} == {
        "All cases",
        "Dominant path",
        "Rare paths",
        "Deviation cases",
        "Slow cases",
        "Rework cases",
    }


def test_build_time_series_monitoring_uses_period_summaries_without_case_ids() -> None:
    log = EventLog(
        [
            _trace("secret-case-a", ["A", "B"], datetime(2024, 1, 1)),
            _trace("secret-case-b", ["A", "B", "C"], datetime(2024, 1, 8)),
        ]
    )

    monitoring = build_time_series_monitoring(log, freq="W")

    assert monitoring["summary"]["period_count"] == 2
    assert monitoring["summary"]["latest_case_count"] == 1
    assert "secret-case" not in str(monitoring)
    assert monitoring["rows"][0]["case_count"] == 1


def test_build_time_series_monitoring_normalizes_timezone_without_warning() -> None:
    log = EventLog([_trace("secret-case-a", ["A", "B"], datetime(2024, 1, 1, tzinfo=timezone.utc))])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        monitoring = build_time_series_monitoring(log, freq="W")

    assert monitoring["summary"]["period_count"] == 1


def test_build_cohort_lenses_prefers_workflow_trace_profiles_when_available() -> None:
    log = EventLog(
        [
            _trace("raw-secret-a", ["X"], datetime(2024, 1, 1)),
            _trace("raw-secret-b", ["Y"], datetime(2024, 1, 2)),
        ]
    )
    profiles = pd.DataFrame(
        [
            {"case_id": "case-001", "variant_signature": "A -> B", "throughput_days": 2.0, "has_deviation": False},
            {"case_id": "case-002", "variant_signature": "A -> B", "throughput_days": 3.0, "has_deviation": True},
            {"case_id": "case-003", "variant_signature": "A -> C", "throughput_days": 10.0, "has_deviation": True},
        ]
    )

    lenses = build_cohort_lenses(log, workflow={"trace_profiles": profiles}, loop_rework_metrics={"rework_cases": 1}, rare_variant_pct=40)

    assert lenses["summary"]["source"] == "workflow_trace_profiles"
    assert lenses["summary"]["case_count"] == 3
    assert lenses["summary"]["dominant_path_cases"] == 2
    assert lenses["summary"]["rare_path_cases"] == 1
    assert lenses["summary"]["deviation_cases"] == 2


def test_resource_perspective_aliases_resources_and_counts_handoffs() -> None:
    first = Trace(attributes={"concept:name": "raw-case-a"})
    first.append(
        {
            "concept:name": "Invitation_mail",
            "org:resource": "Nurse Maria",
            "time:timestamp": datetime(2024, 1, 1),
        }
    )
    first.append(
        {
            "concept:name": "FIT_return",
            "org:resource": "Lab Unit 7",
            "time:timestamp": datetime(2024, 1, 2),
        }
    )
    second = Trace(attributes={"concept:name": "raw-case-b"})
    second.append(
        {
            "concept:name": "Invitation_mail",
            "org:resource": "Nurse Maria",
            "time:timestamp": datetime(2024, 1, 3),
        }
    )
    log = EventLog([first, second])

    perspective = build_resource_perspective(log)

    assert perspective["summary"]["resource_count"] == 2
    assert perspective["summary"]["handoff_count"] == 1
    assert perspective["summary"]["event_with_resource_count"] == 3
    assert {row["resource_alias"] for row in perspective["top_resources"]} == {"resource-001", "resource-002"}
    assert "Nurse Maria" not in str(perspective)
    assert "Lab Unit 7" not in str(perspective)


def test_conformance_root_cause_summary_uses_workflow_without_case_ids() -> None:
    workflow = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Lab_rejection",
                    "display_name": "Lab rejection",
                    "cases": 4,
                    "conformance_bucket": "Model deviation",
                    "severity": "High",
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 10,
                    "conformance_bucket": "Conformant",
                    "severity": "Low",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "business_label": "Lab return → Admin review",
                    "frequency": 3,
                    "conformance_bucket": "Log deviation",
                    "severity": "Moderate",
                    "median_days": 6.0,
                    "trace_refs_summary": {"sample_case_ids": ["case-001"]},
                },
                {
                    "business_label": "Invitation → FIT mail",
                    "frequency": 10,
                    "conformance_bucket": "Conformant",
                    "severity": "Low",
                    "median_days": 1.0,
                },
            ]
        ),
    }
    trace_deviation_df = pd.DataFrame(
        [
            {
                "trace_index": 0,
                "trace_status": "Deviating",
                "missing_tokens": 2,
                "remaining_tokens": 1,
            },
            {
                "trace_index": 1,
                "trace_status": "Conformant",
                "missing_tokens": 0,
                "remaining_tokens": 0,
            },
        ]
    )

    summary = build_conformance_root_cause_summary(workflow, trace_deviation_df=trace_deviation_df)

    assert summary["summary"]["model_deviation_activity_count"] == 1
    assert summary["summary"]["log_deviation_transition_count"] == 1
    assert summary["summary"]["deviating_trace_count"] == 1
    assert summary["top_causes"][0]["label"] == "Lab rejection"
    assert "case-001" not in str(summary)
