"""DFG (Directly-Follows Graph) utilities for process mining visualization.

This module provides functions for discovering and visualizing DFGs with
frequency and performance annotations.
"""

from __future__ import annotations

import math
import re
from typing import Dict, Tuple
import tempfile
from pathlib import Path

from pm4py.objects.log.obj import EventLog
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.statistics.start_activities.log import get as start_activities_get
from pm4py.statistics.end_activities.log import get as end_activities_get

_SVG_SCRIPT_RE = re.compile(r"<\s*script\b[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)
_SVG_EVENT_ATTR_RE = re.compile(r"\s+on[a-zA-Z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)")
_SVG_DANGEROUS_URL_RE = re.compile(r"\s+(?:href|xlink:href)\s*=\s*(\"|')\s*(?:javascript:|data:text/html)[^\"']*\1", re.IGNORECASE)
_SVG_EXTERNAL_REF_RE = re.compile(r"\s+(?:href|xlink:href)\s*=\s*(\"|')\s*https?://[^\"']*\1", re.IGNORECASE)


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


def rank_dfg_edges(dfg: Dict) -> list[dict[str, object]]:
    """Return DFG edges sorted by descending value with rank and coverage metadata."""
    if not dfg:
        return []

    ranked_items = sorted(
        dfg.items(),
        key=lambda item: (-item[1], str(item[0][0]), str(item[0][1])),
    )
    total = len(ranked_items)
    rows: list[dict[str, object]] = []
    for index, ((source, target), value) in enumerate(ranked_items, start=1):
        if total == 1:
            coverage_pct = 100.0
        else:
            coverage_pct = round(((total - index) / (total - 1)) * 100.0, 2)
        rows.append(
            {
                "rank": index,
                "coverage_pct": coverage_pct,
                "source": source,
                "target": target,
                "value": value,
            }
        )
    return rows


def filter_dfg_by_coverage(
    dfg: Dict,
    start_activities: Dict,
    end_activities: Dict,
    coverage_range: Tuple[int, int] = (0, 100),
) -> Tuple[Dict, Dict, Dict]:
    """Filter DFG edges by percentile coverage over ranked edge values.

    Args:
        dfg: DFG dictionary
        start_activities: Start activities dictionary
        end_activities: End activities dictionary
        coverage_range: Inclusive percentile coverage window where 100 is the most
            frequent edge and 0 is the least frequent edge.

    Returns:
        Filtered (dfg, start_activities, end_activities)
    """
    if not dfg:
        return {}, {}, {}

    lower, upper = coverage_range
    lower = max(0, min(100, int(lower)))
    upper = max(0, min(100, int(upper)))
    if lower > upper:
        lower, upper = upper, lower

    ranked_edges = rank_dfg_edges(dfg)
    filtered_rows = [row for row in ranked_edges if lower <= float(row["coverage_pct"]) <= upper]
    filtered_dfg = {(row["source"], row["target"]): row["value"] for row in filtered_rows}

    activities_in_dfg = set()
    for source, target in filtered_dfg.keys():
        activities_in_dfg.add(source)
        activities_in_dfg.add(target)

    filtered_start = {k: v for k, v in start_activities.items() if k in activities_in_dfg}
    filtered_end = {k: v for k, v in end_activities.items() if k in activities_in_dfg}

    return filtered_dfg, filtered_start, filtered_end


def filter_dfg_by_frequency(
    dfg: Dict, start_activities: Dict, end_activities: Dict, min_frequency: int = 1, percentage: float = 0.0
) -> Tuple[Dict, Dict, Dict]:
    """Backward-compatible DFG filter using the legacy threshold contract."""
    if not dfg:
        return {}, {}, {}

    filtered_dfg = {k: v for k, v in dfg.items() if v >= min_frequency}
    if percentage > 0 and filtered_dfg:
        ranked_items = sorted(
            filtered_dfg.items(),
            key=lambda item: (-item[1], str(item[0][0]), str(item[0][1])),
        )
        keep_count = max(1, math.ceil(len(ranked_items) * (percentage / 100.0)))
        filtered_dfg = dict(ranked_items[:keep_count])

    activities_in_dfg = set()
    for source, target in filtered_dfg.keys():
        activities_in_dfg.add(source)
        activities_in_dfg.add(target)

    filtered_start = {k: v for k, v in start_activities.items() if k in activities_in_dfg}
    filtered_end = {k: v for k, v in end_activities.items() if k in activities_in_dfg}

    return filtered_dfg, filtered_start, filtered_end


# ---------------------------------------------------------------------------
# DFG Visualization
# ---------------------------------------------------------------------------


def render_dfg_to_png(dfg: Dict, start_activities: Dict, end_activities: Dict, variant: str = "frequency") -> bytes:
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
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png",
        },
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


def render_dfg_to_svg(dfg: Dict, start_activities: Dict, end_activities: Dict, variant: str = "frequency") -> str:
    """Render DFG to SVG markup.

    Args:
        dfg: DFG dictionary
        start_activities: Start activities
        end_activities: End activities
        variant: "frequency" or "performance"

    Returns:
        SVG markup string
    """
    if variant == "performance":
        vis_variant = dfg_visualizer.Variants.PERFORMANCE
    else:
        vis_variant = dfg_visualizer.Variants.FREQUENCY

    gviz = dfg_visualizer.apply(
        dfg,
        log=None,
        activities_count=None,
        variant=vis_variant,
        parameters={
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.START_ACTIVITIES: start_activities,
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.END_ACTIVITIES: end_activities,
            dfg_visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "svg",
        },
    )

    try:
        svg_bytes = gviz.pipe(format="svg")
    except Exception:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as tmp:
            tmp_path = Path(tmp.name)
        try:
            dfg_visualizer.save(gviz, str(tmp_path))
            svg_bytes = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

    svg_text = sanitize_svg_markup(svg_bytes.decode("utf-8", errors="replace"))
    svg_text = svg_text.replace(
        "<svg ",
        '<svg preserveAspectRatio="xMidYMid meet" style="width:100%; max-width:100%; min-width:0; height:clamp(240px, 30vh, 340px); display:block;" ',
        1,
    )
    return svg_text


def sanitize_svg_markup(svg_text: str) -> str:
    """Strip active SVG content before embedding renderer output in Streamlit HTML."""
    sanitized = _SVG_SCRIPT_RE.sub("", svg_text)
    sanitized = _SVG_EVENT_ATTR_RE.sub("", sanitized)
    sanitized = _SVG_DANGEROUS_URL_RE.sub("", sanitized)
    sanitized = _SVG_EXTERNAL_REF_RE.sub("", sanitized)
    return sanitized


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
    for source, target in dfg.keys():
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
        "max_edge_value": max_edge_value,
    }


__all__ = [
    "discover_dfg_frequency",
    "discover_dfg_performance",
    "filter_dfg_by_coverage",
    "filter_dfg_by_frequency",
    "rank_dfg_edges",
    "render_dfg_to_svg",
    "render_dfg_to_png",
    "sanitize_svg_markup",
    "get_dfg_statistics",
]
