"""Event-log quality diagnostics for accepted CRPM logs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from pm4py.objects.log.obj import EventLog


LARGE_GAP_SECONDS = 90 * 24 * 60 * 60
SEMANTIC_PROFILES = {"generic", "healthcare", "ccr_screening"}
CCR_EXPECTED_ACTIVITIES = {
    "Invitation_mail",
    "FIT_mail",
    "FIT_return",
    "Lab_return",
    "Lab_result",
    "PCC_observation",
}
HEALTHCARE_TERMS = ("patient", "screen", "lab", "fit", "colonoscopy", "pcc", "clinic", "diagnosis")


def compute_event_log_quality(log: EventLog | None, *, semantic_profile: str = "generic") -> dict[str, Any]:
    """Compute privacy-preserving quality diagnostics for a PM4Py EventLog."""

    if log is None:
        return _empty_report()
    if semantic_profile not in SEMANTIC_PROFILES:
        semantic_profile = "generic"

    rows = _flatten_log(log)
    events = len(rows)
    cases = len(log)
    completeness = _completeness(rows, cases=cases, events=events)
    duplicate_groups = _duplicate_groups(rows)
    gaps = _timestamp_gaps(rows)
    timezone_profile = _timezone_profile(rows)
    granularity = _granularity_mode(rows)
    activities = _activity_set(rows)
    semantic = _semantic_validation(activities, profile=semantic_profile)
    timestamp_policy = _timestamp_policy_summary(
        timezone_profile=timezone_profile,
        granularity=granularity,
        gaps=gaps,
    )

    missing_required = (
        completeness["missing_case_id_count"] + completeness["missing_activity_count"] + completeness["missing_timestamp_count"]
    )
    required_field_total = max(cases + (events * 2), 1)
    completeness_pct = round((1 - (missing_required / required_field_total)) * 100, 2)
    duplicate_event_count = int(sum(group["duplicate_count"] - 1 for group in duplicate_groups))
    negative_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "negative")
    zero_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "zero")
    large_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "large")
    issues = _issues(
        completeness=completeness,
        duplicate_event_count=duplicate_event_count,
        negative_gap_count=negative_gap_count,
        timezone_mode=timezone_profile["timezone_mode"],
    )
    issues.extend(semantic["issues"])

    status = "ok"
    if any(issue["severity"] == "critical" for issue in issues):
        status = "critical"
    elif issues:
        status = "warning"

    summary = {
        "cases": cases,
        "events": events,
        "quality_status": status,
        "required_field_completeness_pct": completeness_pct,
        "missing_case_id_count": completeness["missing_case_id_count"],
        "missing_activity_count": completeness["missing_activity_count"],
        "missing_timestamp_count": completeness["missing_timestamp_count"],
        "missing_resource_count": completeness["missing_resource_count"],
        "duplicate_event_count": duplicate_event_count,
        "duplicate_event_group_count": len(duplicate_groups),
        "negative_gap_count": negative_gap_count,
        "zero_gap_count": zero_gap_count,
        "large_gap_count": large_gap_count,
        "one_event_case_count": sum(1 for trace in log if len(trace) == 1),
        "empty_case_count": sum(1 for trace in log if len(trace) == 0),
        "timezone_mode": timezone_profile["timezone_mode"],
        "timezone_naive_count": timezone_profile["naive_count"],
        "timezone_aware_count": timezone_profile["aware_count"],
        "granularity_mode": granularity,
        "semantic_profile": semantic_profile,
        "semantic_status": semantic["status"],
        "activity_vocabulary_count": len(activities),
        "same_timestamp_burst_case_count": _same_timestamp_burst_case_count(rows),
        "ultra_long_trace_count": sum(1 for trace in log if len(trace) > 50),
    }
    return {
        "summary": summary,
        "issues": issues,
        "completeness": completeness["fields"],
        "duplicate_groups": duplicate_groups[:25],
        "timestamp_gaps": gaps[:50],
        "timestamp_policy": timestamp_policy,
        "semantic_validation": semantic,
    }


def quality_bar_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact UI rows for event-log quality dimensions."""

    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    completeness = float(summary.get("required_field_completeness_pct") or 0.0)
    duplicate_events = int(summary.get("duplicate_event_count") or 0)
    negative_gaps = int(summary.get("negative_gap_count") or 0)
    total_events = max(int(summary.get("events") or 0), 1)
    return [
        {"label": "Required fields", "value": completeness, "tone": _quality_tone(completeness)},
        {
            "label": "Duplicate-free events",
            "value": max(0.0, 100.0 - ((duplicate_events / total_events) * 100)),
            "tone": "success" if duplicate_events == 0 else "watch",
        },
        {
            "label": "Ordered traces",
            "value": max(0.0, 100.0 - ((negative_gaps / total_events) * 100)),
            "tone": "success" if negative_gaps == 0 else "watch",
        },
        {
            "label": "Semantic fit",
            "value": _semantic_fit_pct(summary.get("semantic_status")),
            "tone": "success" if str(summary.get("semantic_status")) == "ok" else "watch",
        },
    ]


def _flatten_log(log: EventLog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trace_index, trace in enumerate(log, start=1):
        case_id = trace.attributes.get("concept:name") or trace.attributes.get("case_id")
        case_missing = _is_blank(case_id)
        case_alias = f"case-{trace_index:03d}"
        for event_index, event in enumerate(trace, start=1):
            timestamp = event.get("time:timestamp")
            rows.append(
                {
                    "case_alias": case_alias,
                    "case_missing": case_missing,
                    "event_index": event_index,
                    "activity": event.get("concept:name"),
                    "timestamp": timestamp,
                    "resource": event.get("org:resource"),
                }
            )
    return rows


def _completeness(rows: list[dict[str, Any]], *, cases: int, events: int) -> dict[str, Any]:
    missing_case_ids = len({row["case_alias"] for row in rows if row["case_missing"]})
    missing_activity = sum(1 for row in rows if _is_blank(row.get("activity")))
    missing_timestamp = sum(1 for row in rows if not isinstance(row.get("timestamp"), datetime))
    missing_resource = sum(1 for row in rows if _is_blank(row.get("resource")))
    fields = [
        _field_row("Case ID", "concept:name", cases - missing_case_ids, missing_case_ids, cases),
        _field_row("Activity", "concept:name", events - missing_activity, missing_activity, events),
        _field_row("Timestamp", "time:timestamp", events - missing_timestamp, missing_timestamp, events),
        _field_row("Resource", "org:resource", events - missing_resource, missing_resource, events, optional=True),
    ]
    return {
        "missing_case_id_count": missing_case_ids,
        "missing_activity_count": missing_activity,
        "missing_timestamp_count": missing_timestamp,
        "missing_resource_count": missing_resource,
        "fields": fields,
    }


def _field_row(
    field: str,
    xes_key: str,
    present_count: int,
    missing_count: int,
    total: int,
    *,
    optional: bool = False,
) -> dict[str, Any]:
    missing_pct = round((missing_count / max(total, 1)) * 100, 2)
    if missing_count == 0:
        severity = "ok"
    elif optional:
        severity = "warning"
    else:
        severity = "critical"
    return {
        "field": field,
        "xes_key": xes_key,
        "present_count": max(int(present_count), 0),
        "missing_count": int(missing_count),
        "missing_pct": missing_pct,
        "severity": severity,
    }


def _duplicate_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        timestamp = row.get("timestamp")
        timestamp_label = timestamp.isoformat() if isinstance(timestamp, datetime) else ""
        counter[
            (
                str(row.get("case_alias") or ""),
                str(row.get("activity") or ""),
                timestamp_label,
                str(row.get("resource") or ""),
            )
        ] += 1
    groups = []
    for (case_alias, activity, timestamp, resource), count in counter.items():
        if count <= 1:
            continue
        groups.append(
            {
                "case_alias": case_alias,
                "activity": activity or "N/A",
                "timestamp": timestamp or "N/A",
                "resource": resource or "N/A",
                "duplicate_count": int(count),
            }
        )
    return sorted(groups, key=lambda item: (-item["duplicate_count"], item["case_alias"], item["activity"]))


def _timestamp_gaps(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row["case_alias"]), []).append(row)
    for case_alias, case_rows in by_case.items():
        ordered = sorted(case_rows, key=lambda item: int(item["event_index"]))
        for previous, current in zip(ordered, ordered[1:]):
            previous_ts = previous.get("timestamp")
            current_ts = current.get("timestamp")
            if not isinstance(previous_ts, datetime) or not isinstance(current_ts, datetime):
                continue
            previous_ts = _gap_timestamp(previous_ts)
            current_ts = _gap_timestamp(current_ts)
            seconds = (current_ts - previous_ts).total_seconds()
            if seconds < 0:
                kind = "negative"
            elif seconds == 0:
                kind = "zero"
            elif seconds > LARGE_GAP_SECONDS:
                kind = "large"
            else:
                kind = "normal"
            if kind == "normal":
                continue
            gaps.append(
                {
                    "case_alias": case_alias,
                    "from_event_index": int(previous["event_index"]),
                    "to_event_index": int(current["event_index"]),
                    "from_activity": str(previous.get("activity") or "N/A"),
                    "to_activity": str(current.get("activity") or "N/A"),
                    "gap_seconds": float(seconds),
                    "gap_kind": kind,
                }
            )
    return gaps


def _timestamp_policy_summary(
    *,
    timezone_profile: dict[str, Any],
    granularity: str,
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    negative_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "negative")
    zero_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "zero")
    large_gap_count = sum(1 for gap in gaps if gap["gap_kind"] == "large")
    return {
        "timezone_mode": timezone_profile["timezone_mode"],
        "granularity_mode": granularity,
        "ordering_policy": "trace encounter order with timestamp diagnostics",
        "normalization_recommendation": _timestamp_recommendation(timezone_profile["timezone_mode"], granularity),
        "negative_gap_count": negative_gap_count,
        "zero_gap_count": zero_gap_count,
        "large_gap_count": large_gap_count,
    }


def _gap_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _timezone_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    naive_count = 0
    aware_count = 0
    for row in rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
            naive_count += 1
        else:
            aware_count += 1
    if naive_count and aware_count:
        mode = "mixed"
    elif aware_count:
        mode = "aware"
    elif naive_count:
        mode = "naive"
    else:
        mode = "none"
    return {"timezone_mode": mode, "naive_count": naive_count, "aware_count": aware_count}


def _granularity_mode(rows: list[dict[str, Any]]) -> str:
    buckets: set[str] = set()
    for row in rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        if timestamp.hour == timestamp.minute == timestamp.second == timestamp.microsecond == 0:
            buckets.add("date")
        elif timestamp.microsecond:
            buckets.add("microsecond")
        else:
            buckets.add("second")
    if not buckets:
        return "unknown"
    if len(buckets) == 1:
        return next(iter(buckets))
    return "mixed"


def _activity_set(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("activity") or "").strip() for row in rows if str(row.get("activity") or "").strip()}


def _semantic_validation(activities: set[str], *, profile: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    matched_terms = [activity for activity in activities if any(term in activity.lower() for term in HEALTHCARE_TERMS)]
    missing_expected = sorted(CCR_EXPECTED_ACTIVITIES.difference(activities)) if profile == "ccr_screening" else []

    if profile in {"healthcare", "ccr_screening"} and not matched_terms:
        issues.append({"severity": "warning", "message": "Activity labels do not look healthcare-specific."})
    if profile == "ccr_screening" and missing_expected:
        issues.append(
            {
                "severity": "warning",
                "message": "CCR screening profile is missing expected pathway activities.",
            }
        )

    return {
        "profile": profile,
        "status": "warning" if issues else "ok",
        "matched_healthcare_activity_count": len(matched_terms),
        "missing_expected_activities": missing_expected,
        "issues": issues,
    }


def _same_timestamp_burst_case_count(rows: list[dict[str, Any]]) -> int:
    by_case_timestamp: set[tuple[str, str]] = set()
    duplicate_case_timestamp: set[str] = set()
    for row in rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        key = (str(row["case_alias"]), timestamp.isoformat())
        if key in by_case_timestamp:
            duplicate_case_timestamp.add(str(row["case_alias"]))
        by_case_timestamp.add(key)
    return len(duplicate_case_timestamp)


def _timestamp_recommendation(timezone_mode: str, granularity: str) -> str:
    if timezone_mode == "mixed":
        return "Normalize all timestamps to one timezone policy before interpretation."
    if timezone_mode == "naive":
        return "Document the assumed local timezone or normalize before cross-site comparisons."
    if granularity == "mixed":
        return "Review mixed timestamp granularity before comparing wait times."
    return "Timestamp policy is internally consistent for this run."


def _semantic_fit_pct(status: Any) -> float:
    return 100.0 if str(status or "").lower() == "ok" else 60.0


def _issues(
    *,
    completeness: dict[str, Any],
    duplicate_event_count: int,
    negative_gap_count: int,
    timezone_mode: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if completeness["missing_case_id_count"]:
        issues.append({"severity": "critical", "message": "Some traces do not have a case identifier."})
    if completeness["missing_activity_count"]:
        issues.append({"severity": "critical", "message": "Some events do not have an activity label."})
    if completeness["missing_timestamp_count"]:
        issues.append({"severity": "critical", "message": "Some events do not have a valid timestamp."})
    if duplicate_event_count:
        issues.append({"severity": "warning", "message": "Potential duplicate events were detected."})
    if negative_gap_count:
        issues.append({"severity": "warning", "message": "Some traces contain decreasing timestamps."})
    if timezone_mode == "mixed":
        issues.append({"severity": "warning", "message": "The log mixes timezone-aware and naive timestamps."})
    return issues


def _quality_tone(value: float) -> str:
    if value >= 99.9:
        return "success"
    if value >= 95.0:
        return "watch"
    return "danger"


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _empty_report() -> dict[str, Any]:
    return {
        "summary": {
            "cases": 0,
            "events": 0,
            "quality_status": "critical",
            "required_field_completeness_pct": 0.0,
        },
        "issues": [{"severity": "critical", "message": "No event log is available."}],
        "completeness": [],
        "duplicate_groups": [],
        "timestamp_gaps": [],
    }
