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

import pandas as pd
from pm4py.objects.log.obj import EventLog
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.statistics.start_activities.log import get as start_activities_get
from pm4py.statistics.end_activities.log import get as end_activities_get

from crpm.process_map import build_process_map_kpis, build_selection_context
from crpm.runtime_compat import ensure_graphviz_on_path

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
    ensure_graphviz_on_path()
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

    ensure_graphviz_on_path()
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
        '<svg preserveAspectRatio="xMidYMid meet" style="width:100%; max-width:100%; min-width:0; height:clamp(320px, 38vh, 480px); display:block;" ',
        1,
    )
    return svg_text


def render_dfg_interactive_html(svg_markup: str, *, height: int = 540) -> str:
    """Wrap a sanitized DFG SVG with wheel zoom, keyboard controls and drag pan."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    :root {{ color-scheme: light; font-family: Arial, Helvetica, sans-serif; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; min-height: {height}px; background: transparent; }}
    body {{ overflow: hidden; color: #24343f; }}
    .dfg-shell {{ display: grid; grid-template-rows: 34px 1fr 22px; height: {height}px; padding: 4px 6px 0; }}
    .dfg-toolbar {{ display: flex; align-items: center; gap: 6px; }}
    .dfg-toolbar button {{ min-width: 30px; height: 26px; border: 1px solid #cbd5dd; border-radius: 7px; background: #fff; color: #24343f; font-size: 14px; font-weight: 700; cursor: pointer; }}
    .dfg-toolbar button:hover, .dfg-toolbar button:focus-visible {{ border-color: #2c7a69; background: #eef7f3; outline: none; }}
    .dfg-toolbar button[data-action="reset"] {{ min-width: 58px; font-size: 11px; font-weight: 600; }}
    .dfg-zoom-status {{ margin-left: 4px; font-size: 11px; color: #687680; font-variant-numeric: tabular-nums; }}
    .dfg-viewport {{ min-height: 0; overflow: hidden; border: 1px solid rgba(71, 88, 79, .16); border-radius: 14px; background: rgba(252, 251, 253, .98); cursor: grab; touch-action: none; }}
    .dfg-viewport:focus-visible {{ outline: 2px solid #2c7a69; outline-offset: -2px; }}
    .dfg-viewport.is-dragging {{ cursor: grabbing; }}
    .dfg-viewport svg {{ display: block !important; width: 100% !important; height: 100% !important; min-height: 0 !important; max-width: none !important; }}
    .dfg-hint {{ padding: 3px 2px 0; color: #687680; font-size: 10px; line-height: 1.2; }}
  </style>
</head>
<body>
  <main class="dfg-shell" data-testid="crpm-dfg-zoom-shell">
    <div class="dfg-toolbar" aria-label="DFG map controls">
      <button type="button" data-action="zoom-out" aria-label="Zoom out" title="Zoom out">−</button>
      <button type="button" data-action="zoom-in" aria-label="Zoom in" title="Zoom in">+</button>
      <button type="button" data-action="reset" aria-label="Reset map view" title="Reset map view">Reset</button>
      <span class="dfg-zoom-status" data-testid="crpm-dfg-zoom-status" aria-live="polite">Zoom 100%</span>
    </div>
    <div class="dfg-viewport" data-testid="crpm-dfg-zoom-viewport" tabindex="0" aria-label="Directly-follows map. Use the mouse wheel to zoom and drag to pan.">
      {svg_markup}
    </div>
    <div class="dfg-hint">Mouse wheel to zoom · drag to pan · + / − / 0 keys</div>
  </main>
  <script>
    (() => {{
      const viewport = document.querySelector('[data-testid="crpm-dfg-zoom-viewport"]');
      const svg = viewport && viewport.querySelector('svg');
      const status = document.querySelector('[data-testid="crpm-dfg-zoom-status"]');
      if (!viewport || !svg) return;

      const initialParts = (svg.getAttribute('viewBox') || '0 0 100 100').trim().split(/\\s+/).map(Number);
      if (initialParts.length !== 4 || initialParts.some((value) => !Number.isFinite(value))) return;
      const initial = {{ x: initialParts[0], y: initialParts[1], w: initialParts[2], h: initialParts[3] }};
      let view = {{ ...initial }};
      let dragging = null;

      const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
      const clampAxis = (value, size, origin, limit) => clamp(value, origin, origin + limit - size);
      const apply = () => {{
        svg.setAttribute('viewBox', `${{view.x}} ${{view.y}} ${{view.w}} ${{view.h}}`);
        const zoom = Math.round((initial.w / view.w) * 100);
        if (status) status.textContent = `Zoom ${{zoom}}%`;
      }};
      const zoomAt = (factor, clientX, clientY) => {{
        const rect = svg.getBoundingClientRect();
        const anchorX = view.x + ((clientX - rect.left) / Math.max(rect.width, 1)) * view.w;
        const anchorY = view.y + ((clientY - rect.top) / Math.max(rect.height, 1)) * view.h;
        const nextW = clamp(view.w / factor, initial.w / 4, initial.w);
        const nextH = clamp(view.h / factor, initial.h / 4, initial.h);
        view.x = anchorX - (anchorX - view.x) * (nextW / view.w);
        view.y = anchorY - (anchorY - view.y) * (nextH / view.h);
        view.w = nextW;
        view.h = nextH;
        view.x = clampAxis(view.x, view.w, initial.x, initial.w);
        view.y = clampAxis(view.y, view.h, initial.y, initial.h);
        apply();
      }};
      const zoomBy = (factor) => {{
        const rect = viewport.getBoundingClientRect();
        zoomAt(factor, rect.left + rect.width / 2, rect.top + rect.height / 2);
      }};
      const reset = () => {{ view = {{ ...initial }}; apply(); }};

      viewport.addEventListener('wheel', (event) => {{
        event.preventDefault();
        zoomAt(event.deltaY < 0 ? 1.2 : 0.84, event.clientX, event.clientY);
      }}, {{ passive: false }});
      viewport.addEventListener('pointerdown', (event) => {{
        dragging = {{ x: event.clientX, y: event.clientY, view: {{ ...view }} }};
        viewport.classList.add('is-dragging');
        viewport.setPointerCapture(event.pointerId);
      }});
      viewport.addEventListener('pointermove', (event) => {{
        if (!dragging) return;
        const rect = svg.getBoundingClientRect();
        const dx = (event.clientX - dragging.x) / Math.max(rect.width, 1) * dragging.view.w;
        const dy = (event.clientY - dragging.y) / Math.max(rect.height, 1) * dragging.view.h;
        view.x = clampAxis(dragging.view.x - dx, view.w, initial.x, initial.w);
        view.y = clampAxis(dragging.view.y - dy, view.h, initial.y, initial.h);
        apply();
      }});
      const stopDragging = (event) => {{
        dragging = null;
        viewport.classList.remove('is-dragging');
        if (event && viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
      }};
      viewport.addEventListener('pointerup', stopDragging);
      viewport.addEventListener('pointercancel', stopDragging);
      viewport.addEventListener('keydown', (event) => {{
        if (event.key === '+' || event.key === '=') {{ event.preventDefault(); zoomBy(1.2); }}
        if (event.key === '-' || event.key === '_') {{ event.preventDefault(); zoomBy(0.84); }}
        if (event.key === '0') {{ event.preventDefault(); reset(); }}
      }});
      viewport.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', (event) => {{
        event.stopPropagation();
        const action = button.dataset.action;
        if (action === 'zoom-in') zoomBy(1.2);
        if (action === 'zoom-out') zoomBy(0.84);
        if (action === 'reset') reset();
      }}));
      apply();
    }})();
  </script>
</body>
</html>"""


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


def build_dfg_process_map_payload(
    *,
    frequency_dfg: Dict,
    performance_dfg: Dict | None = None,
    start_activities: Dict | None = None,
    end_activities: Dict | None = None,
    renderer_role: str = "dfg",
) -> dict[str, object]:
    """Return a normalized process-map payload for DFG renderers."""

    start_activities = start_activities or {}
    end_activities = end_activities or {}
    performance_dfg = performance_dfg or {}
    activities = sorted({activity for edge in frequency_dfg for activity in edge} | set(start_activities) | set(end_activities))
    total_frequency = sum(int(value or 0) for value in frequency_dfg.values())
    nodes = pd.DataFrame(
        [
            {
                "node_id": activity,
                "label": activity,
                "start_count": int(start_activities.get(activity, 0) or 0),
                "end_count": int(end_activities.get(activity, 0) or 0),
            }
            for activity in activities
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "edge_uid": f"{source}->{target}",
                "source": source,
                "target": target,
                "frequency": int(frequency or 0),
                "frequency_share_pct": round((int(frequency or 0) / total_frequency) * 100, 2) if total_frequency else 0.0,
                "median_wait_s": _safe_float(performance_dfg.get((source, target))),
            }
            for (source, target), frequency in sorted(
                frequency_dfg.items(), key=lambda item: (-int(item[1] or 0), str(item[0][0]), str(item[0][1]))
            )
        ]
    )
    denominators = {
        "transition_denominator": int(total_frequency),
        "activity_denominator": int(len(nodes.index)),
    }
    return {
        "schema_version": 1,
        "map_kind": "directly_follows_graph",
        "renderer_role": renderer_role,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "activity_count": int(len(nodes.index)),
            "edge_count": int(len(edges.index)),
            "transition_count": int(total_frequency),
            "start_activity_count": int(len(start_activities)),
            "end_activity_count": int(len(end_activities)),
        },
        "denominators": denominators,
        "kpi_rows": build_process_map_kpis(denominators),
        "selection_context": build_selection_context(
            source_page="DFG Visualizations",
            renderer_role=renderer_role,
        ),
    }


def _safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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
    "build_dfg_process_map_payload",
]
