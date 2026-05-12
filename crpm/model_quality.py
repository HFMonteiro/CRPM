"""Model quality and process-behaviour metrics for CRPM analytics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

import pandas as pd
from pm4py.objects.log.obj import EventLog


def compute_loop_rework_metrics(log: EventLog | None) -> dict[str, Any]:
    """Compute self-loop, loop, and rework metrics from activity sequences."""

    if log is None:
        return _empty_loop_metrics()
    case_count = int(len(log))
    self_loop_cases = 0
    loop_cases = 0
    rework_cases = 0
    self_loop_events = 0
    rework_activity_counter: Counter[str] = Counter()
    for trace in log:
        activities = [str(event.get("concept:name") or "").strip() for event in trace if str(event.get("concept:name") or "").strip()]
        if any(source == target for source, target in zip(activities, activities[1:])):
            self_loop_cases += 1
            self_loop_events += sum(1 for source, target in zip(activities, activities[1:]) if source == target)
        repeated = [activity for activity, count in Counter(activities).items() if count > 1]
        if repeated:
            rework_cases += 1
            loop_cases += 1
            for activity in repeated:
                rework_activity_counter[activity] += Counter(activities)[activity] - 1
    return {
        "case_count": case_count,
        "self_loop_cases": self_loop_cases,
        "loop_cases": loop_cases,
        "rework_cases": rework_cases,
        "self_loop_events": self_loop_events,
        "self_loop_cases_pct": _pct(self_loop_cases, case_count),
        "loop_cases_pct": _pct(loop_cases, case_count),
        "rework_cases_pct": _pct(rework_cases, case_count),
        "top_rework_activities": [
            {"activity": activity, "extra_occurrences": int(count)} for activity, count in rework_activity_counter.most_common(10)
        ],
    }


def build_model_quality_matrix(comparison_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return a stable model quality matrix from comparison results."""

    if not isinstance(comparison_df, pd.DataFrame) or comparison_df.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in comparison_df.iterrows():
        fitness = _score(row.get("alignment_fitness"))
        precision = _score(row.get("precision"))
        simplicity = _simplicity_score(row)
        generalization_proxy = _generalization_proxy(row)
        quality_score = round(((fitness * 0.35) + (precision * 0.35) + (simplicity * 0.15) + (generalization_proxy * 0.15)), 4)
        rows.append(
            {
                "model_name": str(row.get("model_name") or "N/A"),
                "algorithm": str(row.get("algorithm") or "N/A"),
                "variant": str(row.get("variant") or "N/A"),
                "fitness": fitness,
                "precision": precision,
                "simplicity_proxy": simplicity,
                "generalization_proxy": generalization_proxy,
                "quality_score": quality_score,
                "quality_band": _quality_band(quality_score),
                "transitions": _int(row.get("num_transitions")),
                "places": _int(row.get("num_places")),
                "arcs": _int(row.get("num_arcs")),
                "complexity_score": _float(row.get("complexity_score")),
            }
        )
    return sorted(rows, key=lambda item: (-float(item["quality_score"]), item["model_name"]))


def summarize_model_quality(matrix: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize the quality matrix for run-level panels and manifests."""

    if not matrix:
        return {}
    best = matrix[0]
    return {
        "best_model": best.get("model_name"),
        "best_quality_score": best.get("quality_score"),
        "best_quality_band": best.get("quality_band"),
        "candidate_count": len(matrix),
        "high_quality_count": sum(1 for row in matrix if row.get("quality_band") in {"Excellent", "Good"}),
    }


def _simplicity_score(row: Mapping[str, Any]) -> float:
    transitions = max(_int(row.get("num_transitions")), 0)
    places = max(_int(row.get("num_places")), 0)
    arcs = max(_int(row.get("num_arcs")), 0)
    structure = transitions + places + arcs
    if structure <= 0:
        return 0.0
    return round(1 / (1 + (structure / 100)), 4)


def _generalization_proxy(row: Mapping[str, Any]) -> float:
    fitness = _score(row.get("alignment_fitness"))
    precision = _score(row.get("precision"))
    if fitness == 0 and precision == 0:
        return 0.0
    penalty = abs(fitness - precision) * 0.5
    return round(max(min(((fitness + precision) / 2) - penalty, 1.0), 0.0), 4)


def _quality_band(score: float) -> str:
    if score >= 0.85:
        return "Excellent"
    if score >= 0.7:
        return "Good"
    if score >= 0.5:
        return "Watch"
    return "Weak"


def _score(value: Any) -> float:
    number = _float(value)
    if number is None:
        return 0.0
    if number > 1.0:
        number /= 100.0
    return round(max(min(number, 1.0), 0.0), 4)


def _float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _int(value: Any) -> int:
    number = _float(value)
    return int(round(number)) if number is not None else 0


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _empty_loop_metrics() -> dict[str, Any]:
    return {
        "case_count": 0,
        "self_loop_cases": 0,
        "loop_cases": 0,
        "rework_cases": 0,
        "self_loop_events": 0,
        "self_loop_cases_pct": 0.0,
        "loop_cases_pct": 0.0,
        "rework_cases_pct": 0.0,
        "top_rework_activities": [],
    }
