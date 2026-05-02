"""Operational flow analytics for screening queues, throughput, and aging."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd
from pm4py.objects.log.obj import EventLog, Trace

from crpm.analytics import compute_transition_statistics
from crpm.screening import (
    PeriodDefinition,
    STEP_LABELS,
    STEP_ORDER,
    compute_screening_kpis,
    get_trace_anchor_timestamp,
    split_log_by_periods,
)

STEP_TIMESTAMP_COLUMNS = {step: f"{step}_ts" for step in STEP_ORDER}


def smooth_series(arr: np.ndarray, window: int = 13) -> np.ndarray:
    """Smooth a 1D series while preserving the edge values."""
    if window <= 1 or arr.size == 0:
        return arr.astype(float, copy=True)

    window = min(window, arr.size)
    if window <= 1:
        return arr.astype(float, copy=True)

    kernel = np.ones(window, dtype=float) / float(window)
    smoothed = np.convolve(arr.astype(float), kernel, mode="same")
    edge = window // 2
    if edge > 0:
        smoothed[:edge] = arr[:edge]
        smoothed[-edge:] = arr[-edge:]
    return smoothed


def build_case_state_frame(log: EventLog, step_map: dict[str, Optional[str]]) -> pd.DataFrame:
    """Derive one row per case with the first timestamp for each canonical step."""
    rows: list[dict[str, Any]] = []

    for index, trace in enumerate(log):
        case_id = _get_case_id(trace, index)
        step_timestamps = {step: _first_timestamp_for_activity(trace, step_map.get(step)) for step in STEP_ORDER}
        anchor_ts = step_timestamps.get("invitation") or get_trace_anchor_timestamp(trace, None)
        observed = [ts for ts in step_timestamps.values() if isinstance(ts, datetime)]
        highest_stage = next((step for step in reversed(STEP_ORDER) if step_timestamps.get(step) is not None), None)
        rows.append(
            {
                "case_id": case_id,
                "anchor_ts": anchor_ts,
                "last_ts": max(observed) if observed else anchor_ts,
                "highest_stage": STEP_LABELS.get(highest_stage, "No mapped steps") if highest_stage else "No mapped steps",
                "has_colonoscopy": step_timestamps.get("colonoscopy") is not None,
                **{STEP_TIMESTAMP_COLUMNS[step]: step_timestamps[step] for step in STEP_ORDER},
            }
        )

    columns = [
        "case_id",
        "anchor_ts",
        "last_ts",
        "highest_stage",
        "has_colonoscopy",
        *STEP_TIMESTAMP_COLUMNS.values(),
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(rows)
    return frame.sort_values("anchor_ts", na_position="last").reset_index(drop=True)


def aggregate_weekly_step_counts(
    case_state_frame: pd.DataFrame,
    *,
    smooth_window: Optional[int] = None,
) -> pd.DataFrame:
    """Aggregate first step completions into sequential weekly buckets."""
    if case_state_frame.empty:
        return pd.DataFrame(index=pd.Index([], name="seq_week"))

    origin = _resolve_origin_timestamp(case_state_frame)
    if origin is None:
        return pd.DataFrame(index=pd.Index([], name="seq_week"))

    weekly_counts: dict[str, pd.Series] = {}
    max_week = 0

    for step in STEP_ORDER:
        ts_col = STEP_TIMESTAMP_COLUMNS[step]
        if ts_col not in case_state_frame.columns:
            continue
        valid = pd.to_datetime(case_state_frame[ts_col].dropna())
        if valid.empty:
            continue

        week_numbers = ((valid - pd.Timestamp(origin)).dt.days // 7).astype(int)
        series = week_numbers.value_counts().sort_index()
        weekly_counts[STEP_LABELS[step]] = series
        max_week = max(max_week, int(series.index.max()))

    week_index = pd.Index(range(max_week + 1), name="seq_week")
    frame = pd.DataFrame(index=week_index)
    for label, series in weekly_counts.items():
        frame[label] = series.reindex(week_index, fill_value=0).astype(float)

    if smooth_window and smooth_window > 1 and not frame.empty:
        for label in frame.columns:
            frame[label] = smooth_series(frame[label].to_numpy(), window=smooth_window)

    return frame


def compute_queue_stock_levels(weekly_counts: pd.DataFrame) -> pd.DataFrame:
    """Approximate operational queue sizes as cumulative inflow minus outflow."""
    if weekly_counts.empty:
        return pd.DataFrame(index=weekly_counts.index)

    index = weekly_counts.index

    def _series(label: str) -> pd.Series:
        if label in weekly_counts.columns:
            return weekly_counts[label].astype(float)
        return pd.Series(0.0, index=index)

    invitation = _series(STEP_LABELS["invitation"]).cumsum()
    fit_mail = _series(STEP_LABELS["fit_mail"]).cumsum()
    fit_return = _series(STEP_LABELS["fit_return"]).cumsum()
    lab_result = _series(STEP_LABELS["lab_result"]).cumsum()
    pcc_observation = _series(STEP_LABELS["pcc_observation"]).cumsum()
    colonoscopy = _series(STEP_LABELS["colonoscopy"]).cumsum()

    stock = pd.DataFrame(index=index)
    stock["Invitation backlog"] = (invitation - fit_mail).clip(lower=0)
    stock["Pending FIT return"] = (fit_mail - fit_return).clip(lower=0)
    stock["Awaiting lab result"] = (fit_return - lab_result).clip(lower=0)
    stock["Awaiting PCC observation"] = (lab_result - pcc_observation).clip(lower=0)
    stock["Awaiting colonoscopy"] = (pcc_observation - colonoscopy).clip(lower=0)
    return stock


def compute_stage_aging_metrics(log: EventLog, step_map: dict[str, Optional[str]]) -> pd.DataFrame:
    """Compute median and P90 delays for the canonical pathway hand-offs."""
    transitions: list[tuple[str, str]] = []
    for first_step, second_step in zip(STEP_ORDER, STEP_ORDER[1:]):
        first_activity = step_map.get(first_step)
        second_activity = step_map.get(second_step)
        if first_activity and second_activity:
            transitions.append((first_activity, second_activity))

    if not transitions:
        return pd.DataFrame()

    transition_stats = compute_transition_statistics(log, model_transitions=transitions, min_occurrences=1)
    if transition_stats.empty:
        return transition_stats

    aging_df = transition_stats.copy()
    aging_df["median_days"] = aging_df["median_duration_s"] / 86400
    aging_df["p90_days"] = aging_df["p90_duration_s"] / 86400
    return (
        aging_df[["transition", "activity", "next_activity", "frequency", "median_days", "p90_days"]]
        .sort_values("median_days", ascending=False)
        .reset_index(drop=True)
    )


def compute_operational_kpis(
    log: EventLog,
    step_map: dict[str, Optional[str]],
    stock_levels: pd.DataFrame,
) -> dict[str, Any]:
    """Combine screening KPIs with current queue levels."""
    kpis = compute_screening_kpis(log, step_map)
    last_stock = stock_levels.iloc[-1] if not stock_levels.empty else pd.Series(dtype=float)
    kpis["current_invitation_backlog"] = float(last_stock.get("Invitation backlog", 0.0))
    kpis["current_pending_fit_return"] = float(last_stock.get("Pending FIT return", 0.0))
    kpis["current_awaiting_pcc"] = float(last_stock.get("Awaiting PCC observation", 0.0))
    kpis["current_awaiting_colonoscopy"] = float(last_stock.get("Awaiting colonoscopy", 0.0))
    return kpis


def build_operational_view(
    log: EventLog,
    step_map: dict[str, Optional[str]],
    *,
    smooth_window: Optional[int] = None,
) -> dict[str, Any]:
    """Build the full operational-flow payload for one log."""
    case_state_frame = build_case_state_frame(log, step_map)
    weekly_counts = aggregate_weekly_step_counts(case_state_frame, smooth_window=smooth_window)
    stock_levels = compute_queue_stock_levels(weekly_counts)
    aging_metrics = compute_stage_aging_metrics(log, step_map)
    kpis = compute_operational_kpis(log, step_map, stock_levels)
    return {
        "case_state_frame": case_state_frame,
        "weekly_counts": weekly_counts,
        "stock_levels": stock_levels,
        "aging_metrics": aging_metrics,
        "kpis": kpis,
    }


def split_operational_periods(
    log: EventLog,
    *,
    anchor_activity: Optional[str],
    followup_days: Optional[int] = None,
    pre_period: Optional[PeriodDefinition] = None,
    post_period: Optional[PeriodDefinition] = None,
) -> dict[str, EventLog]:
    """Split the log into PRE and POST incident cohorts for operational comparisons."""
    if pre_period is None or post_period is None:
        pre_period, post_period = derive_operational_periods(log, anchor_activity=anchor_activity)

    return split_log_by_periods(
        log,
        anchor_activity=anchor_activity,
        period_a=pre_period,
        period_b=post_period,
        followup_days=followup_days,
    )


def derive_operational_periods(
    log: EventLog,
    *,
    anchor_activity: Optional[str],
) -> tuple[PeriodDefinition, PeriodDefinition]:
    """Derive default PRE/POST comparison windows from the log span."""
    anchor_dates = []
    for trace in log:
        anchor_ts = get_trace_anchor_timestamp(trace, anchor_activity)
        if anchor_ts is None:
            anchor_ts = get_trace_anchor_timestamp(trace, None)
        if anchor_ts is None:
            continue
        anchor_dates.append(anchor_ts.date())

    if not anchor_dates:
        today = date.today()
        return (
            PeriodDefinition("PRE", today, today),
            PeriodDefinition("POST", today + timedelta(days=1), today + timedelta(days=1)),
        )

    start_date = min(anchor_dates)
    end_date = max(anchor_dates)
    if start_date >= end_date:
        return (
            PeriodDefinition("PRE", start_date, start_date),
            PeriodDefinition("POST", start_date + timedelta(days=1), start_date + timedelta(days=1)),
        )

    span_days = (end_date - start_date).days
    midpoint_date = start_date + timedelta(days=span_days // 2)
    post_start = midpoint_date + timedelta(days=1)
    if post_start > end_date:
        post_start = end_date

    return (
        PeriodDefinition("PRE", start_date, midpoint_date),
        PeriodDefinition("POST", post_start, end_date),
    )


def _first_timestamp_for_activity(trace: Trace, activity_name: Optional[str]) -> Optional[datetime]:
    if not activity_name:
        return None

    for event in trace:
        if event.get("concept:name") != activity_name:
            continue
        timestamp = event.get("time:timestamp")
        if isinstance(timestamp, datetime):
            return timestamp
    return None


def _get_case_id(trace: Trace, index: int) -> str:
    attributes = getattr(trace, "attributes", {}) or {}
    return str(attributes.get("concept:name") or f"case-{index + 1}")


def _resolve_origin_timestamp(case_state_frame: pd.DataFrame) -> Optional[datetime]:
    if "anchor_ts" in case_state_frame.columns:
        anchors = pd.to_datetime(case_state_frame["anchor_ts"].dropna())
        if not anchors.empty:
            return anchors.min().to_pydatetime()

    for step in STEP_ORDER:
        ts_col = STEP_TIMESTAMP_COLUMNS[step]
        if ts_col not in case_state_frame.columns:
            continue
        values = pd.to_datetime(case_state_frame[ts_col].dropna())
        if not values.empty:
            return values.min().to_pydatetime()
    return None


__all__ = [
    "aggregate_weekly_step_counts",
    "build_case_state_frame",
    "build_operational_view",
    "compute_operational_kpis",
    "compute_queue_stock_levels",
    "compute_stage_aging_metrics",
    "derive_operational_periods",
    "smooth_series",
    "split_operational_periods",
]
