"""Core discovery and comparison runtime for the stabilized CRPM shell."""

from __future__ import annotations

import hashlib
import io
import logging
from collections import Counter, defaultdict
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd
from pm4py.objects.log.obj import EventLog

from crpm.app_state import CRPMState, bounded_cache_get, bounded_cache_put
from crpm.conformance import compute_alignments, compute_token_replay, filter_date_range, filter_start_event, load_log, summarize_metrics
from crpm.discovery import AVAILABLE_ALGORITHMS, DiscoveryResult, compute_model_complexity, discover_all_algorithms
from crpm.formatting import format_decimal
from crpm.interpretations import assess_balanced_quality, assess_bottleneck_severity, assess_fitness, assess_precision, get_executive_summary, get_model_quadrant
from crpm.pipeline import csv_to_event_log, split_log_random
from crpm.screening import describe_followup_window, filter_log_by_incident_period, humanize_activity_label


MAX_UPLOAD_BYTES = 200 * 1024 * 1024
CONFORMANCE_WORKSPACE_CACHE_VERSION = "workflow-v2"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedLog:
    """Resolved log together with its cache signature."""

    log: EventLog
    input_name: str
    log_signature: str


def make_file_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return str(path.resolve())
    return f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


def make_uploaded_signature(raw: bytes, label: str) -> str:
    digest = hashlib.sha1(raw).hexdigest()
    return f"{label}::{digest}"


def compute_filter_key(
    log_signature: str,
    first_event: Optional[str],
    date_filter_mode: str,
    start_dt: Optional[date],
    end_dt: Optional[date],
    followup_days: Optional[int] = None,
) -> str:
    def _fmt(value: Optional[date]) -> str:
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.isoformat()
        return datetime.combine(value, datetime.min.time()).isoformat()

    return "::".join(
        [
            log_signature,
            first_event or "*",
            date_filter_mode or "*",
            _fmt(start_dt),
            _fmt(end_dt),
            str(followup_days) if followup_days is not None else "full",
        ]
    )


def compute_analysis_signature(
    *,
    log_signature: str,
    start_filter: str,
    date_filter_mode: str,
    start_date: Optional[date],
    end_date: Optional[date],
    selected_algorithms: list[str],
    enable_train_test: bool,
    random_seed: int,
    followup_days: Optional[int] = None,
) -> str:
    payload = {
        "log_signature": log_signature,
        "start_filter": start_filter,
        "date_filter_mode": date_filter_mode,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "selected_algorithms": sorted(selected_algorithms),
        "enable_train_test": enable_train_test,
        "random_seed": int(random_seed),
        "followup_days": followup_days,
    }
    return hashlib.sha1(repr(payload).encode("utf-8")).hexdigest()


def first_event_names(log: EventLog) -> list[str]:
    return sorted({trace[0]["concept:name"] for trace in log if trace})


def compute_log_stats(log: EventLog) -> dict[str, Optional[object]]:
    traces = len(log)
    events = 0
    timestamps = []
    for trace in log:
        events += len(trace)
        for event in trace:
            ts = event.get("time:timestamp")
            if isinstance(ts, datetime):
                timestamps.append(ts)
    return {
        "traces": traces,
        "events": events,
        "start": min(timestamps) if timestamps else None,
        "end": max(timestamps) if timestamps else None,
    }


def build_analysis_summary(
    *,
    log: EventLog | None,
    comparison_df: pd.DataFrame,
    conformance_workspace: Mapping[str, Any],
    stage_timings: Mapping[str, float],
) -> dict[str, Any]:
    """Build a reusable, presentation-friendly summary bundle for the current run."""
    if log is None:
        return {}

    stats = compute_log_stats(log)
    unique_activities = {
        str(event.get("concept:name"))
        for trace in log
        for event in trace
        if event.get("concept:name")
    }

    workflow = conformance_workspace.get("workflow", {}) if isinstance(conformance_workspace, Mapping) else {}
    workflow_summary = workflow.get("summary", {}) if isinstance(workflow, Mapping) else {}
    workflow_nodes = workflow.get("nodes", pd.DataFrame()) if isinstance(workflow, Mapping) else pd.DataFrame()
    workflow_edges = workflow.get("edges", pd.DataFrame()) if isinstance(workflow, Mapping) else pd.DataFrame()
    if not isinstance(workflow_nodes, pd.DataFrame):
        workflow_nodes = pd.DataFrame()
    if not isinstance(workflow_edges, pd.DataFrame):
        workflow_edges = pd.DataFrame()

    best_model = None
    best_fitness = None
    best_precision = None
    best_balance = None
    if isinstance(comparison_df, pd.DataFrame) and not comparison_df.empty:
        working = comparison_df.copy()
        if {"alignment_fitness", "precision"}.issubset(working.columns):
            working["_balance_score"] = working["alignment_fitness"].fillna(0) + working["precision"].fillna(0)
            best_row = working.loc[working["_balance_score"].idxmax()]
            best_model = str(best_row.get("model_name", best_row.get("model", "N/A")))
            best_fitness = _safe_float(best_row.get("alignment_fitness"))
            best_precision = _safe_float(best_row.get("precision"))
            if best_fitness is not None and best_precision is not None:
                best_balance = round((best_fitness + best_precision) / 2, 4)

    start = stats.get("start")
    end = stats.get("end")
    period_label = "Unavailable"
    if isinstance(start, datetime) and isinstance(end, datetime):
        period_label = f"{start:%Y-%m-%d} → {end:%Y-%m-%d}"

    return {
        "cases": int(stats.get("traces") or 0),
        "events": int(stats.get("events") or 0),
        "unique_activities": len(unique_activities),
        "period_start": start,
        "period_end": end,
        "period_label": period_label,
        "model_count": int(len(comparison_df.index)) if isinstance(comparison_df, pd.DataFrame) else 0,
        "best_model": best_model,
        "best_fitness": best_fitness,
        "best_precision": best_precision,
        "best_balance": best_balance,
        "dominant_path_share": _safe_float(workflow_summary.get("dominant_path_share")),
        "deviation_share": _safe_float(workflow_summary.get("deviation_share")),
        "median_throughput_days": _safe_float(workflow_summary.get("median_throughput_days")),
        "workflow_nodes": int(len(workflow_nodes.index)),
        "workflow_edges": int(len(workflow_edges.index)),
        "analysis_runtime_s": round(sum(float(value) for value in stage_timings.values()), 3) if stage_timings else 0.0,
    }


def resolve_xes_log(
    state: CRPMState,
    *,
    selected_path: Optional[str],
    uploaded_bytes: Optional[bytes],
    uploaded_name: Optional[str],
) -> LoadedLog:
    if uploaded_bytes is not None:
        _ensure_upload_size(uploaded_bytes)
        signature = make_uploaded_signature(uploaded_bytes, "xes_upload")
        cached_log = bounded_cache_get(state, "log_cache", signature)
        if cached_log is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp:
                tmp.write(uploaded_bytes)
                temp_path = Path(tmp.name)
            try:
                cached_log = load_log(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)
            bounded_cache_put(state, "log_cache", signature, cached_log)
        return LoadedLog(log=cached_log, input_name=uploaded_name or "uploaded.xes", log_signature=f"xes::{signature}")

    if not selected_path:
        raise ValueError("Select a XES log or upload one to continue.")

    path = Path(selected_path)
    signature = make_file_signature(path)
    cached_log = bounded_cache_get(state, "log_cache", signature)
    if cached_log is None:
        cached_log = load_log(path)
        bounded_cache_put(state, "log_cache", signature, cached_log)
    return LoadedLog(log=cached_log, input_name=path.name, log_signature=f"xes::{signature}")


def preview_csv_dataframe(state: CRPMState, uploaded_bytes: bytes) -> pd.DataFrame:
    _ensure_upload_size(uploaded_bytes)
    cache_key = make_uploaded_signature(uploaded_bytes, "csv")
    dataframe = bounded_cache_get(state, "dataframe_cache", cache_key)
    if dataframe is None:
        dataframe = pd.read_csv(io.BytesIO(uploaded_bytes))
        bounded_cache_put(state, "dataframe_cache", cache_key, dataframe)
    return dataframe


def resolve_csv_log(
    state: CRPMState,
    *,
    uploaded_bytes: Optional[bytes],
    uploaded_name: Optional[str],
    case_col: Optional[str],
    activity_col: Optional[str],
    timestamp_col: Optional[str],
) -> tuple[LoadedLog, pd.DataFrame]:
    if uploaded_bytes is None:
        raise ValueError("Upload a CSV file to continue.")

    dataframe = preview_csv_dataframe(state, uploaded_bytes)

    if not case_col or not activity_col or not timestamp_col:
        raise ValueError("Choose the case, activity, and timestamp columns before running the analysis.")

    log_key = f"{make_uploaded_signature(uploaded_bytes, 'csv')}::{case_col}:{activity_col}:{timestamp_col}"
    cached_log = bounded_cache_get(state, "log_cache", log_key)
    if cached_log is None:
        cached_log = csv_to_event_log(dataframe.copy(), case_col, activity_col, timestamp_col)
        bounded_cache_put(state, "log_cache", log_key, cached_log)

    loaded_log = LoadedLog(
        log=cached_log,
        input_name=uploaded_name or "uploaded.csv",
        log_signature=f"csv::{log_key}",
    )
    return loaded_log, dataframe


def run_discovery_comparison_pipeline(
    state: CRPMState,
    *,
    loaded_log: LoadedLog,
    start_filter: str,
    date_filter_mode: str,
    start_date: Optional[date],
    end_date: Optional[date],
    selected_algorithms: list[str],
    enable_train_test: bool,
    random_seed: int,
    followup_days: Optional[int] = None,
) -> None:
    selected_first = None if start_filter == "All" else start_filter
    analysis_signature = compute_analysis_signature(
        log_signature=loaded_log.log_signature,
        start_filter=start_filter,
        date_filter_mode=date_filter_mode,
        start_date=start_date,
        end_date=end_date,
        selected_algorithms=selected_algorithms,
        enable_train_test=enable_train_test,
        random_seed=random_seed,
        followup_days=followup_days,
    )
    filter_key = compute_filter_key(
        loaded_log.log_signature,
        selected_first,
        date_filter_mode,
        start_date,
        end_date,
        followup_days,
    )
    results = state.results
    stage_timings: dict[str, float] = {}

    filtering_started = time.perf_counter()
    filtered_log = bounded_cache_get(state, "filtered_cache", filter_key)
    if filtered_log is None:
        filtered_log = filter_start_event(loaded_log.log, selected_first)
        filtered_log = filter_date_range(filtered_log, start_date, end_date, mode=date_filter_mode)
        if followup_days is not None:
            if not selected_first:
                results.reset(
                    input_name=loaded_log.input_name,
                    log_signature=loaded_log.log_signature,
                    filter_key=filter_key,
                    active_followup_label=describe_followup_window(followup_days),
                    filter_error_message=(
                        "A follow-up window requires an explicit screening anchor. "
                        "Select a start event before rerunning the analysis."
                    ),
                )
                return
            filtered_log = filter_log_by_incident_period(
                filtered_log,
                anchor_activity=selected_first,
                followup_days=followup_days,
            )
        bounded_cache_put(state, "filtered_cache", filter_key, filtered_log)
    stage_timings["filtering_s"] = time.perf_counter() - filtering_started

    results.filter_error_message = None
    results.config_change_message = None

    if len(filtered_log) == 0:
        results.reset(
            input_name=loaded_log.input_name,
            log_signature=loaded_log.log_signature,
            filter_key=filter_key,
            active_followup_label=describe_followup_window(followup_days),
            filter_error_message=(
            "No traces remain after applying the selected filters. Adjust the filter settings and run the analysis again."
            ),
        )
        return

    split_started = time.perf_counter()
    if enable_train_test:
        train_log, test_log, split_info = split_log_random(filtered_log, train_ratio=0.8, random_seed=random_seed)
        discovery_log = train_log
        evaluation_log = test_log
        eval_mode = "test"
        train_log_out = train_log
        test_log_out = test_log
        split_info_out = split_info
    else:
        discovery_log = filtered_log
        evaluation_log = filtered_log
        eval_mode = "full"
        train_log_out = None
        test_log_out = None
        split_info_out = {}
    stage_timings["train_test_split_s"] = time.perf_counter() - split_started

    discovery_cache_key = f"{filter_key}::{','.join(sorted(selected_algorithms))}::{eval_mode}::{random_seed}"
    discovery_started = time.perf_counter()
    discovery_results = bounded_cache_get(state, "discovery_results_cache", discovery_cache_key)
    if discovery_results is None:
        discovery_results = discover_all_algorithms(discovery_log, selected_algorithms)
        bounded_cache_put(state, "discovery_results_cache", discovery_cache_key, discovery_results)
    stage_timings["discovery_s"] = time.perf_counter() - discovery_started

    conformance_results: dict[str, Any] = {}
    conformance_started = time.perf_counter()
    for model_name, result in discovery_results.items():
        conformance_key = f"{filter_key}::{model_name}::{eval_mode}"
        conformance_result = bounded_cache_get(state, "conformance_cache", conformance_key)
        if conformance_result is None:
            conformance_result = compute_full_conformance(evaluation_log, result.net, result.initial_marking, result.final_marking, model_name)
            bounded_cache_put(state, "conformance_cache", conformance_key, conformance_result)
        conformance_results[model_name] = conformance_result
    stage_timings["conformance_s"] = time.perf_counter() - conformance_started

    comparison_started = time.perf_counter()
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)
    stage_timings["comparison_s"] = time.perf_counter() - comparison_started

    workspace_started = time.perf_counter()
    workspace_cache_key = f"{analysis_signature}::{CONFORMANCE_WORKSPACE_CACHE_VERSION}"
    conformance_workspace = bounded_cache_get(state, "conformance_workspace_cache", workspace_cache_key)
    if conformance_workspace is None:
        try:
            conformance_workspace = build_conformance_workspace_payload(
                log=filtered_log,
                discovery_results=discovery_results,
                conformance_results=conformance_results,
                comparison_df=comparison_df,
            )
        except Exception:
            logger.exception("Failed to build conformance workspace payload")
            conformance_workspace = {
                "model_summary_df": pd.DataFrame(),
                "deviation_summary_df": pd.DataFrame(),
                "trace_deviation_df": pd.DataFrame(),
                "workflow": {"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()},
                "has_workflow": False,
            }
        bounded_cache_put(state, "conformance_workspace_cache", workspace_cache_key, conformance_workspace)
    stage_timings["conformance_workspace_s"] = time.perf_counter() - workspace_started

    results.input_name = loaded_log.input_name
    results.log_signature = loaded_log.log_signature
    results.filter_key = filter_key
    results.filtered_log = filtered_log
    results.discovery_results = discovery_results
    results.comparison_df = comparison_df
    results.conformance_results = conformance_results
    results.conformance_workspace = conformance_workspace
    results.analysis_summary = build_analysis_summary(
        log=filtered_log,
        comparison_df=comparison_df,
        conformance_workspace=conformance_workspace,
        stage_timings=stage_timings,
    )
    results.train_log = train_log_out
    results.test_log = test_log_out
    results.split_info = split_info_out
    results.active_followup_label = describe_followup_window(followup_days)
    results.analysis_complete = True
    results.config_change_message = None
    results.filter_error_message = None
    results.stage_timings = stage_timings
    results.last_analysis_signature = analysis_signature


def build_model_comparison_dataframe(
    discovery_results: dict[str, DiscoveryResult],
    conformance_results: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    for model_name, result in discovery_results.items():
        conf = conformance_results.get(model_name, {})
        summary = conf.get("summary", {})
        complexity = compute_model_complexity(result)

        alignment_fitness = summary.get("alignment_fitness", {}).get("log_fitness")
        token_fitness = summary.get("token_fitness", {}).get("log_fitness")
        precision = conf.get("precision")

        rows.append(
            {
                "model_name": model_name,
                "algorithm": result.algorithm,
                "variant": result.variant,
                "alignment_fitness": alignment_fitness,
                "token_fitness": token_fitness,
                "precision": precision,
                "num_transitions": getattr(result, "num_transitions", 0),
                "num_places": getattr(result, "num_places", 0),
                "arc_degree": complexity.get("arc_degree", 0),
                "complexity_score": complexity.get("complexity_score", 0),
                "discovery_time_s": getattr(result, "discovery_time_s", 0),
                "fitness_quality": assess_fitness(alignment_fitness)[0] if pd.notna(alignment_fitness) else "N/A",
                "precision_quality": assess_precision(precision)[0] if pd.notna(precision) else "N/A",
                "quadrant": get_model_quadrant(alignment_fitness, precision),
            }
        )

    return pd.DataFrame(rows)


def compute_full_conformance(log: EventLog, net, im, fm, model_name: str) -> dict[str, Any]:
    align_res = compute_alignments(log, net, im, fm)
    token_res = compute_token_replay(log, net, im, fm)

    try:
        from pm4py.algo.evaluation.precision import algorithm as precision_evaluator

        precision = float(precision_evaluator.apply(log, net, im, fm))
    except Exception:
        precision = None

    summary = summarize_metrics(align_res, token_res)
    if precision is not None:
        summary["precision"] = {"value": precision}

    return {
        "model_name": model_name,
        "alignments": align_res,
        "token": token_res,
        "precision": precision,
        "summary": summary,
    }


def build_conformance_workspace_payload(
    *,
    log: EventLog | None,
    discovery_results: Mapping[str, DiscoveryResult],
    conformance_results: Mapping[str, Any],
    comparison_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build a hybrid conformance workspace payload for the conformance page."""
    model_summary_df = _build_model_summary_table(discovery_results, conformance_results, comparison_df)
    deviation_summary_df = _build_deviation_summary_table(conformance_results)
    trace_deviation_df = _build_trace_deviation_table(conformance_results)
    workflow_payload = _build_workflow_payload(
        log,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    return {
        "model_summary_df": model_summary_df,
        "deviation_summary_df": deviation_summary_df,
        "trace_deviation_df": trace_deviation_df,
        "workflow": workflow_payload,
        "has_workflow": not workflow_payload["nodes"].empty,
    }


def _build_model_summary_table(
    discovery_results: Mapping[str, DiscoveryResult],
    conformance_results: Mapping[str, Any],
    comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    comparison_index = None
    if not comparison_df.empty and "model_name" in comparison_df.columns:
        comparison_index = comparison_df.drop_duplicates("model_name", keep="last").set_index("model_name", drop=False)

    for model_name, discovery_result in discovery_results.items():
        conf = conformance_results.get(model_name, {})
        summary = conf.get("summary", {}) if isinstance(conf, Mapping) else {}
        align_summary = summary.get("alignment_fitness", {}) if isinstance(summary, Mapping) else {}
        token_summary = summary.get("token_fitness", {}) if isinstance(summary, Mapping) else {}

        alignment_fitness = _safe_float(align_summary.get("log_fitness"))
        token_fitness = _safe_float(token_summary.get("log_fitness"))
        precision = _safe_float(conf.get("precision") if isinstance(conf, Mapping) else None)
        recommendation = get_executive_summary(
            alignment_fitness if alignment_fitness is not None else float("nan"),
            precision if precision is not None else float("nan"),
            int(getattr(discovery_result, "num_transitions", 0) or 0),
            str(getattr(discovery_result, "algorithm", model_name)),
        ).get("recommendation", "N/A")

        comparison_row = comparison_index.loc[model_name] if comparison_index is not None and model_name in comparison_index.index else {}
        rows.append(
            {
                "model": model_name,
                "algorithm": getattr(discovery_result, "algorithm", "N/A"),
                "variant": getattr(discovery_result, "variant", "N/A"),
                "alignment_fitness": _first_value(comparison_row, "alignment_fitness", fallback=alignment_fitness),
                "token_fitness": _first_value(comparison_row, "token_fitness", fallback=token_fitness),
                "precision": _first_value(comparison_row, "precision", fallback=precision),
                "quadrant": _first_value(comparison_row, "quadrant", fallback=get_model_quadrant(alignment_fitness, precision)),
                "fitness_quality": _first_value(comparison_row, "fitness_quality", fallback=assess_fitness(alignment_fitness)[0] if alignment_fitness is not None else "N/A"),
                "precision_quality": _first_value(comparison_row, "precision_quality", fallback=assess_precision(precision)[0] if precision is not None else "N/A"),
                "recommendation": recommendation,
                "summary": _summarize_metric_bundle(summary),
            }
        )

    return pd.DataFrame(rows)


def _build_deviation_summary_table(conformance_results: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for model_name, conf in conformance_results.items():
        summary = conf.get("summary", {}) if isinstance(conf, Mapping) else {}
        rows.append(
            {
                "model": model_name,
                "alignment_summary": _summarize_metric_bundle(summary.get("alignment_fitness", {})),
                "token_summary": _summarize_metric_bundle(summary.get("token_fitness", {})),
                "precision": _safe_float(conf.get("precision") if isinstance(conf, Mapping) else None),
                "deviation_note": _build_deviation_note(conf),
            }
        )
    return pd.DataFrame(rows)


def _build_trace_deviation_table(conformance_results: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for model_name, conf in conformance_results.items():
        align_res = conf.get("alignments", {}) if isinstance(conf, Mapping) else {}
        token_res = conf.get("token", {}) if isinstance(conf, Mapping) else {}
        aligned_traces = align_res.get("aligned_traces", []) if isinstance(align_res, Mapping) else []
        token_traces = token_res.get("token_results", []) if isinstance(token_res, Mapping) else []

        max_len = max(len(aligned_traces), len(token_traces))
        for idx in range(max_len):
            align_row = aligned_traces[idx] if idx < len(aligned_traces) and isinstance(aligned_traces[idx], Mapping) else {}
            token_row = token_traces[idx] if idx < len(token_traces) and isinstance(token_traces[idx], Mapping) else {}
            fitness = _safe_float(align_row.get("fitness"))
            trace_value = token_row.get("trace_fitness")
            if trace_value is None:
                trace_value = token_row.get("fitness")
            trace_fitness = _safe_float(trace_value)
            cost = _safe_float(align_row.get("cost"))
            missing = token_row.get("missing_tokens")
            remaining = token_row.get("remaining_tokens")

            if all(value is None for value in (fitness, trace_fitness, cost, missing, remaining)):
                continue

            rows.append(
                {
                    "model": model_name,
                    "trace_index": idx,
                    "alignment_fitness": fitness,
                    "token_trace_fitness": trace_fitness,
                    "alignment_cost": cost,
                    "missing_tokens": _count_tokens(missing),
                    "remaining_tokens": _count_tokens(remaining),
                    "trace_status": _trace_status(fitness, trace_fitness, cost, missing, remaining),
                }
            )

    df = pd.DataFrame(rows)
    if not df.empty and "token_trace_fitness" in df.columns:
        df = df.sort_values(
            by=["token_trace_fitness", "alignment_cost"],
            ascending=[True, False],
            na_position="last",
        ).reset_index(drop=True)
    return df


def _build_workflow_payload(
    log: EventLog | None,
    *,
    conformance_results: Mapping[str, Any] | None = None,
    comparison_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    from crpm.screening import STEP_LABELS, STEP_ORDER, classify_activity_steps, humanize_activity_label

    empty_nodes = pd.DataFrame(
        columns=[
            "step",
            "activity",
            "display_name",
            "business_label",
            "cases",
            "occurrences",
            "median_next_delay_days",
            "p90_next_delay_days",
            "severity",
            "conformance_bucket",
            "step_rank",
            "branch_role",
            "lane",
            "node_type",
            "branch_family",
            "parent_branch",
            "coverage_pct",
            "coverage_rank",
            "coverage_group",
            "sync_cases",
            "log_move_cases",
            "model_move_cases",
            "sync_pct",
            "log_move_pct",
            "model_move_pct",
            "conformance_mix_total_cases",
            "neighbor_ids",
            "related_variant_ids",
            "top_variant_signatures",
            "trace_refs_summary",
            "selection_summary",
        ]
    )
    empty_edges = pd.DataFrame(
        columns=[
            "edge_id",
            "source",
            "target",
            "frequency",
            "share_pct",
            "median_days",
            "p90_days",
            "severity",
            "source_step",
            "target_step",
            "source_rank",
            "target_rank",
            "conformance_bucket",
            "is_deviating",
            "stroke_style",
            "stroke_weight",
            "branch_role",
            "edge_type",
            "branch_family",
            "parent_branch",
            "source_label",
            "target_label",
            "business_label",
            "coverage_rank",
            "coverage_group",
            "related_variant_ids",
            "top_variant_signatures",
            "trace_refs_summary",
            "selection_summary",
        ]
    )
    legend = pd.DataFrame(
        [
            {"group": "Conformance", "bucket": "Conformant", "meaning": "Observed transition follows the expected screening progression.", "severity": "Conformant"},
            {"group": "Conformance", "bucket": "Log deviation", "meaning": "Observed path skips, loops, or reorders the expected progression.", "severity": "Log deviation"},
            {"group": "Conformance", "bucket": "Model deviation", "meaning": "Observed path includes unmapped or off-pathway activities.", "severity": "Model deviation"},
            {"group": "Performance", "bucket": "Low", "meaning": "Median and tail delay remain close to the cohort baseline.", "severity": "Low"},
            {"group": "Performance", "bucket": "Moderate", "meaning": "Delay is rising and should be monitored.", "severity": "Moderate"},
            {"group": "Performance", "bucket": "High", "meaning": "Delay is materially above the pathway baseline.", "severity": "High"},
            {"group": "Performance", "bucket": "Critical", "meaning": "Delay is severe and likely operationally important.", "severity": "Critical"},
        ]
    )

    if log is None or len(log) == 0:
        return {
            "nodes": empty_nodes,
            "edges": empty_edges,
            "legend": legend,
            "trace_profiles": pd.DataFrame(),
            "summary": {},
            "renderer_capabilities": {"svg": True, "html_explorer": True, "cytoscape": True},
        }

    alignment_visible_activities = _workflow_alignment_visible_activities(conformance_results, comparison_df)
    activity_names = sorted(
        {str(event.get("concept:name")) for trace in log for event in trace if event.get("concept:name")}
        | alignment_visible_activities
    )
    activity_step_lookup = classify_activity_steps(activity_names)
    step_rank_lookup = {step: rank for rank, step in enumerate(STEP_ORDER)}

    step_activity_lookup: defaultdict[str, list[str]] = defaultdict(list)
    for activity_name, step in activity_step_lookup.items():
        if step:
            step_activity_lookup[str(step)].append(str(activity_name))

    ordered_nodes = [step for step in STEP_ORDER if step_activity_lookup.get(step)]
    ordered_nodes.extend(activity_name for activity_name in activity_names if activity_step_lookup.get(activity_name) is None)

    def _canonical_node_id(activity_name: str) -> str:
        step = activity_step_lookup.get(activity_name)
        return str(step) if step else str(activity_name)

    def _node_label(node_id: str) -> str:
        return STEP_LABELS.get(node_id, humanize_activity_label(node_id))

    alignment_mix = _workflow_alignment_mix_by_node(
        log,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
        canonicalize_activity=_canonical_node_id,
    )

    node_case_counts: Counter[str] = Counter()
    node_occurrences: Counter[str] = Counter()
    node_outgoing_delays: defaultdict[str, list[float]] = defaultdict(list)
    edge_counts: Counter[tuple[str, str]] = Counter()
    edge_delays: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
    node_variant_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    edge_variant_counts: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    node_raw_activity_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    edge_raw_pair_counts: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    node_case_refs: defaultdict[str, list[str]] = defaultdict(list)
    edge_case_refs: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    throughput_days: list[float] = []
    trace_profiles: list[dict[str, Any]] = []
    canonical_variant_counts: Counter[str] = Counter()

    for trace in log:
        events = [event for event in trace if event.get("concept:name")]
        raw_activities = [str(event.get("concept:name")) for event in events]
        if not raw_activities:
            continue
        case_id = str(trace.attributes.get("concept:name") or trace.attributes.get("case_id") or f"case-{len(throughput_days) + 1}")
        throughput_days_value: Optional[float] = None
        if len(events) >= 2:
            first_ts = events[0].get("time:timestamp")
            last_ts = events[-1].get("time:timestamp")
            if hasattr(first_ts, "timestamp") and hasattr(last_ts, "timestamp"):
                throughput_days_value = max(0.0, (last_ts - first_ts).total_seconds() / 86400)
                throughput_days.append(throughput_days_value)

        canonical_events: list[tuple[str, str, Any, Optional[str]]] = []
        for event in events:
            raw_activity = str(event.get("concept:name"))
            step = activity_step_lookup.get(raw_activity)
            node_id = _canonical_node_id(raw_activity)
            canonical_events.append((raw_activity, node_id, event.get("time:timestamp"), step))
            node_occurrences[node_id] += 1
            node_raw_activity_counts[node_id][raw_activity] += 1

        canonical_path: list[str] = []
        for _, node_id, _, _ in canonical_events:
            if not canonical_path or canonical_path[-1] != node_id:
                canonical_path.append(node_id)
        variant_signature = " → ".join(_node_label(node_id) for node_id in canonical_path)
        canonical_variant_counts[variant_signature] += 1

        seen_nodes: set[str] = set()
        for node_id in canonical_path:
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            node_case_counts[node_id] += 1
            node_variant_counts[node_id][variant_signature] += 1
            if len(node_case_refs[node_id]) < 5:
                node_case_refs[node_id].append(case_id)

        seen_edges: set[tuple[str, str]] = set()
        trace_edge_ids: list[str] = []
        has_log_deviation = False
        for current, nxt in zip(canonical_events, canonical_events[1:]):
            source_raw, source_node, current_ts, source_step = current
            target_raw, target_node, next_ts, target_step = nxt
            if source_node == target_node and source_step is not None and target_step is not None:
                continue
            edge_key = (source_node, target_node)
            edge_counts[edge_key] += 1
            edge_variant_counts[edge_key][variant_signature] += 1
            edge_raw_pair_counts[edge_key][f"{humanize_activity_label(source_raw)} → {humanize_activity_label(target_raw)}"] += 1
            if edge_key not in seen_edges and len(edge_case_refs[edge_key]) < 5:
                edge_case_refs[edge_key].append(case_id)
                seen_edges.add(edge_key)
            current_ts = current_ts
            next_ts = next_ts
            if hasattr(current_ts, "timestamp") and hasattr(next_ts, "timestamp"):
                delta = (next_ts - current_ts).total_seconds()
                if delta >= 0:
                    edge_delays[edge_key].append(delta / 86400)
                    node_outgoing_delays[source_node].append(delta / 86400)
            if _edge_conformance_bucket(
                source_step,
                target_step,
                step_rank_lookup.get(source_step),
                step_rank_lookup.get(target_step),
            ) == "Log deviation":
                has_log_deviation = True
            trace_edge_ids.append(f"{source_node} -> {target_node}")

        has_model_deviation = any(step is None for _, _, _, step in canonical_events)
        trace_profiles.append(
            {
                "case_id": case_id,
                "event_count": len(events),
                "throughput_days": throughput_days_value,
                "variant_signature": variant_signature,
                "has_log_deviation": has_log_deviation,
                "has_model_deviation": has_model_deviation,
                "has_deviation": has_log_deviation or has_model_deviation,
                "node_ids": canonical_path,
                "edge_ids": list(dict.fromkeys(trace_edge_ids)),
            }
        )

    dominant_variant_share = (
        round(canonical_variant_counts.most_common(1)[0][1] / len(log) * 100, 1)
        if canonical_variant_counts and len(log)
        else 0.0
    )
    overall_delay_values = [delay for delays in edge_delays.values() for delay in delays]
    overall_median = float(pd.Series(overall_delay_values).median()) if overall_delay_values else 0.0
    edge_bucket_by_activity: defaultdict[str, set[str]] = defaultdict(set)
    edge_bucket_weight_by_activity: defaultdict[str, Counter[str]] = defaultdict(Counter)
    neighbor_lookup: defaultdict[str, set[str]] = defaultdict(set)

    node_rows = []
    max_cases = max(node_case_counts.values()) if node_case_counts else 0
    max_occurrences = max(node_occurrences.values()) if node_occurrences else 0
    for node_id in ordered_nodes:
        step = node_id if node_id in step_rank_lookup else None
        display_label = _node_label(node_id)
        outgoing_delays = node_outgoing_delays.get(node_id, [])
        severity = _delay_bucket(outgoing_delays, overall_median)
        cases = int(node_case_counts.get(node_id, 0))
        occurrences = int(node_occurrences.get(node_id, 0))
        coverage_pct = round((cases / max_cases) * 100, 1) if max_cases else 0.0
        activity_pct = round((occurrences / max_occurrences) * 100, 1) if max_occurrences else 0.0
        node_variants = node_variant_counts.get(node_id, Counter())
        raw_activities = [activity for activity, _ in node_raw_activity_counts.get(node_id, Counter()).most_common()]
        branch_family = _workflow_branch_family(raw_activities[0] if raw_activities else node_id, step)
        node_type = _workflow_node_type(step=step, step_rank=step_rank_lookup.get(step), total_steps=len(STEP_ORDER))
        mix_stats = alignment_mix.get(node_id, {})
        sync_cases = _safe_int(mix_stats.get("sync_cases"))
        log_move_cases = _safe_int(mix_stats.get("log_move_cases"))
        model_move_cases = _safe_int(mix_stats.get("model_move_cases"))
        mix_total_cases = _safe_int(mix_stats.get("conformance_mix_total_cases"))
        if mix_total_cases <= 0:
            fallback_cases = max(cases, occurrences, 0)
            bucket_value = "Model deviation" if step is None else "Conformant"
            if bucket_value == "Conformant":
                sync_cases = fallback_cases
                log_move_cases = 0
                model_move_cases = 0
            elif bucket_value == "Model deviation":
                sync_cases = 0
                log_move_cases = fallback_cases if step is None else 0
                model_move_cases = 0 if step is None else fallback_cases
            mix_total_cases = sync_cases + log_move_cases + model_move_cases
        sync_pct = round(sync_cases / mix_total_cases * 100, 1) if mix_total_cases else 0.0
        log_move_pct = round(log_move_cases / mix_total_cases * 100, 1) if mix_total_cases else 0.0
        model_move_pct = round(model_move_cases / mix_total_cases * 100, 1) if mix_total_cases else 0.0
        node_rows.append(
            {
                "step": step or "unmapped",
                "activity": node_id,
                "display_name": display_label,
                "business_label": display_label,
                "cases": cases,
                "occurrences": occurrences,
                "median_next_delay_days": _median_or_none(outgoing_delays),
                "p90_next_delay_days": _percentile_or_none(outgoing_delays, 90),
                "severity": severity,
                "conformance_bucket": "Model deviation" if step is None else "Conformant",
                "step_rank": step_rank_lookup.get(step, len(STEP_ORDER) + activity_names.index(node_id) if node_id in activity_names else len(STEP_ORDER)),
                "branch_role": "mainline" if step is not None else "side",
                "lane": "center" if step is not None else "side",
                "node_type": node_type,
                "branch_family": branch_family,
                "parent_branch": None if step is not None else "mainline",
                "coverage_pct": coverage_pct,
                "activity_pct": activity_pct,
                "coverage_rank": 0,
                "coverage_group": _coverage_group(coverage_pct),
                "sync_cases": sync_cases,
                "log_move_cases": log_move_cases,
                "model_move_cases": model_move_cases,
                "sync_pct": sync_pct,
                "log_move_pct": log_move_pct,
                "model_move_pct": model_move_pct,
                "conformance_mix_total_cases": mix_total_cases,
                "raw_activities": raw_activities,
                "related_variant_ids": [signature for signature, _ in node_variants.most_common(3)],
                "top_variant_signatures": [signature for signature, _ in node_variants.most_common(3)],
                "trace_refs_summary": {
                    "sample_case_ids": list(node_case_refs.get(node_id, [])),
                    "case_count": cases,
                },
                "selection_summary": {
                    "kind": "node",
                    "activity": node_id,
                    "business_label": display_label,
                    "cases": cases,
                    "occurrences": occurrences,
                    "coverage_pct": coverage_pct,
                    "activity_pct": activity_pct,
                    "median_days": _median_or_none(outgoing_delays),
                    "p90_days": _percentile_or_none(outgoing_delays, 90),
                    "raw_activities": raw_activities[:5],
                    "sync_cases": sync_cases,
                    "log_move_cases": log_move_cases,
                    "model_move_cases": model_move_cases,
                    "sync_pct": sync_pct,
                    "log_move_pct": log_move_pct,
                    "model_move_pct": model_move_pct,
                },
            }
        )

    edge_rows = []
    total_edges = sum(edge_counts.values()) or 1
    for (source, target), frequency in sorted(edge_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])):
        delays = edge_delays.get((source, target), [])
        source_step = source if source in step_rank_lookup else None
        target_step = target if target in step_rank_lookup else None
        source_rank = step_rank_lookup.get(source_step)
        target_rank = step_rank_lookup.get(target_step)
        conformance_bucket = _edge_conformance_bucket(source_step, target_step, source_rank, target_rank)
        share_pct = round(frequency / total_edges * 100, 1)
        branch_role = "mainline" if source_step is not None and target_step is not None and conformance_bucket == "Conformant" else "side"
        source_label = _node_label(source)
        target_label = _node_label(target)
        edge_variants = edge_variant_counts.get((source, target), Counter())
        raw_pair_labels = [pair for pair, _ in edge_raw_pair_counts.get((source, target), Counter()).most_common()]
        branch_family = _workflow_branch_family((raw_pair_labels[0] if raw_pair_labels else target), target_step)
        edge_bucket_by_activity[source].add(conformance_bucket)
        edge_bucket_by_activity[target].add(conformance_bucket)
        edge_bucket_weight_by_activity[source][conformance_bucket] += int(frequency)
        edge_bucket_weight_by_activity[target][conformance_bucket] += int(frequency)
        neighbor_lookup[source].add(target)
        neighbor_lookup[target].add(source)
        edge_rows.append(
            {
                "edge_id": f"{source} -> {target}",
                "source": source,
                "target": target,
                "source_label": source_label,
                "target_label": target_label,
                "business_label": f"{source_label} → {target_label}",
                "frequency": int(frequency),
                "share_pct": share_pct,
                "median_days": _median_or_none(delays),
                "p90_days": _percentile_or_none(delays, 90),
                "severity": _delay_bucket(delays, overall_median),
                "source_step": source_step or "unmapped",
                "target_step": target_step or "unmapped",
                "source_rank": source_rank if source_rank is not None else len(STEP_ORDER) + 10,
                "target_rank": target_rank if target_rank is not None else len(STEP_ORDER) + 10,
                "conformance_bucket": conformance_bucket,
                "is_deviating": conformance_bucket != "Conformant",
                "stroke_style": "dashed" if conformance_bucket != "Conformant" else "solid",
                "stroke_weight": max(1.0, round(frequency / max(total_edges, 1) * 18, 2)),
                "branch_role": branch_role,
                "edge_type": _workflow_edge_type(source_step, target_step, source_rank, target_rank, source == target, conformance_bucket),
                "branch_family": branch_family,
                "parent_branch": None if branch_role == "mainline" else "mainline",
                "coverage_rank": 0,
                "coverage_group": _coverage_group(share_pct),
                "raw_pairs": raw_pair_labels,
                "related_variant_ids": [signature for signature, _ in edge_variants.most_common(3)],
                "top_variant_signatures": [signature for signature, _ in edge_variants.most_common(3)],
                "trace_refs_summary": {
                    "sample_case_ids": list(edge_case_refs.get((source, target), [])),
                    "case_count": int(frequency),
                },
                "selection_summary": {
                    "kind": "edge",
                    "source": source,
                    "target": target,
                    "business_label": f"{source_label} → {target_label}",
                    "frequency": int(frequency),
                    "median_days": _median_or_none(delays),
                    "p90_days": _percentile_or_none(delays, 90),
                    "share_pct": share_pct,
                    "raw_pairs": raw_pair_labels[:5],
                },
            }
        )

    nodes_df = pd.DataFrame(node_rows)
    edges_df = pd.DataFrame(edge_rows)
    if not nodes_df.empty:
        node_bucket_by_activity: dict[str, str] = {}
        for _, node_row in nodes_df.iterrows():
            activity = str(node_row.get("activity", ""))
            if node_row.get("step") == "unmapped":
                node_bucket_by_activity[activity] = "Model deviation"
                continue
            bucket_weights = edge_bucket_weight_by_activity.get(activity, Counter())
            buckets = edge_bucket_by_activity.get(activity, set())
            has_conformant = bucket_weights.get("Conformant", 0) > 0
            has_log = "Log deviation" in buckets
            has_model = "Model deviation" in buckets
            if has_conformant and (has_log or has_model):
                node_bucket_by_activity[activity] = "Mixed"
            elif has_conformant:
                node_bucket_by_activity[activity] = "Conformant"
            elif has_log:
                node_bucket_by_activity[activity] = "Log deviation"
            elif has_model:
                node_bucket_by_activity[activity] = "Model deviation"
            else:
                node_bucket_by_activity[activity] = "Conformant"

        coverage_rank_lookup = {
            activity: rank
            for rank, activity in enumerate(
                nodes_df.sort_values(by=["cases", "occurrences", "display_name"], ascending=[False, False, True])["activity"].tolist(),
                start=1,
            )
        }
        nodes_df["coverage_rank"] = nodes_df["activity"].map(coverage_rank_lookup).fillna(0).astype(int)
        nodes_df["conformance_bucket"] = nodes_df["activity"].map(node_bucket_by_activity).fillna(nodes_df["conformance_bucket"])
        nodes_df["neighbor_ids"] = nodes_df["activity"].map(lambda activity: sorted(neighbor_lookup.get(str(activity), set())))
        nodes_df["branch_role"] = nodes_df.apply(
            lambda row: "mainline"
            if row.get("step") != "unmapped" and row.get("conformance_bucket") == "Conformant"
            else "side",
            axis=1,
        )
        nodes_df["lane"] = nodes_df.apply(
            lambda row: "center"
            if row.get("branch_role") == "mainline"
            else ("right" if row.get("branch_family") in {"admin_review", "rejection", "no_show"} or row.get("conformance_bucket") == "Model deviation" else "left"),
            axis=1,
        )
        nodes_df["parent_branch"] = nodes_df.apply(
            lambda row: None if row.get("branch_role") == "mainline" else str(row.get("branch_family") or "mainline"),
            axis=1,
        )
    if not edges_df.empty:
        edge_rank_lookup = {
            edge_id: rank
            for rank, edge_id in enumerate(
                edges_df.sort_values(by=["frequency", "share_pct", "business_label"], ascending=[False, False, True])["edge_id"].tolist(),
                start=1,
            )
        }
        edges_df["coverage_rank"] = edges_df["edge_id"].map(edge_rank_lookup).fillna(0).astype(int)
    if not nodes_df.empty:
        nodes_df = nodes_df.sort_values(by=["step_rank", "cases", "occurrences"], ascending=[True, False, False]).reset_index(drop=True)
    if not edges_df.empty:
        edges_df = edges_df.sort_values(by=["source_rank", "target_rank", "frequency"], ascending=[True, True, False]).reset_index(drop=True)

    trace_profiles_df = pd.DataFrame(trace_profiles)

    return {
        "nodes": nodes_df,
        "edges": edges_df,
        "legend": legend,
        "trace_profiles": trace_profiles_df,
        "overall_median_delay_days": overall_median,
        "summary": {
            "cases_covered": int(len(log)),
            "events_covered": int(sum(len(trace) for trace in log)),
            "dominant_path_share": dominant_variant_share,
            "deviation_share": round(
                (sum(1 for profile in trace_profiles if bool(profile.get("has_deviation"))) / len(trace_profiles) * 100),
                1,
            )
            if trace_profiles
            else 0.0,
            "log_deviation_share": round(
                (sum(1 for profile in trace_profiles if bool(profile.get("has_log_deviation"))) / len(trace_profiles) * 100),
                1,
            )
            if trace_profiles
            else 0.0,
            "model_deviation_share": round(
                (sum(1 for profile in trace_profiles if bool(profile.get("has_model_deviation"))) / len(trace_profiles) * 100),
                1,
            )
            if trace_profiles
            else 0.0,
            "median_throughput_days": round(float(pd.Series(throughput_days).median()), 1) if throughput_days else None,
        },
        "renderer_capabilities": {
            "svg": True,
            "html_explorer": True,
            "cytoscape": True,
        },
    }


def _workflow_alignment_mix_by_node(
    log: EventLog | None,
    *,
    conformance_results: Mapping[str, Any] | None,
    comparison_df: pd.DataFrame | None,
    canonicalize_activity,
) -> dict[str, dict[str, float]]:
    if log is None or not conformance_results:
        return {}

    reference_model = _workflow_reference_alignment_model(conformance_results, comparison_df)
    if not reference_model:
        return {}

    model_payload = conformance_results.get(reference_model, {})
    alignments_payload = model_payload.get("alignments", {}) if isinstance(model_payload, Mapping) else {}
    aligned_traces = alignments_payload.get("aligned_traces", []) if isinstance(alignments_payload, Mapping) else []
    if not isinstance(aligned_traces, list) or not aligned_traces:
        return {}

    node_case_sets: defaultdict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"sync": set(), "log": set(), "model": set()}
    )
    for trace, aligned_trace in zip(log, aligned_traces):
        if not isinstance(aligned_trace, Mapping):
            continue
        case_id = str(
            trace.attributes.get("concept:name")
            or trace.attributes.get("case_id")
            or f"case-{len(node_case_sets) + 1}"
        )
        for alignment_move in aligned_trace.get("alignment", []) or []:
            if not isinstance(alignment_move, (list, tuple)) or len(alignment_move) != 2:
                continue
            log_label = _workflow_alignment_activity_label(alignment_move[0])
            model_label = _workflow_alignment_activity_label(alignment_move[1])
            if log_label and model_label:
                if log_label == model_label:
                    node_case_sets[canonicalize_activity(log_label)]["sync"].add(case_id)
                else:
                    node_case_sets[canonicalize_activity(log_label)]["log"].add(case_id)
                    node_case_sets[canonicalize_activity(model_label)]["model"].add(case_id)
            elif log_label:
                node_case_sets[canonicalize_activity(log_label)]["log"].add(case_id)
            elif model_label:
                node_case_sets[canonicalize_activity(model_label)]["model"].add(case_id)

    node_case_counts: dict[str, dict[str, float]] = {}
    for node_id, buckets in node_case_sets.items():
        sync_cases = len(buckets["sync"])
        log_move_cases = len(buckets["log"])
        model_move_cases = len(buckets["model"])
        total = sync_cases + log_move_cases + model_move_cases
        node_case_counts[str(node_id)] = {
            "sync_cases": float(sync_cases),
            "log_move_cases": float(log_move_cases),
            "model_move_cases": float(model_move_cases),
            "conformance_mix_total_cases": float(total),
        }
    return node_case_counts


def _workflow_alignment_visible_activities(
    conformance_results: Mapping[str, Any] | None,
    comparison_df: pd.DataFrame | None,
) -> set[str]:
    if not conformance_results:
        return set()
    reference_model = _workflow_reference_alignment_model(conformance_results, comparison_df)
    if not reference_model:
        return set()
    model_payload = conformance_results.get(reference_model, {})
    alignments_payload = model_payload.get("alignments", {}) if isinstance(model_payload, Mapping) else {}
    aligned_traces = alignments_payload.get("aligned_traces", []) if isinstance(alignments_payload, Mapping) else []
    if not isinstance(aligned_traces, list) or not aligned_traces:
        return set()
    activities: set[str] = set()
    for aligned_trace in aligned_traces:
        if not isinstance(aligned_trace, Mapping):
            continue
        for alignment_move in aligned_trace.get("alignment", []) or []:
            if not isinstance(alignment_move, (list, tuple)) or len(alignment_move) != 2:
                continue
            log_label = _workflow_alignment_activity_label(alignment_move[0])
            model_label = _workflow_alignment_activity_label(alignment_move[1])
            if log_label:
                activities.add(log_label)
            if model_label:
                activities.add(model_label)
    return activities


def _workflow_reference_alignment_model(
    conformance_results: Mapping[str, Any],
    comparison_df: pd.DataFrame | None,
) -> Optional[str]:
    if comparison_df is not None and not comparison_df.empty and "model_name" in comparison_df.columns:
        working = comparison_df.copy()
        for column in ("alignment_fitness", "precision"):
            if column not in working.columns:
                working[column] = 0.0
            working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)
        working = working.assign(_workflow_rank=working["alignment_fitness"] + working["precision"])
        working = working.sort_values(
            by=["_workflow_rank", "alignment_fitness", "precision", "model_name"],
            ascending=[False, False, False, True],
        )
        for _, row in working.iterrows():
            model_name = str(row.get("model_name", "")).strip()
            if not model_name:
                continue
            model_payload = conformance_results.get(model_name, {})
            alignments_payload = model_payload.get("alignments", {}) if isinstance(model_payload, Mapping) else {}
            aligned_traces = alignments_payload.get("aligned_traces", []) if isinstance(alignments_payload, Mapping) else []
            if isinstance(aligned_traces, list) and aligned_traces:
                return model_name

    if "Heuristics (Classic)" in conformance_results:
        model_payload = conformance_results.get("Heuristics (Classic)", {})
        alignments_payload = model_payload.get("alignments", {}) if isinstance(model_payload, Mapping) else {}
        aligned_traces = alignments_payload.get("aligned_traces", []) if isinstance(alignments_payload, Mapping) else []
        if isinstance(aligned_traces, list) and aligned_traces:
            return "Heuristics (Classic)"

    for model_name, model_payload in conformance_results.items():
        alignments_payload = model_payload.get("alignments", {}) if isinstance(model_payload, Mapping) else {}
        aligned_traces = alignments_payload.get("aligned_traces", []) if isinstance(alignments_payload, Mapping) else []
        if isinstance(aligned_traces, list) and aligned_traces:
            return str(model_name)
    return None


def _workflow_alignment_activity_label(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text == ">>" or text.lower() in {"none", "tau"}:
            return None
        return text
    if isinstance(value, (list, tuple)):
        for candidate in reversed(value):
            label = _workflow_alignment_activity_label(candidate)
            if label:
                return label
        return None
    if hasattr(value, "label"):
        return _workflow_alignment_activity_label(getattr(value, "label"))
    text = str(value).strip()
    if not text or text == ">>" or text.lower() in {"none", "tau"}:
        return None
    return text


def _workflow_branch_family(activity: str, step: Optional[str]) -> str:
    activity_key = str(activity or "").lower()
    if "review" in activity_key:
        return "admin_review"
    if "reject" in activity_key:
        return "rejection"
    if "resub" in activity_key:
        return "resubmission"
    if "reminder" in activity_key:
        return "reminder"
    if "no_show" in activity_key or "noshow" in activity_key:
        return "no_show"
    if "resched" in activity_key:
        return "reschedule"
    if step == "unmapped" or step is None:
        return "deviation"
    return "mainline"


def _workflow_node_type(*, step: Optional[str], step_rank: Optional[int], total_steps: int) -> str:
    if step is None:
        return "deviation"
    if step_rank == 0:
        return "start"
    if step_rank == total_steps - 1:
        return "end"
    return "mainline"


def _workflow_edge_type(
    source_step: Optional[str],
    target_step: Optional[str],
    source_rank: Optional[int],
    target_rank: Optional[int],
    is_loop: bool,
    conformance_bucket: str,
) -> str:
    if is_loop:
        return "loop"
    if source_step is None or target_step is None:
        return "off_path"
    if conformance_bucket == "Conformant":
        return "expected"
    if source_rank is not None and target_rank is not None:
        if target_rank < source_rank:
            return "return"
        if target_rank - source_rank > 1:
            return "skip"
    return "off_path"


def _build_deviation_note(conf: Mapping[str, Any]) -> str:
    summary = conf.get("summary", {}) if isinstance(conf, Mapping) else {}
    alignment = summary.get("alignment_fitness", {}) if isinstance(summary, Mapping) else {}
    token = summary.get("token_fitness", {}) if isinstance(summary, Mapping) else {}
    alignment_fitness = _safe_float(alignment.get("log_fitness"))
    token_fitness = _safe_float(token.get("log_fitness"))
    if alignment_fitness is None and token_fitness is None:
        return "Conformance metrics available but insufficient for a deviation note."
    if alignment_fitness is not None and token_fitness is not None and abs(alignment_fitness - token_fitness) <= 0.05:
        return "Alignment and token replay are in close agreement."
    if alignment_fitness is not None and token_fitness is not None and alignment_fitness > token_fitness:
        return "Alignment is stricter than token replay on this model."
    return "Inspect trace-level deviations for additional detail."


def _summarize_metric_bundle(bundle: Any) -> str:
    if not isinstance(bundle, Mapping) or not bundle:
        return "N/A"
    if any(key in bundle for key in ("alignment_fitness", "token_fitness")):
        nested_parts: list[str] = []
        alignment_summary = _summarize_metric_bundle(bundle.get("alignment_fitness"))
        token_summary = _summarize_metric_bundle(bundle.get("token_fitness"))
        if alignment_summary != "N/A":
            nested_parts.append(f"Alignment {alignment_summary}")
        if token_summary != "N/A":
            nested_parts.append(f"Token {token_summary}")
        return " · ".join(nested_parts) if nested_parts else "N/A"

    log_fitness = _safe_float(bundle.get("log_fitness"))
    average_cost = _safe_float(bundle.get("average_cost"))
    fit_pct = _format_percent_value(bundle.get("perc_fit_traces"))
    if fit_pct is None:
        fit_pct = _format_percent_value(bundle.get("percentage_of_fitting_traces"))
    average_trace_fitness = _safe_float(bundle.get("average_trace_fitness"))

    parts: list[str] = []
    if log_fitness is not None:
        parts.append(f"log fit {_format_value(log_fitness)}")
    if fit_pct is not None:
        parts.append(f"{fit_pct} fitting traces")
    if average_trace_fitness is not None and (log_fitness is None or abs(average_trace_fitness - log_fitness) > 0.001):
        parts.append(f"avg trace {_format_value(average_trace_fitness)}")
    if average_cost is not None and average_cost > 0:
        parts.append(f"avg cost {_format_value(average_cost)}")
    if parts:
        return " · ".join(parts)

    sample_items = list(bundle.items())[:3]
    label_map = {
        "perc_fit_traces": "fitting traces",
        "percentage_of_fitting_traces": "fitting traces",
        "average_trace_fitness": "avg trace",
        "average_cost": "avg cost",
    }
    return " · ".join(
        f"{label_map.get(str(key), str(key).replace('_', ' '))} {_format_value(value)}"
        for key, value in sample_items
        if value is not None
    ) or "N/A"


def _format_value(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is not None:
        return format_decimal(numeric, decimals=3, thousands=True)
    return str(value)


def _format_percent_value(value: Any) -> str | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if 0.0 <= numeric <= 1.0:
        numeric *= 100.0
    return f"{format_decimal(numeric, decimals=3, thousands=True)}%"


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(round(float(value)))
    except Exception:
        return default


def _first_value(row: Any, column: str, *, fallback: Any) -> Any:
    try:
        if hasattr(row, "get"):
            value = row.get(column)
            if isinstance(value, pd.Series):
                value = value.iloc[0] if not value.empty else None
            if value is not None and not pd.isna(value):
                return value
    except Exception:
        pass
    return fallback


def _count_tokens(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set)):
        return len(value)
    try:
        return int(value)
    except Exception:
        return 1


def _trace_status(
    fitness: Optional[float],
    trace_fitness: Optional[float],
    cost: Optional[float],
    missing: Any,
    remaining: Any,
) -> str:
    if (fitness is not None and fitness < 1.0) or (trace_fitness is not None and trace_fitness < 1.0):
        return "Deviating"
    if _count_tokens(missing) or _count_tokens(remaining) or (cost is not None and cost > 0):
        return "Deviating"
    return "Conformant"


def _median_or_none(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return float(pd.Series(values).median())


def _percentile_or_none(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    return float(pd.Series(values).quantile(percentile / 100))


def _delay_bucket(values: list[float], overall_median: float) -> str:
    if not values:
        return "Low"
    median = float(pd.Series(values).median())
    p90 = float(pd.Series(values).quantile(0.9))
    if overall_median <= 0:
        return "Low"
    severity, _, _ = assess_bottleneck_severity(median * 86400, p90 * 86400, len(values), overall_median * 86400)
    if median > 0:
        tail_ratio = p90 / median
        if tail_ratio >= 3.5 and severity == "Low":
            severity = "High"
        elif tail_ratio >= 2.0 and severity == "Low":
            severity = "Moderate"
        elif tail_ratio >= 3.5 and severity == "Moderate":
            severity = "High"
    return severity


def _edge_conformance_bucket(
    source_step: str | None,
    target_step: str | None,
    source_rank: int | None,
    target_rank: int | None,
) -> str:
    if source_step is None or target_step is None:
        return "Model deviation"
    if source_rank is None or target_rank is None:
        return "Model deviation"
    if target_rank == source_rank + 1:
        return "Conformant"
    return "Log deviation"


def _coverage_group(coverage_pct: float) -> str:
    if coverage_pct >= 60:
        return "dominant"
    if coverage_pct <= 12:
        return "rare"
    return "mixed"


def _ensure_upload_size(raw_bytes: bytes) -> None:
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Upload too large ({len(raw_bytes)/(1024*1024):.1f} MB). Max allowed: {MAX_UPLOAD_BYTES/(1024*1024):.0f} MB."
        )
