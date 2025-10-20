"""DFG (Directly-Follows Graph) utilities for process mining visualization.

This module provides functions for discovering and visualizing DFGs with
frequency and performance annotations.
"""

from __future__ import annotations

from typing import Dict, Tuple, Optional
import tempfile
from pathlib import Path

from pm4py.objects.log.obj import EventLog
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.statistics.start_activities.log import get as start_activities_get
from pm4py.statistics.end_activities.log import get as end_activities_get


# ---------------------------------------------------------------------------
# DFG Discovery
# ---------------------------------------------------------------------------


def discover_dfg_frequency(log: EventLog) -> Tuple[Dict, Dict, Dict]:
    """Discover frequency-based DFG from event log.

    Args:
        log: Event log

    Returns:
        Tuple of (dfg_dict, start_activities, end_activities)
        - dfg_dict: {(activity1, activity2): frequency}
        - start_activities: {activity: count}
        - end_activities: {activity: count}
    """
    dfg = dfg_discovery.apply(log, variant=dfg_discovery.Variants.FREQUENCY)
    start_activities = start_activities_get.get_start_activities(log)
    end_activities = end_activities_get.get_end_activities(log)

    return dfg, start_activities, end_activities


def discover_dfg_performance(log: EventLog) -> Tuple[Dict, Dict, Dict]:
    """Discover performance-based DFG from event log.

    Args:
        log: Event log

    Returns:
        Tuple of (dfg_dict, start_activities, end_activities)
        - dfg_dict: {(activity1, activity2): median_time_seconds}
        - start_activities: {activity: count}
        - end_activities: {activity: count}
    """
    dfg = dfg_discovery.apply(log, variant=dfg_discovery.Variants.PERFORMANCE)
    start_activities = start_activities_get.get_start_activities(log)
    end_activities = end_activities_get.get_end_activities(log)

    return dfg, start_activities, end_activities


# ---------------------------------------------------------------------------
# DFG Filtering
# ---------------------------------------------------------------------------


def filter_dfg_by_frequency(
    dfg: Dict,
    start_activities: Dict,
    end_activities: Dict,
    min_frequency: int = 1,
    percentage: float = 0.0
) -> Tuple[Dict, Dict, Dict]:
    """Filter DFG edges by frequency threshold.

    Args:
        dfg: DFG dictionary
        start_activities: Start activities dictionary
        end_activities: End activities dictionary
        min_frequency: Minimum absolute frequency
        percentage: Keep top X% of edges (0-100)

    Returns:
        Filtered (dfg, start_activities, end_activities)
    """
    if percentage > 0:
        # Calculate threshold based on percentage
        frequencies = sorted(dfg.values(), reverse=True)
        if frequencies:
            idx = int(len(frequencies) * percentage / 100)
            min_frequency = max(min_frequency, frequencies[min(idx, len(frequencies)-1)])

    # Filter DFG
    filtered_dfg = {k: v for k, v in dfg.items() if v >= min_frequency}

    # Filter activities that still appear
    activities_in_dfg = set()
    for (source, target) in filtered_dfg.keys():
        activities_in_dfg.add(source)
        activities_in_dfg.add(target)

    filtered_start = {k: v for k, v in start_activities.items() if k in activities_in_dfg}
    filtered_end = {k: v for k, v in end_activities.items() if k in activities_in_dfg}

    return filtered_dfg, filtered_start, filtered_end


# ---------------------------------------------------------------------------
# DFG Visualization
# ---------------------------------------------------------------------------


def render_dfg_to_png(
    dfg: Dict,
    start_activities: Dict,
    end_activities: Dict,
    variant: str = "frequency"
) -> bytes:
    """Render DFG to PNG bytes.

    Args:
        dfg: DFG dictionary
        start_activities: Start activities
        end_activities: End activities
        variant: "frequency" or "performance"

    Returns:
        PNG image bytes
    """
    # Choose visualization variant
    if variant == "performance":
        vis_variant = dfg_visualizer.Variants.PERFORMANCE
    else:
        vis_variant = dfg_visualizer.Variants.FREQUENCY

    # Create visualization
    gviz = dfg_visualizer.apply(
        dfg,
        log=None,
        activities_count=None,
        variant=vis_variant,
        parameters={
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.START_ACTIVITIES: start_activities,
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.END_ACTIVITIES: end_activities,
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png"
        }
    )

    # Render to PNG
    try:
        return gviz.pipe(format="png")
    except Exception:
        # Fallback: save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = Path(tmp.name)
        try:
            dfg_visualizer.save(gviz, str(tmp_path))
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)


def get_dfg_statistics(dfg: Dict, start_activities: Dict, end_activities: Dict) -> Dict:
    """Compute statistics about a DFG.

    Args:
        dfg: DFG dictionary
        start_activities: Start activities
        end_activities: End activities

    Returns:
        Dictionary with DFG statistics
    """
    # Count unique activities
    activities = set()
    for (source, target) in dfg.keys():
        activities.add(source)
        activities.add(target)

    # Count edges
    num_edges = len(dfg)

    # Total frequency or time
    total_value = sum(dfg.values())

    # Most frequent edge
    if dfg:
        max_edge = max(dfg.items(), key=lambda x: x[1])
        max_edge_str = f"{max_edge[0][0]} → {max_edge[0][1]}"
        max_edge_value = max_edge[1]
    else:
        max_edge_str = "N/A"
        max_edge_value = 0

    return {
        "num_activities": len(activities),
        "num_edges": num_edges,
        "num_start_activities": len(start_activities),
        "num_end_activities": len(end_activities),
        "total_value": total_value,
        "max_edge": max_edge_str,
        "max_edge_value": max_edge_value
    }


__all__ = [
    "discover_dfg_frequency",
    "discover_dfg_performance",
    "filter_dfg_by_frequency",
    "render_dfg_to_png",
    "get_dfg_statistics",
]
