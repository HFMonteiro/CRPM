"""Shared denominator definitions for CRPM analysis outputs."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

import pandas as pd
from pm4py.objects.log.obj import EventLog


def build_denominator_registry(
    log: EventLog | None,
    *,
    workflow: Mapping[str, Any] | None = None,
    evaluation_log: EventLog | None = None,
) -> dict[str, Any]:
    """Return one compact denominator registry for the current analysis run."""

    source_log = log or EventLog()
    evaluation = evaluation_log or source_log
    workflow_summary = _workflow_summary(workflow)
    return {
        "case_count": int(len(source_log)),
        "event_count": int(sum(len(trace) for trace in source_log)),
        "evaluation_case_count": int(len(evaluation)),
        "evaluation_event_count": int(sum(len(trace) for trace in evaluation)),
        "activity_count": len(_activity_counter(source_log)),
        "evaluation_activity_count": len(_activity_counter(evaluation)),
        "variant_count": len(_variant_counter(source_log)),
        "transition_count": _transition_count(source_log),
        "evaluation_transition_count": _transition_count(evaluation),
        "visible_case_count": _summary_int(workflow_summary, "visible_case_count", len(evaluation)),
        "excluded_case_count": _summary_int(workflow_summary, "excluded_case_count", 0),
        "path_denominator": _summary_int(workflow_summary, "path_denominator", len(evaluation)),
        "activity_denominator": _summary_int(
            workflow_summary,
            "activity_denominator",
            int(sum(len(trace) for trace in evaluation)),
        ),
        "transition_denominator": _summary_int(
            workflow_summary,
            "transition_denominator",
            _transition_count(evaluation),
        ),
        "definitions": {
            "case_count": "Cases in the filtered cohort used for run-level summaries.",
            "event_count": "Events in the filtered cohort before any train/test evaluation split.",
            "evaluation_case_count": "Cases used for conformance and workflow evaluation.",
            "activity_count": "Distinct non-empty activity labels in the filtered cohort.",
            "variant_count": "Distinct activity sequences in the filtered cohort.",
            "path_denominator": "Case denominator used for path and transition share calculations.",
            "activity_denominator": "Event-occurrence denominator used for activity share calculations.",
            "excluded_case_count": "Cases removed from the rendered workflow surface after filtering or visibility rules.",
        },
    }


def denominator_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return display-ready denominator rows without exposing identifiers."""

    labels = (
        ("Cases", "case_count"),
        ("Events", "event_count"),
        ("Activities", "activity_count"),
        ("Variants", "variant_count"),
        ("Evaluation cases", "evaluation_case_count"),
        ("Path denominator", "path_denominator"),
        ("Activity denominator", "activity_denominator"),
        ("Excluded cases", "excluded_case_count"),
    )
    return [{"label": label, "value": int(registry.get(key) or 0), "key": key} for label, key in labels]


def build_preprocessing_impact(
    *,
    source_log: EventLog | None,
    filtered_log: EventLog | None,
    evaluation_log: EventLog | None = None,
) -> dict[str, Any]:
    """Summarize how run filters and evaluation split changed the event-log scope."""

    source_cases, source_events = _log_size(source_log)
    filtered_cases, filtered_events = _log_size(filtered_log)
    evaluation_cases, evaluation_events = _log_size(evaluation_log or filtered_log)
    return {
        "source_cases": source_cases,
        "source_events": source_events,
        "filtered_cases": filtered_cases,
        "filtered_events": filtered_events,
        "evaluation_cases": evaluation_cases,
        "evaluation_events": evaluation_events,
        "excluded_by_filter_cases": max(source_cases - filtered_cases, 0),
        "excluded_by_filter_events": max(source_events - filtered_events, 0),
        "held_out_cases": max(filtered_cases - evaluation_cases, 0),
        "held_out_events": max(filtered_events - evaluation_events, 0),
        "filter_case_retention_pct": _retention_pct(filtered_cases, source_cases),
        "filter_event_retention_pct": _retention_pct(filtered_events, source_events),
        "evaluation_case_retention_pct": _retention_pct(evaluation_cases, filtered_cases),
        "evaluation_event_retention_pct": _retention_pct(evaluation_events, filtered_events),
    }


def _activity_counter(log: EventLog) -> Counter[str]:
    counter: Counter[str] = Counter()
    for trace in log:
        for event in trace:
            activity = str(event.get("concept:name") or "").strip()
            if activity:
                counter[activity] += 1
    return counter


def _variant_counter(log: EventLog) -> Counter[tuple[str, ...]]:
    counter: Counter[tuple[str, ...]] = Counter()
    for trace in log:
        variant = tuple(str(event.get("concept:name") or "").strip() for event in trace)
        counter[variant] += 1
    return counter


def _transition_count(log: EventLog) -> int:
    return int(sum(max(len(trace) - 1, 0) for trace in log))


def _log_size(log: EventLog | None) -> tuple[int, int]:
    if log is None:
        return 0, 0
    return int(len(log)), int(sum(len(trace) for trace in log))


def _retention_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _workflow_summary(workflow: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(workflow, Mapping):
        return {}
    summary = workflow.get("summary", {})
    return summary if isinstance(summary, Mapping) else {}


def _summary_int(summary: Mapping[str, Any], key: str, fallback: int) -> int:
    try:
        value = summary.get(key, fallback)
        if value is None or pd.isna(value):
            return int(fallback)
        return int(round(float(value)))
    except Exception:
        return int(fallback)
