"""Shared state helpers for the staged CRPM Streamlit refactor."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, MutableMapping, Optional

import pandas as pd

PREVIEW_PAGES = (
    "Overview",
    "Discovery",
    "Model Comparison",
    "Operational Flow",
    "DFG Visualizations",
    "Variant Analysis",
    "Conformance Analytics",
    "Process Performance",
)

WORKFLOW_COHORT_FIRST_EVENT_DIRECT = "first_event_direct"
WORKFLOW_COHORT_EXPLICIT_FOLLOWUP_ANCHOR = "explicit_followup_anchor"
WORKFLOW_COHORT_POLICIES = {
    WORKFLOW_COHORT_FIRST_EVENT_DIRECT,
    WORKFLOW_COHORT_EXPLICIT_FOLLOWUP_ANCHOR,
}

STATE_VERSION = 6
CACHE_LIMITS = {
    "log_cache": 4,
    "dataframe_cache": 2,
    "filtered_cache": 8,
    "model_cache": 4,
    "discovery_results_cache": 6,
    "conformance_cache": 16,
    "conformance_workspace_cache": 8,
    "performance_cache": 8,
    "variant_cache": 8,
    "dfg_cache": 8,
    "screening_cache": 4,
    "workflow_view_cache": 16,
}


@dataclass
class ShellConfig:
    """User-configurable values for the stabilized shell."""

    source_type: str = "XES"
    xes_logs_directory: str = "./examples"
    selected_log_path: Optional[str] = None
    csv_case_col: Optional[str] = None
    csv_activity_col: Optional[str] = None
    csv_timestamp_col: Optional[str] = None
    workflow_cohort_policy: str = WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    start_filter: str = "All"
    apply_date_filter: bool = False
    date_filter_mode: str = "case"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    selected_algorithms: list[str] = field(default_factory=lambda: ["Heuristics (Classic)", "Inductive (IMf)"])
    apply_followup_window: bool = False
    followup_days: int = 365
    enable_train_test: bool = False
    random_seed: int = 42


@dataclass
class AnalysisResults:
    """Current analysis outputs for the stabilized shell."""

    analysis_complete: bool = False
    input_name: Optional[str] = None
    log_signature: Optional[str] = None
    workflow_cohort_policy: str = WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    source_metadata: dict[str, Any] = field(default_factory=dict)
    filter_key: Optional[str] = None
    filtered_log: Any = None
    discovery_results: dict[str, Any] = field(default_factory=dict)
    comparison_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    conformance_results: dict[str, Any] = field(default_factory=dict)
    conformance_workspace: dict[str, Any] = field(default_factory=dict)
    split_info: dict[str, Any] = field(default_factory=dict)
    analysis_summary: dict[str, Any] = field(default_factory=dict)
    train_log: Any = None
    test_log: Any = None
    active_followup_label: Optional[str] = None
    config_change_message: Optional[str] = None
    filter_error_message: Optional[str] = None
    last_analysis_signature: Optional[str] = None
    stage_timings: dict[str, float] = field(default_factory=dict)
    workflow_view_mode: str = "board"
    workflow_detail_level: str = "analyst"
    workflow_selection_kind: str = "none"
    workflow_selection_id: Optional[str] = None
    selected_workflow_node_id: Optional[str] = None
    selected_workflow_edge_id: Optional[str] = None

    def reset(
        self,
        *,
        input_name: Optional[str] = None,
        log_signature: Optional[str] = None,
        filter_key: Optional[str] = None,
        active_followup_label: Optional[str] = None,
        config_change_message: Optional[str] = None,
        filter_error_message: Optional[str] = None,
        source_metadata: Optional[Mapping[str, Any]] = None,
        workflow_cohort_policy: str = WORKFLOW_COHORT_FIRST_EVENT_DIRECT,
    ) -> None:
        """Clear analysis outputs while preserving high-level context."""
        self.analysis_complete = False
        self.input_name = input_name
        self.log_signature = log_signature
        self.workflow_cohort_policy = workflow_cohort_policy
        self.source_metadata = dict(source_metadata or {})
        self.filter_key = filter_key
        self.filtered_log = None
        self.discovery_results = {}
        self.comparison_df = pd.DataFrame()
        self.conformance_results = {}
        self.conformance_workspace = {}
        self.split_info = {}
        self.analysis_summary = {}
        self.train_log = None
        self.test_log = None
        self.active_followup_label = active_followup_label
        self.config_change_message = config_change_message
        self.filter_error_message = filter_error_message
        self.last_analysis_signature = None
        self.stage_timings = {}
        self.workflow_view_mode = "board"
        self.workflow_detail_level = "analyst"
        self.workflow_selection_kind = "none"
        self.workflow_selection_id = None
        self.selected_workflow_node_id = None
        self.selected_workflow_edge_id = None


@dataclass
class CRPMState:
    """Versioned shell state stored in Streamlit session state."""

    version: int = STATE_VERSION
    config: ShellConfig = field(default_factory=ShellConfig)
    results: AnalysisResults = field(default_factory=AnalysisResults)
    caches: dict[str, OrderedDict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisSnapshot:
    """Typed read-only view over the shell state."""

    analysis_complete: bool
    input_name: Optional[str]
    filter_key: Optional[str]
    filtered_log: Any
    discovery_results: Mapping[str, Any]
    comparison_df: pd.DataFrame
    split_info: Mapping[str, Any]
    analysis_summary: Mapping[str, Any]
    active_followup_label: Optional[str]
    config_change_message: Optional[str]
    filter_error_message: Optional[str]
    performance_cache: Mapping[str, Any]
    variant_cache: Mapping[str, Any]
    dfg_cache: Mapping[str, Any]
    conformance_results: Mapping[str, Any]
    conformance_workspace: Mapping[str, Any]
    selected_algorithms: tuple[str, ...]
    stage_timings: Mapping[str, float]
    workflow_cohort_policy: str = WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    workflow_view_mode: str = "board"
    workflow_detail_level: str = "analyst"
    workflow_selection_kind: str = "none"
    workflow_selection_id: Optional[str] = None
    selected_workflow_node_id: Optional[str] = None
    selected_workflow_edge_id: Optional[str] = None

    @property
    def model_names(self) -> list[str]:
        return list(self.discovery_results.keys())

    @property
    def model_count(self) -> int:
        return len(self.discovery_results)

    @property
    def case_count(self) -> int:
        if self.filtered_log is None:
            return 0
        try:
            return len(self.filtered_log)
        except Exception:
            return 0

    @property
    def event_count(self) -> int:
        if self.filtered_log is None:
            return 0
        try:
            return sum(len(trace) for trace in self.filtered_log)
        except Exception:
            return 0

    @property
    def has_comparison(self) -> bool:
        return not self.comparison_df.empty


def initialize_shell_state(session_state: MutableMapping[str, Any]) -> None:
    """Initialize keys used by the CRPM shell."""
    session_state.setdefault("crpm_preview_page", PREVIEW_PAGES[0])
    existing_state = session_state.get("crpm_state")
    if not isinstance(existing_state, CRPMState) or getattr(existing_state, "version", None) != STATE_VERSION:
        session_state["crpm_state"] = _migrate_or_create_state(session_state)
    _ensure_cache_structures(session_state["crpm_state"])


def get_crpm_state(session_state: MutableMapping[str, Any]) -> CRPMState:
    initialize_shell_state(session_state)
    return session_state["crpm_state"]


def bounded_cache_get(state: CRPMState, cache_name: str, cache_key: str) -> Any:
    cache = state.caches[cache_name]
    if cache_key not in cache:
        return None
    cache.move_to_end(cache_key)
    return cache[cache_key]


def bounded_cache_put(state: CRPMState, cache_name: str, cache_key: str, value: Any) -> None:
    cache = state.caches[cache_name]
    cache[cache_key] = value
    cache.move_to_end(cache_key)
    limit = CACHE_LIMITS[cache_name]
    while len(cache) > limit:
        cache.popitem(last=False)


def build_analysis_snapshot(session_state: Mapping[str, Any]) -> AnalysisSnapshot:
    """Build a typed snapshot from the current Streamlit session state."""
    state = session_state.get("crpm_state")
    if not isinstance(state, CRPMState):
        state = _migrate_or_create_state(session_state)

    results = state.results
    comparison_df = results.comparison_df if isinstance(results.comparison_df, pd.DataFrame) else pd.DataFrame()
    discovery_results = results.discovery_results if isinstance(results.discovery_results, Mapping) else {}
    split_info = results.split_info if isinstance(results.split_info, Mapping) else {}

    legacy_node_id = (
        str(getattr(results, "selected_workflow_node_id", None))
        if getattr(results, "selected_workflow_node_id", None) is not None
        else None
    )
    legacy_edge_id = (
        str(getattr(results, "selected_workflow_edge_id", None))
        if getattr(results, "selected_workflow_edge_id", None) is not None
        else None
    )
    selection_kind = str(getattr(results, "workflow_selection_kind", "none") or "none")
    selection_id = (
        str(getattr(results, "workflow_selection_id", None)) if getattr(results, "workflow_selection_id", None) is not None else None
    )
    if selection_kind not in {"node", "edge", "none"}:
        selection_kind = "none"
        selection_id = None
    if selection_kind == "none":
        if legacy_edge_id:
            selection_kind = "edge"
            selection_id = legacy_edge_id
        elif legacy_node_id:
            selection_kind = "node"
            selection_id = legacy_node_id

    return AnalysisSnapshot(
        analysis_complete=bool(results.analysis_complete),
        input_name=results.input_name,
        workflow_cohort_policy=str(
            getattr(results, "workflow_cohort_policy", state.config.workflow_cohort_policy) or WORKFLOW_COHORT_FIRST_EVENT_DIRECT
        ),
        source_metadata=results.source_metadata if isinstance(getattr(results, "source_metadata", {}), Mapping) else {},
        filter_key=results.filter_key,
        filtered_log=results.filtered_log,
        discovery_results=discovery_results,
        comparison_df=comparison_df,
        split_info=split_info,
        analysis_summary=results.analysis_summary if isinstance(getattr(results, "analysis_summary", {}), Mapping) else {},
        active_followup_label=results.active_followup_label,
        config_change_message=results.config_change_message,
        filter_error_message=results.filter_error_message,
        performance_cache=state.caches["performance_cache"],
        variant_cache=state.caches["variant_cache"],
        dfg_cache=state.caches["dfg_cache"],
        conformance_results=results.conformance_results if isinstance(results.conformance_results, Mapping) else {},
        conformance_workspace=results.conformance_workspace if isinstance(results.conformance_workspace, Mapping) else {},
        selected_algorithms=tuple(state.config.selected_algorithms),
        stage_timings=results.stage_timings if isinstance(results.stage_timings, Mapping) else {},
        workflow_view_mode=str(getattr(results, "workflow_view_mode", "board") or "board"),
        workflow_detail_level=str(getattr(results, "workflow_detail_level", "analyst") or "analyst"),
        workflow_selection_kind=selection_kind,
        workflow_selection_id=selection_id,
        selected_workflow_node_id=legacy_node_id,
        selected_workflow_edge_id=legacy_edge_id,
    )


def _create_empty_caches() -> dict[str, OrderedDict[str, Any]]:
    return {cache_name: OrderedDict() for cache_name in CACHE_LIMITS}


def _ensure_cache_structures(state: CRPMState) -> None:
    if not isinstance(state.caches, dict):
        state.caches = {}
    for cache_name in CACHE_LIMITS:
        cache_value = state.caches.get(cache_name)
        if isinstance(cache_value, OrderedDict):
            continue
        if isinstance(cache_value, Mapping):
            state.caches[cache_name] = OrderedDict(cache_value.items())
        else:
            state.caches[cache_name] = OrderedDict()
        while len(state.caches[cache_name]) > CACHE_LIMITS[cache_name]:
            state.caches[cache_name].popitem(last=False)


def _migrate_or_create_state(session_state: Mapping[str, Any]) -> CRPMState:
    state = CRPMState(caches=_create_empty_caches())
    state.results = AnalysisResults(
        analysis_complete=bool(session_state.get("analysis_complete", False)),
        input_name=session_state.get("current_input_name"),
        workflow_cohort_policy=str(
            session_state.get("workflow_cohort_policy", WORKFLOW_COHORT_FIRST_EVENT_DIRECT) or WORKFLOW_COHORT_FIRST_EVENT_DIRECT
        ),
        source_metadata=dict(session_state.get("source_metadata", {})) if isinstance(session_state.get("source_metadata"), Mapping) else {},
        filter_key=session_state.get("current_filter_key"),
        filtered_log=session_state.get("current_filtered_log"),
        discovery_results=(
            dict(session_state.get("discovery_results", {})) if isinstance(session_state.get("discovery_results"), Mapping) else {}
        ),
        comparison_df=(
            session_state.get("comparison_df") if isinstance(session_state.get("comparison_df"), pd.DataFrame) else pd.DataFrame()
        ),
        split_info=dict(session_state.get("split_info", {})) if isinstance(session_state.get("split_info"), Mapping) else {},
        analysis_summary=(
            dict(session_state.get("analysis_summary", {})) if isinstance(session_state.get("analysis_summary"), Mapping) else {}
        ),
        train_log=session_state.get("train_log"),
        test_log=session_state.get("test_log"),
        active_followup_label=session_state.get("active_followup_label"),
        config_change_message=session_state.get("config_change_message"),
        filter_error_message=session_state.get("filter_error_message"),
        last_analysis_signature=session_state.get("last_analysis_signature"),
        stage_timings=dict(session_state.get("stage_timings", {})) if isinstance(session_state.get("stage_timings"), Mapping) else {},
        conformance_workspace=(
            dict(session_state.get("conformance_workspace", {})) if isinstance(session_state.get("conformance_workspace"), Mapping) else {}
        ),
        workflow_view_mode=str(session_state.get("workflow_view_mode", "board") or "board"),
        workflow_detail_level=str(session_state.get("workflow_detail_level", "analyst") or "analyst"),
        workflow_selection_kind=str(session_state.get("workflow_selection_kind", "none") or "none"),
        workflow_selection_id=(
            str(session_state.get("workflow_selection_id")) if session_state.get("workflow_selection_id") is not None else None
        ),
        selected_workflow_node_id=(
            str(session_state.get("selected_workflow_node_id")) if session_state.get("selected_workflow_node_id") is not None else None
        ),
        selected_workflow_edge_id=(
            str(session_state.get("selected_workflow_edge_id")) if session_state.get("selected_workflow_edge_id") is not None else None
        ),
    )
    state.config.date_filter_mode = str(session_state.get("date_filter_mode", state.config.date_filter_mode))
    state.config.workflow_cohort_policy = str(
        session_state.get("workflow_cohort_policy", state.config.workflow_cohort_policy) or WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    )
    if state.config.workflow_cohort_policy not in WORKFLOW_COHORT_POLICIES:
        state.config.workflow_cohort_policy = WORKFLOW_COHORT_FIRST_EVENT_DIRECT

    for cache_name in CACHE_LIMITS:
        cache_value = session_state.get(cache_name)
        if isinstance(cache_value, Mapping):
            state.caches[cache_name] = OrderedDict(cache_value.items())
    _ensure_cache_structures(state)
    return state
