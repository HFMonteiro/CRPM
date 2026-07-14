"""Operational flow page for queue, throughput, and stage-aging monitoring."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import (
    render_empty_state,
    render_html_ranked_table,
    render_inline_empty,
    render_metric_card_grid,
    render_page_cockpit_topbar,
    render_plotly_chart,
    render_quiet_note,
)
from crpm.queue_flow import build_operational_view, derive_operational_periods, split_operational_periods
from crpm.screening import PeriodDefinition, STEP_ORDER, infer_step_mapping
from crpm.visualization import create_operational_flow_chart, create_queue_stock_chart, create_stage_aging_chart


def render_operational_flow_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Operational Flow")

    if not snapshot.analysis_complete or snapshot.filtered_log is None:
        render_empty_state("No operational flow results yet. Run the analysis from the sidebar to populate this page.")
        return

    log = snapshot.filtered_log
    render_page_cockpit_topbar(
        snapshot,
        title="Operational flow cockpit",
        subtitle="Review stage throughput, queue pressure, and aging from the current filtered screening pathway.",
        meta=[snapshot.input_name or "No log loaded", f"{snapshot.case_count:,} cases"],
    )
    activity_names = sorted({event.get("concept:name") for trace in log for event in trace if event.get("concept:name")})
    step_map = infer_step_mapping(activity_names)
    anchor_activity = step_map.get("invitation")

    st.caption("Operational flow shows stage throughput, queue pressure, and hand-off aging over the current filtered screening pathway.")

    control_cols = st.columns([1.35, 1.05, 1.0])
    with control_cols[0]:
        view_mode = st.selectbox(
            "View",
            ["Full log", "PRE vs POST"],
            key="crpm_operational_view_mode",
            help="Full log shows the current filtered cohort. PRE vs POST splits the log into two incident windows for drift comparison.",
        )
    with control_cols[1]:
        smoothing_enabled = st.checkbox(
            "Smooth weekly flows",
            value=True,
            key="crpm_operational_smoothing",
            help="Smoothing helps reveal shape, but can hide short-lived spikes. Disable it to inspect raw weekly counts.",
        )
    with control_cols[2]:
        smoothing_window = st.slider(
            "Smoothing window (weeks)",
            min_value=1,
            max_value=13,
            value=13,
            disabled=not smoothing_enabled,
            key="crpm_operational_smoothing_window",
            help="Larger windows smooth more aggressively. Use smaller windows when the pathway is short or sparse.",
        )

    with st.expander("Method notes and mapped pathway steps", expanded=False):
        render_quiet_note(
            "Counts and queue stocks are case-level operational indicators. Queue stock is approximated from cumulative inflow minus outflow, and PRE/POST defaults are derived from the loaded data span."
        )
        mapping_rows = pd.DataFrame(
            [{"Canonical step": step, "Mapped activity": step_map.get(step) or "Not mapped"} for step in STEP_ORDER]
        )
        render_html_ranked_table(mapping_rows, title="Mapped pathway steps", label_column="Mapped activity")

    smooth_window = smoothing_window if smoothing_enabled else None

    if view_mode == "PRE vs POST":
        default_pre_period, default_post_period = derive_operational_periods(log, anchor_activity=anchor_activity)
        render_quiet_note("Default PRE/POST windows are derived from the loaded data span and can be overridden below.")
        period_cols = st.columns(2, gap="large")
        period_key = snapshot.filter_key or "operational"
        with period_cols[0]:
            pre_start = st.date_input("PRE start", value=default_pre_period.start, key=f"{period_key}_pre_start")
            pre_end = st.date_input("PRE end", value=default_pre_period.end, key=f"{period_key}_pre_end")
        with period_cols[1]:
            post_start = st.date_input("POST start", value=default_post_period.start, key=f"{period_key}_post_start")
            post_end = st.date_input("POST end", value=default_post_period.end, key=f"{period_key}_post_end")

        if pre_end >= post_start:
            st.warning("PRE must end before POST starts. Adjust the custom windows to continue.")
            return

        periods = split_operational_periods(
            log,
            anchor_activity=anchor_activity,
            pre_period=PeriodDefinition("PRE", pre_start, pre_end),
            post_period=PeriodDefinition("POST", post_start, post_end),
        )
        pre_view = build_operational_view(periods["PRE"], step_map, smooth_window=smooth_window)
        post_view = build_operational_view(periods["POST"], step_map, smooth_window=smooth_window)
        _render_comparison_view(pre_view, post_view)
        return

    selected_log = log
    section_title = "Current filtered cohort"

    view = build_operational_view(selected_log, step_map, smooth_window=smooth_window)
    _render_single_view(section_title, view)


def _render_single_view(section_title: str, view: dict[str, Any]) -> None:
    kpis = view["kpis"]
    render_metric_card_grid(
        [
            {
                "eyebrow": "Cohort",
                "title": "Cases",
                "value": f"{int(kpis.get('total_cases', 0)):,}",
                "body": "Current filtered cohort.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Return",
                "title": "FIT return rate",
                "value": _format_rate(kpis.get("fit_return_rate")),
                "body": _fit_return_body(kpis),
                "tone": "accent",
            },
            {
                "eyebrow": "Completion",
                "title": "Colonoscopy completion",
                "value": _format_rate(kpis.get("colonoscopy_completion_rate")),
                "body": _completion_body(kpis),
                "tone": "success",
            },
            {
                "eyebrow": "Queue",
                "title": "Awaiting colonoscopy",
                "value": f"{int(round(kpis.get('current_awaiting_colonoscopy', 0))):,}",
                "body": "Current outstanding load.",
                "tone": "neutral",
            },
        ]
    )

    lens = _render_lens_control(
        "Operational lens",
        ["Stage flow", "Queue stock", "Stage aging"],
        key=f"operational_lens_{section_title}",
        help="Choose the operational surface you want to inspect without hiding the KPI strip above.",
    )

    if lens == "Stage flow":
        st.caption("Weekly case volumes by canonical stage for the current filtered cohort; unit is cases per sequential week.")
        render_plotly_chart(
            create_operational_flow_chart(view["weekly_counts"], title=f"{section_title} · weekly flow"),
            key=f"operational_flow_{section_title}",
        )
    elif lens == "Queue stock":
        st.caption(
            "Estimated queue stock by sequential week from cumulative stage throughput; latest queue cards use the final observed week."
        )
        render_plotly_chart(
            create_queue_stock_chart(view["stock_levels"], title=f"{section_title} · queue stock"),
            key=f"operational_stock_{section_title}",
        )
    else:
        st.caption(
            "Median and P90 hand-off delays in days for observed canonical transitions in the current filtered cohort. Use the table for exact values."
        )
        aging_cols = st.columns([1.45, 1.0], gap="large")
        with aging_cols[0]:
            render_plotly_chart(
                create_stage_aging_chart(view["aging_metrics"], title=f"{section_title} · stage aging"),
                key=f"operational_aging_{section_title}",
            )
        with aging_cols[1]:
            if view["aging_metrics"].empty:
                render_inline_empty("No stage-aging transitions were observed in this selection.")
            else:
                render_html_ranked_table(
                    view["aging_metrics"], title="Stage aging exact values", label_column=view["aging_metrics"].columns[0]
                )


def _render_comparison_view(pre_view: dict[str, Any], post_view: dict[str, Any]) -> None:
    render_metric_card_grid(
        [
            {
                "eyebrow": "PRE",
                "title": "Cases",
                "value": _format_count(pre_view["kpis"].get("total_cases", 0)),
                "body": "Pre-incident cohort size.",
                "tone": "neutral",
            },
            {
                "eyebrow": "POST",
                "title": "Cases",
                "value": _format_count(post_view["kpis"].get("total_cases", 0)),
                "body": "Post-incident cohort size.",
                "tone": "accent",
            },
            {
                "eyebrow": "PRE",
                "title": "FIT return rate",
                "value": _format_rate(pre_view["kpis"].get("fit_return_rate")),
                "body": _fit_return_body(pre_view["kpis"]),
                "tone": "success",
            },
            {
                "eyebrow": "POST",
                "title": "FIT return rate",
                "value": _format_rate(post_view["kpis"].get("fit_return_rate")),
                "body": _fit_return_body(post_view["kpis"]),
                "tone": "neutral",
            },
        ]
    )
    comparison_rows = pd.DataFrame(
        [
            {
                "Metric": "Cases",
                "PRE": _format_count(pre_view["kpis"].get("total_cases", 0)),
                "POST": _format_count(post_view["kpis"].get("total_cases", 0)),
            },
            {
                "Metric": "FIT return rate",
                "PRE": _format_rate(pre_view["kpis"].get("fit_return_rate")),
                "POST": _format_rate(post_view["kpis"].get("fit_return_rate")),
            },
            {
                "Metric": "Colonoscopy completion rate",
                "PRE": _format_rate(pre_view["kpis"].get("colonoscopy_completion_rate")),
                "POST": _format_rate(post_view["kpis"].get("colonoscopy_completion_rate")),
            },
            {
                "Metric": "Awaiting colonoscopy (latest)",
                "PRE": _format_count(pre_view["kpis"].get("current_awaiting_colonoscopy", 0)),
                "POST": _format_count(post_view["kpis"].get("current_awaiting_colonoscopy", 0)),
            },
        ]
    )
    render_html_ranked_table(comparison_rows, title="PRE versus POST summary", label_column="Metric")

    lens = _render_lens_control(
        "Comparison lens",
        ["Stage flow", "Queue stock", "Stage aging"],
        key="operational_comparison_lens",
        help="Switch the main PRE/POST surface while keeping both periods visible side by side.",
    )

    if lens == "Stage flow":
        st.caption("Weekly stage throughput comparison between the PRE and POST incident cohorts; unit is cases per sequential week.")
        render_plotly_chart(create_operational_flow_chart(pre_view["weekly_counts"], title="PRE weekly flow"), key="operational_pre_flow")
        render_plotly_chart(
            create_operational_flow_chart(post_view["weekly_counts"], title="POST weekly flow"), key="operational_post_flow"
        )
    elif lens == "Queue stock":
        st.caption("Estimated queue accumulation comparison between PRE and POST cohorts; stock is cumulative inflow minus outflow.")
        render_plotly_chart(create_queue_stock_chart(pre_view["stock_levels"], title="PRE queue stock"), key="operational_pre_stock")
        render_plotly_chart(create_queue_stock_chart(post_view["stock_levels"], title="POST queue stock"), key="operational_post_stock")
    else:
        st.caption("Median and P90 delay comparison in days between PRE and POST cohorts, using observed canonical hand-offs.")
        render_plotly_chart(create_stage_aging_chart(pre_view["aging_metrics"], title="PRE stage aging"), key="operational_pre_aging")
        if not pre_view["aging_metrics"].empty:
            with st.expander("PRE exact values", expanded=False):
                render_html_ranked_table(
                    pre_view["aging_metrics"], title="PRE stage aging exact values", label_column=pre_view["aging_metrics"].columns[0]
                )
        render_plotly_chart(create_stage_aging_chart(post_view["aging_metrics"], title="POST stage aging"), key="operational_post_aging")
        if not post_view["aging_metrics"].empty:
            with st.expander("POST exact values", expanded=False):
                render_html_ranked_table(
                    post_view["aging_metrics"], title="POST stage aging exact values", label_column=post_view["aging_metrics"].columns[0]
                )


def _format_rate(value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    numeric_value = float(value)
    if not 0 <= numeric_value <= 1:
        return "Review denominator"
    return f"{numeric_value * 100:.1f}%"


def _fit_return_body(kpis: dict[str, Any]) -> str:
    numerator = kpis.get("fit_return_cases")
    denominator = kpis.get("invitation_cases")
    if numerator is not None and denominator:
        rate = kpis.get("fit_return_rate")
        prefix = "Check denominator: " if rate is not None and not pd.isna(rate) and float(rate) > 1.0 else ""
        return f"{prefix}{int(numerator):,} / {int(denominator):,} invited cases."
    return "Observed return conversion."


def _completion_body(kpis: dict[str, Any]) -> str:
    numerator = kpis.get("colonoscopy_completion_numerator_count")
    denominator = kpis.get("colonoscopy_completion_denominator_count")
    denominator_label = str(kpis.get("colonoscopy_completion_denominator") or "eligible previous step")
    rate = kpis.get("colonoscopy_completion_rate")
    if numerator is not None and denominator:
        warning = kpis.get("colonoscopy_completion_warning")
        prefix = "Check denominator: " if warning or (rate is not None and not pd.isna(rate) and float(rate) > 1.0) else ""
        return f"{prefix}{int(numerator):,} / {int(denominator):,} after {denominator_label}."
    return "Observed pathway completion."


def _format_count(value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{int(round(float(value))):,}"


def _render_lens_control(label: str, options: list[str], *, key: str, help: str) -> str:
    default = options[0]
    segmented_control = getattr(st, "segmented_control", None)
    if callable(segmented_control):
        try:
            selected = segmented_control(label, options, default=default, key=key, help=help)
        except TypeError:
            selected = None
        if isinstance(selected, str) and selected in options:
            return selected
        if selected is None:
            return default

    return st.radio(label, options, index=0, key=key, help=help, horizontal=True)
