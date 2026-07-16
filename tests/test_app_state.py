import pandas as pd

from crpm.app_state import (
    PREVIEW_PAGES,
    WORKFLOW_COHORT_FIRST_EVENT_DIRECT,
    bounded_cache_put,
    build_analysis_snapshot,
    get_crpm_state,
    initialize_shell_state,
)
from crpm.pages import PAGE_REGISTRY


def test_initialize_shell_state_sets_defaults() -> None:
    session_state = {}

    initialize_shell_state(session_state)

    assert session_state["crpm_preview_page"] == PREVIEW_PAGES[0]


def test_build_analysis_snapshot_uses_expected_defaults() -> None:
    snapshot = build_analysis_snapshot({})

    assert snapshot.analysis_complete is False
    assert snapshot.model_count == 0
    assert snapshot.case_count == 0
    assert snapshot.event_count == 0
    assert snapshot.comparison_df.empty
    assert snapshot.analysis_summary == {}
    assert snapshot.workflow_view_mode == "explorer"
    assert snapshot.workflow_detail_level == "analyst"
    assert snapshot.selected_workflow_node_id is None
    assert snapshot.selected_workflow_edge_id is None
    assert snapshot.workflow_cohort_policy == WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    assert snapshot.source_metadata == {}
    assert snapshot.denominator_registry == {}
    assert snapshot.log_quality == {}
    assert snapshot.run_manifest == {}


def test_build_analysis_snapshot_reads_existing_results() -> None:
    comparison_df = pd.DataFrame([{"model": "Inductive", "precision": 0.9}])
    filtered_log = [[{"concept:name": "Start"}, {"concept:name": "End"}]]
    session_state = {
        "analysis_complete": True,
        "current_input_name": "running-example.xes",
        "current_filter_key": "example",
        "current_filtered_log": filtered_log,
        "discovery_results": {"Inductive": object(), "Heuristics": object()},
        "comparison_df": comparison_df,
        "analysis_summary": {"cases": 1, "events": 2},
        "conformance_workspace": {"model_summary_df": pd.DataFrame()},
        "variant_cache": {"v": {"variant_stats": []}},
        "dfg_cache": {"d": {"dfg": {}}},
        "performance_cache": {"p": {"activity_stats": []}},
    }

    snapshot = build_analysis_snapshot(session_state)

    assert snapshot.analysis_complete is True
    assert snapshot.input_name == "running-example.xes"
    assert snapshot.model_names == ["Inductive", "Heuristics"]
    assert snapshot.case_count == 1
    assert snapshot.event_count == 2
    assert snapshot.has_comparison is True
    assert snapshot.analysis_summary["cases"] == 1
    assert "model_summary_df" in snapshot.conformance_workspace


def test_page_registry_matches_preview_pages() -> None:
    assert tuple(PAGE_REGISTRY.keys()) == (
        "Overview",
        "Discovery",
        "Model Comparison",
        "Operational Flow",
        "DFG Visualizations",
        "Variant Analysis",
        "Conformance Analytics",
        "Process Performance",
    )
    assert PREVIEW_PAGES == (
        "Overview",
        "Discovery",
        "Model Comparison",
        "Operational Flow",
        "DFG Visualizations",
        "Variant Analysis",
        "Conformance Analytics",
        "Process Performance",
    )


def test_get_crpm_state_initializes_versioned_state() -> None:
    session_state = {}

    state = get_crpm_state(session_state)

    assert state.version == 7
    assert state.config.workflow_cohort_policy == WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    assert state.config.selected_algorithms
    assert "conformance_cache" in state.caches
    assert "conformance_workspace_cache" in state.caches
    assert "workflow_view_cache" in state.caches
    assert "log_quality_cache" in state.caches
    assert state.results.workflow_view_mode == "explorer"
    assert state.results.workflow_detail_level == "analyst"
    assert state.results.workflow_cohort_policy == WORKFLOW_COHORT_FIRST_EVENT_DIRECT


def test_bounded_cache_put_evicts_oldest_entries() -> None:
    state = get_crpm_state({})

    for index in range(18):
        bounded_cache_put(state, "conformance_cache", f"key-{index}", index)

    assert len(state.caches["conformance_cache"]) == 16
    assert "key-0" not in state.caches["conformance_cache"]
    assert "key-17" in state.caches["conformance_cache"]


def test_analysis_results_reset_clears_last_analysis_signature() -> None:
    state = get_crpm_state({})
    state.results.last_analysis_signature = "demo-signature"
    state.results.denominator_registry = {"case_count": 1}
    state.results.log_quality = {"summary": {"quality_status": "ok"}}
    state.results.run_manifest = {"schema_version": 1}

    state.results.reset()

    assert state.results.last_analysis_signature is None
    assert state.results.denominator_registry == {}
    assert state.results.log_quality == {}
    assert state.results.run_manifest == {}
