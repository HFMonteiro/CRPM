"""Performance analytics and bottleneck detection for process mining.

This module provides functions for:
- Activity-level statistics (duration, frequency)
- Transition-level performance analysis
- Bottleneck detection
- Sojourn time analysis
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

import pandas as pd
import numpy as np
from pm4py.objects.log.obj import EventLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Activity Statistics
# ---------------------------------------------------------------------------


def compute_activity_statistics(log: EventLog) -> pd.DataFrame:
    """Compute frequency and duration statistics for each activity.

    Args:
        log: Event log to analyze

    Returns:
        DataFrame with columns: activity, frequency, min_duration, avg_duration,
        median_duration, max_duration, p90_duration, std_duration, cv
    """
    activity_data = []

    # Group events by activity
    activity_events: Dict[str, List[Dict[str, Any]]] = {}

    for trace in log:
        for i, event in enumerate(trace):
            activity = event.get("concept:name", "Unknown")
            timestamp = event.get("time:timestamp")

            if activity not in activity_events:
                activity_events[activity] = []

            # Store event with trace context for duration calculation
            activity_events[activity].append({
                "timestamp": timestamp,
                "trace_id": id(trace),
                "event_index": i,
                "trace": trace
            })

    # Compute statistics for each activity
    for activity, events in activity_events.items():
        frequency = len(events)

        # Calculate durations (time between consecutive events in same trace)
        durations = []
        for event_info in events:
            trace = event_info["trace"]
            idx = event_info["event_index"]

            # Duration from this event to next event in same trace
            if idx + 1 < len(trace):
                current_ts = trace[idx].get("time:timestamp")
                next_ts = trace[idx + 1].get("time:timestamp")

                if isinstance(current_ts, datetime) and isinstance(next_ts, datetime):
                    duration = (next_ts - current_ts).total_seconds()
                    if duration >= 0:  # Filter out negative durations (data quality)
                        durations.append(duration)

        # Compute statistics
        if durations:
            durations_array = np.array(durations)
            min_dur = float(np.min(durations_array))
            avg_dur = float(np.mean(durations_array))
            median_dur = float(np.median(durations_array))
            max_dur = float(np.max(durations_array))
            p90_dur = float(np.percentile(durations_array, 90))
            std_dur = float(np.std(durations_array))
            cv = std_dur / avg_dur if avg_dur > 0 else 0
        else:
            min_dur = avg_dur = median_dur = max_dur = p90_dur = std_dur = cv = None

        activity_data.append({
            "activity": activity,
            "frequency": frequency,
            "min_duration_s": min_dur,
            "avg_duration_s": avg_dur,
            "median_duration_s": median_dur,
            "max_duration_s": max_dur,
            "p90_duration_s": p90_dur,
            "std_duration_s": std_dur,
            "coefficient_of_variation": cv
        })

    df = pd.DataFrame(activity_data)
    df = df.sort_values("frequency", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Transition Statistics & Bottleneck Detection
# ---------------------------------------------------------------------------


def compute_transition_statistics(
    log: EventLog,
    model_transitions: Optional[List[Tuple[str, str]]] = None,
    min_occurrences: int = 3
) -> pd.DataFrame:
    """Compute statistics for activity transitions (activity → next_activity).

    Args:
        log: Event log to analyze
        model_transitions: Optional list of (activity, next_activity) pairs from model.
                          If provided, only compute stats for these transitions.
        min_occurrences: Minimum number of occurrences to include a transition

    Returns:
        DataFrame with transition statistics including median, p90, frequency
    """
    transition_data: Dict[Tuple[str, str], List[float]] = {}

    # Extract transitions from log
    for trace in log:
        for i in range(len(trace) - 1):
            current_event = trace[i]
            next_event = trace[i + 1]

            current_activity = current_event.get("concept:name", "Unknown")
            next_activity = next_event.get("concept:name", "Unknown")

            current_ts = current_event.get("time:timestamp")
            next_ts = next_event.get("time:timestamp")

            # Calculate transition time
            if isinstance(current_ts, datetime) and isinstance(next_ts, datetime):
                duration = (next_ts - current_ts).total_seconds()
                if duration >= 0:  # Filter negative durations
                    transition = (current_activity, next_activity)

                    # Filter by model transitions if provided
                    if model_transitions is None or transition in model_transitions:
                        if transition not in transition_data:
                            transition_data[transition] = []
                        transition_data[transition].append(duration)

    # Compute statistics
    results = []
    for (activity, next_activity), durations in transition_data.items():
        frequency = len(durations)

        # Filter by minimum occurrences
        if frequency < min_occurrences:
            continue

        durations_array = np.array(durations)

        results.append({
            "activity": activity,
            "next_activity": next_activity,
            "transition": f"{activity} → {next_activity}",
            "frequency": frequency,
            "min_duration_s": float(np.min(durations_array)),
            "avg_duration_s": float(np.mean(durations_array)),
            "median_duration_s": float(np.median(durations_array)),
            "max_duration_s": float(np.max(durations_array)),
            "p90_duration_s": float(np.percentile(durations_array, 90)),
            "std_duration_s": float(np.std(durations_array))
        })

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("median_duration_s", ascending=False).reset_index(drop=True)
    return df


def detect_bottlenecks(
    transition_stats: pd.DataFrame,
    top_n: int = 10,
    weight_duration: float = 0.7,
    weight_frequency: float = 0.3
) -> pd.DataFrame:
    """Identify bottleneck transitions using weighted scoring.

    Args:
        transition_stats: DataFrame from compute_transition_statistics
        top_n: Number of top bottlenecks to return
        weight_duration: Weight for duration component (0-1)
        weight_frequency: Weight for frequency component (0-1)

    Returns:
        DataFrame with top N bottlenecks sorted by bottleneck score
    """
    if transition_stats.empty:
        return transition_stats

    df = transition_stats.copy()

    # Normalize metrics to 0-1 scale
    if df["median_duration_s"].max() > 0:
        df["duration_score"] = df["median_duration_s"] / df["median_duration_s"].max()
    else:
        df["duration_score"] = 0

    if df["frequency"].max() > 0:
        df["frequency_score"] = df["frequency"] / df["frequency"].max()
    else:
        df["frequency_score"] = 0

    # Compute bottleneck score (high duration + high frequency = bigger bottleneck)
    df["bottleneck_score"] = (
        weight_duration * df["duration_score"] +
        weight_frequency * df["frequency_score"]
    )

    # Sort and return top N
    df = df.sort_values("bottleneck_score", ascending=False).head(top_n)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Case Duration Analysis
# ---------------------------------------------------------------------------


def compute_case_durations(log: EventLog) -> pd.DataFrame:
    """Compute duration for each case/trace.

    Args:
        log: Event log to analyze

    Returns:
        DataFrame with case_id, start_time, end_time, duration_s, num_events
    """
    case_data = []

    for trace in log:
        if not trace:
            continue

        case_id = trace.attributes.get("concept:name") if hasattr(trace, "attributes") else None
        num_events = len(trace)

        # Get timestamps
        timestamps = []
        for event in trace:
            ts = event.get("time:timestamp")
            if isinstance(ts, datetime):
                timestamps.append(ts)

        if len(timestamps) >= 2:
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration = (end_time - start_time).total_seconds()

            case_data.append({
                "case_id": case_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_s": duration,
                "duration_hours": duration / 3600,
                "duration_days": duration / 86400,
                "num_events": num_events
            })

    df = pd.DataFrame(case_data)
    return df


def compute_case_statistics(case_durations: pd.DataFrame) -> Dict[str, float]:
    """Compute summary statistics for case durations.

    Args:
        case_durations: DataFrame from compute_case_durations

    Returns:
        Dictionary with min, avg, median, max, p90, std statistics
    """
    if case_durations.empty:
        return {}

    durations = case_durations["duration_s"].values

    return {
        "total_cases": len(case_durations),
        "min_duration_s": float(np.min(durations)),
        "avg_duration_s": float(np.mean(durations)),
        "median_duration_s": float(np.median(durations)),
        "max_duration_s": float(np.max(durations)),
        "p25_duration_s": float(np.percentile(durations, 25)),
        "p75_duration_s": float(np.percentile(durations, 75)),
        "p90_duration_s": float(np.percentile(durations, 90)),
        "std_duration_s": float(np.std(durations))
    }


# ---------------------------------------------------------------------------
# Model Transition Extraction
# ---------------------------------------------------------------------------


def extract_model_transitions(net, im, fm) -> List[Tuple[str, str]]:
    """Extract activity transitions from a Petri net model.

    Args:
        net: Petri net
        im: Initial marking
        fm: Final marking

    Returns:
        List of (activity, next_activity) tuples representing model transitions
    """
    transitions = []

    try:
        # Build transition map
        transition_map = {}
        for trans in net.transitions:
            if trans.label:  # Only labeled transitions (activities)
                transition_map[trans] = trans.label

        # Extract arcs between transitions (via places)
        for place in net.places:
            # Get incoming transitions
            incoming = [arc.source for arc in place.in_arcs if arc.source in transition_map]
            # Get outgoing transitions
            outgoing = [arc.target for arc in place.out_arcs if arc.target in transition_map]

            # Create transition pairs
            for in_trans in incoming:
                for out_trans in outgoing:
                    activity1 = transition_map[in_trans]
                    activity2 = transition_map[out_trans]
                    if (activity1, activity2) not in transitions:
                        transitions.append((activity1, activity2))

    except Exception:
        # If extraction fails, return empty list
        logger.warning("Failed to extract model transitions", exc_info=True)

    return transitions


__all__ = [
    "compute_activity_statistics",
    "compute_transition_statistics",
    "detect_bottlenecks",
    "compute_case_durations",
    "compute_case_statistics",
    "extract_model_transitions",
]
