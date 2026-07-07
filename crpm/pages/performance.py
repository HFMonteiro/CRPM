"""Performance page — native execution from the filtered log."""

from __future__ import annotations

import html
import time

import pandas as pd
import streamlit as st

from crpm.analytics import (
    collect_timing_buckets,
    compute_activity_statistics,
    compute_case_durations,
    compute_transition_statistics,
    detect_bottlenecks,
)
from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import (
    format_metric_value,
    render_empty_state,
    render_html_card_grid,
    render_html_ranked_table,
    render_inline_empty,
    render_metric_card_grid,
    render_page_cockpit_topbar,
    render_plotly_chart,
    render_quiet_note,
    store_cache_entry,
)
from crpm.screening import humanize_activity_label
from crpm.visualization import create_activity_duration_chart, create_bottleneck_chart


def render_performance_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Process Performance")

    if not snapshot.analysis_complete or snapshot.filtered_log is None:
        render_empty_state("No performance results yet. Run the analysis from the sidebar to populate this page.")
        return

    log = snapshot.filtered_log
    render_page_cockpit_topbar(
        snapshot,
        title="Performance cockpit",
        subtitle="Start with bottlenecks and tail risk, then use exact tables for activity and case-duration detail.",
        meta=[snapshot.input_name or "No log loaded", f"{snapshot.case_count:,} cases"],
    )
    cache_key = f"{snapshot.filter_key or 'current'}::performance"
    cached_payload = snapshot.performance_cache.get(cache_key) if hasattr(snapshot.performance_cache, "get") else None

    if cached_payload is None:
        with st.spinner("Computing performance analytics…"):
            started = time.perf_counter()
            timing_buckets = collect_timing_buckets(log)
            activity_stats = compute_activity_statistics(log, timing_buckets=timing_buckets)
            transition_stats = compute_transition_statistics(log, timing_buckets=timing_buckets)
            bottlenecks = detect_bottlenecks(transition_stats) if not transition_stats.empty else pd.DataFrame()
            case_durations = compute_case_durations(log, timing_buckets=timing_buckets)
            cached_payload = {
                "activity_stats": activity_stats,
                "transition_stats": transition_stats,
                "bottlenecks": bottlenecks,
                "case_durations": case_durations,
                "timings": {"performance_page_s": time.perf_counter() - started},
            }
            try:
                store_cache_entry(snapshot.performance_cache, cache_key, cached_payload)
            except Exception:
                pass
    else:
        st.caption("Using cached performance analytics for the current filtered selection.")
    activity_stats = cached_payload["activity_stats"]
    transition_stats = cached_payload["transition_stats"]
    bottlenecks = cached_payload["bottlenecks"]
    case_durations = cached_payload["case_durations"]

    render_metric_card_grid(
        [
            {
                "eyebrow": "Scope",
                "title": "Activities",
                "value": len(activity_stats),
                "body": "Ranked activity durations.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Flow",
                "title": "Transitions",
                "value": len(transition_stats),
                "body": "Observed hand-offs.",
                "tone": "accent",
            },
            {
                "eyebrow": "Risk",
                "title": "Bottlenecks",
                "value": len(bottlenecks),
                "body": "Delay-heavy transitions.",
                "tone": "success",
            },
            {
                "eyebrow": "Cohort",
                "title": "Cases with duration",
                "value": len(case_durations),
                "body": "Cases with valid start/end.",
                "tone": "neutral",
            },
        ]
    )

    # --- Bottlenecks ---
    if not bottlenecks.empty:
        st.markdown("#### Top bottlenecks")
        chart_col, detail_col = st.columns([1.35, 1.0], gap="medium")
        with chart_col:
            render_plotly_chart(create_bottleneck_chart(bottlenecks), key="perf_bottleneck_chart")
        with detail_col:
            bottleneck_table = bottlenecks.copy()
            if "transition" in bottleneck_table.columns:
                bottleneck_table["Transition"] = bottleneck_table["transition"].map(_humanize_transition_label)
            if "frequency" in bottleneck_table.columns:
                bottleneck_table = bottleneck_table.rename(columns={"frequency": "Events"})
            if "median_duration_s" in bottleneck_table.columns:
                bottleneck_table["Median delay (days)"] = bottleneck_table["median_duration_s"].map(
                    lambda value: round(float(value) / 86400, 1) if pd.notna(value) else None
                )
            if "p90_duration_s" in bottleneck_table.columns:
                bottleneck_table["P90 delay (days)"] = bottleneck_table["p90_duration_s"].map(
                    lambda value: round(float(value) / 86400, 1) if pd.notna(value) else None
                )
            if "bottleneck_score" in bottleneck_table.columns:
                bottleneck_table["Score"] = bottleneck_table["bottleneck_score"].map(
                    lambda value: round(float(value), 2) if pd.notna(value) else None
                )
            bottleneck_table = (
                bottleneck_table[
                    [
                        column
                        for column in ["Transition", "Events", "Median delay (days)", "P90 delay (days)", "Score"]
                        if column in bottleneck_table.columns
                    ]
                ]
                .head(8)
                .reset_index(drop=True)
            )
            bottleneck_table.insert(0, "Rank", range(1, len(bottleneck_table) + 1))
            render_html_ranked_table(
                bottleneck_table,
                title="Bottleneck detail",
                label_column="Transition",
                max_label_chars=72,
            )
    else:
        render_inline_empty("No bottleneck transitions were detected in the current filtered selection.")

    # --- Activity statistics ---
    if not activity_stats.empty:
        st.markdown("#### Activity statistics")
        chart_col, detail_col = st.columns([1.35, 1.0], gap="medium")
        with chart_col:
            render_plotly_chart(create_activity_duration_chart(activity_stats), key="perf_activity_chart")
        with detail_col:
            activity_table = activity_stats.copy()
            if "activity" in activity_table.columns:
                activity_table["Activity"] = activity_table["activity"].map(lambda value: humanize_activity_label(str(value)) or str(value))
            if "frequency" in activity_table.columns:
                activity_table = activity_table.rename(columns={"frequency": "Events"})
            if "median_duration_s" in activity_table.columns:
                activity_table["Median delay (days)"] = activity_table["median_duration_s"].map(
                    lambda value: round(float(value) / 86400, 1) if pd.notna(value) else None
                )
            if "p90_duration_s" in activity_table.columns:
                activity_table["P90 delay (days)"] = activity_table["p90_duration_s"].map(
                    lambda value: round(float(value) / 86400, 1) if pd.notna(value) else None
                )
            if "coefficient_of_variation" in activity_table.columns:
                activity_table["Variation"] = activity_table["coefficient_of_variation"].map(
                    lambda value: round(float(value), 2) if pd.notna(value) else None
                )
            activity_table = (
                activity_table[
                    [
                        column
                        for column in ["Activity", "Events", "Median delay (days)", "P90 delay (days)", "Variation"]
                        if column in activity_table.columns
                    ]
                ]
                .head(8)
                .reset_index(drop=True)
            )
            activity_table.insert(0, "Rank", range(1, len(activity_table) + 1))
            render_html_ranked_table(
                activity_table,
                title="Activity detail",
                label_column="Activity",
                max_label_chars=72,
            )
    else:
        render_inline_empty("No activity duration summary was available for the current filtered selection.")

    # --- Case durations ---
    if not case_durations.empty:
        st.markdown("#### Case duration summary")
        _render_case_duration_summary(case_durations)
    else:
        render_inline_empty("No complete case duration summary could be computed for the current filtered selection.")


def _render_case_duration_summary(case_durations: pd.DataFrame) -> None:
    duration_days = case_durations["duration_days"].dropna()
    if duration_days.empty:
        render_inline_empty("No complete case duration summary could be computed for the current filtered selection.")
        return

    summary = duration_days.describe(percentiles=[0.25, 0.5, 0.75]).round(2)
    p90 = round(float(duration_days.quantile(0.9)), 2)
    p25 = float(summary.get("25%", 0.0))
    p50 = float(summary.get("50%", 0.0))
    p75 = float(summary.get("75%", 0.0))
    min_days = float(summary.get("min", 0.0))
    max_days = float(summary.get("max", 0.0))
    mean_days = float(summary.get("mean", 0.0))
    std_days = float(summary.get("std", 0.0))
    iqr_days = round(max(0.0, p75 - p25), 2)

    render_html_card_grid(
        [
            {
                "eyebrow": "Case cohort",
                "title": "Cases with measured duration",
                "value": format_metric_value(summary.get("count", 0), kind="count"),
                "body": "Completed cases with valid start and end timestamps.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Central tendency",
                "title": "Median case duration",
                "value": format_metric_value(p50, kind="days"),
                "body": f"Mean {format_metric_value(mean_days, kind='days')} · Std {format_metric_value(std_days, kind='days')}",
                "tone": "accent",
            },
            {
                "eyebrow": "Tail risk",
                "title": "P90 case duration",
                "value": format_metric_value(p90, kind="days"),
                "body": "Upper-tail waiting time for the slowest 10% of cases.",
                "tone": "watch",
            },
            {
                "eyebrow": "Spread",
                "title": "Interquartile range",
                "value": format_metric_value(iqr_days, kind="days"),
                "body": f"{format_metric_value(p25, kind='days')} → {format_metric_value(p75, kind='days')}",
                "tone": "success",
            },
        ]
    )

    st.markdown(_render_case_duration_detail_table(summary, p90=p90, iqr_days=iqr_days), unsafe_allow_html=True)
    render_quiet_note(
        f"Median and P90 are usually more informative than the mean for pathway timing. "
        f"Current range: {format_metric_value(min_days, kind='days')} to {format_metric_value(max_days, kind='days')}."
    )


def _humanize_transition_label(value: object) -> str:
    label = str(value or "").strip()
    if "->" in label:
        left, right = [part.strip() for part in label.split("->", 1)]
        return f"{humanize_activity_label(left) or left} → {humanize_activity_label(right) or right}"
    return humanize_activity_label(label) or label


def _render_case_duration_detail_table(summary: pd.Series, *, p90: float, iqr_days: float) -> str:
    rows = [
        ("Count", format_metric_value(summary.get("count", 0), kind="count"), "Cases with complete duration"),
        ("Mean", format_metric_value(summary.get("mean", 0.0), kind="days"), "Average duration across the cohort"),
        ("Std dev", format_metric_value(summary.get("std", 0.0), kind="days"), "Variation around the mean"),
        ("Min", format_metric_value(summary.get("min", 0.0), kind="days"), "Fastest observed case"),
        ("P25", format_metric_value(summary.get("25%", 0.0), kind="days"), "Lower quartile"),
        ("Median", format_metric_value(summary.get("50%", 0.0), kind="days"), "Typical case duration"),
        ("P75", format_metric_value(summary.get("75%", 0.0), kind="days"), "Upper quartile"),
        ("P90", format_metric_value(p90, kind="days"), "Slow-tail threshold"),
        ("IQR", format_metric_value(iqr_days, kind="days"), "Middle 50% spread"),
        ("Max", format_metric_value(summary.get("max", 0.0), kind="days"), "Slowest observed case"),
    ]
    row_html = "".join(
        (
            "<tr>"
            f"<td class='crpm-table__cell crpm-table__cell--label'>{html.escape(label)}</td>"
            f"<td class='crpm-table__cell crpm-table__cell--num'>{html.escape(value)}</td>"
            f"<td class='crpm-table__cell'>{html.escape(note)}</td>"
            "</tr>"
        )
        for label, value, note in rows
    )
    return (
        "<div class='crpm-ranked-table'>"
        "<div class='crpm-ranked-table__title'>Distribution detail</div>"
        "<div class='crpm-ranked-table__scroller'>"
        "<table><thead><tr><th>Metric</th><th>Value</th><th>Reading</th></tr></thead>"
        f"<tbody>{row_html}</tbody></table></div></div>"
    )
