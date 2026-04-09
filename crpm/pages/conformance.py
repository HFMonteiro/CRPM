"""Conformance page for the staged CRPM refactor."""

from __future__ import annotations

import html
import logging
from typing import Any, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from crpm.app_state import AnalysisSnapshot, CRPMState, bounded_cache_get, bounded_cache_put, get_crpm_state
from crpm.interpretations import assess_balanced_quality, assess_fitness, assess_precision
from crpm.pages.common import render_empty_state, render_inline_empty, render_legend_note, render_quiet_note
from crpm.screening import humanize_activity_label
from crpm.visualization import (
    create_workflow_interactive_payload,
    filter_workflow_payload,
    render_workflow_conformance_svg,
    render_workflow_explorer_html,
)

try:  # optional interactive workflow dependency
    from streamlit_cytoscape import streamlit_cytoscape  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    streamlit_cytoscape = None


logger = logging.getLogger(__name__)
WORKFLOW_VIEW_CACHE_VERSION = "workflow-view-v2"


def render_conformance_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Conformance Analytics")
    st.caption(
        "Board mode explains the filtered pathway. Interactive mode investigates the same payload with the inspector on the right."
    )

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

    board_col, detail_col = st.columns([1.9, 1.0], gap="large")

    with board_col:
        st.markdown("#### Workflow pathway board")
        st.caption("Use the shared controls to focus dominant or rare paths, isolate deviations, and switch coloring without cluttering the board.")
        if has_workflow:
            controls = _render_workflow_controls(snapshot)
            workflow_mode = controls["workflow_mode"]
            _store_workflow_state(snapshot, workflow_view_mode=workflow_mode, workflow_detail_level=controls["detail_level"])
            if controls["reset_selection"]:
                _store_workflow_state(snapshot, selected_workflow_node_id=None, selected_workflow_edge_id=None)
            _render_workflow_mode_banner(workflow_mode)

            filtered_workflow = _get_filtered_workflow(snapshot, workflow, controls)
            filtered_nodes_df, filtered_edges_df, filtered_legend_df = _workflow_dfs(filtered_workflow)
            _render_workflow_kpi_strip(snapshot, filtered_workflow, controls)
            _render_workflow_feedback(filtered_workflow, filtered_nodes_df, filtered_edges_df)

            selected_node_id, selected_edge_id = _render_workflow_board_or_graph(
                workflow=filtered_workflow,
                nodes_df=filtered_nodes_df,
                edges_df=filtered_edges_df,
                workflow_mode=workflow_mode,
                snapshot=snapshot,
                metric_coloring=controls["metric_coloring"],
                detail_level=controls["detail_level"],
            )

            _store_workflow_state(
                snapshot,
                selected_workflow_node_id=selected_node_id,
                selected_workflow_edge_id=selected_edge_id,
            )
        else:
            controls = {
                "workflow_mode": "board",
                "coverage_view": "all",
                "deviation_view": "All",
                "metric_coloring": "Conformance bucket",
                "detail_level": snapshot.workflow_detail_level,
                "reset_selection": False,
            }
            filtered_workflow = workflow
            filtered_nodes_df, filtered_edges_df, filtered_legend_df = nodes_df, edges_df, legend_df
            selected_node_id = None
            selected_edge_id = None
            render_inline_empty("No workflow graph is available for this selection. Use the model and deviation summaries in the inspector.")

    with detail_col:
        _render_right_panel(
            snapshot=snapshot,
            model_summary_df=model_summary_df,
            deviation_summary_df=deviation_summary_df,
            trace_deviation_df=trace_deviation_df,
            nodes_df=filtered_nodes_df,
            edges_df=filtered_edges_df,
            legend_df=filtered_legend_df,
            workflow=filtered_workflow,
            selected_node_id=selected_node_id,
            selected_edge_id=selected_edge_id,
            controls=controls,
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
) -> tuple[Optional[str], Optional[str]]:
    if nodes_df.empty and edges_df.empty:
        st.caption("No workflow structure could be derived from the current filtered log.")
        return None, None

    if workflow_mode == "interactive":
        graph_rendered, selected_node_id, selected_edge_id, fallback_message = _render_interactive_workflow_graph(
            workflow,
            nodes_df,
            edges_df,
            snapshot,
            metric_coloring=metric_coloring,
            detail_level=detail_level,
        )
        if graph_rendered:
            return selected_node_id, selected_edge_id
        if fallback_message:
            st.warning(fallback_message)
        st.markdown(render_workflow_conformance_svg(workflow), unsafe_allow_html=True)
        return None, None

    st.markdown(render_workflow_conformance_svg(workflow), unsafe_allow_html=True)
    return None, None


def _render_interactive_workflow_graph(
    workflow: dict[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    snapshot: AnalysisSnapshot,
    *,
    metric_coloring: str,
    detail_level: str,
) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
    try:
        explorer_payload = create_workflow_interactive_payload(
            workflow,
            metric_coloring=metric_coloring,
            detail_level=detail_level,
            selected_node_id=snapshot.selected_workflow_node_id,
            selected_edge_id=snapshot.selected_workflow_edge_id,
        )
        components.html(
            render_workflow_explorer_html(explorer_payload),
            height=int(explorer_payload.get("height", 520)) + 74,
            scrolling=False,
        )
        return True, snapshot.selected_workflow_node_id, snapshot.selected_workflow_edge_id, None
    except Exception:
        logger.exception("Interactive workflow graph rendering failed")
        return (
            False,
            None,
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
    selected_node_id: Optional[str],
    selected_edge_id: Optional[str],
    controls: dict[str, Any],
) -> None:
    st.markdown("#### Workflow inspector")

    model_count = snapshot.model_count or len(model_summary_df)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Models", f"{model_count:,}")
    metric_cols[1].metric("Cases", f"{snapshot.case_count:,}")
    metric_cols[2].metric("Events", f"{snapshot.event_count:,}")

    if not model_summary_df.empty:
        best_fitness = _best_row(model_summary_df, "alignment_fitness")
        best_precision = _best_row(model_summary_df, "precision")
        best_balance = _best_balance_row(model_summary_df)
        if best_fitness is not None:
            st.metric("Best fitness", _row_label(best_fitness), _format_metric_value(best_fitness.get("alignment_fitness")))
            st.caption(_quality_caption("fitness", best_fitness.get("alignment_fitness")))
        if best_precision is not None:
            st.metric("Best precision", _row_label(best_precision), _format_metric_value(best_precision.get("precision")))
            st.caption(_quality_caption("precision", best_precision.get("precision")))
        if best_balance is not None:
            fitness = float(best_balance.get("alignment_fitness", 0) or 0)
            precision = float(best_balance.get("precision", 0) or 0)
            st.metric("Best balance", _row_label(best_balance), f"{(fitness + precision) / 2:.4f}")
            st.caption(assess_balanced_quality(fitness, precision)[2])

    st.markdown("##### Inspect workflow items")
    node_id, node_row = _render_selector(
        label="Node",
        df=nodes_df,
        id_column="activity",
        default_id=selected_node_id or snapshot.selected_workflow_node_id,
        key=_widget_key(snapshot, "selected_node"),
        format_label=_node_option_label,
    )
    edge_id, edge_row = _render_selector(
        label="Edge",
        df=_workflow_edges_with_ids(edges_df),
        id_column="edge_id",
        default_id=selected_edge_id or snapshot.selected_workflow_edge_id,
        key=_widget_key(snapshot, "selected_edge"),
        format_label=_edge_option_label,
    )

    _store_workflow_state(
        snapshot,
        selected_workflow_node_id=node_id,
        selected_workflow_edge_id=edge_id,
    )

    selection_active = node_row is not None or edge_row is not None
    _render_selection_summary_card(node_row=node_row, edge_row=edge_row)
    st.caption(
        "The inspector shows overall conformance at rest and switches to focused node or edge metrics when you pin a workflow item."
    )
    if node_row is not None:
        st.markdown("###### Selected node")
        _render_detail_card(_format_node_detail(node_row), card_kind="node")
        _render_selection_shortcuts(snapshot=snapshot, node_row=node_row, edge_row=edge_row)
    else:
        render_inline_empty("No workflow node is selected. Use the selectors or keep the explorer on overall mode.")

    if edge_row is not None:
        st.markdown("###### Selected edge")
        _render_detail_card(_format_edge_detail(edge_row), card_kind="edge")
    else:
        render_inline_empty("No workflow edge is selected. Use the selectors when you want a precise transition drilldown.")

    if selection_active:
        st.markdown("###### Related variants and cases")
        _render_related_trace_context(workflow, node_row=node_row, edge_row=edge_row)
    else:
        render_legend_note("Selection-first workflow inspection: pick a node or edge to surface related variants, case context, and exact metrics here.")

    st.markdown("##### Event / process details")
    _render_event_process_details(
        model_summary_df=model_summary_df,
        nodes_df=nodes_df,
        edges_df=edges_df,
        metric_coloring=controls["metric_coloring"],
        detail_level=controls["detail_level"],
        selected_node_id=node_id,
        selected_edge_id=edge_id,
    )

    st.markdown("##### Supporting detail")
    legend_tab, deviations_tab, trace_tab = st.tabs(["Legend", "Deviations", "Trace"])
    with legend_tab:
        render_legend_note(
            f"Coverage focus: {controls['coverage_view'].title()} · Deviation focus: {controls['deviation_view']} · Coloring: {controls['metric_coloring']} · Detail level: {controls['detail_level'].title()}"
        )
        if legend_df.empty:
            st.dataframe(_legend_fallback_table(workflow), use_container_width=True, hide_index=True)
        else:
            st.dataframe(legend_df, use_container_width=True, hide_index=True)

    with deviations_tab:
        if deviation_summary_df.empty:
            render_inline_empty("No model-level deviation summary was extracted for the current selection.")
        else:
            st.dataframe(_format_deviation_summary(deviation_summary_df), use_container_width=True, hide_index=True)

    with trace_tab:
        if trace_deviation_df.empty:
            render_inline_empty("No trace-level deviations were extracted for the current selection.")
        else:
            st.dataframe(_format_trace_deviations(trace_deviation_df), use_container_width=True, hide_index=True)


def _render_workflow_controls(snapshot: AnalysisSnapshot) -> dict[str, Any]:
    control_cols = st.columns([1.15, 0.95, 1.05, 1.1, 1.0, 0.65], gap="small")
    with control_cols[0]:
        mode_label = st.radio(
            "Mode",
            ["Board mode", "Interactive mode"],
            index=0 if snapshot.workflow_view_mode != "interactive" else 1,
            horizontal=True,
            key=_widget_key(snapshot, "workflow_mode"),
        )
    with control_cols[1]:
        coverage_view = st.selectbox(
            "Coverage",
            options=["All", "Dominant", "Mixed", "Rare"],
            index=0,
            key=_widget_key(snapshot, "workflow_coverage"),
        )
    with control_cols[2]:
        deviation_view = st.selectbox(
            "Filter",
            options=["All", "Conformant", "Log deviations", "Model deviations"],
            index=0,
            key=_widget_key(snapshot, "workflow_deviation"),
        )
    with control_cols[3]:
        metric_coloring = st.selectbox(
            "Metric coloring",
            options=["Conformance bucket", "Frequency", "Median delay", "P90 delay"],
            index=0,
            key=_widget_key(snapshot, "workflow_metric_coloring"),
        )
    with control_cols[4]:
        detail_label = st.selectbox(
            "Detail level",
            options=["Executive", "Analyst", "Research"],
            index={"executive": 0, "analyst": 1, "research": 2}.get(snapshot.workflow_detail_level, 1),
            key=_widget_key(snapshot, "workflow_detail_level"),
        )
    with control_cols[5]:
        st.caption("Selection")
        reset_selection = st.button("Reset", key=_widget_key(snapshot, "workflow_reset"))

    return {
        "workflow_mode": "interactive" if mode_label == "Interactive mode" else "board",
        "coverage_view": str(coverage_view).lower(),
        "deviation_view": str(deviation_view),
        "metric_coloring": str(metric_coloring),
        "detail_level": str(detail_label).lower(),
        "reset_selection": bool(reset_selection),
    }


def _render_workflow_mode_banner(workflow_mode: str) -> None:
    if workflow_mode == "interactive":
        st.markdown(
            (
                "<div class='crpm-mode-banner crpm-mode-banner--interactive'>"
                "<div class='crpm-mode-banner__title'>Interactive mode: investigation view</div>"
                "<div class='crpm-mode-banner__body'>"
                "Use zoom and click nodes or edges in the graph to focus branches quickly. "
                "The right inspector remains the source of exact ranked metrics."
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        (
            "<div class='crpm-mode-banner crpm-mode-banner--board'>"
            "<div class='crpm-mode-banner__title'>Board mode: explanation view</div>"
            "<div class='crpm-mode-banner__body'>"
            "Use this editorial board for executive storytelling: mainline first, side branches second, details in the inspector."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_workflow_feedback(workflow: dict[str, Any], nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    covered_cases = _coerce_int(summary.get("cases_covered"))
    log_deviation_share = _coerce_float(summary.get("log_deviation_share"))
    model_deviation_share = _coerce_float(summary.get("model_deviation_share"))
    bucket_counts = nodes_df.get("conformance_bucket", pd.Series(dtype=str)).value_counts()
    severity_counts = nodes_df.get("severity", pd.Series(dtype=str)).value_counts()
    bucket_text = ", ".join(f"{bucket}: {count}" for bucket, count in bucket_counts.items()) if not bucket_counts.empty else "No conformance mix available"
    severity_text = ", ".join(f"{bucket}: {count}" for bucket, count in severity_counts.items()) if not severity_counts.empty else "No severity mix available"
    deviation_bits = []
    if log_deviation_share is not None:
        deviation_bits.append(f"log deviation {log_deviation_share:.1f}%")
    if model_deviation_share is not None:
        deviation_bits.append(f"model deviation {model_deviation_share:.1f}%")
    render_legend_note(
        f"Visible subset: {covered_cases:,} cases · {len(nodes_df):,} nodes · {len(edges_df):,} edges"
        + (f" · {' · '.join(deviation_bits)}" if deviation_bits else "")
        + f" · {bucket_text} · {severity_text}"
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
        .rename(columns={"variant_signature": "Variant", "Median_throughput_days": "Median throughput (days)"})
        .sort_values(by=["Cases", "Median throughput (days)", "Variant"], ascending=[False, False, True], na_position="last")
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
) -> None:
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    cases_covered = _coerce_int(summary.get("cases_covered", snapshot.case_count))
    events_covered = _coerce_int(summary.get("events_covered", snapshot.event_count))
    dominant_share = _coerce_float(summary.get("dominant_path_share"))
    deviation_share = _coerce_float(summary.get("deviation_share"))
    throughput = _coerce_float(summary.get("median_throughput_days"))
    insight = _workflow_insight(summary, controls)

    cols = st.columns([1, 1, 1, 1, 1, 1.35], gap="small")
    cols[0].metric("Cases covered", f"{cases_covered:,}")
    cols[1].metric("Events covered", f"{events_covered:,}")
    cols[2].metric("Dominant path", "N/A" if dominant_share is None else f"{dominant_share:.1f}%")
    cols[3].metric("Deviation share", "N/A" if deviation_share is None else f"{deviation_share:.1f}%")
    cols[4].metric("Median throughput", "N/A" if throughput is None else f"{throughput:.1f} d")
    with cols[5]:
        render_legend_note(insight)


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
            controls["metric_coloring"],
            controls["detail_level"],
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

    conformance_order = {"Model deviation": 3, "Log deviation": 2, "Mixed": 1, "Conformant": 0}
    if metric_coloring == "Frequency":
        node_sort = ["cases", "occurrences", "display_name"]
        edge_sort = ["frequency", "share_pct", "business_label"]
        metric_name = "Frequency"
    elif metric_coloring == "P90 delay":
        node_sort = ["p90_next_delay_days", "median_next_delay_days", "display_name"]
        edge_sort = ["p90_days", "median_days", "business_label"]
        metric_name = "P90 delay (days)"
    elif metric_coloring == "Conformance bucket":
        conformance_order = {"Model deviation": 3, "Log deviation": 2, "Mixed": 1, "Conformant": 0}
        node_sort = ["_conformance_rank", "cases", "display_name"]
        edge_sort = ["_conformance_rank", "frequency", "business_label"]
        metric_name = "Conformance bucket"
    else:
        node_sort = ["median_next_delay_days", "cases", "display_name"]
        edge_sort = ["median_days", "frequency", "business_label"]
        metric_name = "Median delay (days)"

    row_limit = {"executive": 5, "analyst": 8, "research": 12}.get(detail_level, 8)
    node_row = None
    edge_row = None
    if selected_node_id and not nodes_df.empty:
        selected_rows = nodes_df[nodes_df["activity"].astype(str) == str(selected_node_id)]
        if not selected_rows.empty:
            node_row = selected_rows.iloc[0]
    if selected_edge_id and not edges_df.empty:
        selected_rows = edges_df[edges_df.get("edge_id", pd.Series(dtype=str)).astype(str) == str(selected_edge_id)]
        if not selected_rows.empty:
            edge_row = selected_rows.iloc[0]

    nodes_table = pd.DataFrame()
    if not nodes_df.empty:
        working_nodes = nodes_df.copy()
        for column in ["display_name", "cases", "occurrences", "median_next_delay_days", "p90_next_delay_days", "conformance_bucket"]:
            if column not in working_nodes.columns:
                working_nodes[column] = None
        working_nodes["_conformance_rank"] = working_nodes["conformance_bucket"].map(conformance_order if metric_coloring == "Conformance bucket" else {}).fillna(0)
        working_nodes["_selected"] = working_nodes["activity"].astype(str).eq(str(selected_node_id)) if selected_node_id else False
        working_nodes["display_name"] = working_nodes.apply(_node_display_label, axis=1)
        nodes_table = working_nodes.sort_values(by=["_selected", *node_sort], ascending=[False, False, False, True]).head(row_limit)[
            ["display_name", "cases", "occurrences", "median_next_delay_days", "p90_next_delay_days", "conformance_bucket"]
        ].rename(
            columns={
                "display_name": "Activity",
                "cases": "Cases",
                "occurrences": "Events",
                "median_next_delay_days": "Median delay (days)",
                "p90_next_delay_days": "P90 delay (days)",
                "conformance_bucket": "Conformance",
            }
        ).reset_index(drop=True)
        nodes_table.insert(0, "Rank", range(1, len(nodes_table) + 1))
    edges_table = pd.DataFrame()
    if not edges_df.empty:
        working_edges = edges_df.copy()
        for column in ["business_label", "frequency", "share_pct", "median_days", "p90_days", "conformance_bucket"]:
            if column not in working_edges.columns:
                working_edges[column] = None
        working_edges["_conformance_rank"] = working_edges["conformance_bucket"].map(conformance_order if metric_coloring == "Conformance bucket" else {}).fillna(0)
        working_edges["_selected"] = working_edges["edge_id"].astype(str).eq(str(selected_edge_id)) if selected_edge_id else False
        working_edges["business_label"] = working_edges.apply(_edge_display_label, axis=1)
        edges_table = working_edges.sort_values(by=["_selected", *edge_sort], ascending=[False, False, False, True]).head(row_limit)[
            ["business_label", "frequency", "share_pct", "median_days", "p90_days", "conformance_bucket"]
        ].rename(
            columns={
                "business_label": "Transition",
                "frequency": "Events",
                "share_pct": "Share (%)",
                "median_days": "Median delay (days)",
                "p90_days": "P90 delay (days)",
                "conformance_bucket": "Conformance",
            }
        ).reset_index(drop=True)
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
        f"Event/process details sorted by {metric_name.lower()} · detail level: {detail_level.title()}" + (f" · {' · '.join(selection_bits)}" if selection_bits else "")
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
                    title="Activity detail",
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
                    title="Transition detail",
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


def _render_selector(
    *,
    label: str,
    df: pd.DataFrame,
    id_column: str,
    default_id: Optional[str],
    key: str,
    format_label,
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
        f"Selected {label.lower()}",
        options=ids,
        index=ids.index(default_id) if default_id in ids else 0,
        key=key,
        format_func=lambda option: f"Overview ({label.lower()} not pinned)" if option == "" else format_label(working.loc[working[id_column] == option].iloc[0]),
    )
    if selected_id == "":
        return None, None

    selected_rows = working[working[id_column] == str(selected_id)]
    if selected_rows.empty:
        return str(selected_id), None
    return str(selected_id), selected_rows.iloc[0]


def _workflow_dfs(workflow: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
    if "edge_id" not in working.columns:
        working["edge_id"] = working.apply(
            lambda row: f"{row.get('source', '')} -> {row.get('target', '')}",
            axis=1,
        )
    return working


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
        node = (
            selection.get("selected_node")
            or selection.get("selectedNode")
            or selection.get("node")
            or selection.get("selected")
        )
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
            str(edge_row.get("conformance_bucket", node_row.get("conformance_bucket", "Conformant"))),
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
        title = "Overall process view"
        subtitle = "No workflow item pinned"
        meta = ["Inspector in overview mode", "Use the selectors to pin a node or edge", "Exact metrics stay below"]
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
    numeric_keywords = ("rank", "cases", "events", "delay", "share", "fitness", "precision", "balance")
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
                cell_html = (
                    f"<td class='{class_name}' title='{html.escape(full_value)}'>"
                    f"{html.escape(str(display_value))}</td>"
                )
            elif column == chip_column:
                class_name += " crpm-table__cell--chip"
                chip_slug = _slugify(str(raw_value))
                cell_html = (
                    f"<td class='{class_name}'><span class='crpm-chip crpm-chip--{chip_slug}'>"
                    f"{html.escape(str(display_value))}</span></td>"
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
    return f"{(fitness + precision) / 2:.4f}"


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
            {"bucket": "Conformant", "meaning": "Expected screening progression", "severity": "Conformant"},
            {"bucket": "Log deviation", "meaning": "Observed skip, loop, or reorder", "severity": "Log deviation"},
            {"bucket": "Model deviation", "meaning": "Unmapped or off-pathway activity", "severity": "Model deviation"},
            {"bucket": "Low", "meaning": "Delay near cohort baseline", "severity": "Low"},
            {"bucket": "Moderate", "meaning": "Delay requires monitoring", "severity": "Moderate"},
            {"bucket": "High", "meaning": "Delay materially above baseline", "severity": "High"},
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
    try:
        if value is None or pd.isna(value):
            return "N/A"
        return f"{float(value):.4f}"
    except Exception:
        return str(value)


def _format_number(value: Any) -> str:
    try:
        if value is None or pd.isna(value):
            return "N/A"
        numeric = float(value)
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:,.1f}"
    except Exception:
        return str(value)


def _format_numberish(value: Any) -> Any:
    try:
        if value is None or pd.isna(value):
            return "N/A"
    except Exception:
        pass
    if isinstance(value, str):
        return value
    return _format_number(value)


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
    workspace = snapshot.conformance_workspace if isinstance(snapshot.conformance_workspace, dict) else dict(snapshot.conformance_workspace or {})
    if workspace:
        return workspace
    if snapshot.comparison_df.empty:
        return {}
    return {
        "model_summary_df": snapshot.comparison_df.copy(),
        "deviation_summary_df": pd.DataFrame(),
        "trace_deviation_df": pd.DataFrame(),
        "workflow": {"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()},
    }


def _format_decimal(value: object) -> object:
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.4f}"
    except Exception:
        return value
