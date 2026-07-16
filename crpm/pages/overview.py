"""Overview page for the CRPM screening workbench."""

from __future__ import annotations

import html
from typing import Any, Mapping

import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.denominators import denominator_rows
from crpm.log_quality import quality_bar_rows
from crpm.pages.common import (
    format_metric_value,
    redact_dashboard_value,
    render_dashboard_bar_list,
    render_html_card_grid,
    render_inline_empty,
)
from crpm.run_manifest import manifest_to_json
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
OVERVIEW_VIEWS = ("Process map", "Cohort", "Evidence")


def render_overview_page(snapshot: AnalysisSnapshot) -> None:
    summary = _analysis_summary(snapshot)
    st.markdown(
        (
            "<div class='crpm-overview-workbench'>"
            "<div><span>Explore</span><strong>Process overview</strong></div>"
            "<p>Start with the process map, then open cohort or evidence views when the pathway raises a question.</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    render_html_card_grid(
        [
            {
                "eyebrow": "Cohort",
                "title": "Cases",
                "value": format_metric_value(summary.get("cases"), kind="count"),
                "body": "Filtered run",
                "tone": "neutral",
            },
            {
                "eyebrow": "Cohort",
                "title": "Events",
                "value": format_metric_value(summary.get("events"), kind="count"),
                "body": "Activity records",
                "tone": "accent",
            },
            {
                "eyebrow": "Pathway",
                "title": "Mainline coverage",
                "value": _display_optional(summary.get("dominant_path_share"), kind="percent"),
                "body": "Cases sharing the dominant workflow backbone",
                "tone": "success",
            },
            {
                "eyebrow": "Timing",
                "title": "Median throughput",
                "value": _display_optional(summary.get("median_throughput_days"), kind="days"),
                "body": "Cohort median",
                "tone": "neutral",
            },
        ],
        grid_class="crpm-conformance-kpi-strip crpm-overview-kpi-strip",
    )

    active_view = _overview_view_selector(snapshot)

    if active_view == "Cohort":
        pathway_col, cohort_col = st.columns(2, gap="small")
        with pathway_col:
            st.markdown(
                "<div class='crpm-dashboard-section-title'>Pathway and cohort</div>",
                unsafe_allow_html=True,
            )
            render_dashboard_bar_list("Pathway mix", _overview_pathway_rows(summary))
            if _cohort_lens_rows(summary):
                render_dashboard_bar_list("Cohort lenses", _cohort_lens_rows(summary))
        with cohort_col:
            st.markdown(
                "<div class='crpm-dashboard-section-title'>Denominators and signals</div>",
                unsafe_allow_html=True,
            )
            if snapshot.denominator_registry:
                render_dashboard_bar_list(
                    "Denominators",
                    _overview_denominator_rows(snapshot.denominator_registry),
                    value_label="",
                    max_value=_denominator_max(snapshot.denominator_registry),
                )
            render_html_card_grid(
                _overview_signal_cards(snapshot, summary),
                grid_class="crpm-dashboard-card-stack",
            )
        return

    if active_view == "Evidence":
        model_col, status_col = st.columns(2, gap="small")
        with model_col:
            st.markdown(
                "<div class='crpm-dashboard-section-title'>Model and log evidence</div>",
                unsafe_allow_html=True,
            )
            render_dashboard_bar_list("Model evidence", _overview_model_rows(summary))
            if snapshot.analysis_complete and snapshot.log_quality:
                render_dashboard_bar_list("Event log quality", quality_bar_rows(dict(snapshot.log_quality)))
        with status_col:
            st.markdown(
                "<div class='crpm-dashboard-section-title'>Run status</div>",
                unsafe_allow_html=True,
            )
            render_html_card_grid(
                _overview_status_cards(snapshot, summary),
                grid_class="crpm-dashboard-card-stack",
            )
            if snapshot.analysis_complete:
                render_html_card_grid(
                    _overview_quality_cards(snapshot, summary),
                    grid_class="crpm-dashboard-card-stack",
                )
                _render_manifest_download(snapshot)
        return

    _render_overview_pathway_preview(snapshot)
    with st.expander("Workspace guide", expanded=False):
        st.markdown(
            _render_page_guide_html(snapshot.analysis_complete),
            unsafe_allow_html=True,
        )


def _overview_view_selector(snapshot: AnalysisSnapshot) -> str:
    key = f"overview_view_{snapshot.filter_key or 'current'}"
    segmented_control = getattr(st, "segmented_control", None)
    if callable(segmented_control):
        selected = segmented_control(
            "Overview view",
            OVERVIEW_VIEWS,
            default=OVERVIEW_VIEWS[0],
            key=key,
            selection_mode="single",
            label_visibility="collapsed",
        )
        if selected in OVERVIEW_VIEWS:
            return str(selected)
    return str(
        st.radio(
            "Overview view",
            OVERVIEW_VIEWS,
            index=0,
            key=key,
            horizontal=True,
            label_visibility="collapsed",
        )
    )


def _render_overview_pathway_preview(snapshot: AnalysisSnapshot) -> None:
    st.markdown(
        "<div class='crpm-dashboard-section-title'>Central process map</div>",
        unsafe_allow_html=True,
    )
    workflow = _workflow_from_snapshot(snapshot)
    if _workflow_available(workflow):
        board_markup = render_workflow_conformance_svg(workflow, layout_mode="horizontal", detail_level="analyst")
        st.markdown(
            f"<div class='crpm-overview-map-frame crpm-overview-map-frame--expanded'>{board_markup}</div>",
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
            "label": "Mainline coverage",
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
            "title": "Mainline vs deviation mix",
            "value": f"{_display_optional(summary.get('dominant_path_share'), kind='percent')} mainline",
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
    cache_summary = _cache_telemetry_summary(summary)
    cache_entries = cache_summary.get("total_entries")
    cache_capacity = cache_summary.get("total_capacity")
    cache_utilization = cache_summary.get("utilization_pct")
    legacy_cache_entries = len(snapshot.performance_cache) + len(snapshot.variant_cache) + len(snapshot.dfg_cache)
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
            "value": (
                f"{format_metric_value(cache_entries, kind='count')} entries"
                if cache_entries is not None
                else f"{legacy_cache_entries:,} entries"
            ),
            "body": (
                f"Capacity {format_metric_value(cache_capacity, kind='count')} · utilization {_display_optional(cache_utilization, kind='percent')}"
                if cache_summary
                else f"Performance {len(snapshot.performance_cache):,} · Variants {len(snapshot.variant_cache):,} · DFG {len(snapshot.dfg_cache):,}"
            ),
            "tone": "accent",
        },
    ]


def _overview_quality_cards(snapshot: AnalysisSnapshot, summary: Mapping[str, Any]) -> list[dict[str, str]]:
    quality_summary = {}
    if isinstance(snapshot.log_quality, Mapping):
        quality_summary = snapshot.log_quality.get("summary", {}) if isinstance(snapshot.log_quality.get("summary"), Mapping) else {}
    source_metadata = snapshot.source_metadata if isinstance(snapshot.source_metadata, Mapping) else {}
    return [
        {
            "eyebrow": "Provenance",
            "title": "Source validation",
            "value": str(source_metadata.get("validation_status") or summary.get("source_validation_status") or "N/A"),
            "body": (
                f"{redact_dashboard_value(source_metadata.get('display_name') or snapshot.input_name)} · "
                f"{redact_dashboard_value(source_metadata.get('source_kind') or 'source')} · "
                f"{format_metric_value(source_metadata.get('size_bytes'), kind='count')} bytes"
            ),
            "tone": "accent",
        },
        {
            "eyebrow": "Quality",
            "title": "Accepted event log",
            "value": str(quality_summary.get("quality_status") or "N/A").upper(),
            "body": (
                f"Required fields {_display_optional(quality_summary.get('required_field_completeness_pct'), kind='percent')} · "
                f"duplicates {format_metric_value(quality_summary.get('duplicate_event_count'), kind='count')} · "
                f"timezone {quality_summary.get('timezone_mode', 'N/A')} · "
                f"semantic {quality_summary.get('semantic_status', 'N/A')}"
            ),
            "tone": _quality_card_tone(str(quality_summary.get("quality_status") or "")),
        },
        {
            "eyebrow": "Preprocessing",
            "title": "Filter impact",
            "value": _display_optional(_preprocessing_impact(summary).get("filter_case_retention_pct"), kind="percent"),
            "body": (
                f"Source {_display_optional(_preprocessing_impact(summary).get('source_cases'), kind='count')} cases · "
                f"filtered {_display_optional(_preprocessing_impact(summary).get('filtered_cases'), kind='count')} · "
                f"evaluation {_display_optional(_preprocessing_impact(summary).get('evaluation_cases'), kind='count')}"
            ),
            "tone": "neutral",
        },
        {
            "eyebrow": "Process behaviour",
            "title": "Loop/rework posture",
            "value": _display_optional(_loop_rework_metrics(summary).get("rework_cases_pct"), kind="percent"),
            "body": (
                f"Self-loop cases {_display_optional(_loop_rework_metrics(summary).get('self_loop_cases_pct'), kind='percent')} · "
                f"loop cases {_display_optional(_loop_rework_metrics(summary).get('loop_cases_pct'), kind='percent')} · "
                f"denominator {_display_optional(_loop_rework_metrics(summary).get('case_count'), kind='count')} cases"
            ),
            "tone": "accent",
        },
        {
            "eyebrow": "Monitoring",
            "title": "Latest period",
            "value": _display_optional(_time_series_summary(summary).get("latest_case_count"), kind="count"),
            "body": (
                f"Median throughput {_display_optional(_time_series_summary(summary).get('latest_median_throughput_days'), kind='days')} · "
                f"case volume delta {_display_optional(_time_series_summary(summary).get('case_volume_delta'), kind='count')}"
            ),
            "tone": "neutral",
        },
        {
            "eyebrow": "Resources",
            "title": "Resource perspective",
            "value": _display_optional(_resource_summary(summary).get("resource_count"), kind="count"),
            "body": (
                f"Handoffs {_display_optional(_resource_summary(summary).get('handoff_count'), kind='count')} · "
                f"coverage {_display_optional(_resource_summary(summary).get('resource_coverage_pct'), kind='percent')}"
            ),
            "tone": "accent",
        },
        {
            "eyebrow": "Conformance",
            "title": "Root-cause summary",
            "value": _display_optional(_root_cause_summary(summary).get("deviating_trace_count"), kind="count"),
            "body": (
                f"Model-deviation activities {_display_optional(_root_cause_summary(summary).get('model_deviation_activity_count'), kind='count')} · "
                f"log-deviation transitions {_display_optional(_root_cause_summary(summary).get('log_deviation_transition_count'), kind='count')}"
            ),
            "tone": "neutral",
        },
        {
            "eyebrow": "Coverage",
            "title": "Mainline coverage",
            "value": _display_optional(summary.get("dominant_path_share"), kind="percent"),
            "body": "Share of cases following the dominant workflow backbone. Use Variant Analysis for exact trace concentration.",
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


def _overview_denominator_rows(registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": row["label"],
            "value": row["value"],
            "display": format_metric_value(row["value"], kind="count"),
            "tone": "accent" if row["key"] in {"path_denominator", "activity_denominator"} else "neutral",
        }
        for row in denominator_rows(registry)
    ]


def _denominator_max(registry: Mapping[str, Any]) -> float:
    values = [float(row["value"]) for row in denominator_rows(registry)]
    return max(values) if values else 1.0


def _render_manifest_download(snapshot: AnalysisSnapshot) -> None:
    if not snapshot.run_manifest:
        return
    st.markdown(
        """
        <div class="crpm-manifest-download-note">
            <strong>Reproducibility record</strong>
            <span>JSON summary of the input, filters, algorithms and quality checks. Local paths are redacted.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        "Download run record (.json)",
        data=manifest_to_json(snapshot.run_manifest),
        file_name="crpm_run_manifest.json",
        mime="application/json",
        help="Use this record to audit or reproduce the current analysis run.",
        use_container_width=True,
    )


def _quality_card_tone(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "ok":
        return "success"
    if normalized == "warning":
        return "neutral"
    return "danger"


def _preprocessing_impact(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("preprocessing_impact", {})
    return value if isinstance(value, Mapping) else {}


def _loop_rework_metrics(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("loop_rework_metrics", {})
    return value if isinstance(value, Mapping) else {}


def _cohort_lens_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    cohort_lenses = summary.get("cohort_lenses", {})
    rows = cohort_lenses.get("rows", []) if isinstance(cohort_lenses, Mapping) else []
    if not isinstance(rows, list):
        return []
    return [
        {"label": row.get("label"), "value": row.get("share_pct"), "display": format_metric_value(row.get("count"), kind="count")}
        for row in rows[:6]
        if isinstance(row, Mapping)
    ]


def _time_series_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("time_series_monitoring", {})
    nested = value.get("summary", {}) if isinstance(value, Mapping) else {}
    return nested if isinstance(nested, Mapping) else {}


def _resource_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("resource_perspective", {})
    nested = value.get("summary", {}) if isinstance(value, Mapping) else {}
    return nested if isinstance(nested, Mapping) else {}


def _root_cause_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("conformance_root_causes", {})
    nested = value.get("summary", {}) if isinstance(value, Mapping) else {}
    return nested if isinstance(nested, Mapping) else {}


def _cache_telemetry_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    value = summary.get("cache_telemetry", {})
    nested = value.get("summary", {}) if isinstance(value, Mapping) else {}
    return nested if isinstance(nested, Mapping) else {}


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
