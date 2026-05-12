"""Workflow-intelligence summaries for CRPM dashboards and manifests."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Mapping

import pandas as pd
from pm4py.objects.log.obj import EventLog


def build_cohort_lenses(
    log: EventLog | None,
    *,
    workflow: Mapping[str, Any] | None = None,
    loop_rework_metrics: Mapping[str, Any] | None = None,
    rare_variant_pct: float = 5.0,
) -> dict[str, Any]:
    """Build reusable investigation lenses over the current cohort."""

    if log is None:
        return {"rows": [], "summary": {"case_count": 0}}
    workflow_profiles = _workflow_trace_profiles(workflow)
    if workflow_profiles is not None:
        return _cohort_lenses_from_profiles(
            workflow_profiles,
            loop_rework_metrics=loop_rework_metrics,
            rare_variant_pct=rare_variant_pct,
        )
    case_count = int(len(log))
    variants = _variant_counts(log)
    dominant_count = variants.most_common(1)[0][1] if variants else 0
    rare_case_count = sum(count for _, count in variants.items() if _pct(count, case_count) <= rare_variant_pct)
    slow_case_count, slow_threshold_days = _slow_cases(log)
    deviation_count = _workflow_deviation_count(workflow)
    rework_count = int((loop_rework_metrics or {}).get("rework_cases") or 0)
    rows = [
        _lens_row("All cases", case_count, case_count, "Baseline filtered cohort."),
        _lens_row("Dominant path", dominant_count, case_count, "Cases on the most common observed variant."),
        _lens_row("Rare paths", rare_case_count, case_count, f"Cases on variants at or below {rare_variant_pct:g}% share."),
        _lens_row("Deviation cases", deviation_count, case_count, "Cases marked by the workflow conformance payload."),
        _lens_row("Slow cases", slow_case_count, case_count, "Cases at or above the current P90 throughput threshold."),
        _lens_row("Rework cases", rework_count, case_count, "Cases with at least one repeated activity."),
    ]
    return {
        "rows": rows,
        "summary": {
            "case_count": case_count,
            "variant_count": len(variants),
            "dominant_path_cases": dominant_count,
            "rare_path_cases": rare_case_count,
            "deviation_cases": deviation_count,
            "slow_cases": slow_case_count,
            "slow_case_threshold_days": slow_threshold_days,
            "rework_cases": rework_count,
        },
    }


def build_time_series_monitoring(
    log: EventLog | None,
    *,
    freq: str = "W",
) -> dict[str, Any]:
    """Build compact time-series monitoring summaries without case identifiers."""

    if log is None:
        return {"rows": [], "summary": {"period_count": 0}}
    case_rows = []
    for trace in log:
        timestamps = [event.get("time:timestamp") for event in trace if isinstance(event.get("time:timestamp"), datetime)]
        if not timestamps:
            continue
        start = min(timestamps)
        end = max(timestamps)
        period_start = pd.Timestamp(start)
        if period_start.tzinfo is not None:
            period_start = period_start.tz_convert(None)
        case_rows.append(
            {
                "period": period_start.to_period(freq).start_time,
                "case_count": 1,
                "event_count": len(trace),
                "throughput_days": max((end - start).total_seconds() / 86400, 0.0),
            }
        )
    if not case_rows:
        return {"rows": [], "summary": {"period_count": 0}}
    frame = pd.DataFrame(case_rows)
    grouped = (
        frame.groupby("period", as_index=False)
        .agg(
            case_count=("case_count", "sum"),
            event_count=("event_count", "sum"),
            median_throughput_days=("throughput_days", "median"),
            p90_throughput_days=("throughput_days", lambda values: values.quantile(0.9)),
        )
        .sort_values("period", kind="stable")
    )
    rows = [
        {
            "period": row["period"].date().isoformat(),
            "case_count": int(row["case_count"]),
            "event_count": int(row["event_count"]),
            "median_throughput_days": round(float(row["median_throughput_days"]), 2),
            "p90_throughput_days": round(float(row["p90_throughput_days"]), 2),
        }
        for _, row in grouped.iterrows()
    ]
    first = rows[0]
    latest = rows[-1]
    return {
        "rows": rows[-12:],
        "summary": {
            "period_count": len(rows),
            "frequency": freq,
            "first_period": first["period"],
            "latest_period": latest["period"],
            "latest_case_count": latest["case_count"],
            "latest_event_count": latest["event_count"],
            "latest_median_throughput_days": latest["median_throughput_days"],
            "peak_case_count": max(row["case_count"] for row in rows),
            "case_volume_delta": latest["case_count"] - first["case_count"],
            "median_throughput_delta_days": round(
                latest["median_throughput_days"] - first["median_throughput_days"],
                2,
            ),
        },
    }


def build_resource_perspective(log: EventLog | None, *, top_n: int = 6) -> dict[str, Any]:
    """Summarize optional resource evidence with stable privacy-preserving aliases."""

    if log is None:
        return {"top_resources": [], "handoffs": [], "summary": {"resource_count": 0}}
    resource_counts: Counter[str] = Counter()
    activity_resource_counts: Counter[tuple[str, str]] = Counter()
    handoffs: Counter[tuple[str, str]] = Counter()
    event_with_resource_count = 0
    total_events = 0

    for trace in log:
        ordered_events = [
            event
            for event in sorted(
                enumerate(trace),
                key=lambda item: _event_sort_key(item[1], item[0]),
            )
            if event[1].get("concept:name")
        ]
        previous_resource: str | None = None
        for _, event in ordered_events:
            total_events += 1
            activity = str(event.get("concept:name") or "").strip()
            resource = _event_resource(event)
            if not resource:
                previous_resource = None
                continue
            event_with_resource_count += 1
            resource_counts[resource] += 1
            activity_resource_counts[(activity, resource)] += 1
            if previous_resource and previous_resource != resource:
                handoffs[(previous_resource, resource)] += 1
            previous_resource = resource

    aliases = {resource: f"resource-{index:03d}" for index, resource in enumerate(sorted(resource_counts), start=1)}
    top_resources = [
        {
            "resource_alias": aliases[resource],
            "event_count": int(count),
            "share_pct": _pct(int(count), event_with_resource_count),
        }
        for resource, count in resource_counts.most_common(top_n)
    ]
    top_handoffs = [
        {
            "source_resource_alias": aliases[source],
            "target_resource_alias": aliases[target],
            "handoff_count": int(count),
        }
        for (source, target), count in handoffs.most_common(top_n)
    ]
    top_activity_resource_pairs = [
        {
            "activity": activity,
            "resource_alias": aliases[resource],
            "event_count": int(count),
        }
        for (activity, resource), count in activity_resource_counts.most_common(top_n)
    ]
    return {
        "top_resources": top_resources,
        "handoffs": top_handoffs,
        "activity_resource_pairs": top_activity_resource_pairs,
        "summary": {
            "resource_count": int(len(resource_counts)),
            "event_with_resource_count": int(event_with_resource_count),
            "total_event_count": int(total_events),
            "resource_coverage_pct": _pct(event_with_resource_count, total_events),
            "handoff_count": int(sum(handoffs.values())),
            "activity_resource_pair_count": int(len(activity_resource_counts)),
        },
    }


def build_conformance_root_cause_summary(
    workflow: Mapping[str, Any] | None,
    *,
    trace_deviation_df: pd.DataFrame | None = None,
    top_n: int = 6,
) -> dict[str, Any]:
    """Build a compact conformance root-cause summary without case identifiers."""

    nodes = _workflow_frame(workflow, "nodes")
    edges = _workflow_frame(workflow, "edges")
    causes: list[dict[str, Any]] = []

    model_deviation_activity_count = 0
    if not nodes.empty:
        node_buckets = nodes.get("conformance_bucket", pd.Series(dtype=str)).astype(str)
        model_nodes = nodes[node_buckets.str.lower().eq("model deviation")]
        model_deviation_activity_count = int(len(model_nodes.index))
        for _, row in model_nodes.iterrows():
            cases = _safe_int(row.get("cases"))
            causes.append(
                {
                    "kind": "activity",
                    "label": _row_label(row, fallback_key="activity"),
                    "issue": "Model deviation activity",
                    "count": cases,
                    "severity": str(row.get("severity") or "Model deviation"),
                }
            )

    log_deviation_transition_count = 0
    high_delay_transition_count = 0
    if not edges.empty:
        edge_buckets = edges.get("conformance_bucket", pd.Series(dtype=str)).astype(str)
        log_edges = edges[edge_buckets.str.lower().eq("log deviation")]
        log_deviation_transition_count = int(len(log_edges.index))
        for _, row in log_edges.iterrows():
            causes.append(
                {
                    "kind": "transition",
                    "label": _row_label(row, fallback_key="edge_id"),
                    "issue": "Log deviation transition",
                    "count": _safe_int(row.get("frequency")),
                    "severity": str(row.get("severity") or "Log deviation"),
                }
            )

        severity = edges.get("severity", pd.Series(dtype=str)).astype(str).str.lower()
        slow_edges = edges[severity.isin({"high", "critical"})]
        high_delay_transition_count = int(len(slow_edges.index))
        for _, row in slow_edges.iterrows():
            causes.append(
                {
                    "kind": "transition",
                    "label": _row_label(row, fallback_key="edge_id"),
                    "issue": "High-delay transition",
                    "count": _safe_int(row.get("frequency")),
                    "severity": str(row.get("severity") or "High"),
                    "median_days": _safe_float(row.get("median_days")),
                }
            )

    deviating_trace_count = 0
    missing_token_count = 0
    remaining_token_count = 0
    if isinstance(trace_deviation_df, pd.DataFrame) and not trace_deviation_df.empty:
        status = trace_deviation_df.get("trace_status", pd.Series(dtype=str)).astype(str).str.lower()
        deviating_trace_count = int(status.ne("conformant").sum())
        missing_token_count = _series_sum(trace_deviation_df.get("missing_tokens"))
        remaining_token_count = _series_sum(trace_deviation_df.get("remaining_tokens"))

    top_causes = sorted(
        causes,
        key=lambda item: (_severity_rank(item.get("severity")), _safe_int(item.get("count"))),
        reverse=True,
    )[:top_n]
    return {
        "top_causes": top_causes,
        "summary": {
            "model_deviation_activity_count": model_deviation_activity_count,
            "log_deviation_transition_count": log_deviation_transition_count,
            "high_delay_transition_count": high_delay_transition_count,
            "deviating_trace_count": deviating_trace_count,
            "missing_token_count": missing_token_count,
            "remaining_token_count": remaining_token_count,
        },
    }


def _variant_counts(log: EventLog) -> Counter[tuple[str, ...]]:
    counter: Counter[tuple[str, ...]] = Counter()
    for trace in log:
        counter[tuple(str(event.get("concept:name") or "").strip() for event in trace)] += 1
    return counter


def _event_resource(event: Mapping[str, Any]) -> str | None:
    for key in ("org:resource", "resource", "Resource"):
        value = event.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _event_sort_key(event: Mapping[str, Any], index: int) -> tuple[int, Any, int]:
    timestamp = event.get("time:timestamp")
    if isinstance(timestamp, datetime):
        return (0, timestamp, index)
    return (1, index, index)


def _workflow_frame(workflow: Mapping[str, Any] | None, key: str) -> pd.DataFrame:
    if not isinstance(workflow, Mapping):
        return pd.DataFrame()
    value = workflow.get(key)
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _row_label(row: pd.Series, *, fallback_key: str) -> str:
    for key in ("business_label", "display_name", fallback_key):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return "N/A"


def _safe_int(value: Any) -> int:
    try:
        if value is None or pd.isna(value):
            return 0
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _series_sum(series: Any) -> int:
    if series is None:
        return 0
    return int(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def _severity_rank(value: Any) -> int:
    return {
        "critical": 5,
        "high": 4,
        "model deviation": 4,
        "log deviation": 3,
        "moderate": 2,
        "low": 1,
    }.get(str(value or "").strip().lower(), 0)


def _slow_cases(log: EventLog) -> tuple[int, float | None]:
    durations = []
    for trace in log:
        timestamps = [event.get("time:timestamp") for event in trace if isinstance(event.get("time:timestamp"), datetime)]
        if len(timestamps) < 2:
            continue
        durations.append(max((max(timestamps) - min(timestamps)).total_seconds() / 86400, 0.0))
    if not durations:
        return 0, None
    series = pd.Series(durations)
    threshold = float(series.quantile(0.9))
    return int((series >= threshold).sum()), round(threshold, 2)


def _workflow_deviation_count(workflow: Mapping[str, Any] | None) -> int:
    if not isinstance(workflow, Mapping):
        return 0
    profiles = workflow.get("trace_profiles")
    if not isinstance(profiles, pd.DataFrame) or profiles.empty or "has_deviation" not in profiles.columns:
        return 0
    return int(profiles["has_deviation"].astype(bool).sum())


def _workflow_trace_profiles(workflow: Mapping[str, Any] | None) -> pd.DataFrame | None:
    if not isinstance(workflow, Mapping):
        return None
    profiles = workflow.get("trace_profiles")
    if not isinstance(profiles, pd.DataFrame) or profiles.empty:
        return None
    if "variant_signature" not in profiles.columns:
        return None
    return profiles.copy()


def _cohort_lenses_from_profiles(
    profiles: pd.DataFrame,
    *,
    loop_rework_metrics: Mapping[str, Any] | None,
    rare_variant_pct: float,
) -> dict[str, Any]:
    case_count = int(len(profiles.index))
    variant_counts = profiles["variant_signature"].astype(str).value_counts()
    dominant_count = int(variant_counts.iloc[0]) if not variant_counts.empty else 0
    rare_variants = variant_counts[(variant_counts / max(case_count, 1) * 100) <= rare_variant_pct]
    rare_case_count = int(rare_variants.sum())
    throughput = pd.to_numeric(profiles.get("throughput_days", pd.Series(dtype=float)), errors="coerce").dropna()
    slow_threshold_days = round(float(throughput.quantile(0.9)), 2) if not throughput.empty else None
    slow_case_count = int((throughput >= slow_threshold_days).sum()) if slow_threshold_days is not None else 0
    deviation_count = int(profiles["has_deviation"].astype(bool).sum()) if "has_deviation" in profiles.columns else 0
    rework_count = int((loop_rework_metrics or {}).get("rework_cases") or 0)
    rows = [
        _lens_row("All cases", case_count, case_count, "Baseline workflow cohort."),
        _lens_row("Dominant path", dominant_count, case_count, "Cases on the most common workflow variant."),
        _lens_row("Rare paths", rare_case_count, case_count, f"Cases on workflow variants at or below {rare_variant_pct:g}% share."),
        _lens_row("Deviation cases", deviation_count, case_count, "Cases marked by the workflow conformance payload."),
        _lens_row("Slow cases", slow_case_count, case_count, "Cases at or above the current P90 throughput threshold."),
        _lens_row("Rework cases", rework_count, case_count, "Cases with at least one repeated activity."),
    ]
    return {
        "rows": rows,
        "summary": {
            "case_count": case_count,
            "variant_count": int(len(variant_counts.index)),
            "dominant_path_cases": dominant_count,
            "rare_path_cases": rare_case_count,
            "deviation_cases": deviation_count,
            "slow_cases": slow_case_count,
            "slow_case_threshold_days": slow_threshold_days,
            "rework_cases": rework_count,
            "source": "workflow_trace_profiles",
        },
    }


def _lens_row(label: str, count: int, denominator: int, note: str) -> dict[str, Any]:
    return {
        "label": label,
        "count": int(count),
        "denominator": int(denominator),
        "share_pct": _pct(count, denominator),
        "note": note,
    }


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)
