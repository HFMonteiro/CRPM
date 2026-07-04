"""Conformance page for the staged CRPM refactor."""

from __future__ import annotations

import html
import logging
from typing import Any, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from crpm.app_state import (
    AnalysisSnapshot,
    CRPMState,
    bounded_cache_get,
    bounded_cache_put,
    get_crpm_state,
)
from crpm.formatting import format_decimal as format_display_decimal
from crpm.formatting import format_metric_value as format_display_metric
from crpm.interpretations import assess_fitness, assess_precision
from crpm.pages.common import (
    render_dashboard_bar_list,
    render_dashboard_topbar,
    render_empty_state,
    render_html_card_grid,
    render_html_ranked_table,
    render_inline_empty,
    render_legend_note,
    render_quiet_note,
)
from crpm.screening import humanize_activity_label
from crpm.visualization import (
    create_workflow_cytoscape_payload,
    create_workflow_interactive_payload,
    filter_workflow_payload,
    render_workflow_bpmn_style_svg,
    render_workflow_conformance_svg,
    render_workflow_explorer_html,
    workflow_edge_uid,
)

try:  # optional interactive workflow dependency
    from streamlit_cytoscape import streamlit_cytoscape  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    streamlit_cytoscape = None


logger = logging.getLogger(__name__)
WORKFLOW_VIEW_CACHE_VERSION = "workflow-view-v3"
WORKFLOW_LOCAL_FOCUS_HINT = "Local focus is visual only. Pin from the right rail for exact metrics."
WORKFLOW_FILTER_DEFAULTS = {
    "workflow_mode": "Explorer",
    "filter_category": "Pathway",
    "coverage_view": "All",
    "deviation_view": "All",
    "metric_coloring": "Conformance bucket",
    "detail_level": "Analyst",
    "conformance_lens": "% of paths",
}
WORKFLOW_FILTER_CATEGORIES = ["Pathway", "Deviation", "Display", "Actions"]
WORKFLOW_VIEW_OPTIONS = ["Explorer", "Board", "BPMN style"]
WORKFLOW_VIEW_LABELS = {"explorer": "Explorer", "board": "Board", "bpmn": "BPMN style"}


def render_conformance_page(snapshot: AnalysisSnapshot) -> None:
    workspace = _get_workspace(snapshot)
    model_summary_df = workspace.get("model_summary_df", pd.DataFrame()) if isinstance(workspace, dict) else pd.DataFrame()
    deviation_summary_df = workspace.get("deviation_summary_df", pd.DataFrame()) if isinstance(workspace, dict) else pd.DataFrame()
    trace_deviation_df = workspace.get("trace_deviation_df", pd.DataFrame()) if isinstance(workspace, dict) else pd.DataFrame()
    workflow = workspace.get("workflow", {}) if isinstance(workspace, dict) else {}

    if model_summary_df.empty and snapshot.comparison_df.empty:
        render_empty_state("No conformance results yet. Run the analysis from the sidebar to populate this page.")
        return

    if model_summary_df.empty and not snapshot.comparison_df.empty:
        model_summary_df = snapshot.comparison_df.copy()

    nodes_df, edges_df, legend_df = _workflow_dfs(workflow)
    has_workflow = not (nodes_df.empty and edges_df.empty)
    if not has_workflow and not model_summary_df.empty:
        render_quiet_note("No workflow graph could be derived for this selection. The model and deviation tables remain available.")

    st.subheader("Conformance Analytics")
    _render_conformance_header(workflow=workflow, model_summary_df=model_summary_df)

    if has_workflow:
        controls = _workflow_controls_from_state(snapshot)
    else:
        controls = {
            "workflow_mode": _normalize_workflow_mode(WORKFLOW_FILTER_DEFAULTS["workflow_mode"]),
            "coverage_view": "all",
            "deviation_view": "All",
            "metric_coloring": "Conformance bucket",
            "detail_level": snapshot.workflow_detail_level,
            "conformance_lens": "% of paths",
            "reset_filters": False,
            "reset_graph_viewport": False,
        }

    if has_workflow:
        workflow_mode = _normalize_workflow_mode(controls.get("workflow_mode"))
        current_selection_kind = (
            snapshot.workflow_selection_kind if snapshot.workflow_selection_kind in {"node", "edge", "none"} else "none"
        )
        current_selection_id = snapshot.workflow_selection_id
        _store_workflow_state(
            snapshot,
            workflow_view_mode=workflow_mode,
            workflow_detail_level=controls["detail_level"],
        )
        if controls["reset_filters"]:
            _reset_workflow_filters(snapshot)
            current_selection_kind = "none"
            current_selection_id = None
        filtered_workflow = _get_filtered_workflow(snapshot, workflow, controls)
        if isinstance(filtered_workflow, dict):
            filtered_workflow = dict(filtered_workflow)
            filtered_workflow["conformance_lens"] = controls["conformance_lens"]
            _annotate_workflow_renderer_metadata(
                filtered_workflow,
                base_workflow=workflow if isinstance(workflow, dict) else None,
                renderer_role="conformance_explorer",
            )
        filtered_nodes_df, filtered_edges_df, filtered_legend_df = _workflow_dfs(filtered_workflow)
        current_selection_kind, current_selection_id = _coerce_selection_to_visible_subset(
            nodes_df=filtered_nodes_df,
            edges_df=filtered_edges_df,
            selection_kind=current_selection_kind,
            selection_id=current_selection_id,
        )
    else:
        workflow_mode = _normalize_workflow_mode(controls.get("workflow_mode"))
        filtered_workflow = dict(workflow) if isinstance(workflow, dict) else workflow
        if isinstance(filtered_workflow, dict):
            filtered_workflow["conformance_lens"] = controls["conformance_lens"]
            _annotate_workflow_renderer_metadata(
                filtered_workflow,
                base_workflow=workflow if isinstance(workflow, dict) else None,
                renderer_role="conformance_explorer",
            )
        filtered_nodes_df, filtered_edges_df, filtered_legend_df = (
            nodes_df,
            edges_df,
            legend_df,
        )
        current_selection_kind = "none"
        current_selection_id = None

    if has_workflow:
        _render_workflow_kpi_strip(
            snapshot,
            filtered_workflow,
            controls,
            model_summary_df=model_summary_df,
            grid_class="crpm-conformance-kpi-strip crpm-conformance-kpi-strip--cockpit",
        )

    filter_col, main_col, detail_col = st.columns([0.5, 2.86, 0.7], gap="small")

    with filter_col:
        _render_conformance_filter_rail(
            snapshot,
            filtered_workflow,
            controls,
            model_summary_df=model_summary_df,
        )

    with main_col:
        stage_actions = _render_workflow_stage_toolbar(snapshot=snapshot, workflow=filtered_workflow, controls=controls)
        if stage_actions["reset_selection"]:
            _clear_workflow_selection(snapshot)
            _store_workflow_state(
                snapshot,
                workflow_selection_kind="none",
                workflow_selection_id=None,
                selected_workflow_node_id=None,
                selected_workflow_edge_id=None,
            )
            current_selection_kind = "none"
            current_selection_id = None

        if has_workflow:
            selection_kind, selection_id = _render_workflow_board_or_graph(
                workflow=filtered_workflow,
                nodes_df=filtered_nodes_df,
                edges_df=filtered_edges_df,
                workflow_mode=workflow_mode,
                snapshot=snapshot,
                metric_coloring=controls["metric_coloring"],
                detail_level=controls["detail_level"],
                selection_kind=current_selection_kind,
                selection_id=current_selection_id,
            )
        else:
            selection_kind = "none"
            selection_id = None
            render_inline_empty(
                "No workflow graph is available for this selection. Use the model and deviation summaries in the inspector."
            )
    with detail_col:
        _render_conformance_side_intro(
            title="Inspector",
            lead="Pin one node or transition only when exact evidence is needed.",
            variant="inspector",
        )
        pinned_kind, pinned_id = _render_right_panel(
            snapshot=snapshot,
            model_summary_df=model_summary_df,
            deviation_summary_df=deviation_summary_df,
            trace_deviation_df=trace_deviation_df,
            nodes_df=filtered_nodes_df,
            edges_df=filtered_edges_df,
            legend_df=filtered_legend_df,
            workflow=filtered_workflow,
            controls=controls,
            selection_kind=selection_kind,
            selection_id=selection_id,
        )
    _store_workflow_state(
        snapshot,
        workflow_selection_kind=pinned_kind,
        workflow_selection_id=pinned_id,
        selected_workflow_node_id=pinned_id if pinned_kind == "node" else None,
        selected_workflow_edge_id=pinned_id if pinned_kind == "edge" else None,
    )
    if has_workflow:
        _render_board_export_view(
            filtered_workflow,
            model_summary_df=model_summary_df,
            nodes_df=filtered_nodes_df,
            edges_df=filtered_edges_df,
        )


def _render_workflow_board_or_graph(
    *,
    workflow: dict[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    workflow_mode: str,
    snapshot: AnalysisSnapshot,
    metric_coloring: str,
    detail_level: str,
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[str, Optional[str]]:
    if nodes_df.empty and edges_df.empty:
        st.caption("No workflow structure could be derived from the current filtered log.")
        return "none", None

    workflow_mode = _normalize_workflow_mode(workflow_mode)
    if workflow_mode == "explorer":
        graph_rendered, selection_kind, selection_id, fallback_message = _render_interactive_workflow_graph(
            workflow,
            nodes_df,
            edges_df,
            snapshot,
            metric_coloring=metric_coloring,
            detail_level=detail_level,
            selection_kind=selection_kind,
            selection_id=selection_id,
        )
        if graph_rendered:
            return selection_kind, selection_id
        if fallback_message:
            st.warning(fallback_message)
        workflow_for_render = _workflow_payload_with_selection(workflow, selection_kind=selection_kind, selection_id=selection_id)
        st.markdown(render_workflow_conformance_svg(workflow_for_render), unsafe_allow_html=True)
        return selection_kind, selection_id

    workflow_for_render = _workflow_payload_with_selection(workflow, selection_kind=selection_kind, selection_id=selection_id)
    if workflow_mode == "bpmn":
        st.markdown(
            render_workflow_bpmn_style_svg(
                workflow_for_render,
                metric_coloring=metric_coloring,
                detail_level=detail_level,
            ),
            unsafe_allow_html=True,
        )
        return selection_kind, selection_id

    st.markdown(
        render_workflow_conformance_svg(
            workflow_for_render,
            layout_mode="horizontal",
            detail_level=detail_level,
        ),
        unsafe_allow_html=True,
    )
    return selection_kind, selection_id


def _workflow_payload_with_selection(
    workflow: dict[str, Any],
    *,
    selection_kind: str,
    selection_id: Optional[str],
) -> dict[str, Any]:
    workflow_for_render = dict(workflow) if isinstance(workflow, dict) else {}
    workflow_for_render["selected_node_id"] = selection_id if selection_kind == "node" else None
    workflow_for_render["selected_edge_uid"] = selection_id if selection_kind == "edge" else None
    return workflow_for_render


def _render_interactive_workflow_graph(
    workflow: dict[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    snapshot: AnalysisSnapshot,
    *,
    metric_coloring: str,
    detail_level: str,
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[bool, str, Optional[str], Optional[str]]:
    try:
        selected_node_id = selection_id if selection_kind == "node" else None
        selected_edge_id = selection_id if selection_kind == "edge" else None
        viewport_nonce = int(st.session_state.get(_widget_key(snapshot, "workflow_viewport_nonce"), 0) or 0)
        workflow_for_render = dict(workflow) if isinstance(workflow, dict) else workflow
        if isinstance(workflow_for_render, dict):
            workflow_for_render["selected_node_id"] = selected_node_id
            workflow_for_render["selected_edge_uid"] = selected_edge_id
        explorer_payload = create_workflow_interactive_payload(
            workflow_for_render,
            metric_coloring=metric_coloring,
            detail_level=detail_level,
            selected_node_id=selected_node_id,
            selected_edge_id=selected_edge_id,
        )
        explorer_payload["instance_id"] = f"{_widget_key(snapshot, 'workflow_explorer_html')}_{viewport_nonce}"
        initial_frame_height = int(explorer_payload.get("frame_height", int(explorer_payload.get("height", 520)) + 116)) + 56
        components.html(
            render_workflow_explorer_html(explorer_payload),
            height=initial_frame_height,
            scrolling=True,
        )
        return True, selection_kind, selection_id, None
    except Exception:
        logger.exception("Interactive workflow graph rendering failed")
        if streamlit_cytoscape is not None:
            try:
                cyto_payload = create_workflow_cytoscape_payload(workflow)
                selection = streamlit_cytoscape(
                    elements=cyto_payload["elements"],
                    layout=cyto_payload.get("layout", "preset"),
                    node_styles=cyto_payload.get("node_styles", []),
                    edge_styles=cyto_payload.get("edge_styles", []),
                    events=cyto_payload.get("events", []),
                    height=560,
                    key=f"{_widget_key(snapshot, 'workflow_sync_cytoscape')}_{viewport_nonce}",
                )
                selected_node, selected_edge = _coerce_graph_selection(selection)
                render_legend_note(
                    "CRPM fell back to the technical workflow component because the primary process figure could not be rendered."
                )
                if selected_edge:
                    return True, "edge", selected_edge, None
                if selected_node:
                    return True, "node", selected_node, None
                return True, selection_kind, selection_id, None
            except Exception:
                logger.exception("Cytoscape fallback also failed")
        return (
            False,
            "none",
            None,
            "Interactive workflow mode could not be rendered for this selection. CRPM is showing the SVG board instead. Check the workflow component installation and retry.",
        )


def _render_right_panel(
    *,
    snapshot: AnalysisSnapshot,
    model_summary_df: pd.DataFrame,
    deviation_summary_df: pd.DataFrame,
    trace_deviation_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    legend_df: pd.DataFrame,
    workflow: dict[str, Any],
    controls: dict[str, Any],
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[str, Optional[str]]:
    st.markdown(
        "<div class='crpm-conformance-side-subtitle'>Selection focus</div>",
        unsafe_allow_html=True,
    )
    selected_kind, selected_id, node_row, edge_row = _render_selection_focus(
        snapshot=snapshot,
        nodes_df=nodes_df,
        edges_df=edges_df,
        workflow=workflow,
        selection_kind=selection_kind,
        selection_id=selection_id,
    )
    if selected_id:
        st.markdown(
            "<div class='crpm-conformance-side-subtitle'>Pinned exact metrics</div>",
            unsafe_allow_html=True,
        )
        _render_event_process_details(
            model_summary_df=model_summary_df,
            nodes_df=nodes_df,
            edges_df=edges_df,
            metric_coloring=controls["metric_coloring"],
            detail_level=controls["detail_level"],
            selected_node_id=selected_id if selected_kind == "node" else None,
            selected_edge_id=selected_id if selected_kind == "edge" else None,
        )

    st.markdown(
        "<div class='crpm-conformance-side-subtitle'>Watchlist</div>",
        unsafe_allow_html=True,
    )
    _render_root_cause_watchlist(snapshot)
    _render_workflow_lead_time_rail(workflow=workflow, nodes_df=nodes_df, edges_df=edges_df)

    with st.expander("Context", expanded=False):
        _render_workflow_scope_rail(workflow)
        _render_resource_perspective(snapshot)
        _render_insight_action_panel(workflow, controls)

    with st.expander("Drilldown", expanded=False):
        _render_reference_model_panel(model_summary_df)
        if model_summary_df.empty:
            render_inline_empty("No model posture is available for this selection.")
        else:
            _render_model_posture_section(model_summary_df)
        _render_supporting_detail_tabs(
            workflow=workflow,
            legend_df=legend_df,
            deviation_summary_df=deviation_summary_df,
            trace_deviation_df=trace_deviation_df,
            controls=controls,
        )
    return selected_kind, selected_id


def _render_workflow_evidence_rail(*, workflow: dict[str, Any], nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> None:
    _render_workflow_scope_rail(workflow)
    _render_workflow_lead_time_rail(workflow=workflow, nodes_df=nodes_df, edges_df=edges_df)


def _render_root_cause_watchlist(snapshot: AnalysisSnapshot) -> None:
    workspace = _get_workspace(snapshot)
    root_causes = workspace.get("conformance_root_causes", {}) if isinstance(workspace, dict) else {}
    top_causes = root_causes.get("top_causes", []) if isinstance(root_causes, dict) else []
    if isinstance(top_causes, list) and top_causes:
        rows = []
        for cause in top_causes[:4]:
            if not isinstance(cause, dict):
                continue
            rows.append(
                {
                    "label": str(cause.get("label") or cause.get("issue") or "Conformance issue"),
                    "value": _coerce_float(cause.get("count")) or 0.0,
                    "display": _format_number(cause.get("count")),
                    "tone": str(cause.get("severity") or cause.get("issue") or "neutral"),
                }
            )
        if rows:
            render_dashboard_bar_list("Root-cause watchlist", rows, value_label="")
            return

    summary = root_causes.get("summary", {}) if isinstance(root_causes, dict) else {}
    if not isinstance(summary, dict) or not any(_coerce_int(summary.get(key)) for key in summary):
        return
    render_dashboard_bar_list(
        "Root-cause watchlist",
        [
            {
                "label": "Deviating traces",
                "value": float(_coerce_int(summary.get("deviating_trace_count"))),
                "display": _format_number(summary.get("deviating_trace_count")),
                "tone": "warning",
            },
            {
                "label": "Model-deviation activities",
                "value": float(_coerce_int(summary.get("model_deviation_activity_count"))),
                "display": _format_number(summary.get("model_deviation_activity_count")),
                "tone": "danger",
            },
            {
                "label": "Log-deviation transitions",
                "value": float(_coerce_int(summary.get("log_deviation_transition_count"))),
                "display": _format_number(summary.get("log_deviation_transition_count")),
                "tone": "watch",
            },
        ],
        value_label="",
    )


def _render_resource_perspective(snapshot: AnalysisSnapshot) -> None:
    workspace = _get_workspace(snapshot)
    perspective = workspace.get("resource_perspective", {}) if isinstance(workspace, dict) else {}
    summary = perspective.get("summary", {}) if isinstance(perspective, dict) else {}
    if not isinstance(summary, dict) or not any(_coerce_int(summary.get(key)) for key in summary):
        return
    render_dashboard_bar_list(
        "Resource perspective",
        [
            {
                "label": "Resources",
                "value": float(_coerce_int(summary.get("resource_count"))),
                "display": _format_number(summary.get("resource_count")),
                "tone": "neutral",
            },
            {
                "label": "Handoffs",
                "value": float(_coerce_int(summary.get("handoff_count"))),
                "display": _format_number(summary.get("handoff_count")),
                "tone": "accent",
            },
            {
                "label": "Resource coverage",
                "value": _coerce_float(summary.get("resource_coverage_pct")) or 0.0,
                "display": f"{(_coerce_float(summary.get('resource_coverage_pct')) or 0.0):.1f}%",
                "tone": "success",
            },
        ],
        value_label="",
    )


def _render_workflow_scope_rail(workflow: dict[str, Any]) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    visible_cases = _coerce_int(summary.get("visible_case_count", summary.get("cases_covered")))
    excluded_cases = _coerce_int(summary.get("excluded_case_count"))
    path_denominator = _coerce_int(summary.get("path_denominator"))
    if visible_cases or excluded_cases or path_denominator:
        scope_rows = [
            {
                "label": "Visible cases",
                "value": float(visible_cases),
                "display": f"{visible_cases:,}" + (f" / {path_denominator:,}" if path_denominator else ""),
                "tone": "neutral",
            }
        ]
        if excluded_cases:
            scope_rows.append(
                {
                    "label": "Excluded by view",
                    "value": float(excluded_cases),
                    "display": f"{excluded_cases:,}",
                    "tone": "warning",
                }
            )
        render_dashboard_bar_list("Cohort scope", scope_rows, value_label="")


def _render_workflow_lead_time_rail(*, workflow: dict[str, Any], nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    throughput = _coerce_float(summary.get("median_throughput_days"))
    if throughput is not None:
        render_dashboard_bar_list(
            "Lead-time headline",
            [
                {
                    "label": "Median throughput",
                    "value": throughput,
                    "display": f"{throughput:.1f} d",
                    "tone": "neutral",
                }
            ],
            value_label=" d",
        )

    if not edges_df.empty:
        working = edges_df.copy()
        ranking_column = "p90_days" if "p90_days" in working.columns else "median_days"
        if ranking_column in working.columns:
            working["_delay_rank"] = pd.to_numeric(working[ranking_column], errors="coerce").fillna(0)
            working = working.sort_values(by=["_delay_rank"], ascending=False).head(4)
            rows = []
            for _, row in working.iterrows():
                value = float(row.get("_delay_rank", 0) or 0)
                rows.append(
                    {
                        "label": _edge_display_label(row),
                        "value": value,
                        "display": f"{value:.1f} d",
                        "tone": row.get("severity", "neutral"),
                    }
                )
            render_dashboard_bar_list("Lead-time watchlist", rows, value_label=" d")
            return

    if not nodes_df.empty and "cases" in nodes_df.columns:
        working = nodes_df.copy()
        working["_cases"] = pd.to_numeric(working["cases"], errors="coerce").fillna(0)
        working = working.sort_values(by=["_cases"], ascending=False).head(4)
        render_dashboard_bar_list(
            "Activity evidence",
            [
                {
                    "label": _node_display_label(row),
                    "value": float(row.get("_cases", 0) or 0),
                    "display": _format_number(row.get("_cases")),
                    "tone": row.get("severity", "neutral"),
                }
                for _, row in working.iterrows()
            ],
            value_label="",
        )


def _render_selection_focus(
    *,
    snapshot: AnalysisSnapshot,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    workflow: dict[str, Any],
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[str, Optional[str], Optional[pd.Series], Optional[pd.Series]]:
    return _render_selection_focus_content(
        snapshot=snapshot,
        nodes_df=nodes_df,
        edges_df=edges_df,
        workflow=workflow,
        selection_kind=selection_kind,
        selection_id=selection_id,
    )


def _render_selection_focus_content(
    *,
    snapshot: AnalysisSnapshot,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    workflow: dict[str, Any],
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[str, Optional[str], Optional[pd.Series], Optional[pd.Series]]:
    normalized_kind = selection_kind if selection_kind in {"node", "edge", "none"} else "none"
    selected_node_id = selection_id if normalized_kind == "node" else None
    selected_edge_id = selection_id if normalized_kind == "edge" else None

    _render_selector_guide(selection_kind=normalized_kind, selection_id=selection_id)

    selector_kind_key = _widget_key(snapshot, "selection_kind")
    selector_kind_label = _render_choice_control(
        "Pinned metric type",
        ["Overview", "Node", "Edge"],
        key=selector_kind_key,
        default={"none": "Overview", "node": "Node", "edge": "Edge"}.get(normalized_kind, "Overview"),
    )
    active_kind = {"Overview": "none", "Node": "node", "Edge": "edge"}.get(selector_kind_label, "none")

    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    node_row: Optional[pd.Series] = None
    edge_row: Optional[pd.Series] = None

    if active_kind == "node":
        node_id, node_row = _render_selector(
            label="Pinned node",
            df=nodes_df,
            id_column="activity",
            default_id=selected_node_id,
            key=_widget_key(snapshot, "selected_node"),
            format_label=_node_option_label,
            empty_label="Overview (node not pinned)",
        )
    elif active_kind == "edge":
        edge_id, edge_row = _render_selector(
            label="Pinned edge",
            df=_workflow_edges_with_ids(edges_df),
            id_column="edge_uid",
            default_id=selected_edge_id,
            key=_widget_key(snapshot, "selected_edge"),
            format_label=_edge_option_label,
            empty_label="Overview (edge not pinned)",
        )

    next_kind = "none"
    next_id = None
    if node_id:
        next_kind = "node"
        next_id = node_id
    elif edge_id:
        next_kind = "edge"
        next_id = edge_id

    _store_workflow_state(
        snapshot,
        workflow_selection_kind=next_kind,
        workflow_selection_id=next_id,
        selected_workflow_node_id=next_id if next_kind == "node" else None,
        selected_workflow_edge_id=next_id if next_kind == "edge" else None,
    )

    selection_active = bool(next_id)
    _render_selection_summary_card(
        node_row=node_row if next_kind == "node" else None,
        edge_row=edge_row if next_kind == "edge" else None,
    )
    if next_kind == "node" and node_row is not None:
        st.markdown("###### Node metrics")
        _render_detail_card(_format_node_detail(node_row), card_kind="node")

    if next_kind == "edge" and edge_row is not None:
        st.markdown("###### Edge metrics")
        _render_detail_card(_format_edge_detail(edge_row), card_kind="edge")

    if selection_active:
        with st.expander("Related variants and case context", expanded=True):
            _render_related_trace_context(workflow, node_row=node_row, edge_row=edge_row)

    return next_kind, next_id, node_row, edge_row


def _render_selector_guide(*, selection_kind: str, selection_id: Optional[str]) -> None:
    if selection_kind == "node" and selection_id:
        state = f"Pinned node: {humanize_activity_label(selection_id) or selection_id}"
    elif selection_kind == "edge" and selection_id:
        state = f"Pinned transition: {humanize_activity_label(selection_id) or selection_id}"
    else:
        state = "Overview active: no pinned detail"
    st.markdown(
        (
            "<div class='crpm-conformance-panel crpm-conformance-panel--muted'>"
            "<div class='crpm-conformance-panel__eyebrow'>Selection state</div>"
            f"<div class='crpm-conformance-panel__body'><strong>{html.escape(state)}</strong></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_supporting_detail_tabs(
    *,
    workflow: dict[str, Any],
    legend_df: pd.DataFrame,
    deviation_summary_df: pd.DataFrame,
    trace_deviation_df: pd.DataFrame,
    controls: dict[str, Any],
) -> None:
    support_tabs = st.tabs(["Legend", "Deviations", "Trace"])
    with support_tabs[0]:
        render_legend_note(
            f"Path view: {controls['coverage_view'].title()} · Deviation focus: {controls['deviation_view']} · Color by: {controls['metric_coloring']} · Density: {controls['detail_level'].title()}"
        )
        legend_display = _legend_fallback_table(workflow) if legend_df.empty else legend_df.copy()
        legend_display = legend_display.rename(columns={"bucket": "Bucket", "meaning": "Meaning", "severity": "Severity"})
        render_html_ranked_table(
            legend_display[[column for column in ("Bucket", "Meaning", "Severity") if column in legend_display.columns]],
            title="Legend guide",
            label_column="Meaning",
            chip_column="Severity" if "Severity" in legend_display.columns else None,
        )

    with support_tabs[1]:
        if deviation_summary_df.empty:
            render_inline_empty("No model-level deviation summary was extracted for the current selection.")
        else:
            render_legend_note(
                "Alignment replay summarizes strict replay fit. Token replay highlights how much of the observed log replays cleanly against the model."
            )
            deviation_display = _format_deviation_summary(deviation_summary_df).rename(
                columns={
                    "model": "Model",
                    "precision": "Precision",
                    "alignment_summary": "Alignment replay",
                    "token_summary": "Token replay",
                    "deviation_note": "Interpretation",
                }
            )
            preferred_columns = [
                column
                for column in (
                    "Model",
                    "Precision",
                    "Alignment replay",
                    "Token replay",
                    "Interpretation",
                )
                if column in deviation_display.columns
            ]
            render_html_ranked_table(
                deviation_display[preferred_columns],
                title="Deviation summary",
                label_column=("Interpretation" if "Interpretation" in deviation_display.columns else preferred_columns[0]),
            )

    with support_tabs[2]:
        if trace_deviation_df.empty:
            render_inline_empty("No trace-level deviations were extracted for the current selection.")
        else:
            render_legend_note(
                "Lower fitness and higher replay cost usually indicate traces that diverge more strongly from the selected reference model."
            )
            trace_display = _format_trace_deviations(trace_deviation_df).rename(
                columns={
                    "model": "Model",
                    "trace_index": "Trace",
                    "alignment_fitness": "Alignment fitness",
                    "token_trace_fitness": "Token fitness",
                    "alignment_cost": "Alignment cost",
                    "trace_status": "Trace status",
                }
            )
            preferred_columns = [
                column
                for column in (
                    "Trace",
                    "Trace status",
                    "Alignment fitness",
                    "Token fitness",
                    "Alignment cost",
                    "Model",
                )
                if column in trace_display.columns
            ]
            render_html_ranked_table(
                trace_display[preferred_columns],
                title="Trace deviations",
                label_column=("Trace" if "Trace" in trace_display.columns else preferred_columns[0]),
                chip_column=("Trace status" if "Trace status" in trace_display.columns else None),
            )


def _workflow_controls_from_state(snapshot: AnalysisSnapshot) -> dict[str, Any]:
    mode_key = _widget_key(snapshot, "workflow_mode")
    category_key = _widget_key(snapshot, "workflow_filter_category")
    coverage_key = _widget_key(snapshot, "workflow_coverage")
    deviation_key = _widget_key(snapshot, "workflow_deviation")
    metric_key = _widget_key(snapshot, "workflow_metric_coloring")
    detail_key = _widget_key(snapshot, "workflow_detail_level")
    lens_key = _widget_key(snapshot, "workflow_lens")
    reset_pending_key = _widget_key(snapshot, "workflow_reset_pending")

    reset_triggered = bool(st.session_state.get(reset_pending_key))
    if reset_triggered:
        st.session_state[category_key] = WORKFLOW_FILTER_DEFAULTS["filter_category"]
        st.session_state[coverage_key] = WORKFLOW_FILTER_DEFAULTS["coverage_view"]
        st.session_state[deviation_key] = WORKFLOW_FILTER_DEFAULTS["deviation_view"]
        st.session_state[metric_key] = WORKFLOW_FILTER_DEFAULTS["metric_coloring"]
        st.session_state[detail_key] = WORKFLOW_FILTER_DEFAULTS["detail_level"]
        st.session_state[lens_key] = WORKFLOW_FILTER_DEFAULTS["conformance_lens"]
        st.session_state[reset_pending_key] = False

    stored_mode = st.session_state.get(mode_key, getattr(snapshot, "workflow_view_mode", WORKFLOW_FILTER_DEFAULTS["workflow_mode"]))
    current_mode = _normalize_workflow_mode(stored_mode)
    st.session_state[mode_key] = _workflow_mode_label(current_mode)
    current_category = str(st.session_state.get(category_key, WORKFLOW_FILTER_DEFAULTS["filter_category"]))
    current_coverage = str(st.session_state.get(coverage_key, WORKFLOW_FILTER_DEFAULTS["coverage_view"]))
    current_deviation = str(st.session_state.get(deviation_key, WORKFLOW_FILTER_DEFAULTS["deviation_view"]))
    current_metric = str(st.session_state.get(metric_key, WORKFLOW_FILTER_DEFAULTS["metric_coloring"]))
    current_detail = str(st.session_state.get(detail_key, WORKFLOW_FILTER_DEFAULTS["detail_level"]))
    current_lens = str(st.session_state.get(lens_key, WORKFLOW_FILTER_DEFAULTS["conformance_lens"]))

    metric_options = ["Conformance bucket", "Frequency", "Median delay", "P90 delay"]
    metric_default = current_metric if current_metric in metric_options else "Conformance bucket"
    return {
        "workflow_mode": current_mode,
        "filter_category": _normalize_filter_category(current_category),
        "coverage_view": current_coverage.lower() if current_coverage else "all",
        "deviation_view": current_deviation or "All",
        "metric_coloring": metric_default,
        "detail_level": current_detail.lower() if current_detail else "analyst",
        "conformance_lens": (current_lens if current_lens in {"% of activities", "% of paths"} else "% of paths"),
        "reset_filters": reset_triggered,
        "reset_graph_viewport": False,
    }


def _render_workflow_controls(
    snapshot: AnalysisSnapshot,
    *,
    controls: Optional[dict[str, Any]] = None,
    layout: str = "panel",
) -> dict[str, Any]:
    mode_key = _widget_key(snapshot, "workflow_mode")
    category_key = _widget_key(snapshot, "workflow_filter_category")
    coverage_key = _widget_key(snapshot, "workflow_coverage")
    deviation_key = _widget_key(snapshot, "workflow_deviation")
    metric_key = _widget_key(snapshot, "workflow_metric_coloring")
    detail_key = _widget_key(snapshot, "workflow_detail_level")
    lens_key = _widget_key(snapshot, "workflow_lens")
    reset_pending_key = _widget_key(snapshot, "workflow_reset_pending")

    state_controls = controls or _workflow_controls_from_state(snapshot)
    current_coverage = str(state_controls.get("coverage_view", "all")).title()
    current_deviation = str(state_controls.get("deviation_view", "All"))
    current_metric = str(state_controls.get("metric_coloring", "Conformance bucket"))
    current_detail = str(state_controls.get("detail_level", "analyst")).title()
    current_lens = str(state_controls.get("conformance_lens", "% of paths"))
    current_category = _normalize_filter_category(str(state_controls.get("filter_category", "Pathway")))
    current_mode = _workflow_mode_label(state_controls.get("workflow_mode", WORKFLOW_FILTER_DEFAULTS["workflow_mode"]))

    metric_options = ["Conformance bucket", "Frequency", "Median delay", "P90 delay"]
    metric_default = current_metric if current_metric in metric_options else "Conformance bucket"
    filter_category = current_category
    if layout == "toolbar":
        toolbar_cols = st.columns([1.02, 1.1, 0.82, 0.86, 0.78, 0.82, 0.6], gap="medium")
        with toolbar_cols[0]:
            coverage_view = _render_choice_control(
                "Path view",
                ["All", "Dominant", "Mixed", "Rare"],
                key=coverage_key,
                default=current_coverage,
            )
        with toolbar_cols[1]:
            deviation_view = _render_choice_control(
                "Deviation focus",
                ["All", "Conformant", "Log deviations", "Model deviations"],
                key=deviation_key,
                default=current_deviation,
            )
        with toolbar_cols[2]:
            metric_coloring = st.selectbox(
                "Color",
                options=metric_options,
                index=metric_options.index(metric_default),
                key=metric_key,
            )
        with toolbar_cols[3]:
            workflow_mode_label = _render_choice_control(
                "View",
                WORKFLOW_VIEW_OPTIONS,
                key=mode_key,
                default=current_mode,
            )
        with toolbar_cols[4]:
            detail_label = _render_choice_control(
                "Density",
                ["Executive", "Analyst", "Research"],
                key=detail_key,
                default=current_detail,
            )
        with toolbar_cols[5]:
            lens_label = _render_choice_control(
                "Lens",
                ["% of activities", "% of paths"],
                key=lens_key,
                default=current_lens,
            )
        with toolbar_cols[6]:
            st.markdown("##### Actions")
            reset_filters = st.button("Reset filters", key=_widget_key(snapshot, "workflow_reset_filters"))
    elif layout == "rail":
        filter_category = _render_filter_category_boxes(
            snapshot,
            category_key=category_key,
            current_category=current_category,
        )

        coverage_view = current_coverage
        deviation_view = current_deviation
        metric_coloring = metric_default
        detail_label = current_detail
        lens_label = current_lens
        workflow_mode_label = current_mode
        reset_filters = False

        _render_filter_composer_child(filter_category)
        if filter_category == "Pathway":
            coverage_view = _render_choice_control(
                "Path view",
                ["All", "Dominant", "Mixed", "Rare"],
                key=coverage_key,
                default=current_coverage,
            )
        elif filter_category == "Deviation":
            deviation_view = _render_choice_control(
                "Deviation focus",
                ["All", "Conformant", "Log deviations", "Model deviations"],
                key=deviation_key,
                default=current_deviation,
            )
        elif filter_category == "Display":
            workflow_mode_label = _render_choice_control(
                "View",
                WORKFLOW_VIEW_OPTIONS,
                key=mode_key,
                default=current_mode,
            )
            metric_coloring = st.selectbox(
                "Color",
                options=metric_options,
                index=metric_options.index(metric_default),
                key=metric_key,
            )
            detail_label = _render_choice_control(
                "Density",
                ["Executive", "Analyst", "Research"],
                key=detail_key,
                default=current_detail,
            )
            lens_label = _render_choice_control(
                "Lens",
                ["% of activities", "% of paths"],
                key=lens_key,
                default=current_lens,
            )
        elif filter_category == "Actions":
            reset_filters = st.button(
                "Reset filters",
                key=_widget_key(snapshot, "workflow_reset_filters"),
                help="Clear pathway, deviation, and display filters.",
                use_container_width=True,
            )

        _render_active_filter_summary(
            coverage_view=coverage_view,
            deviation_view=deviation_view,
            metric_coloring=metric_coloring,
            detail_label=detail_label,
            lens_label=lens_label,
            workflow_mode_label=workflow_mode_label,
            filter_category=filter_category,
        )
        if filter_category != "Actions":
            reset_filters = st.button(
                "Reset filters",
                key=_widget_key(snapshot, "workflow_reset_filters"),
                help="Clear pathway, deviation, and display filters without resetting the graph viewport.",
                use_container_width=True,
            )
    else:
        coverage_view = _render_choice_control(
            "Path view",
            ["All", "Dominant", "Mixed", "Rare"],
            key=coverage_key,
            default=current_coverage,
        )
        deviation_view = _render_choice_control(
            "Deviation focus",
            ["All", "Conformant", "Log deviations", "Model deviations"],
            key=deviation_key,
            default=current_deviation,
        )
        metric_coloring = st.selectbox(
            "Color",
            options=metric_options,
            index=metric_options.index(metric_default),
            key=metric_key,
        )
        workflow_mode_label = _render_choice_control(
            "View",
            WORKFLOW_VIEW_OPTIONS,
            key=mode_key,
            default=current_mode,
        )
        detail_label = _render_choice_control(
            "Density",
            ["Executive", "Analyst", "Research"],
            key=detail_key,
            default=current_detail,
        )
        lens_label = _render_choice_control(
            "Lens",
            ["% of activities", "% of paths"],
            key=lens_key,
            default=current_lens,
        )
        reset_filters = st.button("Reset filters", key=_widget_key(snapshot, "workflow_reset_filters"))
    if reset_filters:
        st.session_state[reset_pending_key] = True
        rerun = getattr(st, "rerun", None)
        if callable(rerun):
            rerun()

    return {
        "workflow_mode": _normalize_workflow_mode(workflow_mode_label),
        "filter_category": _normalize_filter_category(filter_category),
        "coverage_view": str(coverage_view).lower(),
        "deviation_view": str(deviation_view),
        "metric_coloring": str(metric_coloring),
        "detail_level": str(detail_label).lower(),
        "conformance_lens": str(lens_label),
        "reset_filters": bool(reset_filters),
        "reset_graph_viewport": False,
    }


def _render_conformance_filter_rail(
    snapshot: AnalysisSnapshot,
    workflow: dict[str, Any],
    controls: dict[str, Any],
    *,
    model_summary_df: pd.DataFrame,
) -> None:
    _render_workflow_top_transition_rail(workflow)
    _render_workflow_controls(snapshot, controls=controls, layout="rail")
    _render_filter_context_note()


def _render_workflow_top_transition_rail(workflow: dict[str, Any]) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    nodes_df, edges_df, _ = _workflow_dfs(workflow)
    if not edges_df.empty and "frequency" in edges_df.columns:
        top_edges = edges_df.copy()
        top_edges["_frequency"] = pd.to_numeric(top_edges["frequency"], errors="coerce").fillna(0)
        top_edges = top_edges.sort_values(by=["_frequency"], ascending=False).head(4)
        render_dashboard_bar_list(
            "Top transitions",
            [
                {
                    "label": _edge_display_label(row),
                    "value": float(row.get("_frequency", 0) or 0),
                    "display": _format_number(row.get("_frequency")),
                    "tone": row.get("severity", "neutral"),
                }
                for _, row in top_edges.iterrows()
            ],
            value_label="",
        )
        return
    elif not nodes_df.empty and "cases" in nodes_df.columns:
        top_nodes = nodes_df.copy()
        top_nodes["_cases"] = pd.to_numeric(top_nodes["cases"], errors="coerce").fillna(0)
        top_nodes = top_nodes.sort_values(by=["_cases"], ascending=False).head(4)
        render_dashboard_bar_list(
            "Top activities",
            [
                {
                    "label": _node_display_label(row),
                    "value": float(row.get("_cases", 0) or 0),
                    "display": _format_number(row.get("_cases")),
                    "tone": row.get("severity", "neutral"),
                }
                for _, row in top_nodes.iterrows()
            ],
            value_label="",
        )
        return

    render_dashboard_bar_list(
        "Top transitions",
        [
            {
                "label": "Dominant path",
                "value": _coerce_float(summary.get("dominant_path_share")) or 0.0,
                "tone": "success",
            },
            {
                "label": "Deviation share",
                "value": _coerce_float(summary.get("deviation_share")) or 0.0,
                "tone": "watch",
            },
        ],
    )


def _render_filter_context_note() -> None:
    st.caption("Subset filters change only the visible workflow. The first-event direct gate remains fixed.")


def _render_conformance_side_intro(*, title: str, lead: str, variant: str) -> None:
    title_modifier = "crpm-conformance-side-title--inspector" if variant == "inspector" else "crpm-conformance-side-title--rail"
    st.markdown(
        (
            f"<div class='crpm-conformance-panel crpm-conformance-panel--muted crpm-conformance-panel--rail "
            f"crpm-conformance-side-rail crpm-conformance-side-rail--{html.escape(variant)}'>"
            f"<div class='crpm-conformance-side-title {title_modifier}'>{html.escape(title)}</div>"
            f"<div class='crpm-conformance-side-lead'>{html.escape(lead)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_workflow_stage_toolbar(snapshot: AnalysisSnapshot, *, workflow: dict[str, Any], controls: dict[str, Any]) -> dict[str, bool]:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    visible_cases = _coerce_int(summary.get("visible_case_count", summary.get("cases_covered")))
    excluded_cases = _coerce_int(summary.get("excluded_case_count"))
    mode = "Overview mode"
    if snapshot.workflow_selection_kind == "node":
        mode = "Pinned node"
    elif snapshot.workflow_selection_kind == "edge":
        mode = "Pinned edge"
    case_scope = f"{visible_cases:,} visible cases" if visible_cases else "Visible case scope pending"
    if excluded_cases:
        case_scope += f" · {excluded_cases:,} excluded"
    lens = str(controls.get("conformance_lens", "% of paths"))
    workflow_mode = _normalize_workflow_mode(controls.get("workflow_mode"))
    workflow_title = {
        "explorer": "Interactive workflow explorer",
        "board": "Workflow board",
        "bpmn": "BPMN-style workflow map",
    }.get(workflow_mode, "Interactive workflow explorer")
    header_col, clear_col, reset_col = st.columns([0.74, 0.13, 0.13], gap="small")
    with header_col:
        st.markdown(
            (
                "<div class='crpm-dashboard-map-toolbar crpm-conformance-stage-header'>"
                "<div class='crpm-conformance-stage-header__copy'>"
                "<div class='crpm-conformance-stage-header__eyebrow'>Process map</div>"
                f"<div class='crpm-conformance-stage-header__title'>{html.escape(workflow_title)}</div>"
                "</div>"
                "<div class='crpm-conformance-stage-header__chips'>"
                f"<span>{html.escape(mode)}</span>"
                f"<span>{html.escape(lens)}</span>"
                f"<span>{html.escape(case_scope)}</span>"
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with clear_col:
        reset_selection = st.button(
            "Clear pin",
            key=_widget_key(snapshot, "workflow_reset"),
            help="Clear the pinned node or edge selection.",
            use_container_width=True,
        )
    with reset_col:
        reset_graph_viewport = st.button(
            "Reset view",
            key=_widget_key(snapshot, "workflow_reset_viewport"),
            help="Reset the interactive workflow viewport without changing filters.",
            use_container_width=True,
        )
    if reset_graph_viewport:
        viewport_nonce_key = _widget_key(snapshot, "workflow_viewport_nonce")
        st.session_state[viewport_nonce_key] = int(st.session_state.get(viewport_nonce_key, 0) or 0) + 1
    return {
        "reset_selection": bool(reset_selection),
        "reset_graph_viewport": bool(reset_graph_viewport),
    }


def _render_conformance_header(*, workflow: dict[str, Any], model_summary_df: pd.DataFrame) -> None:
    reference_model = _top_model_name(model_summary_df) or "No reference model"
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    summary_bits = []
    if dominant_share is not None:
        summary_bits.append(f"dominant path {dominant_share:.1f}%")
    if deviation_share is not None:
        summary_bits.append(f"deviation share {deviation_share:.1f}%")
    if throughput is not None:
        summary_bits.append(f"median throughput {throughput:.1f} d")
    summary_text = (
        " · ".join(summary_bits)
        if summary_bits
        else "Read the process map first, then isolate deviations only where the pathway or delay story breaks."
    )
    st.markdown(
        "<div class='crpm-conformance-page-marker crpm-conformance-cockpit-marker' aria-hidden='true'></div>",
        unsafe_allow_html=True,
    )
    render_dashboard_topbar(
        title="Conformance cockpit",
        subtitle=summary_text,
        badges=[
            {"label": "Mode", "value": "Direct workflow mode", "tone": "accent"},
            {"label": "Reference", "value": reference_model, "tone": "neutral"},
        ],
        meta=["First-event workflow gate", "Board/export view is report-only"],
    )


def _render_board_summary(*, workflow: dict[str, Any], model_summary_df: pd.DataFrame) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    top_model = _top_model_name(model_summary_df)
    story_bits = []
    if dominant_share is not None:
        story_bits.append(f"dominant path covers {dominant_share:.1f}% of visible cases")
    if deviation_share is not None:
        story_bits.append(f"deviation share is {deviation_share:.1f}%")
    if throughput is not None:
        story_bits.append(f"median throughput is {throughput:.1f} d")
    if top_model:
        story_bits.append(f"best current model is {top_model}")
    if story_bits:
        render_quiet_note("Board readout: " + " · ".join(story_bits) + ".")
    else:
        render_quiet_note(
            "Board readout: use the dominant pathway on the left as the canonical story, then open drilldown only when the backbone looks suspicious."
        )


def _top_model_name(model_summary_df: pd.DataFrame) -> Optional[str]:
    display_df = _format_model_summary(model_summary_df).copy()
    if display_df.empty:
        return None
    if {"Alignment fitness", "Precision"}.issubset(display_df.columns):
        balance_series = pd.to_numeric(display_df["Alignment fitness"], errors="coerce").fillna(0) + pd.to_numeric(
            display_df["Precision"], errors="coerce"
        ).fillna(0)
        display_df = display_df.assign(_balance_rank=balance_series).sort_values(
            by=["_balance_rank", "Alignment fitness", "Precision"],
            ascending=[False, False, False],
        )
    top_value = str(display_df.iloc[0].get("Model", "")).strip()
    return top_value or None


def _render_choice_control(label: str, options: list[str], *, key: str, default: str) -> str:
    default_value = default if default in options else options[0]
    segmented_control = getattr(st, "segmented_control", None)
    has_state_value = key in st.session_state
    if callable(segmented_control):
        try:
            if has_state_value:
                selected = segmented_control(label, options, key=key)
            else:
                selected = segmented_control(label, options, default=default_value, key=key)
        except TypeError:
            selected = None
        if isinstance(selected, str) and selected in options:
            return selected
        if isinstance(st.session_state.get(key), str) and st.session_state[key] in options:
            return str(st.session_state[key])
        if _has_streamlit_run_context():
            return default_value

    return st.radio(label, options, index=options.index(default_value), key=key, horizontal=True)


def _normalize_filter_category(value: str) -> str:
    return value if value in WORKFLOW_FILTER_CATEGORIES else WORKFLOW_FILTER_DEFAULTS["filter_category"]


def _normalize_workflow_mode(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    if text in {"explorer", "interactive", "interaction", "dynamic"}:
        return "explorer"
    if text in {"board", "static", "svg"}:
        return "board"
    if text in {"bpmn", "bpmn style", "bpmn styled", "bpmn map"}:
        return "bpmn"
    return _normalize_workflow_mode(WORKFLOW_FILTER_DEFAULTS["workflow_mode"]) if text else "explorer"


def _workflow_mode_label(value: Any) -> str:
    return WORKFLOW_VIEW_LABELS.get(_normalize_workflow_mode(value), WORKFLOW_FILTER_DEFAULTS["workflow_mode"])


def _render_filter_category_boxes(
    snapshot: AnalysisSnapshot,
    *,
    category_key: str,
    current_category: str,
) -> str:
    selected = _normalize_filter_category(current_category)
    if category_key not in st.session_state:
        st.session_state[category_key] = selected

    st.markdown(
        "<div class='crpm-filter-parent-label'>Filter category</div>",
        unsafe_allow_html=True,
    )
    descriptions = {
        "Pathway": "Show all, dominant, mixed, or rare paths.",
        "Deviation": "Isolate conformant and deviation cohorts.",
        "Display": "Tune color, density, and denominator lens.",
        "Actions": "Reset subset filters without changing graph zoom.",
    }
    for category in WORKFLOW_FILTER_CATEGORIES:
        if st.button(
            category,
            key=_widget_key(snapshot, f"workflow_filter_category_{category.lower()}"),
            type="primary" if category == selected else "tertiary",
            use_container_width=True,
            help=descriptions[category],
        ):
            selected = category
            st.session_state[category_key] = category
            if _has_streamlit_run_context():
                st.rerun()

    return selected


def _render_filter_composer_child(filter_category: str) -> None:
    descriptions = {
        "Pathway": "First-event gate fixed.",
        "Deviation": "Isolate conformance buckets without changing cohort semantics.",
        "Display": "Tune color, density, and denominator lens.",
        "Actions": "Reset subset filters; graph viewport reset stays above the map.",
    }
    st.markdown(
        (
            "<div class='crpm-filter-composer'>"
            f"<div class='crpm-filter-composer__body'>{html.escape(descriptions.get(filter_category, 'Choose a filter category.'))}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_active_filter_summary(
    *,
    coverage_view: str,
    deviation_view: str,
    metric_coloring: str,
    detail_label: str,
    lens_label: str,
    workflow_mode_label: str,
    filter_category: str,
) -> None:
    chips = [
        ("Active", filter_category),
        ("View", workflow_mode_label),
        ("Pathway", coverage_view),
        ("Deviation", deviation_view),
        ("Lens", lens_label),
    ]
    chip_markup = "".join(
        (
            "<span class='crpm-active-filter-summary__chip'>"
            f"<span>{html.escape(label)}</span>"
            f"<strong>{html.escape(str(value))}</strong>"
            "</span>"
        )
        for label, value in chips
    )
    st.markdown(
        (
            "<div class='crpm-active-filter-summary'>"
            "<div class='crpm-active-filter-summary__title'>Active filters</div>"
            f"<div class='crpm-active-filter-summary__chips'>{chip_markup}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _has_streamlit_run_context() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _render_workflow_mode_banner(workflow_mode: str) -> None:
    workflow_mode = _normalize_workflow_mode(workflow_mode)
    if workflow_mode == "explorer":
        st.markdown(
            (
                "<div class='crpm-mode-banner crpm-mode-banner--interactive'>"
                "<div class='crpm-mode-banner__title'>Explorer: investigation view</div>"
                "<div class='crpm-mode-banner__body'>"
                "Use zoom and local focus in the explorer to inspect neighboring branches quickly. "
                "Pin exact node and edge metrics from the inspector selectors when you need stable ranked detail."
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return
    if workflow_mode == "bpmn":
        st.markdown(
            (
                "<div class='crpm-mode-banner crpm-mode-banner--bpmn'>"
                "<div class='crpm-mode-banner__title'>BPMN style: notation view</div>"
                "<div class='crpm-mode-banner__body'>"
                "The diagram uses the same filtered workflow payload with BPMN-style events, gateways, tasks, and sequence flows."
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return


def _render_conformance_report_band(
    *,
    workflow: dict[str, Any],
    model_summary_df: pd.DataFrame,
) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    model_name = _top_model_name(model_summary_df)

    facts = []
    if dominant_share is not None:
        facts.append(f"dominant {dominant_share:.1f}%")
    if deviation_share is not None:
        facts.append(f"deviation {deviation_share:.1f}%")
    if throughput is not None:
        facts.append(f"median throughput {throughput:.1f} d")
    if model_name:
        facts.append(f"reference model {model_name}")
    if not facts:
        render_legend_note("Conformance readout: inspect the pathway first, then pin exact node or edge metrics in the inspector.")
        return
    st.markdown(
        (
            "<div class='crpm-conformance-report-band'>"
            "<div class='crpm-conformance-report-band__label'>Conformance summary</div>"
            f"<div class='crpm-conformance-report-band__body'>{html.escape(' · '.join(facts))}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_workflow_feedback(
    workflow: dict[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    *,
    workflow_mode: str,
) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    requested_coverage_view = str(workflow.get("requested_coverage_view", "")).lower() if isinstance(workflow, dict) else ""
    applied_coverage_view = (
        str(workflow.get("applied_coverage_view", requested_coverage_view)).lower()
        if isinstance(workflow, dict)
        else requested_coverage_view
    )
    log_deviation_share = _coerce_float(summary.get("log_deviation_share"))
    model_deviation_share = _coerce_float(summary.get("model_deviation_share"))
    deviation_bits = []
    if log_deviation_share is not None:
        deviation_bits.append(f"log deviation {log_deviation_share:.1f}%")
    if model_deviation_share is not None:
        deviation_bits.append(f"model deviation {model_deviation_share:.1f}%")
    coverage_suffix = ""
    if requested_coverage_view and applied_coverage_view and requested_coverage_view != applied_coverage_view:
        coverage_suffix = f" · requested {requested_coverage_view.title()} view, showing {applied_coverage_view.title()} because the requested slice was empty"
    visible_case_count = _coerce_int(summary.get("visible_case_count", summary.get("cases_covered")))
    path_denominator = _coerce_int(summary.get("path_denominator"))
    excluded_case_count = _coerce_int(summary.get("excluded_case_count"))
    case_text = f"{visible_case_count:,} cases"
    if path_denominator:
        case_text = f"{visible_case_count:,}/{path_denominator:,} cases"
    if excluded_case_count:
        case_text += f" · {excluded_case_count:,} excluded"
    st.markdown(
        (
            "<div class='crpm-conformance-evidence-band'>"
            f"Visible subset: {case_text} · {len(nodes_df):,} nodes · {len(edges_df):,} edges"
            + (f" · {' · '.join(deviation_bits)}" if deviation_bits else "")
            + coverage_suffix
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_reference_model_panel(model_summary_df: pd.DataFrame) -> None:
    top_model = _top_model_name(model_summary_df)
    if not top_model:
        render_inline_empty("No reference model is available for this selection.")
        return
    st.markdown(
        (
            "<div class='crpm-conformance-panel'>"
            "<div class='crpm-conformance-panel__eyebrow'>Reference model</div>"
            f"<div class='crpm-conformance-panel__title'>{html.escape(top_model)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_insight_action_panel(workflow: dict[str, Any], controls: dict[str, Any]) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    insight = _workflow_insight(summary, controls).replace("Insight: ", "")
    st.markdown(
        (
            "<div class='crpm-conformance-panel crpm-conformance-panel--muted'>"
            "<div class='crpm-conformance-panel__eyebrow'>Interpretation</div>"
            f"<div class='crpm-conformance-panel__body'>{html.escape(insight)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_selection_shortcuts(
    *,
    snapshot: AnalysisSnapshot,
    node_row: Optional[pd.Series],
    edge_row: Optional[pd.Series],
) -> None:
    shortcuts = []
    if node_row is not None:
        shortcuts.append(f"Filter to this activity: {_node_display_label(node_row)}")
        shortcuts.append("Show related variants in the expander below")
    if edge_row is not None:
        shortcuts.append(f"Inspect cases crossing {_edge_display_label(edge_row)}")
    if shortcuts:
        render_legend_note(" · ".join(shortcuts))


def _render_related_trace_context(
    workflow: dict[str, Any],
    *,
    node_row: Optional[pd.Series],
    edge_row: Optional[pd.Series],
) -> None:
    trace_profiles_df = workflow.get("trace_profiles", pd.DataFrame()) if isinstance(workflow, dict) else pd.DataFrame()
    if not isinstance(trace_profiles_df, pd.DataFrame) or trace_profiles_df.empty:
        render_inline_empty("No trace-level workflow context is available for the current selection.")
        return

    target_node_id = str(node_row.get("activity")) if node_row is not None and node_row.get("activity") is not None else None
    target_edge_id = str(edge_row.get("edge_id")) if edge_row is not None and edge_row.get("edge_id") is not None else None
    matching_profiles = trace_profiles_df.copy()

    if target_node_id:
        matching_profiles = matching_profiles[
            matching_profiles["node_ids"].map(lambda values: target_node_id in {str(value) for value in values if value})
        ]
    if target_edge_id:
        matching_profiles = matching_profiles[
            matching_profiles["edge_ids"].map(lambda values: target_edge_id in {str(value) for value in values if value})
        ]

    if matching_profiles.empty:
        render_inline_empty("No related variants or cases matched the current workflow selection.")
        return

    top_variants = (
        matching_profiles.groupby("variant_signature", dropna=False)
        .agg(
            Cases=("case_id", "count"),
            Median_throughput_days=("throughput_days", "median"),
            Deviation_rate=("has_deviation", "mean"),
        )
        .reset_index()
        .rename(
            columns={
                "variant_signature": "Variant",
                "Median_throughput_days": "Median throughput (days)",
            }
        )
        .sort_values(
            by=["Cases", "Median throughput (days)", "Variant"],
            ascending=[False, False, True],
            na_position="last",
        )
        .head(6)
        .reset_index(drop=True)
    )
    top_variants.insert(0, "Rank", range(1, len(top_variants) + 1))
    top_variants["Conformance"] = top_variants["Deviation_rate"].map(
        lambda value: "Deviation-heavy" if pd.notna(value) and float(value) >= 0.5 else "Watch"
    )
    top_variants = top_variants.drop(columns=["Deviation_rate"])
    st.caption(f"Matched cases: {len(matching_profiles.index):,}")
    st.markdown(
        _render_ranked_table_html(
            top_variants,
            label_column="Variant",
            chip_column="Conformance",
            title="Related variants",
        ),
        unsafe_allow_html=True,
    )


def _render_workflow_kpi_strip(
    snapshot: AnalysisSnapshot,
    workflow: dict[str, Any],
    controls: dict[str, Any],
    *,
    model_summary_df: pd.DataFrame,
    grid_class: str = "crpm-conformance-kpi-strip",
) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    cases_covered = _coerce_int(summary.get("cases_covered", snapshot.case_count))
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    render_html_card_grid(
        [
            {
                "eyebrow": "Cases",
                "title": "Cases covered",
                "value": f"{cases_covered:,}",
                "body": "",
                "tone": "neutral",
            },
            {
                "eyebrow": "Pathway",
                "title": "Dominant path",
                "value": "N/A" if dominant_share is None else f"{dominant_share:.1f}%",
                "body": "",
                "tone": "success",
            },
            {
                "eyebrow": "Deviation",
                "title": "Deviation share",
                "value": ("N/A" if deviation_share is None else f"{deviation_share:.1f}%"),
                "body": "",
                "tone": "neutral",
            },
            {
                "eyebrow": "Timing",
                "title": "Median throughput",
                "value": "N/A" if throughput is None else f"{throughput:.1f} d",
                "body": "",
                "tone": "neutral",
            },
        ],
        grid_class=grid_class,
    )


def _render_compact_filter_summary(controls: dict[str, Any]) -> None:
    summary_text = (
        f"Path view: {controls['coverage_view'].title()} · Deviation: {controls['deviation_view']} · "
        f"Color: {controls['metric_coloring']} · Density: {controls['detail_level'].title()} · Lens: {controls['conformance_lens']}"
    )
    st.markdown(
        (
            "<div class='crpm-conformance-panel crpm-conformance-panel--muted'>"
            "<div class='crpm-conformance-panel__body'>"
            f"{html.escape(summary_text)}"
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )


def _workflow_feedback_text(
    workflow: dict[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
) -> str:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    requested_coverage_view = str(workflow.get("requested_coverage_view", "")).lower() if isinstance(workflow, dict) else ""
    applied_coverage_view = (
        str(workflow.get("applied_coverage_view", requested_coverage_view)).lower()
        if isinstance(workflow, dict)
        else requested_coverage_view
    )
    log_deviation_share = _coerce_float(summary.get("log_deviation_share"))
    model_deviation_share = _coerce_float(summary.get("model_deviation_share"))
    deviation_bits = []
    if log_deviation_share is not None:
        deviation_bits.append(f"log deviation {log_deviation_share:.1f}%")
    if model_deviation_share is not None:
        deviation_bits.append(f"model deviation {model_deviation_share:.1f}%")
    coverage_suffix = ""
    if requested_coverage_view and applied_coverage_view and requested_coverage_view != applied_coverage_view:
        coverage_suffix = f" · requested {requested_coverage_view.title()} view, showing {applied_coverage_view.title()} because the requested slice was empty"
    visible_case_count = _coerce_int(summary.get("visible_case_count", summary.get("cases_covered")))
    path_denominator = _coerce_int(summary.get("path_denominator"))
    excluded_case_count = _coerce_int(summary.get("excluded_case_count"))
    case_text = f"{visible_case_count:,} cases"
    if path_denominator:
        case_text = f"{visible_case_count:,}/{path_denominator:,} cases"
    if excluded_case_count:
        case_text += f" · {excluded_case_count:,} excluded"
    return (
        f"Visible subset: {case_text} · {len(nodes_df):,} nodes · {len(edges_df):,} edges"
        + (f" · {' · '.join(deviation_bits)}" if deviation_bits else "")
        + coverage_suffix
    )


def _annotate_workflow_renderer_metadata(
    workflow: dict[str, Any],
    *,
    base_workflow: Optional[dict[str, Any]],
    renderer_role: str,
) -> None:
    if not isinstance(workflow, dict):
        return
    summary = workflow.get("summary")
    if not isinstance(summary, dict):
        summary = {}
        workflow["summary"] = summary
    base_summary = base_workflow.get("summary", {}) if isinstance(base_workflow, dict) else {}
    if not isinstance(base_summary, dict):
        base_summary = {}

    visible_case_count = _coerce_int(summary.get("visible_case_count", summary.get("cases_covered")))
    base_case_count = _coerce_int(base_summary.get("visible_case_count", base_summary.get("cases_covered", visible_case_count)))
    if base_case_count <= 0:
        base_case_count = _coerce_int(base_summary.get("path_denominator", visible_case_count))
    excluded_case_count = max(base_case_count - visible_case_count, 0)

    path_denominator = _coerce_int(summary.get("path_denominator", base_summary.get("path_denominator", base_case_count)))
    activity_denominator = _coerce_int(summary.get("activity_denominator", base_summary.get("activity_denominator", 0)))
    transition_denominator = _coerce_int(summary.get("transition_denominator", base_summary.get("transition_denominator", 0)))

    summary["visible_case_count"] = visible_case_count
    summary["excluded_case_count"] = excluded_case_count
    summary["path_denominator"] = path_denominator
    summary.setdefault("path_denominator_label", base_summary.get("path_denominator_label", "cases in evaluation log"))
    summary["activity_denominator"] = activity_denominator
    summary.setdefault("activity_denominator_label", base_summary.get("activity_denominator_label", "events in evaluation log"))
    summary["transition_denominator"] = transition_denominator
    summary.setdefault(
        "transition_denominator_label",
        base_summary.get("transition_denominator_label", "observed transitions in evaluation log"),
    )

    workflow["visible_case_count"] = visible_case_count
    workflow["excluded_case_count"] = excluded_case_count
    workflow["path_denominator"] = path_denominator
    workflow["activity_denominator"] = activity_denominator
    workflow.setdefault("selected_node_id", None)
    workflow.setdefault("selected_edge_uid", None)
    workflow["local_focus_hint"] = WORKFLOW_LOCAL_FOCUS_HINT
    workflow["renderer_role"] = renderer_role

    nodes_df, edges_df, legend_df = _workflow_dfs(workflow)
    trace_profiles_df = workflow.get("trace_profiles", pd.DataFrame())
    if not isinstance(trace_profiles_df, pd.DataFrame):
        trace_profiles_df = pd.DataFrame()
    workflow["process_map_payload"] = {
        "renderer_role": renderer_role,
        "nodes": nodes_df,
        "edges": edges_df,
        "legend": legend_df,
        "trace_profiles": trace_profiles_df,
        "summary": dict(summary),
        "denominators": {
            "visible_case_count": visible_case_count,
            "excluded_case_count": excluded_case_count,
            "path_denominator": path_denominator,
            "activity_denominator": activity_denominator,
            "transition_denominator": transition_denominator,
        },
        "selection": {
            "selected_node_id": workflow.get("selected_node_id"),
            "selected_edge_uid": workflow.get("selected_edge_uid"),
        },
    }


def _board_export_story_text(*, workflow: dict[str, Any], model_summary_df: pd.DataFrame) -> str:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    top_model = _top_model_name(model_summary_df)
    story_bits = []
    if dominant_share is not None:
        story_bits.append(f"dominant path covers {dominant_share:.1f}% of visible cases")
    if deviation_share is not None:
        story_bits.append(f"deviation share is {deviation_share:.1f}%")
    if throughput is not None:
        story_bits.append(f"median throughput is {throughput:.1f} d")
    if top_model:
        story_bits.append(f"best current model is {top_model}")
    if story_bits:
        return "Board readout: " + " · ".join(story_bits) + "."
    return (
        "Board readout: use the dominant pathway on the left as the canonical story, then read the rare-path excursions above and below it."
    )


def _render_board_export_view(
    workflow: dict[str, Any],
    *,
    model_summary_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
) -> None:
    subset_text = _workflow_feedback_text(workflow, nodes_df, edges_df)
    story_text = _board_export_story_text(workflow=workflow, model_summary_df=model_summary_df)
    with st.expander("Report/export view", expanded=False):
        board_markup = render_workflow_conformance_svg(workflow, layout_mode="horizontal", detail_level="executive")
        st.markdown(
            (
                "<div class='crpm-conformance-board-shelf'>"
                "<div class='crpm-conformance-board-shelf__eyebrow'>Board export view</div>"
                "<div class='crpm-conformance-board-shelf__title'>Horizontal pathway shelf</div>"
                "<div class='crpm-conformance-board-shelf__body'>"
                "A compact report shelf for the current visible subset."
                "</div>"
                f"<div class='crpm-conformance-board-shelf__meta'>{html.escape(subset_text)}</div>"
                f"<div class='crpm-conformance-board-shelf__summary'>{html.escape(story_text)}</div>"
                f"{board_markup}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _workflow_insight(summary: dict[str, Any], controls: dict[str, Any]) -> str:
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    log_deviation_share = _coerce_float(summary.get("log_deviation_share"))
    model_deviation_share = _coerce_float(summary.get("model_deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    if deviation_share is not None and deviation_share >= 25:
        detail_bits = []
        if log_deviation_share is not None and log_deviation_share > 0:
            detail_bits.append(f"log {log_deviation_share:.1f}%")
        if model_deviation_share is not None and model_deviation_share > 0:
            detail_bits.append(f"model {model_deviation_share:.1f}%")
        detail_suffix = f" ({', '.join(detail_bits)})" if detail_bits else ""
        return f"Insight: deviations are materially visible ({deviation_share:.1f}%){detail_suffix}. Focus on {controls['deviation_view']} paths and use the inspector for exact branch context."
    if throughput is not None and throughput >= 25:
        return f"Insight: throughput is stretched ({throughput:.1f} d median). Switch coloring to delay and inspect branch-heavy transitions first."
    if dominant_share is not None:
        return f"Insight: the dominant path covers {dominant_share:.1f}% of cases. Use coverage presets to compare the backbone with rare-path behavior."
    return "Insight: use the control strip to switch from the mainline story to rare-path investigation without overloading the board."


def _get_filtered_workflow(snapshot: AnalysisSnapshot, workflow: dict[str, Any], controls: dict[str, Any]) -> dict[str, Any]:
    state = get_crpm_state(st.session_state)
    cache_key = "::".join(
        [
            WORKFLOW_VIEW_CACHE_VERSION,
            snapshot.filter_key or snapshot.input_name or "workflow",
            controls["coverage_view"],
            controls["deviation_view"],
            controls["detail_level"],
            controls["conformance_lens"],
        ]
    )
    cached = bounded_cache_get(state, "workflow_view_cache", cache_key)
    if cached is not None:
        return cached

    filtered = filter_workflow_payload(
        workflow,
        coverage_view=controls["coverage_view"],
        deviation_view=controls["deviation_view"],
        detail_level=controls["detail_level"],
    )
    bounded_cache_put(state, "workflow_view_cache", cache_key, filtered)
    return filtered


def _render_event_process_details(
    *,
    model_summary_df: pd.DataFrame,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    metric_coloring: str,
    detail_level: str,
    selected_node_id: Optional[str],
    selected_edge_id: Optional[str],
) -> None:
    if nodes_df.empty and edges_df.empty and model_summary_df.empty:
        render_inline_empty("No workflow items are available for event or process detail summaries.")
        return

    conformance_order = {
        "Model deviation": 3,
        "Log deviation": 2,
        "Mixed": 1,
        "Conformant": 0,
    }
    if metric_coloring == "Frequency":
        node_sort = ["cases", "occurrences", "display_name"]
        edge_sort = ["frequency", "share_pct", "business_label"]
        metric_name = "Frequency"
    elif metric_coloring == "P90 delay":
        node_sort = ["p90_next_delay_days", "median_next_delay_days", "display_name"]
        edge_sort = ["p90_days", "median_days", "business_label"]
        metric_name = "P90 delay (days)"
    elif metric_coloring == "Conformance bucket":
        conformance_order = {
            "Model deviation": 3,
            "Log deviation": 2,
            "Mixed": 1,
            "Conformant": 0,
        }
        node_sort = ["_conformance_rank", "cases", "display_name"]
        edge_sort = ["_conformance_rank", "frequency", "business_label"]
        metric_name = "Conformance bucket"
    else:
        node_sort = ["median_next_delay_days", "cases", "display_name"]
        edge_sort = ["median_days", "frequency", "business_label"]
        metric_name = "Median delay (days)"

    row_limit = {"executive": 4, "analyst": 6, "research": 10}.get(detail_level, 6)
    node_row = None
    edge_row = None
    if selected_node_id and not nodes_df.empty:
        selected_rows = nodes_df[nodes_df["activity"].astype(str) == str(selected_node_id)]
        if not selected_rows.empty:
            node_row = selected_rows.iloc[0]
    edge_id_column = _edge_id_column(edges_df)
    if selected_edge_id and not edges_df.empty and edge_id_column in edges_df.columns:
        selected_rows = edges_df[edges_df[edge_id_column].astype(str) == str(selected_edge_id)]
        if not selected_rows.empty:
            edge_row = selected_rows.iloc[0]

    nodes_table = pd.DataFrame()
    if not nodes_df.empty:
        working_nodes = nodes_df.copy()
        for column in [
            "display_name",
            "cases",
            "occurrences",
            "median_next_delay_days",
            "p90_next_delay_days",
            "conformance_bucket",
        ]:
            if column not in working_nodes.columns:
                working_nodes[column] = None
        working_nodes["_conformance_rank"] = (
            working_nodes["conformance_bucket"].map(conformance_order if metric_coloring == "Conformance bucket" else {}).fillna(0)
        )
        working_nodes["_selected"] = working_nodes["activity"].astype(str).eq(str(selected_node_id)) if selected_node_id else False
        working_nodes["display_name"] = working_nodes.apply(_node_display_label, axis=1)
        nodes_table = (
            working_nodes.sort_values(by=["_selected", *node_sort], ascending=[False, False, False, True])
            .head(row_limit)[
                [
                    "display_name",
                    "cases",
                    "occurrences",
                    "median_next_delay_days",
                    "p90_next_delay_days",
                    "conformance_bucket",
                ]
            ]
            .rename(
                columns={
                    "display_name": "Activity",
                    "cases": "Cases",
                    "occurrences": "Events",
                    "median_next_delay_days": "Median delay (days)",
                    "p90_next_delay_days": "P90 delay (days)",
                    "conformance_bucket": "Conformance",
                }
            )
            .reset_index(drop=True)
        )
        nodes_table.insert(0, "Rank", range(1, len(nodes_table) + 1))
    edges_table = pd.DataFrame()
    if not edges_df.empty:
        working_edges = edges_df.copy()
        for column in [
            "business_label",
            "frequency",
            "share_pct",
            "median_days",
            "p90_days",
            "conformance_bucket",
        ]:
            if column not in working_edges.columns:
                working_edges[column] = None
        working_edges["_conformance_rank"] = (
            working_edges["conformance_bucket"].map(conformance_order if metric_coloring == "Conformance bucket" else {}).fillna(0)
        )
        edge_id_column = _edge_id_column(working_edges)
        working_edges["_selected"] = working_edges[edge_id_column].astype(str).eq(str(selected_edge_id)) if selected_edge_id else False
        working_edges["business_label"] = working_edges.apply(_edge_display_label, axis=1)
        edges_table = (
            working_edges.sort_values(by=["_selected", *edge_sort], ascending=[False, False, False, True])
            .head(row_limit)[
                [
                    "business_label",
                    "frequency",
                    "share_pct",
                    "median_days",
                    "p90_days",
                    "conformance_bucket",
                ]
            ]
            .rename(
                columns={
                    "business_label": "Transition",
                    "frequency": "Events",
                    "share_pct": "Share (%)",
                    "median_days": "Median delay (days)",
                    "p90_days": "P90 delay (days)",
                    "conformance_bucket": "Conformance",
                }
            )
            .reset_index(drop=True)
        )
        edges_table.insert(0, "Rank", range(1, len(edges_table) + 1))

    model_cards_df = _format_model_summary(model_summary_df).reset_index(drop=True)
    if not model_cards_df.empty:
        model_cards_df.insert(0, "Rank", range(1, len(model_cards_df) + 1))

    selection_bits = []
    if selected_node_id:
        selected_node_label = _node_display_label(node_row) if node_row is not None else humanize_activity_label(selected_node_id)
        selection_bits.append(f"selected node: {selected_node_label}")
    if selected_edge_id:
        selected_edge_label = _edge_display_label(edge_row) if edge_row is not None else humanize_activity_label(selected_edge_id)
        selection_bits.append(f"selected edge: {selected_edge_label}")
    render_legend_note(
        f"Sorted by {metric_name.lower()} · {detail_level.title()} density" + (f" · {' · '.join(selection_bits)}" if selection_bits else "")
    )
    activity_tab, transition_tab, model_tab = st.tabs(["Activities", "Transitions", "Models"])
    with activity_tab:
        if nodes_table.empty:
            render_inline_empty("No ranked activity rows are available for this selection.")
        else:
            st.markdown(
                _render_ranked_table_html(
                    nodes_table,
                    label_column="Activity",
                    chip_column="Conformance",
                    title="Top activities",
                ),
                unsafe_allow_html=True,
            )
    with transition_tab:
        if edges_table.empty:
            render_inline_empty("No ranked transition rows are available for this selection.")
        else:
            st.markdown(
                _render_ranked_table_html(
                    edges_table,
                    label_column="Transition",
                    chip_column="Conformance",
                    title="Top transitions",
                ),
                unsafe_allow_html=True,
            )
    with model_tab:
        if model_cards_df.empty:
            render_inline_empty("No model rows are available for this selection.")
        else:
            st.markdown(_render_model_cards_html(model_cards_df), unsafe_allow_html=True)
            summary_rows = []
            for _, row in model_cards_df.iterrows():
                summary_text = str(row.get("Summary", "")).strip()
                if summary_text and summary_text.lower() != "nan":
                    summary_rows.append(
                        f"<div class='crpm-mini-note'><strong>{html.escape(str(row.get('Model', 'Model')))}</strong><br>{html.escape(summary_text)}</div>"
                    )
            if summary_rows:
                with st.expander("Verbose model notes", expanded=False):
                    st.markdown("".join(summary_rows), unsafe_allow_html=True)


def _render_model_posture_section(model_summary_df: pd.DataFrame) -> None:
    display_df = _format_model_summary(model_summary_df).copy()
    if display_df.empty:
        render_inline_empty("No model posture is available for this selection.")
        return

    if {"Alignment fitness", "Precision"}.issubset(display_df.columns):
        balance_series = pd.to_numeric(display_df["Alignment fitness"], errors="coerce").fillna(0) + pd.to_numeric(
            display_df["Precision"], errors="coerce"
        ).fillna(0)
        display_df = display_df.assign(_balance_rank=balance_series).sort_values(
            by=["_balance_rank", "Alignment fitness", "Precision"],
            ascending=[False, False, False],
        )
    display_df = display_df.reset_index(drop=True)
    display_df.insert(0, "Rank", range(1, len(display_df) + 1))
    st.markdown(_render_model_cards_html(display_df.head(1)), unsafe_allow_html=True)

    summary_rows = []
    for _, row in display_df.iterrows():
        summary_text = str(row.get("Summary", "")).strip()
        if summary_text and summary_text.lower() != "nan":
            summary_rows.append(
                f"<div class='crpm-mini-note'><strong>{html.escape(str(row.get('Model', 'Model')))}</strong><br>{html.escape(summary_text)}</div>"
            )

    extra_models = display_df.iloc[1:].copy()
    if not extra_models.empty or summary_rows:
        with st.expander("Model comparison", expanded=False):
            if not extra_models.empty:
                st.markdown(_render_model_cards_html(extra_models), unsafe_allow_html=True)
            if summary_rows:
                st.markdown("".join(summary_rows), unsafe_allow_html=True)


def _render_selector(
    *,
    label: str,
    df: pd.DataFrame,
    id_column: str,
    default_id: Optional[str],
    key: str,
    format_label,
    empty_label: Optional[str] = None,
) -> tuple[Optional[str], Optional[pd.Series]]:
    if df.empty:
        return None, None

    working = df.copy()
    if id_column not in working.columns:
        working[id_column] = working.index.astype(str)
    working[id_column] = working[id_column].astype(str)
    ids = [""]
    ids.extend(working[id_column].tolist())
    default_id = str(default_id) if default_id is not None and str(default_id) in ids else ""

    selected_id = st.selectbox(
        label,
        options=ids,
        index=ids.index(default_id) if default_id in ids else 0,
        key=key,
        format_func=lambda option: (
            (empty_label or f"Overview ({label.lower()} not pinned)")
            if option == ""
            else format_label(working.loc[working[id_column] == option].iloc[0])
        ),
    )
    if selected_id == "":
        return None, None

    selected_rows = working[working[id_column] == str(selected_id)]
    if selected_rows.empty:
        return str(selected_id), None
    return str(selected_id), selected_rows.iloc[0]


def _workflow_dfs(
    workflow: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nodes_df = workflow.get("nodes", pd.DataFrame()) if isinstance(workflow, dict) else pd.DataFrame()
    edges_df = workflow.get("edges", pd.DataFrame()) if isinstance(workflow, dict) else pd.DataFrame()
    legend_df = workflow.get("legend", pd.DataFrame()) if isinstance(workflow, dict) else pd.DataFrame()
    if not isinstance(nodes_df, pd.DataFrame):
        nodes_df = pd.DataFrame()
    if not isinstance(edges_df, pd.DataFrame):
        edges_df = pd.DataFrame()
    if not isinstance(legend_df, pd.DataFrame):
        legend_df = pd.DataFrame()
    return nodes_df, _workflow_edges_with_ids(edges_df), legend_df


def _workflow_edges_with_ids(edges_df: pd.DataFrame) -> pd.DataFrame:
    if edges_df.empty:
        return edges_df.copy()
    working = edges_df.copy()
    if "edge_uid" in working.columns:
        working["edge_uid"] = working["edge_uid"].astype(str)
    else:
        working["edge_uid"] = working.apply(
            lambda row: workflow_edge_uid(
                row.get("edge_id") or f"{row.get('source', '')} -> {row.get('target', '')}",
                row.get("conformance_bucket", "Conformant"),
                row.get("edge_type", "expected"),
                row.get("branch_family", "mainline"),
            ),
            axis=1,
        )
    if "edge_id" not in working.columns:
        working["edge_id"] = working["edge_uid"]
    else:
        working["edge_id"] = working["edge_id"].astype(str)
    return working


def _edge_id_column(edges_df: pd.DataFrame) -> str:
    if "edge_uid" in edges_df.columns:
        return "edge_uid"
    return "edge_id"


def _coerce_selection_to_visible_subset(
    *,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    selection_kind: str,
    selection_id: Optional[str],
) -> tuple[str, Optional[str]]:
    if selection_kind == "edge" and selection_id and not edges_df.empty:
        edge_id_column = _edge_id_column(edges_df)
        if edge_id_column in edges_df.columns:
            edge_ids = set(edges_df[edge_id_column].astype(str))
            if str(selection_id) in edge_ids:
                return "edge", str(selection_id)
    if selection_kind == "node" and selection_id and not nodes_df.empty and "activity" in nodes_df.columns:
        node_ids = set(nodes_df["activity"].astype(str))
        if str(selection_id) in node_ids:
            return "node", str(selection_id)
    return "none", None


def _coerce_graph_selection(selection: Any) -> tuple[Optional[str], Optional[str]]:
    if isinstance(selection, str):
        return selection, None
    if isinstance(selection, dict):
        action = selection.get("action")
        data = selection.get("data", {}) if isinstance(selection.get("data"), dict) else {}
        if action == "selected_node":
            node_id = data.get("target_id")
            return (str(node_id) if node_id else None, None)
        if action == "selected_edge":
            edge_id = data.get("target_id")
            return (None, str(edge_id) if edge_id else None)
        node = selection.get("selected_node") or selection.get("selectedNode") or selection.get("node") or selection.get("selected")
        edge = selection.get("selected_edge") or selection.get("selectedEdge") or selection.get("edge")
        if isinstance(node, dict):
            node = node.get("id") or node.get("data", {}).get("id")
        if isinstance(edge, dict):
            edge = edge.get("id") or edge.get("data", {}).get("id")
        return (str(node) if node else None, str(edge) if edge else None)
    if isinstance(selection, (list, tuple)) and selection:
        node = selection[0]
        edge = selection[1] if len(selection) > 1 else None
        return (str(node) if node else None, str(edge) if edge else None)
    return None, None


def _store_workflow_state(snapshot: AnalysisSnapshot, **updates: Any) -> None:
    state = st.session_state.get("crpm_state")
    if not isinstance(state, CRPMState):
        return
    for field_name, value in updates.items():
        setattr(state.results, field_name, value)


def _clear_workflow_selection(snapshot: AnalysisSnapshot) -> None:
    st.session_state[_widget_key(snapshot, "selected_node")] = ""
    st.session_state[_widget_key(snapshot, "selected_edge")] = ""


def _reset_workflow_filters(snapshot: AnalysisSnapshot) -> None:
    _clear_workflow_selection(snapshot)
    st.session_state[_widget_key(snapshot, "workflow_filter_category")] = WORKFLOW_FILTER_DEFAULTS["filter_category"]
    st.session_state[_widget_key(snapshot, "workflow_coverage")] = WORKFLOW_FILTER_DEFAULTS["coverage_view"]
    st.session_state[_widget_key(snapshot, "workflow_deviation")] = WORKFLOW_FILTER_DEFAULTS["deviation_view"]
    st.session_state[_widget_key(snapshot, "workflow_metric_coloring")] = WORKFLOW_FILTER_DEFAULTS["metric_coloring"]
    st.session_state[_widget_key(snapshot, "workflow_detail_level")] = WORKFLOW_FILTER_DEFAULTS["detail_level"]
    st.session_state[_widget_key(snapshot, "workflow_lens")] = WORKFLOW_FILTER_DEFAULTS["conformance_lens"]
    st.session_state[_widget_key(snapshot, "workflow_reset_pending")] = False
    _store_workflow_state(
        snapshot,
        workflow_selection_kind="none",
        workflow_selection_id=None,
        selected_workflow_node_id=None,
        selected_workflow_edge_id=None,
    )


def _reset_workflow_view(snapshot: AnalysisSnapshot, *, workflow_mode: str) -> None:
    viewport_nonce_key = _widget_key(snapshot, "workflow_viewport_nonce")
    st.session_state[viewport_nonce_key] = int(st.session_state.get(viewport_nonce_key, 0) or 0) + 1


def _widget_key(snapshot: AnalysisSnapshot, suffix: str) -> str:
    prefix = snapshot.filter_key or snapshot.input_name or "conformance"
    return f"crpm_{prefix}_{suffix}"


def _node_option_label(row: pd.Series) -> str:
    return f"{_node_display_label(row)} · {_format_number(row.get('cases'))} cases · {row.get('conformance_bucket', 'Conformant')}"


def _edge_option_label(row: pd.Series) -> str:
    return f"{_edge_display_label(row)} · {_format_number(row.get('frequency'))} events · {row.get('conformance_bucket', 'Conformant')}"


def _format_model_summary(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()
    rename_map = {
        "model": "Model",
        "model_name": "Model",
        "algorithm": "Algorithm",
        "variant": "Variant",
        "alignment_fitness": "Alignment fitness",
        "token_fitness": "Token fitness",
        "precision": "Precision",
        "quadrant": "Quadrant",
        "fitness_quality": "Fitness quality",
        "precision_quality": "Precision quality",
        "recommendation": "Recommendation",
        "summary": "Summary",
    }
    display = display.rename(columns={key: value for key, value in rename_map.items() if key in display.columns})
    for column in ("Alignment fitness", "Token fitness", "Precision"):
        if column in display.columns:
            display[column] = display[column].map(_format_decimal)
    return display


def _format_deviation_summary(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()
    if "precision" in display.columns:
        display["precision"] = display["precision"].map(_format_decimal)
    return display


def _format_trace_deviations(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()
    for column in ("alignment_fitness", "token_trace_fitness", "alignment_cost"):
        if column in display.columns:
            display[column] = display[column].map(_format_decimal)
    return display


def _format_node_detail(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Node": _node_display_label(row),
                "Step": row.get("step", "unmapped"),
                "Cases": _format_number(row.get("cases")),
                "Occurrences": _format_number(row.get("occurrences")),
                "Median next delay (days)": _format_number(row.get("median_next_delay_days")),
                "P90 next delay (days)": _format_number(row.get("p90_next_delay_days")),
                "Conformance": row.get("conformance_bucket", "Conformant"),
                "Severity": row.get("severity", "Low"),
                "Branch role": row.get("branch_role", "mainline"),
                "Coverage": row.get("coverage_group", "mixed"),
            }
        ]
    )


def _format_edge_detail(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Edge": _edge_display_label(row),
                "Frequency": _format_number(row.get("frequency")),
                "Share (%)": _format_number(row.get("share_pct")),
                "Median delay (days)": _format_number(row.get("median_days")),
                "P90 delay (days)": _format_number(row.get("p90_days")),
                "Conformance": row.get("conformance_bucket", "Conformant"),
                "Severity": row.get("severity", "Low"),
                "Branch role": row.get("branch_role", "mainline"),
                "Coverage": row.get("coverage_group", "mixed"),
            }
        ]
    )


def _render_selection_summary_card(
    *,
    node_row: Optional[pd.Series],
    edge_row: Optional[pd.Series],
) -> None:
    if node_row is not None and edge_row is not None:
        title = f"{_node_display_label(node_row)} + {_edge_display_label(edge_row)}"
        subtitle = "Selected node + edge"
        meta = [
            f"{_format_number(node_row.get('cases'))} node cases",
            f"{_format_number(edge_row.get('frequency'))} edge events",
            str(
                edge_row.get(
                    "conformance_bucket",
                    node_row.get("conformance_bucket", "Conformant"),
                )
            ),
        ]
        tone = str(edge_row.get("conformance_bucket", node_row.get("conformance_bucket", "Conformant")))
    elif node_row is not None:
        title = _node_display_label(node_row)
        subtitle = "Selected node"
        meta = [
            f"{_format_number(node_row.get('cases'))} cases",
            str(node_row.get("conformance_bucket", "Conformant")),
            f"{_format_number(node_row.get('median_next_delay_days'))} d median",
        ]
        tone = str(node_row.get("conformance_bucket", "Conformant"))
    elif edge_row is not None:
        title = _edge_display_label(edge_row)
        subtitle = "Selected edge"
        meta = [
            f"{_format_number(edge_row.get('frequency'))} events",
            str(edge_row.get("conformance_bucket", "Conformant")),
            f"{_format_number(edge_row.get('median_days'))} d median",
        ]
        tone = str(edge_row.get("conformance_bucket", "Conformant"))
    else:
        title = "Overview mode"
        subtitle = "No pinned workflow detail"
        meta = [
            "Read the pathway first",
            "Pin only when exact values matter",
        ]
        tone = "Overview"
    st.markdown(
        (
            f"<div class='crpm-selection-card crpm-selection-card--{_slugify(tone)}'>"
            f"<div class='crpm-selection-card__eyebrow'>{html.escape(subtitle)}</div>"
            f"<div class='crpm-selection-card__title'>{html.escape(title)}</div>"
            f"<div class='crpm-selection-card__meta'>{' · '.join(html.escape(item) for item in meta)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_detail_card(df: pd.DataFrame, *, card_kind: str) -> None:
    row = df.iloc[0].to_dict() if not df.empty else {}
    items = []
    for key, value in row.items():
        items.append(
            "<div class='crpm-detail-card__item'>"
            f"<div class='crpm-detail-card__label'>{html.escape(str(key))}</div>"
            f"<div class='crpm-detail-card__value'>{html.escape(str(value))}</div>"
            "</div>"
        )
    st.markdown(
        f"<div class='crpm-detail-card crpm-detail-card--{_slugify(card_kind)}'>{''.join(items)}</div>",
        unsafe_allow_html=True,
    )


def _render_model_cards_html(df: pd.DataFrame) -> str:
    cards = []
    for _, row in df.iterrows():
        title = _short_label(str(row.get("Model", "Model")), max_chars=28)
        recommendation = str(row.get("Recommendation", "Review"))
        cards.append(
            (
                "<div class='crpm-model-card'>"
                f"<div class='crpm-model-card__rank'>#{html.escape(str(row.get('Rank', '')))}</div>"
                f"<div class='crpm-model-card__title' title='{html.escape(str(row.get('Model', 'Model')))}'>{html.escape(title)}</div>"
                f"<div class='crpm-model-card__grid'>"
                f"<div><span>Fitness</span><strong>{html.escape(str(row.get('Alignment fitness', 'N/A')))}</strong></div>"
                f"<div><span>Precision</span><strong>{html.escape(str(row.get('Precision', 'N/A')))}</strong></div>"
                f"<div><span>Balance</span><strong>{html.escape(_format_balance_value(row))}</strong></div>"
                f"<div><span>Recommendation</span><strong>{html.escape(recommendation)}</strong></div>"
                "</div>"
                "</div>"
            )
        )
    return "<div class='crpm-model-card-grid'>" + "".join(cards) + "</div>"


def _node_display_label(row: pd.Series) -> str:
    display_name = str(row.get("display_name") or row.get("business_label") or "").strip()
    if display_name:
        return humanize_activity_label(display_name) or display_name
    return humanize_activity_label(row.get("activity", "Node")) or "Node"


def _edge_display_label(row: pd.Series) -> str:
    business_label = str(row.get("business_label") or "").strip()
    if business_label:
        if "→" in business_label:
            left, right = [part.strip() for part in business_label.split("→", 1)]
            return f"{humanize_activity_label(left) or left} → {humanize_activity_label(right) or right}"
        return humanize_activity_label(business_label) or business_label
    source = humanize_activity_label(row.get("source_label") or row.get("source", "?")) or "?"
    target = humanize_activity_label(row.get("target_label") or row.get("target", "?")) or "?"
    return f"{source} → {target}"


def _render_ranked_table_html(
    df: pd.DataFrame,
    *,
    label_column: str,
    chip_column: str,
    title: str,
) -> str:
    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in df.columns)
    numeric_keywords = (
        "rank",
        "cases",
        "events",
        "delay",
        "share",
        "fitness",
        "precision",
        "balance",
    )
    numeric_maxima: dict[str, float] = {}
    for column in df.columns:
        if any(keyword in str(column).lower() for keyword in numeric_keywords if keyword != "rank"):
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            numeric_maxima[str(column)] = float(numeric_series.max()) if not numeric_series.dropna().empty else 0.0
    rows = []
    for _, row in df.iterrows():
        cells = []
        for column in df.columns:
            raw_value = row.get(column, "N/A")
            display_value = _format_numberish(raw_value)
            class_name = "crpm-table__cell"
            if str(column).lower() == "rank":
                cell_html = (
                    f"<td class='{class_name} crpm-table__cell--rank'>"
                    f"<span class='crpm-rank-pill'>{html.escape(str(display_value))}</span></td>"
                )
            elif column == label_column:
                full_value = str(raw_value)
                display_value = _short_label(full_value, max_chars=34 if label_column == "Activity" else 30)
                class_name += " crpm-table__cell--label"
                cell_html = f"<td class='{class_name}' title='{html.escape(full_value)}'>{html.escape(str(display_value))}</td>"
            elif column == chip_column:
                class_name += " crpm-table__cell--chip"
                full_value = str(raw_value)
                chip_slug = _slugify(full_value)
                cell_html = (
                    f"<td class='{class_name}'><span class='crpm-chip crpm-chip--{chip_slug}' "
                    f"title='{html.escape(full_value)}'>{html.escape(str(display_value))}</span></td>"
                )
            else:
                if any(keyword in column.lower() for keyword in numeric_keywords):
                    class_name += " crpm-table__cell--num"
                cell_html = _render_numeric_ranked_cell(
                    column=str(column),
                    raw_value=raw_value,
                    display_value=display_value,
                    class_name=class_name,
                    maxima=numeric_maxima,
                )
            cells.append(cell_html)
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        "<div class='crpm-ranked-table'>"
        f"<div class='crpm-ranked-table__title'>{html.escape(title)}</div>"
        "<div class='crpm-ranked-table__scroller'>"
        f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        "</div></div>"
    )


def _render_numeric_ranked_cell(
    *,
    column: str,
    raw_value: Any,
    display_value: Any,
    class_name: str,
    maxima: dict[str, float],
) -> str:
    numeric_value = _coerce_float(raw_value)
    max_value = maxima.get(column, 0.0)
    if numeric_value is None or max_value <= 0:
        return f"<td class='{class_name}'>{html.escape(str(display_value))}</td>"

    width_pct = max(0.0, min(100.0, numeric_value / max_value * 100.0))
    return (
        f"<td class='{class_name}'>"
        "<div class='crpm-table__metric-cell'>"
        f"<span class='crpm-table__metric-value'>{html.escape(str(display_value))}</span>"
        f"<span class='crpm-table__metric-track'><span class='crpm-table__metric-fill' style='width:{width_pct:.1f}%'></span></span>"
        "</div>"
        "</td>"
    )


def _format_balance_value(row: pd.Series) -> str:
    fitness = _coerce_float(row.get("Alignment fitness"))
    precision = _coerce_float(row.get("Precision"))
    if fitness is None or precision is None:
        return "N/A"
    return format_display_decimal((fitness + precision) / 2)


def _short_label(value: str, *, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "neutral"


def _legend_fallback_table(workflow: dict[str, Any]) -> pd.DataFrame:
    legend = workflow.get("legend", pd.DataFrame()) if isinstance(workflow, dict) else pd.DataFrame()
    if isinstance(legend, pd.DataFrame) and not legend.empty:
        return legend
    return pd.DataFrame(
        [
            {
                "bucket": "Conformant",
                "meaning": "Expected screening progression",
                "severity": "Conformant",
            },
            {
                "bucket": "Log deviation",
                "meaning": "Observed skip, loop, or reorder",
                "severity": "Log deviation",
            },
            {
                "bucket": "Model deviation",
                "meaning": "Unmapped or off-pathway activity",
                "severity": "Model deviation",
            },
            {
                "bucket": "Low",
                "meaning": "Delay near cohort baseline",
                "severity": "Low",
            },
            {
                "bucket": "Moderate",
                "meaning": "Delay requires monitoring",
                "severity": "Moderate",
            },
            {
                "bucket": "High",
                "meaning": "Delay materially above baseline",
                "severity": "High",
            },
        ]
    )


def _quality_caption(kind: str, value: Any) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    assessment = assess_fitness(float(value)) if kind == "fitness" else assess_precision(float(value))
    return assessment[2]


def _row_label(row: pd.Series) -> str:
    return str(row.get("model", row.get("model_name", "N/A")))


def _format_metric_value(value: Any) -> str:
    return format_display_metric(value, kind="score")


def _format_number(value: Any) -> str:
    return format_display_metric(value)


def _format_numberish(value: Any) -> Any:
    try:
        if value is None or pd.isna(value):
            return "N/A"
    except Exception:
        pass
    if isinstance(value, str):
        return value
    return format_display_metric(value)


def _coerce_int(value: Any) -> int:
    try:
        if value is None or pd.isna(value):
            return 0
        return int(value)
    except Exception:
        return 0


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _best_row(df: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in df.columns or df[column].dropna().empty:
        return None
    return df.loc[df[column].fillna(float("-inf")).idxmax()]


def _best_balance_row(df: pd.DataFrame) -> pd.Series | None:
    if not {"alignment_fitness", "precision"}.issubset(df.columns):
        return None
    scores = df["alignment_fitness"].fillna(0) + df["precision"].fillna(0)
    if scores.empty:
        return None
    return df.loc[scores.idxmax()]


def _get_workspace(snapshot: AnalysisSnapshot) -> dict[str, object]:
    workspace = (
        snapshot.conformance_workspace if isinstance(snapshot.conformance_workspace, dict) else dict(snapshot.conformance_workspace or {})
    )
    if workspace:
        return workspace
    if snapshot.comparison_df.empty:
        return {}
    return {
        "model_summary_df": snapshot.comparison_df.copy(),
        "deviation_summary_df": pd.DataFrame(),
        "trace_deviation_df": pd.DataFrame(),
        "workflow": {
            "nodes": pd.DataFrame(),
            "edges": pd.DataFrame(),
            "legend": pd.DataFrame(),
        },
    }


def _format_decimal(value: object) -> object:
    try:
        if pd.isna(value):
            return "N/A"
        return format_display_decimal(value)
    except Exception:
        return value
