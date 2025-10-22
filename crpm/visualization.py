"""Visualization helpers for process mining analytics.

This module provides functions for creating interactive charts using Plotly.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# Chart Configuration Constants
# ---------------------------------------------------------------------------

# Standardized chart heights for consistent UI
CHART_HEIGHT_STANDARD = 450  # Standard charts (distributions, scatter plots)
CHART_HEIGHT_LARGE = 550     # Large comparison charts (radar, heatmap)
CHART_HEIGHT_DYNAMIC_MIN = 350  # Minimum height for dynamic charts
CHART_HEIGHT_DYNAMIC_FACTOR = 40  # Pixels per row for dynamic charts


# ---------------------------------------------------------------------------
# Performance Charts
# ---------------------------------------------------------------------------


def create_bottleneck_chart(bottleneck_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create horizontal bar chart for bottleneck transitions.

    Args:
        bottleneck_df: DataFrame with transition bottleneck data
        top_n: Number of top bottlenecks to display

    Returns:
        Plotly Figure
    """
    if bottleneck_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No bottleneck data available", showarrow=False)
        return fig

    df = bottleneck_df.head(top_n).copy()

    # Convert to days for readability
    df["median_days"] = df["median_duration_s"] / 86400
    df["p90_days"] = df["p90_duration_s"] / 86400

    # Sort by median duration
    df = df.sort_values("median_days", ascending=True)

    fig = go.Figure()

    # Add median duration bars
    fig.add_trace(go.Bar(
        y=df["transition"],
        x=df["median_days"],
        name="Median Duration",
        orientation="h",
        marker=dict(color="orange"),
        text=df["median_days"].round(4),
        textposition="outside"
    ))

    # Add P90 duration bars
    fig.add_trace(go.Bar(
        y=df["transition"],
        x=df["p90_days"],
        name="P90 Duration",
        orientation="h",
        marker=dict(color="red", opacity=0.6),
        text=df["p90_days"].round(4),
        textposition="outside"
    ))

    fig.update_layout(
        title=f"Top {len(df)} Bottleneck Transitions",
        xaxis_title="Duration (days)",
        yaxis_title="Transition",
        barmode="group",
        height=max(CHART_HEIGHT_DYNAMIC_MIN, len(df) * CHART_HEIGHT_DYNAMIC_FACTOR),
        showlegend=True,
        hovermode="closest"
    )

    return fig


def create_activity_duration_chart(activity_stats: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Create box plot for activity durations.

    Args:
        activity_stats: DataFrame with activity statistics
        top_n: Number of activities to display

    Returns:
        Plotly Figure
    """
    if activity_stats.empty:
        fig = go.Figure()
        fig.add_annotation(text="No activity data available", showarrow=False)
        return fig

    df = activity_stats.head(top_n).copy()

    # Convert to hours
    for col in ["min_duration_s", "avg_duration_s", "median_duration_s", "max_duration_s", "p90_duration_s"]:
        if col in df.columns and df[col].notna().any():
            df[f"{col}_hours"] = df[col] / 3600

    # Create box plot using min, q25, median, q75, max
    fig = go.Figure()

    for idx, row in df.iterrows():
        activity = row["activity"]
        if pd.isna(row.get("median_duration_s")):
            continue

        # Approximate quartiles
        q1 = row.get("min_duration_s_hours", 0)
        median = row.get("median_duration_s_hours", 0)
        q3 = row.get("p90_duration_s_hours", median)
        max_val = row.get("max_duration_s_hours", q3)

        fig.add_trace(go.Box(
            y=[activity],
            x=[max_val],
            name=activity,
            boxmean=True,
            orientation="h",
            showlegend=False
        ))

    fig.update_layout(
        title=f"Activity Duration Distribution (Top {len(df)} by frequency)",
        xaxis_title="Duration (hours)",
        yaxis_title="Activity",
        height=max(CHART_HEIGHT_DYNAMIC_MIN, len(df) * CHART_HEIGHT_DYNAMIC_FACTOR),
        showlegend=False
    )

    return fig


def create_case_duration_histogram(case_durations: pd.DataFrame, bins: int = 50) -> go.Figure:
    """Create horizontal violin plot of case durations with distribution overlay.

    Args:
        case_durations: DataFrame with case duration data
        bins: Number of histogram bins (kept for backwards compatibility but not used)

    Returns:
        Plotly Figure
    """
    # Check for days column first, fallback to hours, then seconds
    duration_col = None
    unit_label = ""

    if "duration_days" in case_durations.columns:
        duration_col = "duration_days"
        unit_label = "days"
    elif "duration_hours" in case_durations.columns:
        duration_col = "duration_hours"
        unit_label = "hours"
    elif "duration_s" in case_durations.columns:
        # Convert seconds to days on the fly
        case_durations = case_durations.copy()
        case_durations["duration_days"] = case_durations["duration_s"] / 86400
        duration_col = "duration_days"
        unit_label = "days"

    if duration_col is None or case_durations.empty:
        fig = go.Figure()
        fig.add_annotation(text="No case duration data available", showarrow=False)
        return fig

    # Calculate statistics
    median_val = case_durations[duration_col].median()
    mean_val = case_durations[duration_col].mean()
    p90_val = case_durations[duration_col].quantile(0.9)

    # Create horizontal violin plot
    fig = go.Figure()

    fig.add_trace(go.Violin(
        x=case_durations[duration_col],
        y0="Distribution",
        name="Case Duration",
        orientation="h",
        side="positive",
        line_color="steelblue",
        fillcolor="lightblue",
        opacity=0.6,
        meanline_visible=True,
        box_visible=True,
        points=False
    ))

    # Add median, mean, and P90 lines
    fig.add_vline(x=median_val, line_dash="dash", line_color="green", line_width=2,
                  annotation_text=f"Median: {median_val:.4f} {unit_label}",
                  annotation_position="top")
    fig.add_vline(x=mean_val, line_dash="dot", line_color="blue", line_width=2,
                  annotation_text=f"Mean: {mean_val:.4f} {unit_label}",
                  annotation_position="top")
    fig.add_vline(x=p90_val, line_dash="dash", line_color="orange", line_width=2,
                  annotation_text=f"P90: {p90_val:.4f} {unit_label}",
                  annotation_position="top")

    # Add interpretation text box
    outlier_pct = ((case_durations[duration_col] > p90_val).sum() / len(case_durations)) * 100
    p90_to_median_ratio = p90_val / median_val if median_val > 0 else 0

    interpretation = ""
    if p90_to_median_ratio >= 2.5:
        interpretation = f"⚠️ {outlier_pct:.1f}% of cases exceed P90 - investigate significant delays"
    elif p90_to_median_ratio >= 1.5:
        interpretation = f"ℹ️ {outlier_pct:.1f}% of cases exceed P90 - some outliers present"
    else:
        interpretation = f"✅ Minimal outliers - consistent process duration"

    fig.add_annotation(
        text=interpretation,
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=12, color="black"),
        bgcolor="lightyellow",
        bordercolor="orange",
        borderwidth=2,
        borderpad=8
    )

    fig.update_layout(
        title="Case Duration Distribution",
        xaxis_title=f"Duration ({unit_label})",
        yaxis_title="",
        showlegend=False,
        height=CHART_HEIGHT_STANDARD,
        yaxis=dict(showticklabels=False)
    )

    return fig


# ---------------------------------------------------------------------------
# Variant Charts
# ---------------------------------------------------------------------------


def create_variant_frequency_chart(variant_stats: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Create bar chart of variant frequencies.

    Args:
        variant_stats: DataFrame with variant statistics
        top_n: Number of variants to display

    Returns:
        Plotly Figure
    """
    if variant_stats.empty:
        fig = go.Figure()
        fig.add_annotation(text="No variant data available", showarrow=False)
        return fig

    df = variant_stats.head(top_n).copy()

    # Truncate long variant names for display
    df["variant_short"] = df["variant_str"].apply(
        lambda x: (x[:40] + "...") if len(str(x)) > 40 else x
    )

    fig = go.Figure()

    # Use variant names as x-axis for better readability
    fig.add_trace(go.Bar(
        x=df["variant_short"],
        y=df["percentage"],
        text=df["percentage"].round(2).astype(str) + "%",
        textposition="outside",
        marker=dict(
            color=df["percentage"],
            colorscale="Blues",
            showscale=False,
            line=dict(color="#1f77b4", width=1.5)
        ),
        hovertemplate="<b>%{x}</b><br>Frequency: %{y:.2f}%<br>Count: " +
                     df["frequency"].astype(str) + "<extra></extra>"
    ))

    # Auto-scale y-axis to show meaningful range
    max_pct = df["percentage"].max()
    y_max = max(max_pct * 1.15, 5)  # At least 5% range, or 115% of max

    fig.update_layout(
        title=f"Top {len(df)} Process Variant Frequencies",
        xaxis_title="Process Variant",
        yaxis_title="Frequency (%)",
        height=CHART_HEIGHT_STANDARD,
        showlegend=False,
        yaxis=dict(range=[0, y_max]),
        xaxis=dict(tickangle=-45, automargin=True)
    )

    return fig


def create_variant_coverage_chart(variant_coverage: pd.DataFrame) -> go.Figure:
    """Create cumulative coverage curve for variants.

    Args:
        variant_coverage: DataFrame with cumulative coverage data

    Returns:
        Plotly Figure
    """
    if variant_coverage.empty or "cumulative_percentage" not in variant_coverage.columns:
        fig = go.Figure()
        fig.add_annotation(text="No coverage data available", showarrow=False)
        return fig

    fig = go.Figure()

    # Add area under curve
    fig.add_trace(go.Scatter(
        x=variant_coverage.index + 1,
        y=variant_coverage["cumulative_percentage"],
        mode="lines+markers",
        marker=dict(size=8, color="#1f77b4", line=dict(width=2, color="white")),
        line=dict(width=3, color="#1f77b4"),
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.2)",
        hovertemplate="<b>%{x} variants</b><br>Coverage: %{y:.2f}%<extra></extra>"
    ))

    # Add reference lines for coverage milestones
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.5,
                  annotation_text="50%", annotation_position="right")
    fig.add_hline(y=80, line_dash="dash", line_color="orange", line_width=2,
                  annotation_text="80% Coverage", annotation_position="right")
    fig.add_hline(y=90, line_dash="dot", line_color="gray", opacity=0.5,
                  annotation_text="90%", annotation_position="right")

    # Auto-scale x-axis for better visibility
    max_variants = len(variant_coverage)

    fig.update_layout(
        title="Cumulative Variant Coverage",
        xaxis_title="Number of Variants",
        yaxis_title="Cumulative Coverage (%)",
        height=CHART_HEIGHT_STANDARD,
        showlegend=False,
        yaxis=dict(range=[0, 105]),
        xaxis=dict(range=[0, max(max_variants * 1.1, 10)])
    )

    return fig


# ---------------------------------------------------------------------------
# Model Comparison Charts
# ---------------------------------------------------------------------------


def create_model_comparison_radar(comparison_df: pd.DataFrame, metrics: List[str]) -> go.Figure:
    """Create radar chart comparing models across multiple metrics.

    Args:
        comparison_df: DataFrame with model comparison data (models as rows)
        metrics: List of metric column names to include

    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No comparison data available", showarrow=False)
        return fig

    fig = go.Figure()

    for idx, row in comparison_df.iterrows():
        model_name = row.get("model_name", f"Model {idx}")

        # Get metric values (normalized 0-1)
        values = []
        for metric in metrics:
            val = row.get(metric, 0)
            if pd.isna(val):
                val = 0
            values.append(float(val))

        # Close the radar chart
        values_closed = values + [values[0]]
        metrics_closed = metrics + [metrics[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=metrics_closed,
            name=model_name,
            fill="toself"
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Model Comparison (Normalized Metrics)",
        height=CHART_HEIGHT_LARGE,
        showlegend=True
    )

    return fig


def create_model_comparison_heatmap(comparison_df: pd.DataFrame, metrics: List[str]) -> go.Figure:
    """Create heatmap comparing models across metrics.

    Args:
        comparison_df: DataFrame with model comparison data
        metrics: List of metric column names

    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No comparison data available", showarrow=False)
        return fig

    # Extract model names and metric values
    model_names = comparison_df.get("model_name", comparison_df.index).tolist()

    # Build matrix
    matrix = []
    for metric in metrics:
        row = comparison_df[metric].tolist() if metric in comparison_df.columns else [0] * len(model_names)
        matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=model_names,
        y=metrics,
        colorscale="RdYlGn",
        text=[[f"{val:.3f}" if not pd.isna(val) else "N/A" for val in row] for row in matrix],
        texttemplate="%{text}",
        textfont={"size": 10},
        colorbar=dict(title="Value")
    ))

    fig.update_layout(
        title="Model Comparison Heatmap",
        xaxis_title="Model",
        yaxis_title="Metric",
        height=max(CHART_HEIGHT_DYNAMIC_MIN, len(metrics) * 50),
        width=max(600, len(model_names) * 100)
    )

    return fig


def create_fitness_precision_scatter(comparison_df: pd.DataFrame) -> go.Figure:
    """Create scatter plot of fitness vs precision (Pareto frontier).

    Args:
        comparison_df: DataFrame with fitness and precision columns

    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No comparison data available", showarrow=False)
        return fig

    # Determine fitness and precision column names
    fitness_col = None
    precision_col = None

    for col in comparison_df.columns:
        if "fitness" in col.lower() and fitness_col is None:
            fitness_col = col
        if "precision" in col.lower() and precision_col is None:
            precision_col = col

    if not fitness_col or not precision_col:
        fig = go.Figure()
        fig.add_annotation(text="Fitness and Precision columns not found", showarrow=False)
        return fig

    model_names = comparison_df.get("model_name", comparison_df.index).tolist()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=comparison_df[fitness_col],
        y=comparison_df[precision_col],
        mode="markers+text",
        marker=dict(size=12, color="steelblue"),
        text=model_names,
        textposition="top center",
        hovertext=[f"{name}<br>Fitness: {f:.3f}<br>Precision: {p:.3f}"
                   for name, f, p in zip(model_names, comparison_df[fitness_col], comparison_df[precision_col])],
        hoverinfo="text"
    ))

    # Add quadrant shading and reference lines
    fitness_threshold = 0.85
    precision_threshold = 0.75

    # Ideal zone (top-right) - green
    fig.add_shape(type="rect",
                  x0=fitness_threshold, y0=precision_threshold, x1=1.0, y1=1.0,
                  fillcolor="lightgreen", opacity=0.15,
                  line=dict(width=0))

    # Overfitting zone (bottom-right) - yellow
    fig.add_shape(type="rect",
                  x0=fitness_threshold, y0=0, x1=1.0, y1=precision_threshold,
                  fillcolor="yellow", opacity=0.08,
                  line=dict(width=0))

    # Underfitting zone (top-left) - yellow
    fig.add_shape(type="rect",
                  x0=0, y0=precision_threshold, x1=fitness_threshold, y1=1.0,
                  fillcolor="yellow", opacity=0.08,
                  line=dict(width=0))

    # Poor quality zone (bottom-left) - red
    fig.add_shape(type="rect",
                  x0=0, y0=0, x1=fitness_threshold, y1=precision_threshold,
                  fillcolor="red", opacity=0.08,
                  line=dict(width=0))

    # Add reference lines
    fig.add_hline(y=precision_threshold, line_dash="dash", line_color="gray",
                  annotation_text="Precision threshold (0.75)",
                  annotation_position="right")
    fig.add_vline(x=fitness_threshold, line_dash="dash", line_color="gray",
                  annotation_text="Fitness threshold (0.85)",
                  annotation_position="top")

    # Add quadrant labels
    fig.add_annotation(x=0.925, y=0.875, text="🟢 Ideal Zone",
                       showarrow=False, font=dict(size=10, color="green"))
    fig.add_annotation(x=0.925, y=0.35, text="🟡 Overfitting",
                       showarrow=False, font=dict(size=9, color="orange"))
    fig.add_annotation(x=0.40, y=0.875, text="🟡 Underfitting",
                       showarrow=False, font=dict(size=9, color="orange"))
    fig.add_annotation(x=0.40, y=0.35, text="🔴 Poor Quality",
                       showarrow=False, font=dict(size=9, color="red"))

    fig.update_layout(
        title="Fitness vs Precision (Pareto Frontier)",
        xaxis_title="Fitness",
        yaxis_title="Precision",
        height=CHART_HEIGHT_LARGE,
        width=600,
        showlegend=False,
        xaxis=dict(range=[0, 1.05]),
        yaxis=dict(range=[0, 1.05])
    )

    return fig


__all__ = [
    "create_bottleneck_chart",
    "create_activity_duration_chart",
    "create_case_duration_histogram",
    "create_variant_frequency_chart",
    "create_variant_coverage_chart",
    "create_model_comparison_radar",
    "create_model_comparison_heatmap",
    "create_fitness_precision_scatter",
]
