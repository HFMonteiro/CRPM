"""Overview page for the CRPM screening workbench."""

from __future__ import annotations

import html
from typing import Any, Mapping

import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import format_metric_value, render_html_card_grid, render_quiet_note


PAGE_GUIDE = [
    ("01", "Overview", "Start with the current run, scope, and executive reading order."),
    ("02", "Discovery", "Mine empirical process models from the current filtered cohort."),
    ("03", "Model Comparison", "Compare fitness, precision, and balance across discovery algorithms."),
    ("04", "Operational Flow", "Review weekly movement, queue stock, and stage aging across the pathway."),
    ("05", "DFG Visualizations", "Inspect dominant and rare directly-follows behaviour with stable process maps."),
    ("06", "Variant Analysis", "See dominant traces, coverage concentration, and per-variant conformance."),
    ("07", "Conformance Analytics", "Interpret pathway compliance, deviations, and workflow investigation surfaces."),
    ("08", "Process Performance", "Use dense timing drilldowns when the executive workflow views need exact depth."),
]


def render_overview_page(snapshot: AnalysisSnapshot) -> None:
    summary = _analysis_summary(snapshot)
    _render_overview_hero(snapshot, summary)

    if snapshot.analysis_complete:
        render_quiet_note(
            "Start with the current run and quality cards, then move to Operational Flow and Conformance Analytics when the cohort shows timing stretch or deviation pressure."
        )
    else:
        render_quiet_note(
            "Load a screening log, set the cohort filters, and run the analysis once. The overview then becomes an executive dashboard for the current filtered run."
        )

    kpi_cols = st.columns(4, gap="small")
    kpi_cols[0].metric("Cases", format_metric_value(summary.get("cases"), kind="count"))
    kpi_cols[1].metric("Events", format_metric_value(summary.get("events"), kind="count"))
    kpi_cols[2].metric("Dominant path", _display_optional(summary.get("dominant_path_share"), kind="percent"))
    kpi_cols[3].metric("Median throughput", _display_optional(summary.get("median_throughput_days"), kind="days"))

    left_col, right_col = st.columns([1.25, 1.0], gap="large")

    with left_col:
        st.markdown("#### Current run")
        render_html_card_grid(_overview_signal_cards(snapshot, summary))
        with st.expander("Reading order", expanded=False):
            st.markdown(_render_page_guide_html(snapshot.analysis_complete), unsafe_allow_html=True)

    with right_col:
        st.markdown("#### Analysis posture")
        render_html_card_grid(_overview_status_cards(snapshot, summary))
        if snapshot.analysis_complete:
            st.markdown("#### Run quality")
            render_html_card_grid(_overview_quality_cards(snapshot, summary))


def _render_overview_hero(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> None:
    title = "CRPM executive overview"
    if snapshot.analysis_complete and snapshot.input_name:
        title = f"{snapshot.input_name} · current filtered run"

    badges = [
        _hero_badge(snapshot.input_name or "No log loaded", tone="neutral"),
        _hero_badge(summary.get("period_label") or "Period unavailable", tone="neutral"),
        _hero_badge(snapshot.active_followup_label or "Full available follow-up", tone="success"),
        _hero_badge(f"{snapshot.model_count:,} model(s)" if snapshot.analysis_complete else "Awaiting analysis", tone="accent"),
    ]

    body = (
        "CRPM is tuned for colorectal screening programs: discovery builds the empirical model baseline, DFG and operational flow explain what is happening, and conformance closes the loop on how observed behaviour departs from the intended pathway."
        if snapshot.analysis_complete
        else "This landing view is designed to become the executive starting point after each run: current scope, pathway signal strength, and the recommended reading order across the analytical pages."
    )

    st.markdown(
        (
            "<div class='crpm-overview-hero'>"
            "<div class='crpm-overview-hero__eyebrow'>CRC process mining workbench</div>"
            f"<div class='crpm-overview-hero__title'>{html.escape(title)}</div>"
            f"<div class='crpm-overview-hero__body'>{html.escape(body)}</div>"
            f"<div class='crpm-overview-hero__chips'>{''.join(badges)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _overview_signal_cards(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> list[dict[str, str]]:
    if not snapshot.analysis_complete:
        return [
            {
                "eyebrow": "Start here",
                "title": "Load an event log",
                "value": "XES or CSV",
                "body": "Use the sidebar to choose the source, map the columns if needed, and confirm the cohort filters before running.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Workflow",
                "title": "Run the analysis once",
                "value": "Discovery → conformance",
                "body": "CRPM computes discovery, comparison, workflow, DFG, variant, and timing views from the same filtered run.",
                "tone": "accent",
            },
            {
                "eyebrow": "Outcome",
                "title": "Use the pages in order",
                "value": "8 pages",
                "body": "The navigation is already sequenced from overview to advanced timing drilldown.",
                "tone": "success",
            },
        ]

    best_model = str(summary.get("best_model") or "No model recommendation")
    return [
        {
            "eyebrow": "Model recommendation",
            "title": "Best balanced model",
            "value": best_model,
            "body": f"Fitness { _display_optional(summary.get('best_fitness'), kind='score') } · Precision { _display_optional(summary.get('best_precision'), kind='score') } · Balance { _display_optional(summary.get('best_balance'), kind='score') }",
            "tone": "accent",
            "title_attr": best_model,
        },
        {
            "eyebrow": "Workflow signal",
            "title": "Dominant vs deviation mix",
            "value": f"{_display_optional(summary.get('dominant_path_share'), kind='percent')} dominant",
            "body": f"Deviation share { _display_optional(summary.get('deviation_share'), kind='percent') } · {format_metric_value(summary.get('unique_activities'), kind='count')} activities · {format_metric_value(summary.get('workflow_nodes'), kind='count')} nodes",
            "tone": "neutral",
        },
        {
            "eyebrow": "Timing posture",
            "title": "Current filtered cohort",
            "value": _display_optional(summary.get("median_throughput_days"), kind="days"),
            "body": f"Period {summary.get('period_label', 'Unavailable')} · Runtime { _display_optional(summary.get('analysis_runtime_s')) } s",
            "tone": "success",
        },
    ]


def _overview_status_cards(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "eyebrow": "Analysis status",
            "title": "Current run",
            "value": "Ready" if snapshot.analysis_complete else "Awaiting run",
            "body": "The overview reflects the latest successful filtered run." if snapshot.analysis_complete else "Load a log and run the analysis to populate discovery, conformance, and timing outputs.",
            "tone": "success" if snapshot.analysis_complete else "neutral",
        },
        {
            "eyebrow": "Comparison",
            "title": "Model comparison",
            "value": "Available" if snapshot.has_comparison else "Not ready",
            "body": f"{format_metric_value(summary.get('model_count'), kind='count')} comparison row(s) available for the current cohort.",
            "tone": "accent" if snapshot.has_comparison else "neutral",
        },
        {
            "eyebrow": "Workflow",
            "title": "Conformance surface",
            "value": "Available" if snapshot.conformance_workspace else "Pending",
            "body": "Board and explorer use the same workflow payload and right-side inspector." if snapshot.conformance_workspace else "Run the analysis to build workflow, deviations, and investigation views.",
            "tone": "neutral",
        },
        {
            "eyebrow": "Cached context",
            "title": "Reusable page state",
            "value": f"{len(snapshot.performance_cache) + len(snapshot.variant_cache) + len(snapshot.dfg_cache):,} entries",
            "body": f"Performance {len(snapshot.performance_cache):,} · Variants {len(snapshot.variant_cache):,} · DFG {len(snapshot.dfg_cache):,}",
            "tone": "accent",
        },
    ]


def _overview_quality_cards(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "eyebrow": "Coverage",
            "title": "Dominant path concentration",
            "value": _display_optional(summary.get("dominant_path_share"), kind="percent"),
            "body": "Use Variant Analysis and DFG when concentration is high; switch to Conformance Analytics when deviation share rises.",
            "tone": "success",
        },
        {
            "eyebrow": "Deviation",
            "title": "Off-path behaviour",
            "value": _display_optional(summary.get("deviation_share"), kind="percent"),
            "body": "Higher deviation share usually means the workflow inspector and the rare-path DFG views are worth prioritising.",
            "tone": "neutral",
        },
        {
            "eyebrow": "Scope",
            "title": "Observed activity spread",
            "value": format_metric_value(summary.get("unique_activities"), kind="count"),
            "body": "A broader activity set normally increases the value of page-to-page drilldown and business-label cleanup.",
            "tone": "accent",
        },
    ]


def _render_page_guide_html(analysis_complete: bool) -> str:
    cards = []
    for order, title, description in PAGE_GUIDE:
        state = "Ready" if analysis_complete else "Awaiting run"
        cards.append(
            (
                "<div class='crpm-page-card'>"
                f"<div class='crpm-page-card__order'>{html.escape(order)}</div>"
                f"<div class='crpm-page-card__title'>{html.escape(title)}</div>"
                f"<div class='crpm-page-card__body'>{html.escape(description)}</div>"
                f"<div class='crpm-page-card__meta'>{html.escape(state)}</div>"
                "</div>"
            )
        )
    return "<div class='crpm-page-card-grid'>" + "".join(cards) + "</div>"


def _analysis_summary(snapshot: AnalysisSnapshot) -> Mapping[str, Any]:
    summary = snapshot.analysis_summary if isinstance(snapshot.analysis_summary, Mapping) else {}
    if summary:
        return summary
    return {
        "cases": snapshot.case_count,
        "events": snapshot.event_count,
        "unique_activities": 0,
        "period_label": "Unavailable",
        "model_count": snapshot.model_count,
        "best_model": None,
        "best_fitness": None,
        "best_precision": None,
        "best_balance": None,
        "dominant_path_share": None,
        "deviation_share": None,
        "median_throughput_days": None,
        "workflow_nodes": 0,
        "workflow_edges": 0,
        "analysis_runtime_s": None,
    }


def _display_optional(value: Any, *, kind: str = "generic") -> str:
    if value is None:
        return "N/A"
    return format_metric_value(value, kind=kind)


def _hero_badge(label: str, *, tone: str) -> str:
    return f"<span class='crpm-overview-hero__chip crpm-overview-hero__chip--{html.escape(tone)}'>{html.escape(label)}</span>"
