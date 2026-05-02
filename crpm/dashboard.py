"""Descriptive-statistics dashboard for loaded event logs.

Provides category filters (activity, resource, group), KPI cards,
frequency tables, and time-intelligence charts powered by Plotly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pm4py.objects.log.obj import EventLog


# ───────────────────────────────────────────────────────────────────
# 1. Log → flat DataFrame
# ───────────────────────────────────────────────────────────────────


def log_to_dataframe(log: EventLog) -> pd.DataFrame:
    """Flatten an EventLog into a DataFrame with one row per event.

    Standard columns produced:
        case_id, activity, timestamp, resource, org_group
    Extra event-level attributes are included as additional columns.
    """
    rows: list[dict] = []
    for trace in log:
        case_id = trace.attributes.get("concept:name", str(id(trace)))
        for event in trace:
            row: dict = {
                "case_id": case_id,
                "activity": event.get("concept:name", "Unknown"),
                "timestamp": event.get("time:timestamp"),
                "resource": event.get("org:resource", event.get("Resource", None)),
                "org_group": event.get("org:group", event.get("Group", None)),
            }
            # Pull in any extra attributes
            for k, v in event.items():
                if k not in {
                    "concept:name",
                    "time:timestamp",
                    "org:resource",
                    "Resource",
                    "org:group",
                    "Group",
                }:
                    row[k] = v
            rows.append(row)

    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df


# ───────────────────────────────────────────────────────────────────
# 2. Categorical filters
# ───────────────────────────────────────────────────────────────────


def get_categorical_columns(df: pd.DataFrame) -> List[str]:
    """Return column names suitable for categorical filtering."""
    always = []
    for col in ("activity", "resource", "org_group"):
        if col in df.columns and df[col].notna().any():
            always.append(col)
    # Include any extra string/object columns with reasonable cardinality
    for col in df.columns:
        if col in ("case_id", "timestamp") or col in always:
            continue
        if df[col].dtype == "object" and 1 < df[col].nunique() <= 200:
            always.append(col)
    return always


def apply_filters(
    df: pd.DataFrame,
    filters: Dict[str, List[str]],
    date_range: Optional[Tuple[datetime, datetime]] = None,
) -> pd.DataFrame:
    """Apply categorical and date-range filters and return the subset."""
    out = df.copy()
    for col, values in filters.items():
        if values and col in out.columns:
            out = out[out[col].isin(values)]
    if date_range and "timestamp" in out.columns:
        start, end = date_range
        if start:
            out = out[out["timestamp"] >= pd.Timestamp(start, tz="UTC")]
        if end:
            out = out[out["timestamp"] <= pd.Timestamp(end, tz="UTC")]
    return out


# ───────────────────────────────────────────────────────────────────
# 3. KPI computation
# ───────────────────────────────────────────────────────────────────


def compute_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute key process indicators from the (optionally filtered) DF.

    Returns a dict with scalar values suited for metric cards.
    """
    n_events = len(df)
    n_cases = df["case_id"].nunique()
    n_activities = df["activity"].nunique()

    resources = df["resource"].nunique() if "resource" in df.columns and df["resource"].notna().any() else None

    # Case durations
    case_dur: Optional[pd.Series] = None
    if "timestamp" in df.columns and df["timestamp"].notna().any():
        grp = df.groupby("case_id")["timestamp"]
        case_dur = (grp.max() - grp.min()).dt.total_seconds()

    median_dur = float(case_dur.median()) if case_dur is not None and len(case_dur) else None
    mean_dur = float(case_dur.mean()) if case_dur is not None and len(case_dur) else None
    p90_dur = float(case_dur.quantile(0.9)) if case_dur is not None and len(case_dur) else None

    # Events per case
    events_per_case = df.groupby("case_id").size()
    avg_events = float(events_per_case.mean()) if len(events_per_case) else None

    # Variants
    variants = df.groupby("case_id")["activity"].apply(tuple)
    n_variants = variants.nunique()

    # Time span
    ts_min = df["timestamp"].min() if "timestamp" in df.columns and df["timestamp"].notna().any() else None
    ts_max = df["timestamp"].max() if "timestamp" in df.columns and df["timestamp"].notna().any() else None

    return {
        "n_events": n_events,
        "n_cases": n_cases,
        "n_activities": n_activities,
        "n_resources": resources,
        "n_variants": n_variants,
        "avg_events_per_case": avg_events,
        "median_duration_s": median_dur,
        "mean_duration_s": mean_dur,
        "p90_duration_s": p90_dur,
        "ts_min": ts_min,
        "ts_max": ts_max,
    }


def _fmt_duration(seconds: Optional[float]) -> str:
    """Format seconds into a human-readable string."""
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


# ───────────────────────────────────────────────────────────────────
# 4. Frequency / distribution tables
# ───────────────────────────────────────────────────────────────────


def activity_frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    """Activity frequency and relative frequency."""
    counts = df["activity"].value_counts().reset_index()
    counts.columns = ["Activity", "Count"]
    counts["Frequency %"] = (counts["Count"] / counts["Count"].sum() * 100).round(2)
    return counts


def resource_frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    """Resource frequency table (if resource column exists)."""
    if "resource" not in df.columns or df["resource"].isna().all():
        return pd.DataFrame(columns=["Resource", "Count", "Frequency %"])
    counts = df["resource"].dropna().value_counts().reset_index()
    counts.columns = ["Resource", "Count"]
    counts["Frequency %"] = (counts["Count"] / counts["Count"].sum() * 100).round(2)
    return counts


def group_frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    """Org group frequency table."""
    if "org_group" not in df.columns or df["org_group"].isna().all():
        return pd.DataFrame(columns=["Group", "Count", "Frequency %"])
    counts = df["org_group"].dropna().value_counts().reset_index()
    counts.columns = ["Group", "Count"]
    counts["Frequency %"] = (counts["Count"] / counts["Count"].sum() * 100).round(2)
    return counts


# ───────────────────────────────────────────────────────────────────
# 5. Time-intelligence charts (Plotly)
# ───────────────────────────────────────────────────────────────────

_BUCKET_MAP = {"Day": "D", "Week": "W", "Month": "MS"}


def events_over_time(
    df: pd.DataFrame,
    bucket: str = "Week",
) -> go.Figure:
    """Line chart of event volume over time.

    Args:
        df: Flat event DataFrame with ``timestamp`` column.
        bucket: Aggregation bucket — ``Day``, ``Week``, or ``Month``.
    """
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        return _empty_fig("No timestamp data available")

    freq = _BUCKET_MAP.get(bucket, "W")
    ts = df.set_index("timestamp").resample(freq).size().reset_index(name="Events")
    ts.columns = ["Period", "Events"]

    fig = px.area(
        ts,
        x="Period",
        y="Events",
        title=f"Event Volume by {bucket}",
        template="plotly_dark",
    )
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="",
        yaxis_title="Events",
    )
    return fig


def cases_started_over_time(
    df: pd.DataFrame,
    bucket: str = "Week",
) -> go.Figure:
    """Line chart of new cases started per time bucket."""
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        return _empty_fig("No timestamp data available")

    freq = _BUCKET_MAP.get(bucket, "W")
    first_events = df.sort_values("timestamp").groupby("case_id").first().reset_index()
    ts = first_events.set_index("timestamp").resample(freq).size().reset_index(name="Cases Started")
    ts.columns = ["Period", "Cases Started"]

    fig = px.bar(
        ts,
        x="Period",
        y="Cases Started",
        title=f"Cases Started by {bucket}",
        template="plotly_dark",
    )
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="",
        yaxis_title="Cases",
    )
    return fig


def case_duration_over_time(
    df: pd.DataFrame,
    bucket: str = "Week",
) -> go.Figure:
    """Median case duration over time (by case start bucket)."""
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        return _empty_fig("No timestamp data available")

    freq = _BUCKET_MAP.get(bucket, "W")
    grp = df.groupby("case_id")["timestamp"]
    case_info = pd.DataFrame(
        {
            "start": grp.min(),
            "duration_h": (grp.max() - grp.min()).dt.total_seconds() / 3600,
        }
    )
    ts = case_info.set_index("start").resample(freq)["duration_h"].median().reset_index()
    ts.columns = ["Period", "Median Duration (h)"]

    fig = px.line(
        ts,
        x="Period",
        y="Median Duration (h)",
        title=f"Median Case Duration by {bucket}",
        template="plotly_dark",
        markers=True,
    )
    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="",
        yaxis_title="Hours",
    )
    return fig


def activity_by_time_heatmap(
    df: pd.DataFrame,
    top_n: int = 15,
) -> go.Figure:
    """Activity × day-of-week heatmap (event counts)."""
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        return _empty_fig("No timestamp data available")

    dfw = df.copy()
    dfw["dow"] = dfw["timestamp"].dt.day_name()
    top_acts = dfw["activity"].value_counts().head(top_n).index
    dfw = dfw[dfw["activity"].isin(top_acts)]
    if dfw.empty:
        return _empty_fig("Not enough activity data for heatmap")
    pivot = dfw.groupby(["activity", "dow"]).size().unstack(fill_value=0)
    # Re-order days
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])

    fig = px.imshow(
        pivot,
        aspect="auto",
        title=f"Top {top_n} Activities × Day of Week",
        template="plotly_dark",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        height=max(300, top_n * 28),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="",
        yaxis_title="",
    )
    return fig


def period_comparison(
    df: pd.DataFrame,
    days: int = 30,
) -> Optional[Dict[str, Any]]:
    """Compare last *days* vs previous *days*.

    Returns a dict with current / previous counts and deltas.  Returns None
    if the log doesn't span at least ``2 * days``.
    """
    if "timestamp" not in df.columns or df["timestamp"].isna().all():
        return None
    ts_max = df["timestamp"].max()
    ts_min = df["timestamp"].min()
    span = (ts_max - ts_min).days
    if span < 2 * days:
        return None

    boundary = ts_max - pd.Timedelta(days=days)
    prev_boundary = boundary - pd.Timedelta(days=days)

    current = df[df["timestamp"] >= boundary]
    previous = df[(df["timestamp"] >= prev_boundary) & (df["timestamp"] < boundary)]

    def _delta_pct(cur: int, prev: int) -> Optional[float]:
        if prev == 0:
            return None
        return (cur - prev) / prev * 100

    cur_events = len(current)
    prev_events = len(previous)
    cur_cases = current["case_id"].nunique()
    prev_cases = previous["case_id"].nunique()

    return {
        "days": days,
        "current_events": cur_events,
        "previous_events": prev_events,
        "delta_events_pct": _delta_pct(cur_events, prev_events),
        "current_cases": cur_cases,
        "previous_cases": prev_cases,
        "delta_cases_pct": _delta_pct(cur_cases, prev_cases),
    }


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────


def _empty_fig(msg: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=16))
    fig.update_layout(
        height=250,
        template="plotly_dark",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
