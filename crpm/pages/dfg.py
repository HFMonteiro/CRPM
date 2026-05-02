"""DFG Visualizations page — native execution from the filtered log."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.dfg_utils import (
    discover_dfg_frequency,
    discover_dfg_performance,
    filter_dfg_by_coverage,
    get_dfg_statistics,
    rank_dfg_edges,
    render_dfg_to_svg,
    render_dfg_to_png,
)
from crpm.pages.common import (
    format_metric_value,
    render_empty_state,
    render_html_ranked_table,
    render_inline_empty as render_inline_empty,
    render_metric_card_grid,
    render_quiet_note,
    store_cache_entry,
)


def render_dfg_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("DFG Visualizations")

    if not snapshot.analysis_complete or snapshot.filtered_log is None:
        render_empty_state("No DFG results yet. Run the analysis from the sidebar to populate this page.")
        return

    log = snapshot.filtered_log

    # --- Controls ---
    ctrl_cols = st.columns([1.0, 1.6])
    dfg_mode = ctrl_cols[0].selectbox("DFG type", ["Frequency", "Performance"], key="dfg_type_sel")
    coverage_range = ctrl_cols[1].slider(
        "Edge coverage band (%)",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=1,
        key="dfg_coverage_range",
        help="100 keeps the most frequent edges and 0 keeps the least frequent edges. Narrow windows isolate a band of ranked edges.",
    )
    st.caption(
        "Coverage keeps a ranked band of directly-follows edges: raise the lower bound for dominant behavior and lower the upper bound for rare paths."
    )
    if coverage_range != (0, 100):
        render_quiet_note(
            f"DFG filtered to ranked edge coverage {coverage_range[0]}%–{coverage_range[1]}%. "
            "Narrow windows can hide start/end activities and produce an intentionally sparse map."
        )

    cache_key = f"{snapshot.filter_key or 'current'}::dfg::{dfg_mode}::{coverage_range[0]}::{coverage_range[1]}"
    cached_payload = snapshot.dfg_cache.get(cache_key) if hasattr(snapshot.dfg_cache, "get") else None
    if cached_payload is None:
        with st.spinner("Discovering DFG…"):
            started = time.perf_counter()
            if dfg_mode == "Performance":
                dfg, starts, ends = discover_dfg_performance(log)
                vis_variant = "performance"
            else:
                dfg, starts, ends = discover_dfg_frequency(log)
                vis_variant = "frequency"

            if coverage_range != (0, 100):
                dfg, starts, ends = filter_dfg_by_coverage(dfg, starts, ends, coverage_range=coverage_range)

            cached_payload = {
                "dfg": dfg,
                "starts": starts,
                "ends": ends,
                "vis_variant": vis_variant,
                "timings": {"dfg_page_s": time.perf_counter() - started},
            }
            try:
                store_cache_entry(snapshot.dfg_cache, cache_key, cached_payload)
            except Exception:
                pass
    dfg = cached_payload["dfg"]
    starts = cached_payload["starts"]
    ends = cached_payload["ends"]
    vis_variant = cached_payload["vis_variant"]

    stats = get_dfg_statistics(dfg, starts, ends)
    max_edge_label = "Most frequent edge" if dfg_mode == "Frequency" else "Slowest edge"
    max_edge_value_label = (
        format_metric_value(stats.get("max_edge_value", 0), kind="count")
        if dfg_mode == "Frequency"
        else _format_dfg_duration(stats.get("max_edge_value"))
    )

    st.markdown("#### Directly-follows map")
    if dfg:
        with st.spinner("Rendering process map…"):
            try:
                svg_markup = render_dfg_to_svg(dfg, starts, ends, variant=vis_variant)
                st.markdown(
                    f'<div class="crpm-dfg-vector">{svg_markup}</div>',
                    unsafe_allow_html=True,
                )
            except Exception:
                try:
                    png_bytes = render_dfg_to_png(dfg, starts, ends, variant=vis_variant)
                    st.image(png_bytes, caption=f"Directly-Follows Graph ({dfg_mode})", use_container_width=True)
                    st.warning("SVG rendering failed, so the DFG fell back to PNG. Confirm Graphviz is installed if labels look clipped.")
                except Exception:
                    st.warning("Could not render the DFG. Check the runtime preflight and confirm Graphviz is installed.")
    else:
        st.markdown(
            "<div class='crpm-inline-empty'>The DFG is empty after applying the current coverage band. Widen the slider to bring more edges back into view.</div>",
            unsafe_allow_html=True,
        )

    render_metric_card_grid(
        [
            {
                "eyebrow": "Map",
                "title": "Activities",
                "value": stats.get("num_activities", 0),
                "body": "Distinct nodes in the current DFG.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Map",
                "title": "Edges",
                "value": stats.get("num_edges", 0),
                "body": "Directly-follows relations retained.",
                "tone": "accent",
            },
            {
                "eyebrow": "Entry",
                "title": "Start activities",
                "value": stats.get("num_start_activities", 0),
                "body": "Observed cohort entry points.",
                "tone": "success",
            },
            {
                "eyebrow": "Exit",
                "title": "End activities",
                "value": stats.get("num_end_activities", 0),
                "body": "Observed cohort exit points.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Focus",
                "title": max_edge_label,
                "value": stats.get("max_edge", "N/A"),
                "body": (
                    f"Peak value in the current band: {max_edge_value_label}."
                    if stats.get("max_edge") != "N/A"
                    else "Most pronounced edge in the current band."
                ),
                "tone": "neutral",
            },
        ]
    )
    if dfg:
        st.markdown("#### Ranked edge detail")
        ranked_rows = rank_dfg_edges(dfg)
        value_label = "Events" if dfg_mode == "Frequency" else "Median delay"
        table_rows = pd.DataFrame(
            [
                {
                    "Rank": row["rank"],
                    "Coverage (%)": row["coverage_pct"],
                    "From": row["source"],
                    "To": row["target"],
                    value_label: (
                        format_metric_value(row["value"], kind="count") if dfg_mode == "Frequency" else _format_dfg_duration(row["value"])
                    ),
                }
                for row in ranked_rows[:25]
            ]
        )
        render_html_ranked_table(
            table_rows,
            title="Leading edges",
            label_column="From",
        )
    else:
        st.markdown(
            "<div class='crpm-inline-empty'>No leading edges are available for the current coverage band.</div>",
            unsafe_allow_html=True,
        )


def _format_dfg_duration(value: object) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if seconds < 0:
        return "N/A"
    if seconds >= 172800:
        return f"{seconds / 86400:,.1f} d"
    if seconds >= 3600:
        return f"{seconds / 3600:,.1f} h"
    if seconds >= 60:
        return f"{seconds / 60:,.0f} min"
    return f"{seconds:,.0f} s"
