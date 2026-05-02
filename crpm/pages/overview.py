"""Overview page for the CRPM screening workbench."""

from __future__ import annotations

import html
from typing import Any, Mapping

import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import (
    format_metric_value,
    render_dashboard_bar_list,
    render_dashboard_topbar,
    render_html_card_grid,
    render_inline_empty,
    render_metric_card_grid,
)
from crpm.visualization import render_workflow_conformance_svg

PAGE_GUIDE = [
    (
        "01",
        "Overview",
        "Start with the current run, scope, and executive reading order.",
    ),
    (
        "02",
        "Discovery",
        "Mine empirical process models from the current filtered cohort.",
    ),
    (
        "03",
        "Model Comparison",
        "Compare fitness, precision, and balance across discovery algorithms.",
    ),
    (
        "04",
        "Operational Flow",
        "Review weekly movement, queue stock, and stage aging across the pathway.",
    ),
    (
        "05",
        "DFG Visualizations",
        "Inspect dominant and rare directly-follows behaviour with stable process maps.",
    ),
    (
        "06",
        "Variant Analysis",
        "See dominant traces, coverage concentration, and per-variant conformance.",
    ),
    (
        "07",
        "Conformance Analytics",
        "Interpret pathway compliance, deviations, and workflow investigation surfaces.",
    ),
    (
        "08",
        "Process Performance",
        "Use dense timing drilldowns when the executive workflow views need exact depth.",
    ),
]


def render_overview_page(snapshot: AnalysisSnapshot) -> None:
    summary = _analysis_summary(snapshot)
    _render_overview_topbar(snapshot, summary)

    render_metric_card_grid(
        [
            {
                "eyebrow": "Cohort",
                "title": "Cases",
                "value": format_metric_value(summary.get("cases"), kind="count"),
                "body": "Current filtered run.",
                "tone": "neutral",
            },
            {
                "eyebrow": "Cohort",
                "title": "Events",
                "value": format_metric_value(summary.get("events"), kind="count"),
                "body": "Observed activity records.",
                "tone": "accent",
            },
            {
                "eyebrow": "Pathway",
                "title": "Dominant path",
                "value": _display_optional(summary.get("dominant_path_share"), kind="percent"),
                "body": "Mainline concentration.",
                "tone": "success",
            },
            {
                "eyebrow": "Timing",
                "title": "Median throughput",
                "value": _display_optional(summary.get("median_throughput_days"), kind="days"),
                "body": "Current cohort median.",
                "tone": "neutral",
            },
        ]
    )

    st.markdown(
        "<div class='crpm-overview-command-center' aria-hidden='true'></div>",
        unsafe_allow_html=True,
    )
    left_col, map_col, right_col = st.columns([0.78, 2.0, 1.02], gap="small")

    with left_col:
        st.markdown(
            "<div class='crpm-dashboard-section-title'>Cohort filter rail</div>",
            unsafe_allow_html=True,
        )
        render_dashboard_bar_list("Pathway mix", _overview_pathway_rows(summary))
        render_html_card_grid(
            _overview_signal_cards(snapshot, summary),
            grid_class="crpm-dashboard-card-stack",
        )

    with map_col:
        _render_overview_pathway_preview(snapshot)
        st.markdown(
            (
                "<div class='crpm-reading-order-band'>"
                "<span class='crpm-reading-order-band__eyebrow'>Guide</span>"
                "<span class='crpm-reading-order-band__title'>Reading order</span>"
                "<span class='crpm-reading-order-band__body'>Open the sequence below to see the recommended page flow for this run.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        with st.expander("Reading order", expanded=False):
            st.markdown(
                _render_page_guide_html(snapshot.analysis_complete),
                unsafe_allow_html=True,
            )

    with right_col:
        st.markdown(
            "<div class='crpm-dashboard-section-title'>Evidence rail</div>",
            unsafe_allow_html=True,
        )
        render_dashboard_bar_list("Model evidence", _overview_model_rows(summary))
        render_html_card_grid(
            _overview_status_cards(snapshot, summary),
            grid_class="crpm-dashboard-card-stack",
        )
        if snapshot.analysis_complete:
            render_html_card_grid(
                _overview_quality_cards(snapshot, summary),
                grid_class="crpm-dashboard-card-stack",
            )


def _render_overview_topbar(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> None:
    title = "Overview command center"
    subtitle = (
        "First-event workflow gate remains the production discovery mode for this filtered run."
        if snapshot.analysis_complete
        else "Load an event log and run analysis to populate the cockpit."
    )
    render_dashboard_topbar(
        title=title,
        subtitle=subtitle,
        badges=[
            {"label": "Mode", "value": "Direct workflow mode", "tone": "accent"},
            {
                "label": "Follow-up",
                "value": snapshot.active_followup_label or "Full available follow-up",
                "tone": "success",
            },
            {
                "label": "Models",
                "value": f"{snapshot.model_count:,}",
                "tone": "neutral",
            },
        ],
        meta=[
            snapshot.input_name or "No log loaded",
            summary.get("period_label") or "Period unavailable",
        ],
    )


def _render_overview_pathway_preview(snapshot: AnalysisSnapshot) -> None:
    st.markdown(
        "<div class='crpm-dashboard-section-title'>Central process map</div>",
        unsafe_allow_html=True,
    )
    workflow = _workflow_from_snapshot(snapshot)
    if _workflow_available(workflow):
        board_markup = render_workflow_conformance_svg(workflow, layout_mode="horizontal", detail_level="executive")
        st.markdown(
            f"<div class='crpm-overview-map-frame'>{board_markup}</div>",
            unsafe_allow_html=True,
        )
        return
    render_inline_empty("No workflow preview is available yet. Run conformance to populate the central process map.")


def _workflow_from_snapshot(snapshot: AnalysisSnapshot) -> Mapping[str, Any]:
    workspace = snapshot.conformance_workspace if isinstance(snapshot.conformance_workspace, Mapping) else {}
    workflow = workspace.get("workflow", {}) if isinstance(workspace, Mapping) else {}
    return workflow if isinstance(workflow, Mapping) else {}


def _workflow_available(workflow: Mapping[str, Any]) -> bool:
    nodes = workflow.get("nodes")
    edges = workflow.get("edges")
    nodes_empty = bool(getattr(nodes, "empty", True))
    edges_empty = bool(getattr(edges, "empty", True))
    return not (nodes_empty and edges_empty)


def _overview_pathway_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "Dominant path",
            "value": _coerce_percent(summary.get("dominant_path_share")),
            "tone": "success",
        },
        {
            "label": "Deviation share",
            "value": _coerce_percent(summary.get("deviation_share")),
            "tone": "watch",
        },
    ]


def _overview_model_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "Fitness",
            "value": _score_as_percent(summary.get("best_fitness")),
            "tone": "success",
        },
        {
            "label": "Precision",
            "value": _score_as_percent(summary.get("best_precision")),
            "tone": "accent",
        },
        {
            "label": "Balance",
            "value": _score_as_percent(summary.get("best_balance")),
            "tone": "neutral",
        },
    ]


def _render_overview_hero(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> None:
    title = "CRPM executive overview"
    if snapshot.analysis_complete and snapshot.input_name:
        title = f"{snapshot.input_name} · current filtered run"

    badges = [
        _hero_badge(snapshot.input_name or "No log loaded", tone="neutral"),
        _hero_badge(summary.get("period_label") or "Period unavailable", tone="neutral"),
        _hero_badge(snapshot.active_followup_label or "Full available follow-up", tone="success"),
        _hero_badge(
            (f"{snapshot.model_count:,} model(s)" if snapshot.analysis_complete else "Awaiting analysis"),
            tone="accent",
        ),
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
            "body": f"Fitness {_display_optional(summary.get('best_fitness'), kind='score')} · Precision {_display_optional(summary.get('best_precision'), kind='score')} · Balance {_display_optional(summary.get('best_balance'), kind='score')}",
            "tone": "accent",
            "title_attr": best_model,
        },
        {
            "eyebrow": "Workflow signal",
            "title": "Dominant vs deviation mix",
            "value": f"{_display_optional(summary.get('dominant_path_share'), kind='percent')} dominant",
            "body": f"Deviation share {_display_optional(summary.get('deviation_share'), kind='percent')} · {format_metric_value(summary.get('unique_activities'), kind='count')} activities · {format_metric_value(summary.get('workflow_nodes'), kind='count')} nodes",
            "tone": "neutral",
        },
        {
            "eyebrow": "Timing posture",
            "title": "Current filtered cohort",
            "value": _display_optional(summary.get("median_throughput_days"), kind="days"),
            "body": f"Period {summary.get('period_label', 'Unavailable')} · Runtime {_display_optional(summary.get('analysis_runtime_s'))} s",
            "tone": "success",
        },
    ]


def _overview_status_cards(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "eyebrow": "Analysis status",
            "title": "Current run",
            "value": "Ready" if snapshot.analysis_complete else "Awaiting run",
            "body": (
                "The overview reflects the latest successful filtered run."
                if snapshot.analysis_complete
                else "Load a log and run the analysis to populate discovery, conformance, and timing outputs."
            ),
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
            "body": (
                "Board and explorer use the same workflow payload and right-side inspector."
                if snapshot.conformance_workspace
                else "Run the analysis to build workflow, deviations, and investigation views."
            ),
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


def _coerce_percent(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(min(number, 100.0), 0.0)


def _score_as_percent(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number <= 1.0:
        number *= 100.0
    return max(min(number, 100.0), 0.0)


def _hero_badge(label: str, *, tone: str) -> str:
    return f"<span class='crpm-overview-hero__chip crpm-overview-hero__chip--{html.escape(tone)}'>{html.escape(label)}</span>"
