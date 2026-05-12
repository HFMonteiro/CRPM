from datetime import datetime, timezone

from pm4py.objects.log.obj import EventLog, Trace

from crpm.log_quality import compute_event_log_quality, quality_bar_rows


def test_event_log_quality_detects_missing_fields_duplicates_and_timestamp_issues() -> None:
    trace = Trace(attributes={})
    trace.append({"concept:name": "Invitation", "time:timestamp": datetime(2024, 1, 2), "org:resource": "team-a"})
    trace.append({"concept:name": "Invitation", "time:timestamp": datetime(2024, 1, 2), "org:resource": "team-a"})
    trace.append({"concept:name": "", "time:timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc)})
    trace.append({"concept:name": "FIT mail"})
    log = EventLog([trace])

    report = compute_event_log_quality(log)
    summary = report["summary"]

    assert summary["quality_status"] == "critical"
    assert summary["missing_case_id_count"] == 1
    assert summary["missing_activity_count"] == 1
    assert summary["missing_timestamp_count"] == 1
    assert summary["missing_resource_count"] == 2
    assert summary["duplicate_event_count"] == 1
    assert summary["negative_gap_count"] == 1
    assert summary["zero_gap_count"] == 1
    assert summary["timezone_mode"] == "mixed"
    assert all("patient" not in str(group).lower() for group in report["duplicate_groups"])


def test_quality_bar_rows_are_percentage_safe() -> None:
    report = {
        "summary": {
            "events": 10,
            "required_field_completeness_pct": 100.0,
            "duplicate_event_count": 1,
            "negative_gap_count": 0,
        }
    }

    rows = quality_bar_rows(report)

    assert rows[0]["label"] == "Required fields"
    assert rows[0]["value"] == 100.0
    assert rows[1]["value"] == 90.0


def test_semantic_profiles_are_diagnostic_not_blocking() -> None:
    trace = Trace(attributes={"concept:name": "case-1"})
    trace.append({"concept:name": "A", "time:timestamp": datetime(2024, 1, 1)})
    trace.append({"concept:name": "B", "time:timestamp": datetime(2024, 1, 2)})
    log = EventLog([trace])

    generic = compute_event_log_quality(log)
    healthcare = compute_event_log_quality(log, semantic_profile="healthcare")
    ccr = compute_event_log_quality(log, semantic_profile="ccr_screening")
    unknown = compute_event_log_quality(log, semantic_profile="unknown")

    assert generic["summary"]["semantic_profile"] == "generic"
    assert generic["summary"]["semantic_status"] == "ok"
    assert healthcare["summary"]["semantic_status"] == "warning"
    assert ccr["semantic_validation"]["missing_expected_activities"]
    assert unknown["summary"]["semantic_profile"] == "generic"


def test_timestamp_policy_reports_granularity_and_same_timestamp_bursts() -> None:
    trace = Trace(attributes={"concept:name": "case-1"})
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": datetime(2024, 1, 1)})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": datetime(2024, 1, 1)})
    trace.append({"concept:name": "FIT_return", "time:timestamp": datetime(2024, 1, 2, 10, 0, 0, 123)})
    log = EventLog([trace])

    report = compute_event_log_quality(log, semantic_profile="ccr_screening")

    assert report["summary"]["granularity_mode"] == "mixed"
    assert report["summary"]["same_timestamp_burst_case_count"] == 1
    assert report["timestamp_policy"]["normalization_recommendation"]
