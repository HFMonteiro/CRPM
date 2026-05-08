"""Screening-program helpers for cohorting, pathway monitoring, and conformance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, Iterable, Optional

import pandas as pd
from pm4py.objects.log.obj import EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils

STEP_ORDER = [
    "invitation",
    "fit_mail",
    "fit_return",
    "lab_result",
    "pcc_observation",
    "colonoscopy",
]

STEP_LABELS = {
    "invitation": "Invitation",
    "fit_mail": "FIT mail",
    "fit_return": "FIT return",
    "lab_result": "Lab result",
    "pcc_observation": "PCC observation",
    "colonoscopy": "Colonoscopy",
}

STEP_KEYWORDS = {
    "invitation": ("invitation", "invite"),
    "fit_mail": ("fit_mail", "fit mail", "send fit", "mail kit", "kit_sent"),
    "fit_return": ("fit_return", "fit return", "receive fit", "kit_return", "return fit"),
    "lab_result": ("lab_result", "lab return", "laboratory", "lab", "result"),
    "pcc_observation": ("pcc_observation", "pcc obs", "primary care", "consult", "observation", "pcc_fwd"),
    "colonoscopy": ("colonoscopy", "colonoscopy_center", "colonoscopy center"),
}

DISPLAY_TOKEN_MAP = {
    "fit": "FIT",
    "pcc": "PCC",
    "crc": "CRC",
    "pre": "PRE",
    "post": "POST",
}


@dataclass(frozen=True)
class PeriodDefinition:
    """Date range for incident cohort extraction."""

    label: str
    start: date
    end: date


def _step_match_score(activity_name: str, step: str, keywords: Iterable[str]) -> int:
    """Return a deterministic score for how well an activity matches a pathway step."""
    normalized = activity_name.lower().strip()
    if not normalized:
        return 0

    score = 0
    step_token = step.replace("_", " ")
    if normalized == step or normalized == step_token:
        score += 200

    compact = normalized.replace("_", " ").replace("-", " ")
    for keyword in keywords:
        keyword_text = str(keyword).lower().strip()
        if not keyword_text:
            continue
        if keyword_text == normalized or keyword_text == compact:
            score = max(score, 180 + len(keyword_text))
        elif keyword_text in normalized or keyword_text in compact:
            score = max(score, 80 + len(keyword_text))

    # Small deterministic tie-breakers so routing stays stable.
    if "result" in normalized and step == "lab_result":
        score += 10
    if "return" in normalized and step == "fit_return":
        score += 8
    if "observation" in normalized and step == "pcc_observation":
        score += 8
    if "colonoscopy" in normalized and step == "colonoscopy":
        score += 8
    return score


def classify_activity_steps(activity_names: Iterable[str]) -> Dict[str, Optional[str]]:
    """Classify raw activity names into canonical screening steps.

    Multiple raw activities may map to the same canonical step. This keeps
    conformance/business visuals from overstating deviations when operational
    labels differ but the pathway meaning is the same.
    """
    classified: Dict[str, Optional[str]] = {}
    for activity_name in sorted({str(name) for name in activity_names if name}):
        best_step: Optional[str] = None
        best_score = 0
        for step, keywords in STEP_KEYWORDS.items():
            score = _step_match_score(activity_name, step, keywords)
            if score > best_score:
                best_score = score
                best_step = step
        classified[activity_name] = best_step if best_score > 0 else None
    return classified


def infer_step_mapping(activity_names: Iterable[str]) -> Dict[str, Optional[str]]:
    """Infer one representative activity per pathway step for compatibility."""
    activity_lookup = classify_activity_steps(activity_names)
    inferred: Dict[str, Optional[str]] = {step: None for step in STEP_ORDER}

    for step in STEP_ORDER:
        candidates = sorted(name for name, candidate_step in activity_lookup.items() if candidate_step == step)
        inferred[step] = candidates[0] if candidates else None

    return inferred


def humanize_activity_label(activity_name: Any) -> str:
    """Normalize raw event names into a cleaner business-facing label."""
    text = str(activity_name or "").strip()
    if not text:
        return ""

    tokens = [token for token in re.split(r"[_\-\s]+", text) if token]
    if not tokens:
        return text

    normalized: list[str] = []
    for index, token in enumerate(tokens):
        key = token.lower()
        if key in DISPLAY_TOKEN_MAP:
            normalized.append(DISPLAY_TOKEN_MAP[key])
        elif token.isupper() and len(token) <= 5:
            normalized.append(token)
        else:
            lowered = token.lower()
            normalized.append(lowered[:1].upper() + lowered[1:] if index == 0 else lowered)
    return " ".join(normalized)


def describe_followup_window(followup_days: Optional[int]) -> str:
    """Return user-facing description of the active follow-up policy."""
    if followup_days is None:
        return "Full available follow-up"
    return f"{followup_days}-day follow-up window"


def get_trace_anchor_timestamp(trace: Trace, anchor_activity: Optional[str]) -> Optional[datetime]:
    """Get the timestamp used to anchor the screening episode."""
    for index, event in enumerate(trace):
        activity = event.get("concept:name")
        if anchor_activity is None or activity == anchor_activity or (index == 0 and not anchor_activity):
            timestamp = event.get("time:timestamp")
            if isinstance(timestamp, datetime):
                return timestamp
    return None


def clone_trace_with_window(
    trace: Trace,
    anchor_ts: datetime,
    followup_days: Optional[int] = None,
) -> Optional[Trace]:
    """Clone a trace and optionally censor events outside the follow-up window."""
    cutoff = anchor_ts + timedelta(days=followup_days) if followup_days is not None else None
    cloned = Trace(attributes=dict(getattr(trace, "attributes", {})))

    for event in trace:
        timestamp = event.get("time:timestamp")
        if cutoff is not None and isinstance(timestamp, datetime) and timestamp > cutoff:
            continue
        cloned.append(dict(event))

    return cloned if len(cloned) > 0 else None


def filter_log_by_incident_period(
    log: EventLog,
    anchor_activity: Optional[str],
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    followup_days: Optional[int] = None,
) -> EventLog:
    """Filter log to cases whose anchor event falls inside the period and horizon."""
    filtered = EventLog()

    for trace in log:
        anchor_ts = get_trace_anchor_timestamp(trace, anchor_activity)
        if anchor_ts is None:
            continue

        anchor_day = anchor_ts.date()
        if period_start and anchor_day < period_start:
            continue
        if period_end and anchor_day > period_end:
            continue

        cloned = clone_trace_with_window(trace, anchor_ts, followup_days=followup_days)
        if cloned is not None:
            filtered.append(cloned)

    return filtered


def split_log_by_periods(
    log: EventLog,
    anchor_activity: Optional[str],
    period_a: PeriodDefinition,
    period_b: PeriodDefinition,
    followup_days: Optional[int] = None,
) -> Dict[str, EventLog]:
    """Split a log into two incident cohorts using the same anchor policy."""
    return {
        period_a.label: filter_log_by_incident_period(
            log,
            anchor_activity=anchor_activity,
            period_start=period_a.start,
            period_end=period_a.end,
            followup_days=followup_days,
        ),
        period_b.label: filter_log_by_incident_period(
            log,
            anchor_activity=anchor_activity,
            period_start=period_b.start,
            period_end=period_b.end,
            followup_days=followup_days,
        ),
    }


def count_cases_with_activity(log: Optional[EventLog], activity_name: Optional[str]) -> int:
    """Count traces that contain the given activity at least once."""
    if log is None or not activity_name:
        return 0
    return sum(1 for trace in log if any(event.get("concept:name") == activity_name for event in trace))


def compute_screening_kpis(log: Optional[EventLog], step_map: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Compute manager-facing counts and rates for the mapped screening pathway."""
    total_cases = len(log) if log is not None else 0
    metrics: Dict[str, Any] = {
        "total_cases": total_cases,
        "followup_mode": None,
    }

    for step in STEP_ORDER:
        metrics[f"{step}_cases"] = count_cases_with_activity(log, step_map.get(step))

    denominator_key = "lab_result_cases" if step_map.get("lab_result") else "pcc_observation_cases"
    denominator_label = STEP_LABELS["lab_result"] if step_map.get("lab_result") else STEP_LABELS["pcc_observation"]
    denominator = metrics.get(denominator_key, 0)
    colonoscopy_cases = metrics.get("colonoscopy_cases", 0)

    metrics["colonoscopy_completion_denominator"] = denominator_label
    metrics["colonoscopy_completion_rate"] = colonoscopy_cases / denominator if denominator else None
    metrics["fit_return_rate"] = metrics["fit_return_cases"] / metrics["invitation_cases"] if metrics["invitation_cases"] else None
    return metrics


def build_normative_pathway_model(step_map: Dict[str, Optional[str]]) -> Optional[tuple[PetriNet, Marking, Marking, list[str]]]:
    """Build a sequential normative Petri net from mapped pathway steps."""
    ordered_steps: list[str] = []
    seen = set()
    for step in STEP_ORDER:
        activity = step_map.get(step)
        if activity and activity not in seen:
            ordered_steps.append(activity)
            seen.add(activity)

    if len(ordered_steps) < 2:
        return None

    net = PetriNet("normative_screening_pathway")
    places = []
    for index in range(len(ordered_steps) + 1):
        place = PetriNet.Place(f"p_{index}")
        net.places.add(place)
        places.append(place)

    for index, activity in enumerate(ordered_steps):
        transition = PetriNet.Transition(f"t_{index}", activity)
        net.transitions.add(transition)
        petri_utils.add_arc_from_to(places[index], transition, net)
        petri_utils.add_arc_from_to(transition, places[index + 1], net)

    initial_marking = Marking({places[0]: 1})
    final_marking = Marking({places[-1]: 1})
    return net, initial_marking, final_marking, ordered_steps


def summarize_transition_benchmarks(
    transition_stats: pd.DataFrame,
    benchmark_days: Dict[tuple[str, str], float],
) -> pd.DataFrame:
    """Attach benchmark and breach information to transition statistics."""
    if transition_stats.empty or not benchmark_days:
        return pd.DataFrame()

    rows = []
    indexed = transition_stats.set_index(["activity", "next_activity"], drop=False)

    for (activity, next_activity), benchmark in benchmark_days.items():
        if (activity, next_activity) not in indexed.index:
            rows.append(
                {
                    "transition": f"{activity} → {next_activity}",
                    "activity": activity,
                    "next_activity": next_activity,
                    "frequency": 0,
                    "median_duration_days": None,
                    "p90_duration_days": None,
                    "benchmark_days": benchmark,
                    "breach_days": None,
                    "benchmark_status": "Not observed",
                }
            )
            continue

        row = indexed.loc[(activity, next_activity)]
        median_days = float(row["median_duration_s"]) / 86400
        p90_days = float(row["p90_duration_s"]) / 86400
        breach_days = median_days - benchmark
        rows.append(
            {
                "transition": row["transition"],
                "activity": activity,
                "next_activity": next_activity,
                "frequency": int(row["frequency"]),
                "median_duration_days": median_days,
                "p90_duration_days": p90_days,
                "benchmark_days": benchmark,
                "breach_days": breach_days,
                "benchmark_status": "Breached" if breach_days > 0 else "Within benchmark",
            }
        )

    benchmark_df = pd.DataFrame(rows)
    return benchmark_df.sort_values(
        by=["benchmark_status", "breach_days", "median_duration_days"],
        ascending=[True, False, False],
        na_position="last",
    ).reset_index(drop=True)


__all__ = [
    "PeriodDefinition",
    "STEP_LABELS",
    "STEP_ORDER",
    "build_normative_pathway_model",
    "compute_screening_kpis",
    "classify_activity_steps",
    "count_cases_with_activity",
    "describe_followup_window",
    "filter_log_by_incident_period",
    "get_trace_anchor_timestamp",
    "humanize_activity_label",
    "infer_step_mapping",
    "split_log_by_periods",
    "summarize_transition_benchmarks",
]
