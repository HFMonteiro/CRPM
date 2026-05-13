"""Visualization helpers for process mining analytics.

This module provides functions for creating interactive charts using Plotly.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape
import json
import math
import logging
from typing import List, Optional, Any, Literal, Mapping
from textwrap import wrap
import pandas as pd
import plotly.graph_objects as go

from crpm.formatting import format_decimal

LOGGER = logging.getLogger(__name__)


CHART_THEME = {
    "paper_bgcolor": "#fbf9fd",
    "plot_bgcolor": "#f4f0f8",
    "font_color": "#1f2c25",
    "title_color": "#1f2c25",
    "grid_major": "#d8d4e2",
    "grid_minor": "#e8e3ef",
    "axis_line": "#a59bb6",
    "annotation_bg": "rgba(255, 255, 255, 0.92)",
    "annotation_border": "#afa4c0",
    "hover_bg": "#25352d",
    "hover_border": "#9f93b3",
    "hover_font": "#ffffff",
    "muted_text": "#58665d",
    "surface_border": "#d5cfdf",
    "interval": "#7c8fa8",
    "median": "#405c51",
    "secondary": "#8e7aa8",
    "accent": "#567368",
    "warning": "#b07a3d",
    "danger": "#9d5f6b",
}

OPERATIONAL_COLORS = {
    "Invitation": "#2c7fb8",
    "FIT mail": "#41ab5d",
    "FIT return": "#7b3294",
    "Lab result": "#d7301f",
    "PCC observation": "#1d4ed8",
    "Colonoscopy": "#e67e22",
    "Invitation backlog": "#9ecae1",
    "Pending FIT return": "#74c476",
    "Awaiting lab result": "#c994c7",
    "Awaiting PCC observation": "#f16913",
    "Awaiting colonoscopy": "#fb6a4a",
}


def _apply_chart_theme(fig: go.Figure) -> go.Figure:
    """Apply a consistent high-contrast theme to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font={"color": CHART_THEME["font_color"], "size": 13},
        title_font={"color": CHART_THEME["title_color"], "size": 18},
        legend={
            "font": {"color": CHART_THEME["font_color"], "size": 13},
            "bgcolor": "rgba(251, 249, 253, 0.99)",
            "bordercolor": CHART_THEME["surface_border"],
            "borderwidth": 1.4,
            "itemsizing": "constant",
            "itemwidth": 42,
        },
        annotationdefaults={
            "font": {"color": CHART_THEME["font_color"], "size": 12},
            "bgcolor": CHART_THEME["annotation_bg"],
            "bordercolor": CHART_THEME["annotation_border"],
            "borderwidth": 1,
            "borderpad": 4,
        },
        hoverlabel={
            "bgcolor": CHART_THEME["hover_bg"],
            "bordercolor": CHART_THEME["hover_border"],
            "font": {"color": CHART_THEME["hover_font"], "size": 12},
        },
        margin=dict(l=80, r=44, t=78, b=62),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=CHART_THEME["grid_major"],
        zeroline=False,
        linecolor=CHART_THEME["axis_line"],
        tickfont=dict(size=12, color=CHART_THEME["font_color"]),
        title_font=dict(size=13, color=CHART_THEME["title_color"]),
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        linecolor=CHART_THEME["axis_line"],
        tickfont=dict(size=12, color=CHART_THEME["font_color"]),
        title_font=dict(size=13, color=CHART_THEME["title_color"]),
    )
    return fig


def _add_empty_annotation(fig: go.Figure, message: str) -> go.Figure:
    fig.add_annotation(
        text=message,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        font={"size": 14, "color": CHART_THEME["font_color"]},
        bgcolor=CHART_THEME["annotation_bg"],
        bordercolor=CHART_THEME["annotation_border"],
        borderwidth=1,
        borderpad=8,
    )
    return _apply_chart_theme(fig)


def _empty_figure(message: str) -> go.Figure:
    return _add_empty_annotation(go.Figure(), message)


# ---------------------------------------------------------------------------
# Chart Configuration Constants
# ---------------------------------------------------------------------------

# Standardized chart heights for consistent UI
CHART_HEIGHT_STANDARD = 450  # Standard charts (distributions, scatter plots)
CHART_HEIGHT_LARGE = 550  # Large comparison charts (radar, heatmap)
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
        return _empty_figure("No bottleneck data available")

    df = bottleneck_df.head(top_n).copy()
    df["transition_label"] = df["transition"].map(_humanize_transition_label)

    # Convert to days for readability
    df["median_days"] = df["median_duration_s"] / 86400
    df["p90_days"] = df["p90_duration_s"] / 86400

    # Sort by median duration
    df = df.sort_values("median_days", ascending=True)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=df["transition_label"],
            x=df["median_days"],
            name="Median delay",
            orientation="h",
            marker=dict(color=CHART_THEME["warning"]),
            hovertemplate=("<b>%{y}</b><br>Median delay: %{x:.1f} days<br>P90 delay: %{customdata[0]:.1f} days<extra></extra>"),
            customdata=df[["p90_days"]].to_numpy(),
        )
    )

    p90_df = df[df["p90_days"] > df["median_days"] + 0.05].copy()
    if not p90_df.empty:
        fig.add_trace(
            go.Scatter(
                y=p90_df["transition_label"],
                x=p90_df["p90_days"],
                mode="markers",
                name="P90 marker",
                marker=dict(color=CHART_THEME["danger"], size=11, symbol="line-ns-open"),
                hovertemplate="<b>%{y}</b><br>P90 delay: %{x:.1f} days<extra></extra>",
            )
        )

    flat_df = df[df["p90_days"] <= df["median_days"] + 0.05]
    if not flat_df.empty:
        fig.add_annotation(
            text="Flat interval: median and P90 are equal for one or more transitions.",
            xref="paper",
            yref="paper",
            x=1,
            y=1.12,
            xanchor="right",
            showarrow=False,
            font=dict(size=11, color=CHART_THEME["font_color"]),
            bgcolor=CHART_THEME["annotation_bg"],
            bordercolor=CHART_THEME["annotation_border"],
            borderwidth=1,
            borderpad=5,
        )

    fig.update_layout(
        title=f"Top {len(df)} Bottleneck Transitions",
        xaxis_title="Duration (days)",
        yaxis_title="Transition",
        height=max(CHART_HEIGHT_DYNAMIC_MIN, len(df) * CHART_HEIGHT_DYNAMIC_FACTOR),
        showlegend=True,
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=210, r=58, t=78, b=55),
    )

    _apply_chart_theme(fig)

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
        return _empty_figure("No activity data available")

    df = activity_stats.head(top_n).copy()
    df = df[df["median_duration_s"].notna()].copy()

    if df.empty:
        return _empty_figure("No activity duration data available")

    for col in ["min_duration_s", "avg_duration_s", "median_duration_s", "max_duration_s", "p90_duration_s"]:
        if col in df.columns:
            df[f"{col}_hours"] = df[col] / 3600
    df["activity_label"] = df["activity"].map(_humanize_chart_label)

    df = df.sort_values("median_duration_s_hours", ascending=True)

    fig = go.Figure()

    # Draw a thick interval line from minimum to P90 to represent the typical spread.
    for _, row in df.iterrows():
        min_hours = row.get("min_duration_s_hours", row.get("median_duration_s_hours", 0))
        median_hours = row.get("median_duration_s_hours", 0)
        p90_hours = row.get("p90_duration_s_hours", row.get("max_duration_s_hours", median_hours))

        fig.add_trace(
            go.Scatter(
                x=[min_hours, p90_hours],
                y=[row["activity_label"], row["activity_label"]],
                mode="lines",
                line=dict(color=CHART_THEME["interval"], width=11),
                opacity=0.85,
                hovertemplate=(
                    f"<b>{row['activity_label']}</b><br>"
                    f"Min: {min_hours:.1f} h<br>"
                    f"Median: {median_hours:.1f} h<br>"
                    f"P90: {p90_hours:.1f} h<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df["median_duration_s_hours"],
            y=df["activity_label"],
            mode="markers",
            name="Median",
            marker=dict(color=CHART_THEME["median"], size=12, symbol="diamond"),
            hovertemplate="<b>%{y}</b><br>Median: %{x:.1f} h<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.get("avg_duration_s_hours", df["median_duration_s_hours"]),
            y=df["activity_label"],
            mode="markers",
            name="Average",
            marker=dict(color=CHART_THEME["warning"], size=9, symbol="circle"),
            hovertemplate="<b>%{y}</b><br>Average: %{x:.1f} h<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Activity Duration Summary (Top {len(df)} by frequency)",
        xaxis_title="Duration (hours)",
        yaxis_title="Activity",
        height=max(420, len(df) * 52),
        showlegend=True,
        hovermode="closest",
        margin=dict(l=120, r=70, t=78, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid_major"], zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color=CHART_THEME["font_color"]))

    _apply_chart_theme(fig)

    return fig


def _humanize_chart_label(value: Any) -> str:
    from crpm.screening import humanize_activity_label

    label = str(value or "").strip()
    return humanize_activity_label(label) or label


def _humanize_transition_label(value: Any) -> str:
    from crpm.screening import humanize_activity_label

    label = str(value or "").strip()
    if "->" in label:
        left, right = [part.strip() for part in label.split("->", 1)]
        return f"{humanize_activity_label(left) or left} → {humanize_activity_label(right) or right}"
    if "→" in label:
        left, right = [part.strip() for part in label.split("→", 1)]
        return f"{humanize_activity_label(left) or left} → {humanize_activity_label(right) or right}"
    return humanize_activity_label(label) or label


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
        return _empty_figure("No case duration data available")

    # Calculate statistics
    median_val = case_durations[duration_col].median()
    mean_val = case_durations[duration_col].mean()
    p90_val = case_durations[duration_col].quantile(0.9)

    # Create horizontal violin plot
    fig = go.Figure()

    fig.add_trace(
        go.Violin(
            x=case_durations[duration_col],
            y0="Distribution",
            name="Case Duration",
            orientation="h",
            side="positive",
            line_color=CHART_THEME["secondary"],
            fillcolor="rgba(142, 122, 168, 0.24)",
            opacity=0.6,
            meanline_visible=True,
            box_visible=True,
            points=False,
        )
    )

    # Add median, mean, and P90 lines
    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color=CHART_THEME["accent"],
        line_width=2,
        annotation_text=f"Median: {format_decimal(median_val)} {unit_label}",
        annotation_position="top",
    )
    fig.add_vline(
        x=mean_val,
        line_dash="dot",
        line_color=CHART_THEME["secondary"],
        line_width=2,
        annotation_text=f"Mean: {format_decimal(mean_val)} {unit_label}",
        annotation_position="top",
    )
    fig.add_vline(
        x=p90_val,
        line_dash="dash",
        line_color=CHART_THEME["warning"],
        line_width=2,
        annotation_text=f"P90: {format_decimal(p90_val)} {unit_label}",
        annotation_position="top",
    )

    # Add interpretation text box
    outlier_pct = ((case_durations[duration_col] > p90_val).sum() / len(case_durations)) * 100
    p90_to_median_ratio = p90_val / median_val if median_val > 0 else 0

    interpretation = ""
    if p90_to_median_ratio >= 2.5:
        interpretation = f"High outlier rate: {outlier_pct:.1f}% of cases exceed the P90 threshold."
    elif p90_to_median_ratio >= 1.5:
        interpretation = f"Moderate outlier rate: {outlier_pct:.1f}% of cases exceed the P90 threshold."
    else:
        interpretation = "Stable duration profile: minimal outlier behaviour detected."

    fig.add_annotation(
        text=interpretation,
        xref="paper",
        yref="paper",
        x=0.5,
        y=1.15,
        showarrow=False,
        font=dict(size=12, color=CHART_THEME["font_color"]),
        bgcolor=CHART_THEME["annotation_bg"],
        bordercolor=CHART_THEME["warning"],
        borderwidth=2,
        borderpad=8,
    )

    fig.update_layout(
        title="Case Duration Distribution",
        xaxis_title=f"Duration ({unit_label})",
        yaxis_title="",
        showlegend=False,
        height=CHART_HEIGHT_STANDARD,
        yaxis=dict(showticklabels=False),
    )

    _apply_chart_theme(fig)

    return fig


def create_operational_flow_chart(weekly_counts: pd.DataFrame, title: str = "Operational flow") -> go.Figure:
    """Create a multi-line weekly flow chart for the mapped screening stages."""
    if weekly_counts.empty:
        return _empty_figure("No weekly operational flow data available")

    fig = go.Figure()
    for column in weekly_counts.columns:
        fig.add_trace(
            go.Scatter(
                x=weekly_counts.index,
                y=weekly_counts[column],
                mode="lines",
                name=column,
                line=dict(color=OPERATIONAL_COLORS.get(column, CHART_THEME["secondary"]), width=3.5),
                hovertemplate=f"<b>{column}</b><br>Week %{{x}}<br>Cases: %{{y:.1f}}<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Sequential week from cohort start",
        yaxis_title="Cases per week",
        height=430,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=70, r=30, t=70, b=55),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid_major"])
    fig.update_yaxes(showgrid=True, gridcolor=CHART_THEME["grid_minor"], zeroline=False)
    _apply_chart_theme(fig)
    return fig


def create_queue_stock_chart(stock_levels: pd.DataFrame, title: str = "Queue stock") -> go.Figure:
    """Create a stacked-area queue chart from cumulative stock approximations."""
    if stock_levels.empty:
        return _empty_figure("No queue stock data available")

    fig = go.Figure()
    for column in stock_levels.columns:
        fig.add_trace(
            go.Scatter(
                x=stock_levels.index,
                y=stock_levels[column],
                mode="lines",
                name=column,
                stackgroup="queue",
                line=dict(width=1.8, color=OPERATIONAL_COLORS.get(column, CHART_THEME["secondary"])),
                hovertemplate=f"<b>{column}</b><br>Week %{{x}}<br>Cases: %{{y:.1f}}<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Sequential week from cohort start",
        yaxis_title="Estimated cases in queue",
        height=430,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=70, r=30, t=70, b=55),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid_major"])
    fig.update_yaxes(showgrid=True, gridcolor=CHART_THEME["grid_minor"], zeroline=False)
    _apply_chart_theme(fig)
    return fig


def create_stage_aging_chart(aging_df: pd.DataFrame, title: str = "Stage aging") -> go.Figure:
    """Create a median-to-P90 horizontal interval chart for pathway hand-offs."""
    if aging_df.empty:
        return _empty_figure("No stage aging data available")

    df = aging_df.sort_values("median_days", ascending=True).copy()
    df["severity"] = pd.cut(
        df["p90_days"],
        bins=[-float("inf"), 14, 45, 90, float("inf")],
        labels=["Very fast", "Fast-moderate", "Moderate-slow", "Very slow"],
    ).astype(str)
    severity_colors = {
        "Very fast": CHART_THEME["accent"],
        "Fast-moderate": "#7ca15f",
        "Moderate-slow": CHART_THEME["warning"],
        "Very slow": CHART_THEME["danger"],
    }
    fig = go.Figure()

    for _, row in df.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["median_days"], row["p90_days"]],
                y=[row["transition"], row["transition"]],
                mode="lines",
                line=dict(color=severity_colors.get(row["severity"], CHART_THEME["interval"]), width=12),
                hovertemplate=(
                    f"<b>{row['transition']}</b><br>"
                    f"Median: {row['median_days']:.1f} days<br>"
                    f"P90: {row['p90_days']:.1f} days<br>"
                    f"Frequency: {int(row['frequency'])}<br>"
                    f"Delay bucket: {row['severity']}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df["p90_days"],
            y=df["transition"],
            mode="markers",
            name="P90",
            marker=dict(color=CHART_THEME["danger"], size=9, symbol="circle"),
            hovertemplate="<b>%{y}</b><br>P90: %{x:.1f} days<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["median_days"],
            y=df["transition"],
            mode="markers",
            name="Median",
            marker=dict(color=CHART_THEME["median"], size=12, symbol="diamond"),
            hovertemplate="<b>%{y}</b><br>Median: %{x:.1f} days<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Delay (days)",
        yaxis_title="Transition",
        height=max(360, len(df) * 52),
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=200, r=80, t=78, b=55),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_THEME["grid_major"], zeroline=False)
    fig.update_yaxes(showgrid=False, automargin=True)
    _apply_chart_theme(fig)
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
        return _empty_figure("No variant data available")

    df = variant_stats.head(top_n).copy()

    # Truncate long variant names for display
    df["variant_short"] = df["variant_str"].apply(lambda x: (x[:40] + "...") if len(str(x)) > 40 else x)

    fig = go.Figure()

    # Use variant names as x-axis for better readability
    fig.add_trace(
        go.Bar(
            x=df["variant_short"],
            y=df["percentage"],
            marker=dict(
                color=df["percentage"],
                colorscale=[[0, "#e8e0f0"], [0.5, "#8e7aa8"], [1, "#365348"]],
                showscale=False,
                line=dict(color=CHART_THEME["surface_border"], width=1.5),
            ),
            customdata=df["frequency"],
            hovertemplate="<b>%{x}</b><br>Frequency: %{y:.2f}%<br>Cases: %{customdata:,}<extra></extra>",
        )
    )

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
        xaxis=dict(tickangle=-35, automargin=True),
        margin=dict(l=70, r=35, t=76, b=105),
    )

    _apply_chart_theme(fig)

    return fig


def create_variant_coverage_chart(variant_coverage: pd.DataFrame) -> go.Figure:
    """Create cumulative coverage curve for variants.

    Args:
        variant_coverage: DataFrame with cumulative coverage data

    Returns:
        Plotly Figure
    """
    if variant_coverage.empty or "cumulative_percentage" not in variant_coverage.columns:
        return _empty_figure("No coverage data available")

    fig = go.Figure()

    # Add area under curve
    fig.add_trace(
        go.Scatter(
            x=variant_coverage.index + 1,
            y=variant_coverage["cumulative_percentage"],
            mode="lines+markers",
            marker=dict(size=8, color=CHART_THEME["secondary"], line=dict(width=2, color="white")),
            line=dict(width=3, color=CHART_THEME["secondary"]),
            fill="tozeroy",
            fillcolor="rgba(142, 122, 168, 0.18)",
            hovertemplate="<b>%{x} variants</b><br>Coverage: %{y:.2f}%<extra></extra>",
        )
    )

    # Add reference lines for coverage milestones
    fig.add_hline(
        y=50, line_dash="dot", line_color=CHART_THEME["muted_text"], opacity=0.5, annotation_text="50%", annotation_position="right"
    )
    fig.add_hline(
        y=80, line_dash="dash", line_color=CHART_THEME["warning"], line_width=2, annotation_text="80% Coverage", annotation_position="right"
    )
    fig.add_hline(
        y=90, line_dash="dot", line_color=CHART_THEME["muted_text"], opacity=0.5, annotation_text="90%", annotation_position="right"
    )

    # Auto-scale x-axis for better visibility
    max_variants = len(variant_coverage)

    fig.update_layout(
        title="Cumulative Variant Coverage",
        xaxis_title="Number of Variants",
        yaxis_title="Cumulative Coverage (%)",
        height=CHART_HEIGHT_STANDARD,
        showlegend=False,
        yaxis=dict(range=[0, 105]),
        xaxis=dict(range=[0, max(max_variants * 1.1, 10)]),
    )

    _apply_chart_theme(fig)

    return fig


def create_variant_coverage_comparison(
    train_coverage: pd.DataFrame,
    test_coverage: pd.DataFrame,
    highlight: Optional[int] = None,
) -> go.Figure:
    """Compare cumulative coverage between train and test logs using train ordering."""
    if train_coverage.empty or "cumulative_percentage" not in train_coverage.columns:
        return _empty_figure("No training coverage data available")

    train_df = train_coverage.reset_index(drop=True).copy()
    x_train = list(range(1, len(train_df) + 1))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_train,
            y=train_df["cumulative_percentage"],
            mode="lines+markers",
            name="Train coverage",
            line=dict(color=CHART_THEME["secondary"], width=3),
            marker=dict(size=8, color=CHART_THEME["secondary"], line=dict(width=2, color="white")),
            hovertemplate="Train variant %{x}<br>Cumulative: %{y:.2f}%<extra></extra>",
        )
    )

    if not test_coverage.empty and "cumulative_percentage" in test_coverage.columns:
        test_df = test_coverage.reset_index(drop=True).copy()
        x_test = list(range(1, len(test_df) + 1))
        fig.add_trace(
            go.Scatter(
                x=x_test,
                y=test_df["cumulative_percentage"],
                mode="lines+markers",
                name="Test coverage (train order)",
                line=dict(color=CHART_THEME["warning"], width=3),
                marker=dict(size=7, color=CHART_THEME["warning"], line=dict(width=1, color="white")),
                hovertemplate="Test variant %{x}<br>Cumulative: %{y:.2f}%<extra></extra>",
            )
        )
    else:
        test_df = pd.DataFrame()

    max_len = max(len(train_df), len(test_df))
    if highlight and highlight > 0:
        highlight = min(highlight, max_len if max_len > 0 else highlight)
        fig.add_vrect(
            x0=0.5,
            x1=highlight + 0.5,
            fillcolor="rgba(142, 122, 168, 0.12)",
            line_width=0,
            layer="below",
        )

    for y, label, dash, color, opacity in [
        (50, "50%", "dot", CHART_THEME["muted_text"], 0.4),
        (80, "80%", "dash", CHART_THEME["warning"], 0.8),
        (90, "90%", "dot", CHART_THEME["muted_text"], 0.4),
    ]:
        fig.add_hline(
            y=y,
            line_dash=dash,
            line_color=color,
            opacity=opacity,
            annotation_text=label,
            annotation_position="right",
        )

    fig.update_layout(
        title="Cumulative Coverage (Train vs Test)",
        xaxis_title="Variant rank (train order)",
        yaxis_title="Cumulative Coverage (%)",
        height=CHART_HEIGHT_STANDARD,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        hovermode="x unified",
        yaxis=dict(range=[0, 105]),
        xaxis=dict(range=[1, max_len + 0.5 if max_len else 2], tickmode="linear"),
    )

    _apply_chart_theme(fig)

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
        return _empty_figure("No comparison data available")

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

        fig.add_trace(go.Scatterpolar(r=values_closed, theta=metrics_closed, name=model_name, fill="toself"))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Model Comparison (Normalized Metrics)",
        height=CHART_HEIGHT_LARGE,
        showlegend=True,
    )

    _apply_chart_theme(fig)

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
        return _empty_figure("No comparison data available")

    # Extract model names and metric values
    model_names = comparison_df.get("model_name", comparison_df.index).tolist()

    # Build matrix
    matrix = []
    for metric in metrics:
        row = comparison_df[metric].tolist() if metric in comparison_df.columns else [0] * len(model_names)
        matrix.append(row)

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=model_names,
            y=metrics,
            colorscale="RdYlGn",
            text=[[f"{val:.3f}" if not pd.isna(val) else "N/A" for val in row] for row in matrix],
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar=dict(title="Value"),
        )
    )

    fig.update_layout(
        title="Model Comparison Heatmap",
        xaxis_title="Model",
        yaxis_title="Metric",
        height=max(CHART_HEIGHT_DYNAMIC_MIN, len(metrics) * 50),
    )

    _apply_chart_theme(fig)

    return fig


def create_fitness_precision_scatter(comparison_df: pd.DataFrame) -> go.Figure:
    """Create scatter plot of fitness vs precision (Pareto frontier).

    Args:
        comparison_df: DataFrame with fitness and precision columns

    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        return _empty_figure("No comparison data available")

    fitness_col = "alignment_fitness" if "alignment_fitness" in comparison_df.columns else None
    precision_col = "precision" if "precision" in comparison_df.columns else None

    if fitness_col is None:
        for col in comparison_df.columns:
            if "fitness" in col.lower():
                fitness_col = col
                break
    if precision_col is None:
        for col in comparison_df.columns:
            if "precision" in col.lower():
                precision_col = col
                break

    if not fitness_col or not precision_col:
        return _empty_figure("Fitness and precision columns not found")

    chart_df = comparison_df.copy()
    model_names = chart_df.get("model_name", chart_df.index).tolist()
    chart_df["_balanced_score"] = chart_df[fitness_col].fillna(0) + chart_df[precision_col].fillna(0)
    highlight_indices = list(chart_df["_balanced_score"].nlargest(min(2, len(chart_df))).index)
    highlight_df = chart_df.loc[highlight_indices].drop_duplicates(subset=["model_name"] if "model_name" in chart_df.columns else None)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df[fitness_col],
            y=chart_df[precision_col],
            mode="markers",
            marker=dict(size=12, color=CHART_THEME["secondary"], line=dict(color="#ffffff", width=1.2)),
            customdata=model_names,
            hovertemplate="<b>%{customdata}</b><br>Fitness: %{x:.3f}<br>Precision: %{y:.3f}<extra></extra>",
            name="Candidates",
            showlegend=False,
        )
    )

    if not highlight_df.empty:
        fig.add_trace(
            go.Scatter(
                x=highlight_df[fitness_col],
                y=highlight_df[precision_col],
                mode="markers",
                marker=dict(size=16, color=CHART_THEME["accent"], line=dict(color="#ffffff", width=1.8), symbol="diamond"),
                customdata=highlight_df.get("model_name", highlight_df.index).tolist(),
                hovertemplate="<b>%{customdata}</b><br>Fitness: %{x:.3f}<br>Precision: %{y:.3f}<extra></extra>",
                name="Recommended focus",
                showlegend=False,
            )
        )

    # Add quadrant shading and reference lines
    fitness_threshold = 0.85
    precision_threshold = 0.75

    # Ideal zone (top-right) - green
    fig.add_shape(
        type="rect",
        x0=fitness_threshold,
        y0=precision_threshold,
        x1=1.0,
        y1=1.0,
        fillcolor="rgba(86, 115, 104, 0.18)",
        opacity=0.18,
        line=dict(width=0),
    )

    # Overfitting zone (bottom-right) - yellow
    fig.add_shape(
        type="rect",
        x0=fitness_threshold,
        y0=0,
        x1=1.0,
        y1=precision_threshold,
        fillcolor="rgba(176, 122, 61, 0.10)",
        opacity=0.10,
        line=dict(width=0),
    )

    # Underfitting zone (top-left) - yellow
    fig.add_shape(
        type="rect",
        x0=0,
        y0=precision_threshold,
        x1=fitness_threshold,
        y1=1.0,
        fillcolor="rgba(176, 122, 61, 0.10)",
        opacity=0.10,
        line=dict(width=0),
    )

    # Poor quality zone (bottom-left) - red
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=fitness_threshold,
        y1=precision_threshold,
        fillcolor="rgba(157, 95, 107, 0.12)",
        opacity=0.12,
        line=dict(width=0),
    )

    # Add reference lines
    fig.add_hline(
        y=precision_threshold,
        line_dash="dash",
        line_color=CHART_THEME["muted_text"],
        annotation_text="Precision threshold (0.75)",
        annotation_position="right",
    )
    fig.add_vline(
        x=fitness_threshold,
        line_dash="dash",
        line_color=CHART_THEME["muted_text"],
        annotation_text="Fitness threshold (0.85)",
        annotation_position="top",
    )

    # Add quadrant labels
    fig.add_annotation(x=0.925, y=0.875, text="Ideal zone", showarrow=False, font=dict(size=10, color=CHART_THEME["accent"]))
    fig.add_annotation(x=0.925, y=0.35, text="Overfitting zone", showarrow=False, font=dict(size=9, color=CHART_THEME["warning"]))
    fig.add_annotation(x=0.40, y=0.875, text="Underfitting zone", showarrow=False, font=dict(size=9, color=CHART_THEME["warning"]))
    fig.add_annotation(x=0.40, y=0.35, text="Low quality zone", showarrow=False, font=dict(size=9, color=CHART_THEME["danger"]))

    fig.update_layout(
        title="Fitness vs Precision (Pareto Frontier)",
        xaxis_title="Fitness",
        yaxis_title="Precision",
        height=CHART_HEIGHT_LARGE,
        showlegend=False,
        xaxis=dict(range=[0, 1.05]),
        yaxis=dict(range=[0, 1.05]),
        margin=dict(l=72, r=42, t=74, b=62),
    )

    _apply_chart_theme(fig)

    return fig


_WORKFLOW_SEVERITY_THEME = {
    "Low": {"fill": "#e9f6ee", "stroke": "#28c67a", "ink": "#20312a", "accent": "#baf0d1"},
    "Moderate": {"fill": "#f7f1df", "stroke": "#d2a43e", "ink": "#3a311a", "accent": "#f1d48a"},
    "High": {"fill": "#fbe8d9", "stroke": "#e07b39", "ink": "#4a2d14", "accent": "#f4b27f"},
    "Critical": {"fill": "#f9dfe3", "stroke": "#cf5b69", "ink": "#4c2330", "accent": "#efa6b1"},
}

_WORKFLOW_CONFORMANCE_THEME = {
    "Conformant": {"fill": "#dff1db", "stroke": "#7ab889", "accent": "#bfe3be", "ink": "#20312a"},
    "Log deviation": {"fill": "#f0db77", "stroke": "#d0a23f", "accent": "#f3e29b", "ink": "#3a311a"},
    "Model deviation": {"fill": "#e39ac3", "stroke": "#c56f9f", "accent": "#edb0d1", "ink": "#4c2330"},
}

_WORKFLOW_MIX_THEME = {
    "sync": {"label": "Sync", "short": "S", "fill": "#cae9cf", "ink": "#265d39", "stroke": "#8dbd98"},
    "log": {"label": "Log", "short": "L", "fill": "#f3e2a7", "ink": "#7b560a", "stroke": "#d4b25e"},
    "model": {"label": "Model", "short": "M", "fill": "#d9deef", "ink": "#4c5f8e", "stroke": "#9cadcf"},
}

_WORKFLOW_TIMING_THEME = [
    ("Very fast", "Below the cohort median band", "#4d7f56"),
    ("Fast-moderate", "Near the cohort median band", "#7ca15f"),
    ("Moderate-slow", "Above the cohort median band", "#d2a43e"),
    ("Very slow", "Well above the cohort median band", "#cf5b69"),
]


def _workflow_max_edge_fanout(normalized_edges: pd.DataFrame) -> int:
    fanout: dict[str, int] = defaultdict(int)
    for _, row in normalized_edges.iterrows():
        source = str(row.get("source", "")).strip()
        if source:
            fanout[source] += 1
    return max(fanout.values(), default=0)


def _workflow_rect_bounds(x: float, y: float, width: float, height: float, *, pad: float = 0.0) -> dict[str, float]:
    return {
        "min_x": float(x) - pad,
        "min_y": float(y) - pad,
        "max_x": float(x) + float(width) + pad,
        "max_y": float(y) + float(height) + pad,
    }


def _workflow_boxes_overlap(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    padding: float = 0.0,
) -> bool:
    return not (
        float(left["max_x"]) + padding <= float(right["min_x"])
        or float(right["max_x"]) + padding <= float(left["min_x"])
        or float(left["max_y"]) + padding <= float(right["min_y"])
        or float(right["max_y"]) + padding <= float(left["min_y"])
    )


def _workflow_nodes_overlap(node_items: list[dict[str, Any]], *, padding: float = 0.0) -> bool:
    node_boxes = [_workflow_node_collision_bounds(node, pad=padding) for node in node_items]
    for index, left_box in enumerate(node_boxes):
        for right_box in node_boxes[index + 1 :]:
            if _workflow_boxes_overlap(left_box, right_box):
                return True
    return False


def _workflow_apply_label_clearance(
    edge_items: list[dict[str, Any]],
    node_items: list[dict[str, Any]],
    *,
    clearance: float,
) -> None:
    blocked_boxes = [_workflow_node_collision_bounds(node, pad=2.0) for node in node_items]
    accepted_boxes: list[dict[str, float]] = []
    candidates = [edge for edge in edge_items if edge.get("show_label")]
    candidates.sort(
        key=lambda edge: (
            0 if edge.get("selected") else 1,
            0 if str(edge.get("branch_role", "mainline")) == "mainline" else 1,
            -_safe_int(edge.get("frequency", 0)),
            str(edge.get("id", "")),
        )
    )
    for edge in candidates:
        label_width = float(edge.get("label_width", 0.0) or 0.0)
        label_height = float(edge.get("label_height", 0.0) or 0.0)
        if label_width <= 0.0 or label_height <= 0.0:
            edge["show_label"] = False
            edge["label_box"] = None
            continue
        label_box = _workflow_rect_bounds(
            float(edge["label_x"]) - (label_width / 2.0),
            float(edge["label_y"]) - (label_height / 2.0),
            label_width,
            label_height,
        )
        blocked = any(_workflow_boxes_overlap(label_box, box, padding=clearance) for box in blocked_boxes)
        blocked = blocked or any(_workflow_boxes_overlap(label_box, box, padding=clearance) for box in accepted_boxes)
        if blocked:
            edge["show_label"] = False
            edge["label_box"] = None
            continue
        edge["label_box"] = label_box
        accepted_boxes.append(label_box)


def _workflow_node_collision_bounds(node: Mapping[str, Any], *, pad: float = 0.0) -> dict[str, float]:
    box = _workflow_rect_bounds(node["x"], node["y"], node["width"], node["height"])
    text_box = node.get("text_box")
    if isinstance(text_box, Mapping):
        box["min_x"] = min(float(box["min_x"]), float(text_box.get("min_x", box["min_x"])))
        box["min_y"] = min(float(box["min_y"]), float(text_box.get("min_y", box["min_y"])))
        box["max_x"] = max(float(box["max_x"]), float(text_box.get("max_x", box["max_x"])))
        box["max_y"] = max(float(box["max_y"]), float(text_box.get("max_y", box["max_y"])))
    if pad:
        box["min_x"] -= pad
        box["min_y"] -= pad
        box["max_x"] += pad
        box["max_y"] += pad
    return box


def _workflow_node_mix_stats(row: Mapping[str, Any]) -> dict[str, Any]:
    sync_cases = _safe_int(row.get("sync_cases", 0))
    log_move_cases = _safe_int(row.get("log_move_cases", 0))
    model_move_cases = _safe_int(row.get("model_move_cases", 0))
    total_cases = _safe_int(row.get("conformance_mix_total_cases", 0))
    if total_cases <= 0:
        fallback_cases = max(_safe_int(row.get("cases", 0)), _safe_int(row.get("occurrences", 0)))
        bucket = str(row.get("conformance_bucket", "Conformant"))
        if bucket == "Model deviation":
            model_move_cases = fallback_cases
        elif bucket == "Log deviation":
            log_move_cases = fallback_cases
        else:
            sync_cases = fallback_cases
        total_cases = sync_cases + log_move_cases + model_move_cases
    if total_cases <= 0:
        total_cases = sync_cases + log_move_cases + model_move_cases
    if total_cases <= 0:
        total_cases = 1
    sync_pct = _safe_float(row.get("sync_pct"))
    log_pct = _safe_float(row.get("log_move_pct"))
    model_pct = _safe_float(row.get("model_move_pct"))
    if sync_pct is None:
        sync_pct = round(sync_cases / total_cases * 100.0, 1)
    if log_pct is None:
        log_pct = round(log_move_cases / total_cases * 100.0, 1)
    if model_pct is None:
        model_pct = round(model_move_cases / total_cases * 100.0, 1)
    segments = []
    for key, cases_value, pct_value in (
        ("sync", sync_cases, sync_pct),
        ("log", log_move_cases, log_pct),
        ("model", model_move_cases, model_pct),
    ):
        theme = _WORKFLOW_MIX_THEME[key]
        segments.append(
            {
                "key": key,
                "label": theme["label"],
                "short": theme["short"],
                "cases": cases_value,
                "pct": max(0.0, float(pct_value or 0.0)),
                "fill": theme["fill"],
                "ink": theme["ink"],
                "stroke": theme["stroke"],
            }
        )
    dominant = max(segments, key=lambda item: (item["pct"], item["cases"], item["label"]))
    return {
        "sync_cases": sync_cases,
        "log_move_cases": log_move_cases,
        "model_move_cases": model_move_cases,
        "sync_pct": float(sync_pct),
        "log_move_pct": float(log_pct),
        "model_move_pct": float(model_pct),
        "total_cases": total_cases,
        "segments": segments,
        "dominant_key": str(dominant["key"]),
        "dominant_label": str(dominant["label"]),
        "dominant_pct": float(dominant["pct"]),
    }


def _workflow_prepare_explorer_node_content(
    row: pd.Series,
    *,
    branch_role: str,
    detail_level: str,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    is_mainline = branch_role == "mainline"
    width_floor = float(profile["mainline_width_min"] if is_mainline else profile["branch_width_min"])
    width_cap = float(profile["mainline_width_max"] if is_mainline else profile["branch_width_max"])
    width_pref = float(profile["mainline_width"] if is_mainline else profile["branch_width"])
    min_height = float(profile["mainline_min_height"] if is_mainline else profile["branch_min_height"])
    title_font_size = float(profile["title_font_size"])
    timing_font_size = float(profile.get("timing_font_size", profile["meta_font_size"]))
    meta_font_size = float(profile["meta_font_size"])
    footer_font_size = float(profile.get("footer_font_size", meta_font_size))
    chip_height = float(profile["chip_height"])
    text_pad_left = float(profile["text_pad_left"])
    text_pad_right = float(profile["text_pad_right"])
    text_top_pad = float(profile["text_top_pad"])
    text_bottom_pad = float(profile["text_bottom_pad"])
    chip_gap = float(profile["chip_gap"])
    title_line_gap = float(profile["title_line_gap"])
    timing_line_gap = float(profile.get("timing_line_gap", profile["meta_line_gap"]))
    meta_line_gap = float(profile["meta_line_gap"])
    footer_line_gap = float(profile.get("footer_line_gap", profile["meta_line_gap"]))
    section_gap = float(profile.get("section_gap", 6.0))
    ribbon_gap = float(profile.get("ribbon_gap", 5.0))
    ribbon_height = float(profile.get("ribbon_height", 4.0))
    show_ribbon = True
    inline_detail = detail_level != "research"

    title = _workflow_display_name(row)
    cases = _safe_int(row.get("cases", 0))
    median_days = _safe_float(row.get("median_next_delay_days"))
    p90_days = _safe_float(row.get("p90_next_delay_days"))
    occurrences = _safe_int(row.get("occurrences", 0))
    path_pct = _safe_float(row.get("coverage_pct"))
    activity_pct = _safe_float(row.get("activity_pct"))
    mix_stats = _workflow_node_mix_stats(row)

    detail_parts: list[str] = []
    detail_parts.append(f"{cases:,} cases" if cases else "0 cases")
    if median_days is not None:
        detail_parts.append(f"median {median_days:.1f} d")
    else:
        detail_parts.append("delay n/a")
    if path_pct is not None:
        detail_parts.append(f"path {path_pct:.1f}%")
    if activity_pct is not None:
        detail_parts.append(f"activity {activity_pct:.1f}%")
    if detail_level == "research" and occurrences and occurrences != cases:
        detail_parts.append(f"{occurrences:,} events")
    if detail_level == "research" and p90_days is not None:
        detail_parts.append(f"p90 {p90_days:.1f} d")
    timing_source_lines = [" · ".join(detail_parts)]

    footer_source_lines: list[str] = []

    title_max_lines = 1
    timing_max_lines = 1
    footer_max_lines = 0
    width_candidates: list[float] = []
    width_value = width_floor
    while width_value <= width_cap + 0.1:
        width_candidates.append(width_value)
        width_value += 10.0
    if width_pref not in width_candidates:
        width_candidates.append(min(width_cap, max(width_floor, width_pref)))
    width_candidates = sorted(set(round(value, 1) for value in width_candidates))

    best_layout: dict[str, Any] | None = None
    best_score: tuple[int, int, float] | None = None
    for width in width_candidates:
        text_width = max(48.0, width - text_pad_left - text_pad_right)
        title_char_limit = max(12, int(text_width / max(title_font_size * 0.57, 5.0)))
        timing_char_limit = max(12, int(text_width / max(timing_font_size * 0.6, 4.8)))
        footer_char_limit = max(12, int(text_width / max(footer_font_size * 0.6, 4.8)))
        wrapped_title = _workflow_text_lines([title], max_chars=title_char_limit)
        wrapped_timing = _workflow_text_lines(timing_source_lines, max_chars=timing_char_limit)
        wrapped_footer = _workflow_text_lines(footer_source_lines, max_chars=footer_char_limit) if footer_source_lines else []
        title_lines = _workflow_fit_text_lines([title], max_chars=title_char_limit, max_lines=title_max_lines)
        timing_lines = _workflow_fit_text_lines(timing_source_lines, max_chars=timing_char_limit, max_lines=timing_max_lines)
        footer_lines = (
            _workflow_fit_text_lines(footer_source_lines, max_chars=footer_char_limit, max_lines=footer_max_lines)
            if footer_source_lines and footer_max_lines > 0
            else []
        )
        overflow_score = (
            max(0, len(wrapped_title) - title_max_lines)
            + max(0, len(wrapped_timing) - timing_max_lines)
            + max(0, len(wrapped_footer) - footer_max_lines)
        )
        if inline_detail and title_lines and timing_lines:
            title_inline_width = len(str(title_lines[0])) * title_font_size * 0.58
            timing_inline_width = len(str(timing_lines[0])) * timing_font_size * 0.56
            inline_gap = 14.0
            if (title_inline_width + inline_gap + timing_inline_width) > text_width:
                overflow_score += 1
        title_block_height = max(1, len(title_lines)) * title_line_gap
        timing_block_height = len(timing_lines) * timing_line_gap if timing_lines else 0.0
        content_height = text_top_pad + chip_height + chip_gap + title_block_height
        if timing_lines:
            if inline_detail:
                content_height = text_top_pad + chip_height + chip_gap + max(title_block_height, timing_block_height)
            else:
                content_height += section_gap + timing_block_height
        if show_ribbon:
            content_height += ribbon_gap + ribbon_height
        if footer_lines:
            content_height += section_gap + (len(footer_lines) * footer_line_gap)
        height = max(min_height, content_height + text_bottom_pad)
        layout = {
            "width": width,
            "height": height,
            "title_lines_render": title_lines,
            "timing_lines_render": timing_lines,
            "footer_lines_render": footer_lines,
            "meta_lines_render": footer_lines,
            "title_font_size": title_font_size,
            "timing_font_size": timing_font_size,
            "meta_font_size": meta_font_size,
            "footer_font_size": footer_font_size,
            "text_pad_left": text_pad_left,
            "text_pad_right": text_pad_right,
            "text_top_pad": text_top_pad,
            "text_bottom_pad": text_bottom_pad,
            "chip_gap": chip_gap,
            "title_line_gap": title_line_gap,
            "timing_line_gap": timing_line_gap,
            "meta_line_gap": meta_line_gap,
            "footer_line_gap": footer_line_gap,
            "section_gap": section_gap,
            "ribbon_gap": ribbon_gap,
            "ribbon_height_render": ribbon_height if show_ribbon else 0.0,
            "ribbon_label_font_size": float(profile.get("ribbon_label_font_size", 6.0)),
            "show_ribbon_labels": bool(profile.get("show_ribbon_labels", False)) and detail_level == "research",
            "show_ribbon": show_ribbon,
            "inline_detail": inline_detail,
            "mix_segments": mix_stats["segments"],
            "mix_total_cases": mix_stats["total_cases"],
            "path_pct": path_pct,
            "activity_pct": activity_pct,
            "text_width": text_width,
        }
        score = (
            overflow_score,
            len(title_lines) + len(timing_lines) + len(footer_lines),
            abs(width_pref - width),
        )
        if best_score is None or score < best_score:
            best_layout = layout
            best_score = score
        if overflow_score == 0 and width >= width_pref:
            break

    assert best_layout is not None
    return best_layout


def _workflow_apply_explorer_text_geometry(node: dict[str, Any]) -> None:
    text_pad_left = float(node.get("text_pad_left", 17.0))
    text_pad_right = float(node.get("text_pad_right", 14.0))
    text_top_pad = float(node.get("text_top_pad", 10.0))
    text_bottom_pad = float(node.get("text_bottom_pad", 10.0))
    chip_height = float(node.get("chip_height_render", 14.0))
    chip_gap = float(node.get("chip_gap", 8.0))
    title_font_size = float(node.get("title_font_size", 8.8))
    timing_font_size = float(node.get("timing_font_size", node.get("meta_font_size", 7.2)))
    footer_font_size = float(node.get("footer_font_size", node.get("meta_font_size", 7.0)))
    title_line_gap = float(node.get("title_line_gap", 11.5))
    timing_line_gap = float(node.get("timing_line_gap", node.get("meta_line_gap", 9.6)))
    meta_line_gap = float(node.get("meta_line_gap", 9.8))
    footer_line_gap = float(node.get("footer_line_gap", meta_line_gap))
    section_gap = float(node.get("section_gap", 6.0))
    ribbon_gap = float(node.get("ribbon_gap", 5.0))
    ribbon_height = float(node.get("ribbon_height_render", 0.0))
    inline_detail = bool(node.get("inline_detail"))
    title_lines = list(node.get("title_lines_render", []))
    timing_lines = list(node.get("timing_lines_render", []))
    footer_lines = list(node.get("footer_lines_render", []))
    text_x = float(node["x"]) + text_pad_left
    current_y = float(node["y"]) + text_top_pad + chip_height + chip_gap
    title_y = current_y + title_font_size
    current_y = title_y + max(0, len(title_lines) - 1) * title_line_gap
    timing_y = title_y
    timing_x = text_x
    text_box_bottom = current_y
    if timing_lines:
        if inline_detail:
            title_text = title_lines[0] if title_lines else ""
            timing_text = timing_lines[0] if timing_lines else ""
            title_estimate = len(str(title_text)) * title_font_size * 0.58
            timing_estimate = len(str(timing_text)) * timing_font_size * 0.56
            text_max_x = float(node["x"]) + float(node["width"]) - text_pad_right
            timing_x = min(text_x + title_estimate + 14.0, text_max_x - timing_estimate)
            timing_x = max(text_x + 18.0, timing_x)
            current_y = title_y + max(0.0, timing_font_size - title_font_size)
        else:
            current_y += section_gap
            timing_y = current_y + timing_font_size
            current_y = timing_y + max(0, len(timing_lines) - 1) * timing_line_gap
        text_box_bottom = current_y
    ribbon_y = current_y
    if node.get("show_ribbon") and ribbon_height > 0.0:
        current_y += ribbon_gap
        ribbon_y = max(current_y, float(node["y"]) + float(node["height"]) - text_bottom_pad - ribbon_height)
        current_y = ribbon_y + ribbon_height
    footer_y = current_y
    if footer_lines:
        current_y += section_gap
        footer_y = current_y + footer_font_size
        current_y = footer_y + max(0, len(footer_lines) - 1) * footer_line_gap
        text_box_bottom = current_y
    text_max_x = float(node["x"]) + float(node["width"]) - text_pad_right
    node["text_origin_x"] = text_x
    node["title_origin_y"] = title_y
    node["timing_origin_x"] = timing_x
    node["timing_origin_y"] = timing_y
    node["meta_origin_y"] = timing_y
    node["footer_origin_y"] = footer_y
    node["ribbon_y"] = ribbon_y
    node["ribbon_x"] = text_x
    node["ribbon_width_render"] = max(18.0, text_max_x - text_x)
    node["text_box"] = {
        "min_x": text_x,
        "min_y": float(node["y"]) + text_top_pad,
        "max_x": max(text_x, text_max_x),
        "max_y": max(title_y, text_box_bottom + text_bottom_pad) + 1.0,
    }


def _workflow_relax_vertical_nodes(
    node_items: list[dict[str, Any]],
    *,
    profile: Mapping[str, Any],
) -> None:
    if not node_items:
        return

    mainline_nodes = sorted(
        [node for node in node_items if str(node.get("branch_role", "mainline")) == "mainline"],
        key=lambda node: (int(node.get("step_rank", 0)), float(node.get("preferred_y", node.get("y", 0.0)))),
    )
    step_gap_floor = max(12.0, float(profile["step_gap"]) * 0.14)

    def _set_node_y(node: dict[str, Any], new_y: float) -> None:
        node["y"] = float(new_y)
        node["center_y"] = float(node["y"]) + float(node["height"]) / 2.0
        _workflow_apply_explorer_text_geometry(node)

    previous_bottom: float | None = None
    for node in mainline_nodes:
        preferred_y = float(node.get("preferred_y", node["y"]))
        target_y = preferred_y if previous_bottom is None else max(preferred_y, previous_bottom + step_gap_floor)
        _set_node_y(node, target_y)
        previous_bottom = float(node["y"]) + float(node["height"])

    for _ in range(6):
        moved = False
        previous_box: Optional[dict[str, float]] = None
        previous_bottom = None
        for node in mainline_nodes:
            preferred_y = float(node.get("preferred_y", node["y"]))
            target_y = preferred_y if previous_bottom is None else max(preferred_y, previous_bottom + step_gap_floor)
            if target_y > float(node["y"]) + 0.1:
                _set_node_y(node, target_y)
                moved = True
            node_box = _workflow_node_collision_bounds(node, pad=3.0)
            if previous_box is not None and _workflow_boxes_overlap(previous_box, node_box):
                push_y = max(10.0, previous_box["max_y"] - node_box["min_y"] + 8.0)
                _set_node_y(node, float(node["y"]) + push_y)
                node_box = _workflow_node_collision_bounds(node, pad=3.0)
                moved = True
            previous_bottom = max(float(node["y"]) + float(node["height"]), node_box["max_y"])
            previous_box = node_box
        if not moved:
            break

    mainline_by_step = {int(node.get("step_rank", 0)): node for node in mainline_nodes}
    lane_gap = float(profile["lane_gap"])
    vertical_gap = float(profile["vertical_gap"])
    for lane_position in ("left", "right"):
        lane_nodes = sorted(
            [node for node in node_items if str(node.get("lane_position", "")) == lane_position],
            key=lambda node: (int(node.get("step_rank", 0)), float(node.get("preferred_y", node.get("y", 0.0)))),
        )
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for node in lane_nodes:
            grouped[int(node.get("step_rank", 0))].append(node)
        for step_rank, items in grouped.items():
            anchor = mainline_by_step.get(step_rank)
            if anchor is None:
                continue
            anchor_center_y = float(anchor["center_y"])
            anchor_left = float(anchor["x"])
            anchor_right = float(anchor["x"]) + float(anchor["width"])
            row_count = len(items)
            for lane_index, node in enumerate(items):
                preferred_x = float(node.get("preferred_x", node["x"]))
                base_y = anchor_center_y + (lane_index - ((row_count - 1) / 2.0)) * (float(node["height"]) + vertical_gap)
                _set_node_y(node, base_y - float(node["height"]) / 2.0)
                if lane_position == "left":
                    lane_x = min(preferred_x, anchor_left - lane_gap - float(node["width"]) - 4.0)
                else:
                    lane_x = max(preferred_x, anchor_right + lane_gap + 4.0)
                node["x"] = lane_x
                node["center_x"] = lane_x + float(node["width"]) / 2.0
                node["center_y"] = float(node["y"]) + float(node["height"]) / 2.0
                _workflow_apply_explorer_text_geometry(node)

    ordered_nodes = sorted(node_items, key=lambda node: (float(node.get("center_y", 0.0)), float(node.get("center_x", 0.0))))
    for _ in range(9):
        moved = False
        for index, left in enumerate(ordered_nodes):
            left_box = _workflow_node_collision_bounds(left, pad=3.0)
            for right in ordered_nodes[index + 1 :]:
                right_box = _workflow_node_collision_bounds(right, pad=3.0)
                if not _workflow_boxes_overlap(left_box, right_box):
                    continue
                overlap_y = min(left_box["max_y"], right_box["max_y"]) - max(left_box["min_y"], right_box["min_y"])
                overlap_x = min(left_box["max_x"], right_box["max_x"]) - max(left_box["min_x"], right_box["min_x"])
                if overlap_y <= 0.0 and overlap_x <= 0.0:
                    continue
                moved = True
                if int(right.get("step_rank", 0)) >= int(left.get("step_rank", 0)):
                    push_y = max(6.0, overlap_y + 6.0)
                    _set_node_y(right, float(right["y"]) + push_y)
                lane_position = str(right.get("lane_position", "mainline"))
                if lane_position != "mainline":
                    direction = -1.0 if lane_position == "left" else 1.0
                    push_x = max(4.0, overlap_x * 0.45)
                    right["x"] = float(right["x"]) + direction * push_x
                    right["center_x"] = float(right["x"]) + float(right["width"]) / 2.0
                _workflow_apply_explorer_text_geometry(right)
                right_box = _workflow_node_collision_bounds(right, pad=3.0)
                left_box = _workflow_node_collision_bounds(left, pad=3.0)
        for node in ordered_nodes:
            preferred_x = float(node.get("preferred_x", node["x"]))
            spring = 0.14 if str(node.get("lane_position", "mainline")) == "mainline" else 0.06
            node["x"] = float(node["x"]) + (preferred_x - float(node["x"])) * spring
            node["center_x"] = float(node["x"]) + float(node["width"]) / 2.0
            _workflow_apply_explorer_text_geometry(node)
        if not moved:
            break


def _workflow_vertical_layout_profile(
    *,
    step_count: int,
    max_branch_depth: int,
    max_edge_fanout: int,
    detail_level: str,
    lens_is_paths: bool,
) -> dict[str, Any]:
    compact = step_count >= 6 or max_branch_depth >= 2 or max_edge_fanout >= 3
    if compact:
        profile = {
            "name": "compact",
            "step_gap": 74.0,
            "top_margin": 64.0,
            "side_margin": 30.0,
            "mainline_width": 344.0,
            "mainline_height": 50.0,
            "branch_width": 248.0,
            "branch_height": 38.0,
            "mainline_width_min": 312.0,
            "mainline_width_max": 396.0,
            "branch_width_min": 220.0,
            "branch_width_max": 296.0,
            "mainline_min_height": 46.0,
            "branch_min_height": 34.0,
            "vertical_gap": 10.0,
            "lane_gap": 20.0,
            "wobble": 138.0 if lens_is_paths else 128.0,
            "sway": 18.0 if lens_is_paths else 14.0,
            "drift": 0.92 if lens_is_paths else 0.74,
            "mainline_sibling_offset": 6.0,
            "branch_sibling_offset": 8.0,
            "stroke_mainline": 1.2,
            "stroke_branch": 0.82,
            "marker_width": 5.2,
            "marker_height": 5.2,
            "marker_ref_x": 4.7,
            "marker_ref_y": 2.6,
            "label_width": 68.0,
            "label_height": 18.0,
            "label_height_secondary": 28.0,
            "label_font": 8.2,
            "label_secondary_font": 7.6,
            "label_clearance": 7.0,
            "title_font_size": 8.2,
            "meta_font_size": 6.9,
            "median_font_size": 6.6,
            "p90_font_size": 8.8,
            "chip_width": 48.0,
            "chip_height": 12.0,
            "chip_font_size": 6.6,
            "chip_offset_y": 6.0,
            "title_line_gap": 9.6,
            "timing_line_gap": 8.2,
            "meta_line_gap": 8.8,
            "footer_line_gap": 8.2,
            "text_pad_left": 16.0,
            "text_pad_right": 12.0,
            "text_top_pad": 6.0,
            "text_bottom_pad": 6.0,
            "chip_gap": 3.2,
            "section_gap": 2.0,
            "ribbon_height": 4.0,
            "ribbon_gap": 3.2,
            "footer_font_size": 6.7,
            "timing_font_size": 6.9,
            "ribbon_label_font_size": 5.8,
            "show_ribbon_labels": False,
            "anchor_font_size": 11.0,
            "card_radius": 9.0,
        }
    else:
        profile = {
            "name": "standard",
            "step_gap": 80.0,
            "top_margin": 66.0,
            "side_margin": 32.0,
            "mainline_width": 360.0,
            "mainline_height": 52.0,
            "branch_width": 260.0,
            "branch_height": 40.0,
            "mainline_width_min": 328.0,
            "mainline_width_max": 420.0,
            "branch_width_min": 232.0,
            "branch_width_max": 316.0,
            "mainline_min_height": 48.0,
            "branch_min_height": 36.0,
            "vertical_gap": 11.0,
            "lane_gap": 24.0,
            "wobble": 146.0 if lens_is_paths else 134.0,
            "sway": 20.0 if lens_is_paths else 16.0,
            "drift": 0.98 if lens_is_paths else 0.8,
            "mainline_sibling_offset": 7.0,
            "branch_sibling_offset": 9.0,
            "stroke_mainline": 1.3,
            "stroke_branch": 0.9,
            "marker_width": 5.8,
            "marker_height": 5.8,
            "marker_ref_x": 5.2,
            "marker_ref_y": 2.9,
            "label_width": 76.0,
            "label_height": 20.0,
            "label_height_secondary": 32.0,
            "label_font": 9.0,
            "label_secondary_font": 8.4,
            "label_clearance": 8.0,
            "title_font_size": 9.0,
            "meta_font_size": 7.6,
            "median_font_size": 7.0,
            "p90_font_size": 9.2,
            "chip_width": 52.0,
            "chip_height": 12.0,
            "chip_font_size": 6.8,
            "chip_offset_y": 7.0,
            "title_line_gap": 9.8,
            "timing_line_gap": 8.4,
            "meta_line_gap": 9.0,
            "footer_line_gap": 8.6,
            "text_pad_left": 16.0,
            "text_pad_right": 12.0,
            "text_top_pad": 6.0,
            "text_bottom_pad": 6.0,
            "chip_gap": 3.4,
            "section_gap": 2.2,
            "ribbon_height": 4.0,
            "ribbon_gap": 3.4,
            "footer_font_size": 7.0,
            "timing_font_size": 7.2,
            "ribbon_label_font_size": 6.1,
            "show_ribbon_labels": False,
            "anchor_font_size": 11.5,
            "card_radius": 9.0,
        }
    if detail_level == "executive":
        profile["mainline_width"] = max(140.0, float(profile["mainline_width"]) - 6.0)
        profile["branch_width"] = max(112.0, float(profile["branch_width"]) - 6.0)
        profile["mainline_height"] = max(64.0, float(profile["mainline_height"]) - 4.0)
        profile["branch_height"] = max(46.0, float(profile["branch_height"]) - 4.0)
        profile["chip_width"] = max(40.0, float(profile["chip_width"]) - 2.0)
        profile["chip_height"] = max(13.0, float(profile["chip_height"]) - 1.0)
        profile["title_font_size"] = max(7.8, float(profile["title_font_size"]) - 0.3)
        profile["meta_font_size"] = max(6.8, float(profile["meta_font_size"]) - 0.2)
        profile["median_font_size"] = max(6.4, float(profile["median_font_size"]) - 0.2)
    if detail_level == "research":
        profile["vertical_gap"] = float(profile["vertical_gap"]) + 1.5
    return profile


def _workflow_horizontal_layout_profile(
    *,
    step_count: int,
    max_top_branches: int,
    max_bottom_branches: int,
    detail_level: str = "analyst",
) -> dict[str, Any]:
    simple_mainline_mode = step_count <= 7 and max_top_branches == 0 and max_bottom_branches == 0
    max_branch_depth = max(max_top_branches, max_bottom_branches)
    compact = step_count >= 7 or max_branch_depth >= 2
    if simple_mainline_mode:
        profile = {
            "name": "compact" if compact else "standard",
            "simple_mainline_mode": True,
            "preferred_shelf_width": 1240.0,
            "left_margin": 34.0 if compact else 36.0,
            "right_margin": 34.0 if compact else 36.0,
            "min_inter_step_gap": 16.0 if step_count > 1 else 0.0,
            "max_inter_step_gap": 56.0 if compact else 74.0,
            "preferred_mainline_width": 212.0 if compact else 252.0,
            "min_mainline_width": 184.0,
            "max_mainline_width": 236.0 if compact else 286.0,
            "branch_width_ratio": 0.78 if compact else 0.82,
            "min_branch_width": 148.0,
            "max_branch_width": 176.0 if compact else 190.0,
            "mainline_height": 86.0 if compact else 118.0,
            "branch_height": 54.0 if compact else 60.0,
            "lane_gap_y": 54.0 if compact else 62.0,
            "top_margin": 52.0 if compact else 60.0,
            "bottom_margin": 58.0 if compact else 64.0,
            "title_size_mainline": 13.0 if compact else 15.0,
            "title_size_branch": 11.5 if compact else 13.0,
            "detail_size_mainline": 9.4 if compact else 11.0,
            "detail_size_branch": 8.6 if compact else 10.0,
            "chip_width": 62.0 if compact else 72.0,
            "chip_height": 20.0 if compact else 24.0,
            "chip_font_size": 8.4 if compact else 10.0,
            "stroke_mainline": 2.0 if compact else 2.2,
            "stroke_branch": 1.1 if compact else 1.35,
            "marker_width": 6.0 if compact else 7.0,
            "marker_height": 6.0 if compact else 7.0,
            "marker_ref_x": 5.3 if compact else 6.0,
            "marker_ref_y": 3.0 if compact else 3.5,
            "label_font_size": 9.2 if compact else 11.0,
            "label_secondary_font_size": 8.0 if compact else 9.0,
            "label_clearance": 8.0,
            "node_label_chars": 28 if compact else 34,
            "detail_line_gap": 13.0 if compact else 15.0,
            "title_line_gap": 14.0 if compact else 16.0,
            "header_band_height": 26.0 if compact else 30.0,
            "header_pad_x": 16.0 if compact else 18.0,
            "card_radius": 14.0 if compact else 16.0,
            "board_min_height": 328 if compact else 364,
            "fit_mode": "shelf",
        }
    else:
        profile = {
            "name": "compact" if compact else "standard",
            "simple_mainline_mode": False,
            "preferred_shelf_width": 1720.0,
            "left_margin": 32.0 if compact else 36.0,
            "right_margin": 32.0 if compact else 36.0,
            "min_inter_step_gap": 16.0 if step_count > 1 else 0.0,
            "max_inter_step_gap": 52.0 if compact else 68.0,
            "preferred_mainline_width": 198.0 if compact else 224.0,
            "min_mainline_width": 184.0,
            "max_mainline_width": 214.0 if compact else 238.0,
            "branch_width_ratio": 0.76 if compact else 0.82,
            "min_branch_width": 148.0,
            "max_branch_width": 170.0 if compact else 190.0,
            "mainline_height": 84.0 if compact else 100.0,
            "branch_height": 54.0 if compact else 66.0,
            "lane_gap_y": 56.0 if compact else 72.0,
            "top_margin": 46.0 if compact else 50.0,
            "bottom_margin": 52.0 if compact else 58.0,
            "title_size_mainline": 12.6 if compact else 15.0,
            "title_size_branch": 11.0 if compact else 13.0,
            "detail_size_mainline": 9.0 if compact else 11.0,
            "detail_size_branch": 8.3 if compact else 10.0,
            "chip_width": 62.0 if compact else 74.0,
            "chip_height": 20.0 if compact else 24.0,
            "chip_font_size": 8.2 if compact else 10.0,
            "stroke_mainline": 1.9 if compact else 2.2,
            "stroke_branch": 1.05 if compact else 1.35,
            "marker_width": 6.0 if compact else 7.0,
            "marker_height": 6.0 if compact else 7.0,
            "marker_ref_x": 5.3 if compact else 6.0,
            "marker_ref_y": 3.0 if compact else 3.5,
            "label_font_size": 8.8 if compact else 11.0,
            "label_secondary_font_size": 7.8 if compact else 9.0,
            "label_clearance": 8.0,
            "node_label_chars": 26 if compact else 34,
            "detail_line_gap": 12.0 if compact else 15.0,
            "title_line_gap": 13.0 if compact else 16.0,
            "header_band_height": 25.0 if compact else 29.0,
            "header_pad_x": 15.0 if compact else 17.0,
            "card_radius": 14.0 if compact else 16.0,
            "board_min_height": 300 if compact else 328,
            "fit_mode": "scroll",
        }
    if str(detail_level or "analyst").lower() == "executive":
        executive_scale = 0.75
        for key in (
            "preferred_mainline_width",
            "min_mainline_width",
            "max_mainline_width",
            "min_branch_width",
            "max_branch_width",
            "mainline_height",
            "branch_height",
            "chip_width",
            "chip_height",
            "title_size_mainline",
            "title_size_branch",
            "detail_size_mainline",
            "detail_size_branch",
            "chip_font_size",
            "marker_width",
            "marker_height",
            "marker_ref_x",
            "marker_ref_y",
            "header_band_height",
            "header_pad_x",
            "title_line_gap",
            "detail_line_gap",
        ):
            profile[key] = round(float(profile[key]) * executive_scale, 1)
        profile["board_min_height"] = 116 if bool(profile["simple_mainline_mode"]) else 148
        profile["top_margin"] = 12.0
        profile["bottom_margin"] = 14.0
        profile["lane_gap_y"] = round(max(40.0, float(profile["lane_gap_y"]) * 0.86), 1)
        profile["max_inter_step_gap"] = round(
            max(float(profile["min_inter_step_gap"]), float(profile["max_inter_step_gap"]) * 0.84),
            1,
        )
        profile["node_label_chars"] = max(18, int(float(profile["node_label_chars"]) * 0.82))
    return profile


def render_workflow_conformance_svg(
    payload: Mapping[str, Any] | pd.DataFrame | None,
    edges: pd.DataFrame | None = None,
    *,
    layout_mode: Literal["vertical", "horizontal"] = "vertical",
    detail_level: Literal["executive", "analyst", "research"] = "analyst",
) -> str:
    """Render a deterministic SVG workflow board from workflow conformance payloads."""
    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, edges)
    ordered_nodes = _order_workflow_nodes(nodes_df)
    normalized_edges = _normalize_workflow_edges(edges_df, ordered_nodes)
    layout_mode = str(layout_mode or "vertical").lower()
    detail_level = str(detail_level or "analyst").lower()

    if ordered_nodes.empty and normalized_edges.empty:
        return _workflow_svg_empty("No workflow conformance structure available")

    if ordered_nodes.empty and not normalized_edges.empty:
        ordered_nodes = _derive_nodes_from_edges(normalized_edges)

    if layout_mode == "horizontal":
        step_groups: dict[int, list[pd.Series]] = defaultdict(list)
        for _, row in ordered_nodes.iterrows():
            step_groups[_workflow_layout_step_rank(row.get("step_rank", 999))].append(row)

        sorted_steps = sorted(step_groups)
        step_count = max(1, len(sorted_steps))

        max_top_branches = 0
        max_bottom_branches = 0
        for rows in step_groups.values():
            top_count = 0
            bottom_count = 0
            for row in rows:
                if str(row.get("branch_role", "mainline")) == "mainline":
                    continue
                if str(row.get("lane", "left") or "left").lower() == "right":
                    bottom_count += 1
                else:
                    top_count += 1
            max_top_branches = max(max_top_branches, top_count)
            max_bottom_branches = max(max_bottom_branches, bottom_count)

        profile = _workflow_horizontal_layout_profile(
            step_count=step_count,
            max_top_branches=max_top_branches,
            max_bottom_branches=max_bottom_branches,
            detail_level=detail_level,
        )
        preferred_shelf_width = float(profile["preferred_shelf_width"])
        left_margin = float(profile["left_margin"])
        right_margin = float(profile["right_margin"])
        per_step_slot = max(1.0, (preferred_shelf_width - left_margin - right_margin) / float(step_count))
        mainline_width = min(
            float(profile["max_mainline_width"]),
            max(float(profile["min_mainline_width"]), per_step_slot * 0.82),
        )
        inter_step_gap = max(
            float(profile["min_inter_step_gap"]),
            min(float(profile["max_inter_step_gap"]), per_step_slot - mainline_width),
        )
        required_mainline_span = (step_count * mainline_width) + (max(0, step_count - 1) * inter_step_gap)
        board_width = int(math.ceil(max(preferred_shelf_width, left_margin + right_margin + required_mainline_span)))
        side_margin = max(left_margin, (board_width - required_mainline_span) / 2.0)
        branch_width = max(
            float(profile["min_branch_width"]),
            min(float(profile["max_branch_width"]), mainline_width * float(profile["branch_width_ratio"])),
        )
        mainline_height = float(profile["mainline_height"])
        branch_height = float(profile["branch_height"])
        lane_gap_y = float(profile["lane_gap_y"])
        top_margin = float(profile["top_margin"])
        bottom_margin = float(profile["bottom_margin"])

        upper_stack_height = max_top_branches * (branch_height + lane_gap_y) if max_top_branches else 0.0
        x_by_step: dict[int, float] = {}
        current_x = side_margin
        for step_rank in sorted_steps:
            x_by_step[step_rank] = current_x + (mainline_width / 2.0)
            current_x += mainline_width + inter_step_gap
        mainline_center_y = top_margin + upper_stack_height + (mainline_height / 2.0)
        nodes_layout: list[dict[str, Any]] = []
        for step_rank in sorted_steps:
            rows = sorted(
                step_groups[step_rank],
                key=lambda row: (
                    0 if str(row.get("branch_role", "mainline")) == "mainline" else 1,
                    -_safe_int(row.get("cases", 0)),
                    str(row.get("display_name", row.get("activity", ""))),
                ),
            )
            mainline_rows = [row for row in rows if str(row.get("branch_role", "mainline")) == "mainline"]
            top_rows = [
                row
                for row in rows
                if str(row.get("branch_role", "mainline")) != "mainline" and str(row.get("lane", "left") or "left").lower() != "right"
            ]
            bottom_rows = [
                row
                for row in rows
                if str(row.get("branch_role", "mainline")) != "mainline" and str(row.get("lane", "left") or "left").lower() == "right"
            ]
            x_center = x_by_step[step_rank]
            for main_index, row in enumerate(mainline_rows):
                activity = str(row.get("activity", row.get("display_name", f"node-{step_rank}-{main_index}")))
                nodes_layout.append(
                    {
                        "row": row,
                        "index": len(nodes_layout),
                        "activity": activity,
                        "x": x_center - mainline_width / 2.0,
                        "y": mainline_center_y - mainline_height / 2.0 + (main_index * 10.0),
                        "width": mainline_width,
                        "height": mainline_height,
                    }
                )
            for branch_index, row in enumerate(top_rows):
                activity = str(row.get("activity", row.get("display_name", f"branch-top-{step_rank}-{branch_index}")))
                y = mainline_center_y - mainline_height / 2.0 - lane_gap_y - branch_height - (branch_index * (branch_height + lane_gap_y))
                nodes_layout.append(
                    {
                        "row": row,
                        "index": len(nodes_layout),
                        "activity": activity,
                        "x": x_center - branch_width / 2.0,
                        "y": y,
                        "width": branch_width,
                        "height": branch_height,
                    }
                )
            for branch_index, row in enumerate(bottom_rows):
                activity = str(row.get("activity", row.get("display_name", f"branch-bottom-{step_rank}-{branch_index}")))
                y = mainline_center_y + mainline_height / 2.0 + lane_gap_y + (branch_index * (branch_height + lane_gap_y))
                nodes_layout.append(
                    {
                        "row": row,
                        "index": len(nodes_layout),
                        "activity": activity,
                        "x": x_center - branch_width / 2.0,
                        "y": y,
                        "width": branch_width,
                        "height": branch_height,
                    }
                )

        if nodes_layout:
            content_max_y = max(float(item["y"]) + float(item["height"]) for item in nodes_layout)
            board_height = max(int(profile["board_min_height"]), int(math.ceil(content_max_y + bottom_margin)))
        else:
            board_height = int(profile["board_min_height"])

        node_positions = {str(item["activity"]): item for item in nodes_layout}
        edge_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        edge_records = []
        for _, row in normalized_edges.iterrows():
            source = str(row.get("source", ""))
            target = str(row.get("target", ""))
            if source not in node_positions or target not in node_positions:
                continue
            edge_groups[source].append({"source": source, "target": target, "row": row})

        for source, group in edge_groups.items():
            group.sort(
                key=lambda item: (
                    node_positions[item["target"]]["index"],
                    -_safe_int(item["row"].get("frequency", 0)),
                    item["target"],
                )
            )
            for lane_index, item in enumerate(group):
                item["lane_index"] = lane_index
                edge_records.append(item)

        edge_layouts: list[dict[str, Any]] = []
        max_frequency = max((_safe_int(row.get("frequency", 0)) for _, row in normalized_edges.iterrows()), default=0)
        for item in edge_records:
            row = item["row"]
            source_layout = node_positions[item["source"]]
            target_layout = node_positions[item["target"]]
            lane_index = item["lane_index"]
            severity = str(row.get("severity", "Low"))
            palette = _WORKFLOW_SEVERITY_THEME.get(severity, _WORKFLOW_SEVERITY_THEME["Low"])
            freq = _safe_int(row.get("frequency", 0))
            median_days = _safe_float(row.get("median_days"))
            source_x = source_layout["x"] + source_layout["width"]
            source_y = source_layout["y"] + source_layout["height"] / 2.0
            target_x = target_layout["x"]
            target_y = target_layout["y"] + target_layout["height"] / 2.0
            label_width = 0.0
            label_height = 0.0
            if source_layout["row"].get("activity") == target_layout["row"].get("activity"):
                loop_span = 28.0 + lane_index * (12.0 if profile["name"] == "compact" else 16.0)
                loop_up = str(source_layout["row"].get("lane", "center") or "center").lower() != "right"
                loop_y = source_layout["y"] - loop_span if loop_up else source_layout["y"] + source_layout["height"] + loop_span
                path = (
                    f"M {source_x - 14.0:.1f} {source_y:.1f} "
                    f"C {source_x + 28.0:.1f} {source_y:.1f}, {source_x + 28.0:.1f} {loop_y:.1f}, {source_x - 4.0:.1f} {loop_y:.1f} "
                    f"C {source_layout['x'] - 16.0:.1f} {loop_y:.1f}, {source_layout['x'] - 16.0:.1f} {source_y:.1f}, {source_layout['x'] + 8.0:.1f} {source_y:.1f}"
                )
                label_x = source_layout["x"] + source_layout["width"] / 2.0
                label_y = loop_y - 8.0 if loop_up else loop_y + 14.0
            else:
                delta_x = max(68.0, target_x - source_x)
                control = min(118.0, delta_x * 0.34)
                bend_y = (source_y + target_y) / 2.0 + ((lane_index - 0.5) * (8.0 if profile["name"] == "compact" else 10.0))
                path = (
                    f"M {source_x:.1f} {source_y:.1f} "
                    f"C {source_x + control:.1f} {source_y:.1f}, {target_x - control:.1f} {target_y:.1f}, {target_x:.1f} {target_y:.1f}"
                )
                label_x = (source_x + target_x) / 2.0
                label_y = bend_y - 12.0 if source_y <= target_y else bend_y + 6.0

            is_deviating = bool(row.get("is_deviating")) or str(row.get("stroke_style", "")).lower() == "dashed"
            dash = ' stroke-dasharray="9 6"' if is_deviating else ""
            is_mainline_edge = str(row.get("branch_role", "mainline")) == "mainline"
            opacity = "0.94" if is_mainline_edge else "0.66"
            base_stroke = float(profile["stroke_mainline"] if is_mainline_edge else profile["stroke_branch"])
            stroke_width = base_stroke + min(freq / 32000.0, 2.4 if is_mainline_edge else 0.9)
            conf_bucket = str(row.get("conformance_bucket", "Conformant"))
            conf_theme = _WORKFLOW_CONFORMANCE_THEME.get(conf_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
            show_label = is_mainline_edge and freq >= max(220, int(max_frequency * 0.6))
            edge_label = [f"{freq:,} cases" if freq else "0 cases"]
            if median_days is not None and freq >= 200:
                edge_label.append(f"{median_days:.1f} d")
            text_lines = _workflow_text_lines(edge_label, max_chars=12 if profile["name"] == "compact" else 14)
            if show_label:
                label_width = max(64.0, min(124.0, max((len(line) for line in text_lines), default=8) * 6.6 + 16.0))
                label_height = 16.0 + max(0, len(text_lines) - 1) * 11.0 + 8.0
            edge_layouts.append(
                {
                    "path": path,
                    "palette": palette,
                    "opacity": opacity,
                    "dash": dash,
                    "stroke_width": stroke_width,
                    "conf_theme": conf_theme,
                    "show_label": show_label,
                    "label_x": label_x,
                    "label_y": label_y,
                    "label_width": label_width,
                    "label_height": label_height,
                    "text_lines": text_lines,
                    "edge_id": str(row.get("edge_id", f"{item['source']} -> {item['target']}")),
                    "edge_role": str(row.get("edge_type", "expected")),
                    "branch_role": str(row.get("branch_role", "mainline")),
                    "frequency": freq,
                }
            )

        _workflow_apply_label_clearance(
            edge_layouts,
            nodes_layout,
            clearance=float(profile["label_clearance"]),
        )
        fit_mode = str(profile.get("fit_mode", "scroll"))
        svg_style = (
            "display:block;width:100%;max-width:100%;height:auto;"
            if fit_mode == "shelf"
            else f"display:block;width:{board_width:.0f}px;min-width:100%;height:auto;"
        )

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {board_width} {board_height}" width="{board_width:.0f}" height="{board_height:.0f}" style="{svg_style}" role="img" aria-label="Workflow conformance board" data-density-profile="{escape(str(profile["name"]))}" data-fit-mode="{escape(fit_mode)}">',
            "<defs>",
            '<linearGradient id="workflow-bg" x1="0" y1="0" x2="0" y2="1">',
            '<stop offset="0%" stop-color="#ffffff"/>',
            '<stop offset="100%" stop-color="#faf7fd"/>',
            "</linearGradient>",
            '<filter id="workflow-shadow" x="-20%" y="-20%" width="160%" height="160%">',
            '<feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#433655" flood-opacity="0.12"/>',
            "</filter>",
            (
                f'<marker id="workflow-arrow" markerWidth="{float(profile["marker_width"]):.1f}" '
                f'markerHeight="{float(profile["marker_height"]):.1f}" '
                f'refX="{float(profile["marker_ref_x"]):.1f}" refY="{float(profile["marker_ref_y"]):.1f}" '
                'orient="auto" markerUnits="strokeWidth">'
            ),
            (
                f'<path d="M 0 0 L {float(profile["marker_width"]):.1f} {float(profile["marker_ref_y"]):.1f} '
                f'L 0 {float(profile["marker_height"]):.1f} z" fill="#51645a"/>'
            ),
            "</marker>",
            "</defs>",
            '<rect x="0" y="0" width="100%" height="100%" fill="url(#workflow-bg)"/>',
        ]

        top_branch_items = [
            item
            for item in nodes_layout
            if str(item["row"].get("branch_role", "mainline")) != "mainline"
            and str(item["row"].get("lane", "left") or "left").lower() != "right"
        ]
        bottom_branch_items = [
            item
            for item in nodes_layout
            if str(item["row"].get("branch_role", "mainline")) != "mainline"
            and str(item["row"].get("lane", "left") or "left").lower() == "right"
        ]

        if top_branch_items:
            upper_band_y = min(float(item["y"]) for item in top_branch_items) - 16.0
            upper_band_height = max(float(item["y"]) + float(item["height"]) for item in top_branch_items) - upper_band_y + 16.0
            svg_parts.extend(
                [
                    f'<rect x="{side_margin - 16:.1f}" y="{upper_band_y:.1f}" width="{board_width - (side_margin * 2.0) + 32:.1f}" height="{upper_band_height:.1f}" rx="22" ry="22" fill="#f6f4fa" fill-opacity="0.88"/>',
                    f'<text x="{side_margin - 6:.1f}" y="{upper_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#8a8097">Upper variation</text>',
                ]
            )
        if bottom_branch_items:
            lower_band_y = min(float(item["y"]) for item in bottom_branch_items) - 14.0
            lower_band_height = max(float(item["y"]) + float(item["height"]) for item in bottom_branch_items) - lower_band_y + 18.0
            svg_parts.extend(
                [
                    f'<rect x="{side_margin - 16:.1f}" y="{lower_band_y:.1f}" width="{board_width - (side_margin * 2.0) + 32:.1f}" height="{lower_band_height:.1f}" rx="22" ry="22" fill="#f6f4fa" fill-opacity="0.84"/>',
                    f'<text x="{side_margin - 6:.1f}" y="{lower_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#8a8097">Lower variation</text>',
                ]
            )

        for edge_layout in edge_layouts:
            svg_parts.append(
                f'<path d="{edge_layout["path"]}" fill="none" stroke="{edge_layout["palette"]["stroke"]}" stroke-width="{float(edge_layout["stroke_width"]):.1f}" stroke-linecap="round"{edge_layout["dash"]} opacity="{edge_layout["opacity"]}" marker-end="url(#workflow-arrow)" data-edge-id="{escape(edge_layout["edge_id"])}" data-edge-role="{escape(edge_layout["edge_role"])}"/>'
            )
            if edge_layout.get("show_label"):
                svg_parts.append(
                    f'<g transform="translate({float(edge_layout["label_x"]):.1f},{float(edge_layout["label_y"]):.1f})">'
                    f'<rect x="{-float(edge_layout["label_width"]) / 2.0:.1f}" y="{-float(edge_layout["label_height"]) / 2.0:.1f}" width="{float(edge_layout["label_width"]):.1f}" height="{float(edge_layout["label_height"]):.1f}" rx="8" ry="8" fill="#ffffff" fill-opacity="0.93" stroke="{edge_layout["conf_theme"]["stroke"]}" stroke-width="0.8"/>'
                )
                for line_index, line in enumerate(edge_layout["text_lines"]):
                    dy = -3 + line_index * 11 if len(edge_layout["text_lines"]) > 1 else 4
                    weight = "700" if line_index == 0 else "500"
                    size = float(profile["label_font_size"] if line_index == 0 else profile["label_secondary_font_size"])
                    svg_parts.append(
                        f'<text x="0" y="{dy}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="#20312a">{escape(line)}</text>'
                    )
                svg_parts.append("</g>")

        for item in nodes_layout:
            row = item["row"]
            severity = str(row.get("severity", "Low"))
            palette = _WORKFLOW_SEVERITY_THEME.get(severity, _WORKFLOW_SEVERITY_THEME["Low"])
            title = str(row.get("display_name") or row.get("business_label") or row.get("activity") or "Node")
            cases = _safe_int(row.get("cases", 0))
            median_delay = _safe_float(row.get("median_next_delay_days"))
            conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
            conformance_theme = _WORKFLOW_CONFORMANCE_THEME.get(conformance_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
            mix_stats = _workflow_node_mix_stats(row)
            branch_role = str(row.get("branch_role", "mainline"))
            chip_label = conformance_bucket if conformance_bucket != "Conformant" else severity
            title_size = float(profile["title_size_mainline"] if branch_role == "mainline" else profile["title_size_branch"])
            detail_size = float(profile["detail_size_mainline"] if branch_role == "mainline" else profile["detail_size_branch"])
            header_band_height = float(profile.get("header_band_height", 28.0))
            header_pad_x = float(profile.get("header_pad_x", 16.0))
            chip_height = float(profile["chip_height"])
            chip_width = max(
                float(profile["chip_width"]),
                min(104.0, len(chip_label) * (4.8 if profile["name"] == "compact" else 5.4) + 22.0),
            )
            chip_x = item["x"] + item["width"] - chip_width - header_pad_x
            chip_y = item["y"] + max(6.0, (header_band_height - chip_height) / 2.0)
            content_x = item["x"] + header_pad_x
            title_room = max(12.0, chip_x - content_x - 10.0)
            title_char_limit = max(12, int(title_room / (5.4 if profile["name"] == "compact" else 6.2)))
            detail_room = max(12.0, item["width"] - (header_pad_x * 2.0))
            detail_char_limit = max(12, int(detail_room / max(detail_size * 0.62, 5.0)))
            max_title_lines = 2 if branch_role == "mainline" else 1
            max_detail_lines = 1 if detail_level == "executive" else (2 if branch_role == "mainline" else 1)
            header_lines = _workflow_fit_text_lines([title], max_chars=title_char_limit, max_lines=max_title_lines)
            if detail_level == "executive":
                combined_detail = (
                    f"{cases:,} cases · {median_delay:.1f} d median" if median_delay is not None else f"{cases:,} cases · Delay n/a"
                )
                detail_lines = _workflow_fit_text_lines([combined_detail], max_chars=detail_char_limit, max_lines=2)
            else:
                detail_source_lines = (
                    [
                        f"{cases:,} cases" if cases else "0 cases",
                        f"{median_delay:.1f} d median" if median_delay is not None else "Delay n/a",
                    ]
                    if branch_role == "mainline"
                    else [f"{cases:,} cases" if cases else "0 cases"]
                )
                detail_lines = _workflow_fit_text_lines(
                    detail_source_lines,
                    max_chars=detail_char_limit,
                    max_lines=max_detail_lines,
                )
            mix_bar_x = item["x"] + header_pad_x
            mix_bar_y = item["y"] + item["height"] - 8.0
            mix_bar_width = max(18.0, item["width"] - (header_pad_x * 2.0))
            mix_bar_height = 4.0
            svg_parts.append(
                f'<g filter="url(#workflow-shadow)" data-activity="{escape(str(row.get("activity", title)))}" data-branch-role="{escape(branch_role)}" data-lane="{escape(str(row.get("lane", "center")))}" data-node-type="{escape(str(row.get("node_type", "mainline")))}" data-qa="workflow-board-card">'
                f'<rect x="{item["x"]:.1f}" y="{item["y"]:.1f}" width="{item["width"]:.1f}" height="{item["height"]:.1f}" rx="{float(profile["card_radius"]):.1f}" ry="{float(profile["card_radius"]):.1f}" fill="{palette["fill"]}" stroke="{palette["stroke"]}" stroke-width="2.0"/>'
                f'<rect x="{item["x"]:.1f}" y="{item["y"]:.1f}" width="{item["width"]:.1f}" height="{header_band_height:.1f}" rx="{float(profile["card_radius"]):.1f}" ry="{float(profile["card_radius"]):.1f}" fill="{conformance_theme["fill"]}" fill-opacity="0.72"/>'
                f'<rect x="{chip_x:.1f}" y="{chip_y:.1f}" width="{chip_width:.1f}" height="{chip_height:.1f}" rx="{chip_height / 2.0:.1f}" ry="{chip_height / 2.0:.1f}" fill="{palette["stroke"]}" data-qa="workflow-board-chip" />'
                f'<text x="{chip_x + chip_width / 2.0:.1f}" y="{chip_y + chip_height * 0.67:.1f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{float(profile["chip_font_size"]):.1f}" font-weight="700" fill="#ffffff">{escape(chip_label)}</text>'
            )
            title_y = (
                item["y"] + header_band_height + (12.0 if detail_level == "executive" else (16.0 if profile["name"] == "compact" else 18.0))
            )
            for line_index, line in enumerate(header_lines):
                svg_parts.append(
                    f'<text x="{content_x:.1f}" y="{title_y + line_index * float(profile["title_line_gap"]):.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="{title_size}" font-weight="700" fill="{palette["ink"]}" data-qa="workflow-board-title">{escape(line)}</text>'
                )
            detail_start = title_y + max(len(header_lines), 1) * float(profile["title_line_gap"]) + 7.0
            for line_index, line in enumerate(detail_lines):
                svg_parts.append(
                    f'<text x="{content_x:.1f}" y="{detail_start + line_index * float(profile["detail_line_gap"]):.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="{detail_size}" fill="{palette["ink"]}" fill-opacity="0.88" data-qa="workflow-board-meta">{escape(line)}</text>'
                )
            svg_parts.append(
                f'<rect x="{mix_bar_x:.1f}" y="{mix_bar_y:.1f}" width="{mix_bar_width:.1f}" height="{mix_bar_height:.1f}" rx="{mix_bar_height / 2.0:.1f}" ry="{mix_bar_height / 2.0:.1f}" fill="#eef1f4" fill-opacity="0.92"/>'
            )
            segment_cursor = mix_bar_x
            positive_segments = [segment for segment in mix_stats["segments"] if float(segment["pct"]) > 0.0]
            total_mix_pct = sum(float(segment["pct"]) for segment in positive_segments) or 100.0
            for segment_index, segment in enumerate(positive_segments):
                remaining = (mix_bar_x + mix_bar_width) - segment_cursor
                if remaining <= 0.0:
                    break
                if segment_index == len(positive_segments) - 1:
                    segment_width = remaining
                else:
                    segment_width = max(2.0, mix_bar_width * (float(segment["pct"]) / total_mix_pct))
                    segment_width = min(segment_width, remaining)
                svg_parts.append(
                    f'<rect x="{segment_cursor:.1f}" y="{mix_bar_y:.1f}" width="{segment_width:.1f}" height="{mix_bar_height:.1f}" rx="{mix_bar_height / 2.0:.1f}" ry="{mix_bar_height / 2.0:.1f}" fill="{segment["fill"]}" fill-opacity="0.96"/>'
                )
                segment_cursor += segment_width
            svg_parts.append("</g>")

        svg_parts.append("</svg>")
        return (
            f'<div class="crpm-workflow-board crpm-workflow-board--horizontal" '
            f'data-density-profile="{escape(str(profile["name"]))}" '
            f'data-fit-mode="{escape(fit_mode)}">{"".join(svg_parts)}</div>'
        )

    board_width = 1180
    center_x = board_width / 2
    lane_x = {
        "left": center_x - 285,
        "center": center_x,
        "right": center_x + 285,
    }
    mainline_width = 424.0
    branch_width = 208.0
    mainline_height = 110.0
    branch_height = 64.0
    top_margin = 44
    step_gap = 194
    branch_gap = 82
    lens_value = str(payload.get("conformance_lens", "% of paths")) if isinstance(payload, Mapping) else "% of paths"
    lens_is_activity = "activit" in lens_value.lower()
    lens_is_paths = not lens_is_activity

    step_groups: dict[int, list[pd.Series]] = defaultdict(list)
    for _, row in ordered_nodes.iterrows():
        step_groups[_workflow_layout_step_rank(row.get("step_rank", 999))].append(row)

    nodes_layout: list[dict[str, Any]] = []
    center_step = max(1.0, (len(step_groups) - 1) / 2.0)
    for step_index, step_rank in enumerate(sorted(step_groups)):
        rows = sorted(
            step_groups[step_rank],
            key=lambda row: (
                0 if str(row.get("branch_role", "mainline")) == "mainline" else 1,
                -_safe_int(row.get("cases", 0)),
                str(row.get("display_name", row.get("activity", ""))),
            ),
        )
        mainline_rows = [row for row in rows if str(row.get("branch_role", "mainline")) == "mainline"]
        branch_rows = [row for row in rows if str(row.get("branch_role", "mainline")) != "mainline"]
        base_y = top_margin + step_index * step_gap
        wobble = math.sin(step_index * 0.86) * (28.0 if lens_is_paths else 20.0)
        drift = (step_index - center_step) * (2.0 if lens_is_paths else 1.2)
        x_center = center_x + wobble + drift

        for main_index, row in enumerate(mainline_rows):
            activity = str(row.get("activity", row.get("display_name", f"node-{step_rank}-{main_index}")))
            nodes_layout.append(
                {
                    "row": row,
                    "index": len(nodes_layout),
                    "activity": activity,
                    "x": x_center - mainline_width / 2,
                    "y": base_y + (main_index * 12.0),
                    "width": mainline_width,
                    "height": mainline_height,
                }
            )

        for branch_index, row in enumerate(branch_rows):
            activity = str(row.get("activity", row.get("display_name", f"branch-{step_rank}-{branch_index}")))
            lane = str(row.get("lane", "left") or "left").lower()
            x = (x_center + 320.0) if lane == "right" else (x_center - 320.0)
            nodes_layout.append(
                {
                    "row": row,
                    "index": len(nodes_layout),
                    "activity": activity,
                    "x": x - branch_width / 2,
                    "y": base_y + 56 + branch_index * branch_gap,
                    "width": branch_width,
                    "height": branch_height,
                }
            )

    board_height = int(max((item["y"] + item["height"] for item in nodes_layout), default=top_margin + 120) + 72)

    node_positions = {str(item["activity"]): item for item in nodes_layout}
    edge_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edge_records = []
    for _, row in normalized_edges.iterrows():
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if source not in node_positions or target not in node_positions:
            continue
        edge_groups[source].append({"source": source, "target": target, "row": row})

    for source, group in edge_groups.items():
        group.sort(
            key=lambda item: (
                node_positions[item["target"]]["index"],
                -_safe_int(item["row"].get("frequency", 0)),
                item["target"],
            )
        )
        for lane_index, item in enumerate(group):
            item["lane_index"] = lane_index
            edge_records.append(item)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {board_width} {board_height}" width="100%" height="100%" style="display:block;width:100%;height:auto;" role="img" aria-label="Workflow conformance board">',
        "<defs>",
        '<linearGradient id="workflow-bg" x1="0" y1="0" x2="0" y2="1">',
        '<stop offset="0%" stop-color="#ffffff"/>',
        '<stop offset="100%" stop-color="#faf7fd"/>',
        "</linearGradient>",
        '<filter id="workflow-shadow" x="-20%" y="-20%" width="160%" height="160%">',
        '<feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#433655" flood-opacity="0.12"/>',
        "</filter>",
        '<marker id="workflow-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto" markerUnits="strokeWidth">',
        '<path d="M 0 0 L 7 3.5 L 0 7 z" fill="#51645a"/>',
        "</marker>",
        "</defs>",
        '<rect x="0" y="0" width="100%" height="100%" fill="url(#workflow-bg)"/>',
        f'<line x1="{lane_x["center"]:.1f}" y1="{top_margin - 6}" x2="{lane_x["center"]:.1f}" y2="{board_height - 30}" stroke="#c4bacf" stroke-width="3.2" stroke-dasharray="6 7"/>',
        f'<line x1="{lane_x["left"]:.1f}" y1="{top_margin + 12}" x2="{lane_x["left"]:.1f}" y2="{board_height - 42}" stroke="#d7cfdf" stroke-width="1.1" stroke-dasharray="4 10"/>',
        f'<line x1="{lane_x["right"]:.1f}" y1="{top_margin + 12}" x2="{lane_x["right"]:.1f}" y2="{board_height - 42}" stroke="#d7cfdf" stroke-width="1.1" stroke-dasharray="4 10"/>',
    ]

    max_frequency = max((_safe_int(row.get("frequency", 0)) for _, row in normalized_edges.iterrows()), default=0)
    for item in edge_records:
        row = item["row"]
        source_layout = node_positions[item["source"]]
        target_layout = node_positions[item["target"]]
        lane_index = item["lane_index"]
        severity = str(row.get("severity", "Low"))
        palette = _WORKFLOW_SEVERITY_THEME.get(severity, _WORKFLOW_SEVERITY_THEME["Low"])
        freq = _safe_int(row.get("frequency", 0))
        median_days = _safe_float(row.get("median_days"))
        source_x = source_layout["x"] + source_layout["width"] / 2
        source_y = source_layout["y"] + source_layout["height"]
        target_x = target_layout["x"] + target_layout["width"] / 2
        target_y = target_layout["y"]
        source_lane = str(source_layout["row"].get("lane", "center") or "center").lower()
        target_lane = str(target_layout["row"].get("lane", "center") or "center").lower()

        if source_layout["row"].get("activity") == target_layout["row"].get("activity"):
            loop_x = center_x + (160 if source_lane != "left" else -160) + lane_index * 18
            loop_y = source_layout["y"] + source_layout["height"] / 2
            path = (
                f"M {source_x:.1f} {loop_y:.1f} "
                f"C {loop_x:.1f} {loop_y - 58:.1f}, {loop_x + 10:.1f} {loop_y + 32:.1f}, {source_x + 16:.1f} {loop_y + 16:.1f} "
                f"C {source_x + 28:.1f} {loop_y + 10:.1f}, {source_x + 30:.1f} {loop_y + 4:.1f}, {source_x:.1f} {loop_y:.1f}"
            )
            label_x = loop_x + 16
            label_y = loop_y - 4
        else:
            control_offset = 44.0 if str(row.get("branch_role", "mainline")) == "mainline" else 68.0
            bend_x = (source_x + target_x) / 2
            if source_lane == "left" or target_lane == "left":
                bend_x = min(bend_x, center_x - 72 - lane_index * 10)
            if source_lane == "right" or target_lane == "right":
                bend_x = max(bend_x, center_x + 72 + lane_index * 10)
            path = (
                f"M {source_x:.1f} {source_y:.1f} "
                f"C {source_x:.1f} {source_y + control_offset:.1f}, {bend_x:.1f} {((source_y + target_y) / 2) - 28:.1f}, {bend_x:.1f} {((source_y + target_y) / 2):.1f} "
                f"C {bend_x:.1f} {((source_y + target_y) / 2) + 28:.1f}, {target_x:.1f} {target_y - control_offset:.1f}, {target_x:.1f} {target_y:.1f}"
            )
            label_x = bend_x
            label_y = ((source_y + target_y) / 2) - 14 - lane_index * 2

        is_deviating = bool(row.get("is_deviating")) or str(row.get("stroke_style", "")).lower() == "dashed"
        dash = ' stroke-dasharray="9 6"' if is_deviating else ""
        is_mainline_edge = str(row.get("branch_role", "mainline")) == "mainline"
        opacity = "0.94" if is_mainline_edge else "0.66"
        stroke_width = (2.2 if is_mainline_edge else 1.35) + min(freq / 32000.0, 2.8 if is_mainline_edge else 1.15)
        conf_bucket = str(row.get("conformance_bucket", "Conformant"))
        conf_theme = _WORKFLOW_CONFORMANCE_THEME.get(conf_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
        show_label = is_mainline_edge and freq >= max(220, int(max_frequency * 0.6))

        edge_id = str(row.get("edge_id", f"{item['source']} -> {item['target']}"))
        svg_parts.append(
            f'<path d="{path}" fill="none" stroke="{palette["stroke"]}" stroke-width="{stroke_width:.1f}" stroke-linecap="round"{dash} opacity="{opacity}" marker-end="url(#workflow-arrow)" data-edge-id="{escape(edge_id)}" data-edge-role="{escape(str(row.get("edge_type", "expected")))}"/>'
        )
        if show_label:
            edge_label = [f"{freq:,} cases" if freq else "0 cases"]
            if median_days is not None and freq >= 200:
                edge_label.append(f"{median_days:.1f} d")
            text_lines = _workflow_text_lines(edge_label, max_chars=14)
            label_width = max(76, min(132, max((len(line) for line in edge_label), default=8) * 7 + 14))
            label_height = 18 + max(0, len(text_lines) - 1) * 12 + 8
            svg_parts.append(
                f'<g transform="translate({label_x:.1f},{label_y:.1f})">'
                f'<rect x="{-label_width / 2:.1f}" y="{-label_height / 2:.1f}" width="{label_width:.1f}" height="{label_height:.1f}" rx="8" ry="8" fill="#ffffff" fill-opacity="0.93" stroke="{conf_theme["stroke"]}" stroke-width="0.8"/>'
            )
            for line_index, line in enumerate(text_lines):
                dy = -3 + line_index * 12 if len(text_lines) > 1 else 4
                weight = "700" if line_index == 0 else "500"
                size = 11 if line_index == 0 else 9
                svg_parts.append(
                    f'<text x="0" y="{dy}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="#20312a">{escape(line)}</text>'
                )
            svg_parts.append("</g>")

    if not edge_records:
        svg_parts.append(
            f'<text x="{center_x:.1f}" y="{top_margin + 36:.1f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#5d6a63">No transition links were available for the current selection.</text>'
        )

    for item in nodes_layout:
        row = item["row"]
        severity = str(row.get("severity", "Low"))
        palette = _WORKFLOW_SEVERITY_THEME.get(severity, _WORKFLOW_SEVERITY_THEME["Low"])
        title = str(row.get("display_name") or row.get("business_label") or row.get("activity") or "Node")
        cases = _safe_int(row.get("cases", 0))
        median_delay = _safe_float(row.get("median_next_delay_days"))
        conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
        conformance_theme = _WORKFLOW_CONFORMANCE_THEME.get(conformance_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
        branch_role = str(row.get("branch_role", "mainline"))
        header_lines = _workflow_text_lines([title], max_chars=34)
        detail_lines = (
            [
                f"{cases:,} cases" if cases else "0 cases",
                f"{median_delay:.1f} d median" if median_delay is not None else "Delay n/a",
            ]
            if branch_role == "mainline"
            else [
                f"{cases:,} cases" if cases else "0 cases",
            ]
        )
        chip_label = conformance_bucket if conformance_bucket != "Conformant" else severity
        title_size = 15 if branch_role == "mainline" else 13
        detail_size = 11 if branch_role == "mainline" else 10
        svg_parts.append(
            f'<g filter="url(#workflow-shadow)" data-activity="{escape(str(row.get("activity", title)))}" data-branch-role="{escape(branch_role)}" data-lane="{escape(str(row.get("lane", "center")))}" data-node-type="{escape(str(row.get("node_type", "mainline")))}">'
            f'<rect x="{item["x"]:.1f}" y="{item["y"]:.1f}" width="{item["width"]:.1f}" height="{item["height"]:.1f}" rx="16" ry="16" fill="{palette["fill"]}" stroke="{palette["stroke"]}" stroke-width="2.2"/>'
            f'<rect x="{item["x"]:.1f}" y="{item["y"]:.1f}" width="{item["width"]:.1f}" height="11" rx="16" ry="16" fill="{conformance_theme["fill"]}" fill-opacity="0.95"/>'
            f'<rect x="{item["x"] + item["width"] - 110:.1f}" y="{item["y"] + 15:.1f}" width="94" height="24" rx="12" ry="12" fill="{palette["stroke"]}" />'
            f'<text x="{item["x"] + item["width"] - 63:.1f}" y="{item["y"] + 31:.1f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="700" fill="#ffffff">{escape(chip_label)}</text>'
        )
        title_y = item["y"] + 33
        for line_index, line in enumerate(header_lines):
            svg_parts.append(
                f'<text x="{item["x"] + 16:.1f}" y="{title_y + line_index * 16:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="{title_size}" font-weight="700" fill="{palette["ink"]}">{escape(line)}</text>'
            )
        detail_start = title_y + max(len(header_lines), 1) * 16 + 7
        for line_index, line in enumerate(detail_lines):
            svg_parts.append(
                f'<text x="{item["x"] + 16:.1f}" y="{detail_start + line_index * 15:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="{detail_size}" fill="{palette["ink"]}" fill-opacity="0.88">{escape(line)}</text>'
            )
        svg_parts.append("</g>")

    svg_parts.append("</svg>")
    return f'<div class="crpm-workflow-board crpm-workflow-board--vertical">{"".join(svg_parts)}</div>'


def filter_workflow_payload(
    payload: Mapping[str, Any] | pd.DataFrame | None,
    *,
    coverage_view: str = "all",
    deviation_view: str = "all",
    detail_level: str = "analyst",
) -> dict[str, Any]:
    """Filter a workflow payload for view-specific coverage and deviation focus."""
    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, None)
    trace_profiles_df = _ensure_workflow_df(payload.get("trace_profiles")) if isinstance(payload, Mapping) else pd.DataFrame()
    ordered_nodes = _order_workflow_nodes(nodes_df)
    normalized_edges = _normalize_workflow_edges(edges_df, ordered_nodes)

    coverage_key = str(coverage_view or "all").lower()
    deviation_key = str(deviation_view or "all").lower()
    allowed_groups = {
        "dominant": {"dominant"},
        "mixed": {"mixed"},
        "rare": {"rare"},
        "all": {"dominant", "mixed", "rare"},
    }.get(coverage_key, {"dominant", "mixed", "rare"})
    allowed_buckets = {
        "all": {"Conformant", "Log deviation", "Model deviation"},
        "conformant": {"Conformant"},
        "log deviations": {"Log deviation"},
        "model deviations": {"Model deviation"},
    }.get(deviation_key, {"Conformant", "Log deviation", "Model deviation"})

    if not normalized_edges.empty:
        normalized_edges = normalized_edges[
            normalized_edges.get("coverage_group", pd.Series(["dominant"] * len(normalized_edges)))
            .astype(str)
            .str.lower()
            .isin(allowed_groups)
        ]
        normalized_edges = normalized_edges[
            normalized_edges.get("conformance_bucket", pd.Series(["Conformant"] * len(normalized_edges))).astype(str).isin(allowed_buckets)
        ].copy()

    active_nodes: set[str] = set()
    if not normalized_edges.empty:
        active_nodes.update(normalized_edges["source"].astype(str).tolist())
        active_nodes.update(normalized_edges["target"].astype(str).tolist())

    if not ordered_nodes.empty:
        node_groups = ordered_nodes.get("coverage_group", pd.Series(["dominant"] * len(ordered_nodes))).astype(str).str.lower()
        node_buckets = ordered_nodes.get("conformance_bucket", pd.Series(["Conformant"] * len(ordered_nodes))).astype(str)
        ordered_nodes = ordered_nodes[node_groups.isin(allowed_groups) & node_buckets.isin(allowed_buckets)].copy()

    detail_key = str(detail_level or "analyst").lower()
    if detail_key == "executive":
        if not ordered_nodes.empty:
            branch_roles = (
                ordered_nodes["branch_role"].astype(str)
                if "branch_role" in ordered_nodes.columns
                else pd.Series(["mainline"] * len(ordered_nodes), index=ordered_nodes.index)
            )
            ordered_nodes = ordered_nodes.loc[branch_roles.eq("mainline")].copy()
            active_nodes = set(ordered_nodes["activity"].astype(str).tolist())
        if not normalized_edges.empty and active_nodes:
            normalized_edges = normalized_edges[
                normalized_edges["source"].astype(str).isin(active_nodes) & normalized_edges["target"].astype(str).isin(active_nodes)
            ].copy()
    elif detail_key == "analyst":
        if not normalized_edges.empty:
            selected_edge_uid = str(payload.get("selected_edge_uid") or "") if isinstance(payload, Mapping) else ""
            normalized_edges = _select_analyst_workflow_edges(normalized_edges, selected_edge_uid=selected_edge_uid, limit=18)
        if not ordered_nodes.empty and not normalized_edges.empty:
            active_nodes = set(normalized_edges["source"].astype(str).tolist()) | set(normalized_edges["target"].astype(str).tolist())
            deviation_nodes = set(
                ordered_nodes.loc[
                    ordered_nodes.get("conformance_bucket", pd.Series(["Conformant"] * len(ordered_nodes))).astype(str).ne("Conformant"),
                    "activity",
                ].astype(str)
            )
            ordered_nodes = ordered_nodes[ordered_nodes["activity"].astype(str).isin(active_nodes | deviation_nodes)].copy()

    if ordered_nodes.empty and not normalized_edges.empty:
        ordered_nodes = _derive_nodes_from_edges(normalized_edges)

    if coverage_key != "all" and ordered_nodes.empty and normalized_edges.empty:
        fallback = filter_workflow_payload(
            payload,
            coverage_view="all",
            deviation_view=deviation_view,
            detail_level=detail_level,
        )
        if isinstance(fallback, dict):
            fallback = dict(fallback)
            fallback["requested_coverage_view"] = coverage_key
            fallback["applied_coverage_view"] = "all"
        return fallback

    visible_node_ids = set(ordered_nodes.get("activity", pd.Series(dtype=str)).astype(str).tolist())
    visible_edge_ids = set(normalized_edges.get("edge_id", pd.Series(dtype=str)).astype(str).tolist())
    visible_edge_ids.update(normalized_edges.get("edge_uid", pd.Series(dtype=str)).astype(str).tolist())
    filtered_trace_profiles = _filter_workflow_trace_profiles(
        trace_profiles_df,
        visible_node_ids=visible_node_ids,
        visible_edge_ids=visible_edge_ids,
    )
    filtered_summary = _workflow_view_summary(
        payload.get("summary", {}) if isinstance(payload, Mapping) else {},
        ordered_nodes,
        normalized_edges,
        filtered_trace_profiles,
    )
    renderer_role = str(payload.get("renderer_role") or "conformance_explorer") if isinstance(payload, Mapping) else "conformance_explorer"
    local_focus_hint = (
        str(payload.get("local_focus_hint"))
        if isinstance(payload, Mapping) and payload.get("local_focus_hint")
        else "Local graph focus stays inside the frame; use Pinned exact metrics to persist node or transition metrics."
    )
    visible_case_count = _safe_int(filtered_summary.get("visible_case_count", filtered_summary.get("cases_covered", 0)))
    excluded_case_count = _safe_int(filtered_summary.get("excluded_case_count", 0))
    path_denominator = _safe_int(filtered_summary.get("path_denominator", visible_case_count))
    activity_denominator = _safe_int(filtered_summary.get("activity_denominator", 0))

    return {
        "nodes": ordered_nodes.reset_index(drop=True),
        "edges": normalized_edges.reset_index(drop=True),
        "legend": legend_df.copy(),
        "trace_profiles": filtered_trace_profiles.reset_index(drop=True),
        "overall_median_delay_days": overall_median,
        "summary": filtered_summary,
        "visible_case_count": visible_case_count,
        "excluded_case_count": excluded_case_count,
        "path_denominator": path_denominator,
        "activity_denominator": activity_denominator,
        "selected_node_id": payload.get("selected_node_id") if isinstance(payload, Mapping) else None,
        "selected_edge_uid": payload.get("selected_edge_uid") if isinstance(payload, Mapping) else None,
        "local_focus_hint": local_focus_hint,
        "renderer_role": renderer_role,
        "process_map_payload": _workflow_process_map_payload(
            nodes_df=ordered_nodes.reset_index(drop=True),
            edges_df=normalized_edges.reset_index(drop=True),
            legend_df=legend_df.copy(),
            trace_profiles_df=filtered_trace_profiles.reset_index(drop=True),
            summary=filtered_summary,
            renderer_role=renderer_role,
            selected_node_id=payload.get("selected_node_id") if isinstance(payload, Mapping) else None,
            selected_edge_uid=payload.get("selected_edge_uid") if isinstance(payload, Mapping) else None,
        ),
        "renderer_capabilities": dict(payload.get("renderer_capabilities", {})) if isinstance(payload, Mapping) else {},
        "detail_level": detail_key,
        "requested_coverage_view": coverage_key,
        "applied_coverage_view": coverage_key,
    }


def _workflow_process_map_payload(
    *,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    legend_df: pd.DataFrame,
    trace_profiles_df: pd.DataFrame,
    summary: Mapping[str, Any],
    renderer_role: str,
    selected_node_id: Any = None,
    selected_edge_uid: Any = None,
) -> dict[str, Any]:
    visible_case_count = _safe_int(summary.get("visible_case_count", summary.get("cases_covered", 0)))
    excluded_case_count = _safe_int(summary.get("excluded_case_count", 0))
    return {
        "renderer_role": renderer_role,
        "nodes": nodes_df,
        "edges": edges_df,
        "legend": legend_df,
        "trace_profiles": trace_profiles_df,
        "summary": dict(summary),
        "denominators": {
            "visible_case_count": visible_case_count,
            "excluded_case_count": excluded_case_count,
            "path_denominator": _safe_int(summary.get("path_denominator", visible_case_count)),
            "activity_denominator": _safe_int(summary.get("activity_denominator", 0)),
            "transition_denominator": _safe_int(summary.get("transition_denominator", 0)),
        },
        "selection": {
            "selected_node_id": str(selected_node_id) if selected_node_id else None,
            "selected_edge_uid": str(selected_edge_uid) if selected_edge_uid else None,
        },
    }


def _filter_workflow_trace_profiles(
    trace_profiles_df: pd.DataFrame,
    *,
    visible_node_ids: set[str],
    visible_edge_ids: set[str],
) -> pd.DataFrame:
    if trace_profiles_df.empty:
        return trace_profiles_df.copy()
    if not visible_node_ids and not visible_edge_ids:
        return trace_profiles_df.iloc[0:0].copy()

    def _matches(row: pd.Series) -> bool:
        node_ids = {str(value) for value in row.get("node_ids", []) if value}
        edge_ids = {str(value) for value in row.get("edge_ids", []) if value}
        edge_uids = {str(value) for value in row.get("edge_uids", []) if value}
        return bool(node_ids & visible_node_ids) or bool((edge_ids | edge_uids) & visible_edge_ids)

    return trace_profiles_df[trace_profiles_df.apply(_matches, axis=1)].copy()


def _workflow_view_summary(
    base_summary: Mapping[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    trace_profiles_df: pd.DataFrame,
) -> dict[str, Any]:
    base_case_count = _safe_int(base_summary.get("visible_case_count", base_summary.get("cases_covered", 0)))
    if base_case_count <= 0:
        base_case_count = _safe_int(base_summary.get("path_denominator", 0))
    path_denominator = _safe_int(base_summary.get("path_denominator", base_case_count))
    activity_denominator = _safe_int(base_summary.get("activity_denominator", 0))
    transition_denominator = _safe_int(base_summary.get("transition_denominator", 0))
    path_denominator_label = str(base_summary.get("path_denominator_label", "cases in evaluation log"))
    activity_denominator_label = str(base_summary.get("activity_denominator_label", "events in evaluation log"))
    transition_denominator_label = str(base_summary.get("transition_denominator_label", "observed transitions in evaluation log"))
    if trace_profiles_df.empty:
        events_covered = int(nodes_df.get("occurrences", pd.Series(dtype=float)).fillna(0).sum()) if not nodes_df.empty else 0
        return {
            "cases_covered": 0,
            "events_covered": events_covered,
            "visible_case_count": 0,
            "excluded_case_count": max(base_case_count, 0),
            "path_denominator": path_denominator,
            "path_denominator_label": path_denominator_label,
            "activity_denominator": activity_denominator,
            "activity_denominator_label": activity_denominator_label,
            "transition_denominator": transition_denominator,
            "transition_denominator_label": transition_denominator_label,
            "dominant_path_share": 0.0,
            "deviation_share": 0.0,
            "log_deviation_share": 0.0,
            "model_deviation_share": 0.0,
            "median_throughput_days": None,
            "visible_nodes": int(len(nodes_df.index)),
            "visible_edges": int(len(edges_df.index)),
        }

    dominant_variant_share = 0.0
    if "variant_signature" in trace_profiles_df.columns:
        dominant_variant_counts = trace_profiles_df["variant_signature"].astype(str).value_counts()
        if not dominant_variant_counts.empty:
            dominant_variant_share = round(float(dominant_variant_counts.iloc[0]) / float(len(trace_profiles_df.index)) * 100, 1)

    throughput_series = (
        pd.to_numeric(trace_profiles_df.get("throughput_days", pd.Series(dtype=float)), errors="coerce").dropna()
        if "throughput_days" in trace_profiles_df.columns
        else pd.Series(dtype=float)
    )
    deviation_share = 0.0
    if "has_deviation" in trace_profiles_df.columns:
        deviation_share = round(float(trace_profiles_df["has_deviation"].astype(bool).mean()) * 100, 1)

    visible_case_count = int(len(trace_profiles_df.index))
    events_covered = int(pd.to_numeric(trace_profiles_df.get("event_count", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    log_deviation_share = 0.0
    if "has_log_deviation" in trace_profiles_df.columns:
        log_deviation_share = round(float(trace_profiles_df["has_log_deviation"].astype(bool).mean()) * 100, 1)
    model_deviation_share = 0.0
    if "has_model_deviation" in trace_profiles_df.columns:
        model_deviation_share = round(float(trace_profiles_df["has_model_deviation"].astype(bool).mean()) * 100, 1)

    return {
        "cases_covered": visible_case_count,
        "events_covered": events_covered,
        "visible_case_count": visible_case_count,
        "excluded_case_count": max(base_case_count - visible_case_count, 0),
        "path_denominator": path_denominator,
        "path_denominator_label": path_denominator_label,
        "activity_denominator": activity_denominator,
        "activity_denominator_label": activity_denominator_label,
        "transition_denominator": transition_denominator,
        "transition_denominator_label": transition_denominator_label,
        "dominant_path_share": dominant_variant_share,
        "deviation_share": deviation_share,
        "log_deviation_share": log_deviation_share,
        "model_deviation_share": model_deviation_share,
        "median_throughput_days": (
            round(float(throughput_series.median()), 1) if not throughput_series.empty else base_summary.get("median_throughput_days")
        ),
        "visible_nodes": int(len(nodes_df.index)),
        "visible_edges": int(len(edges_df.index)),
    }


def _workflow_layout_step_rank(value: Any) -> int:
    from crpm.screening import STEP_ORDER

    if value is None or pd.isna(value):
        return len(STEP_ORDER)
    return max(0, min(_safe_int(value), len(STEP_ORDER)))


def _workflow_primary_path_nodes(node_items: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Pick one dominant path node per step for anchors/backbone when mainline tags are absent."""
    if not node_items:
        return []

    explicit_mainline = [node for node in node_items if str(node.get("branch_role", "")).lower() == "mainline"]
    if explicit_mainline:
        return sorted(
            explicit_mainline,
            key=lambda node: (float(node.get("center_y", 0.0)), -_safe_int(node.get("cases", 0))),
        )

    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for node in node_items:
        grouped[_safe_int(node.get("step_rank", 999))].append(node)

    primary_nodes: list[Mapping[str, Any]] = []
    for step_rank in sorted(grouped):
        candidates = grouped[step_rank]
        preferred_candidates = [node for node in candidates if str(node.get("lane_position", "")).lower() in {"mainline", "left", "center"}]
        usable_candidates = preferred_candidates or ([] if primary_nodes else candidates)
        if not usable_candidates:
            continue
        usable_candidates.sort(
            key=lambda node: (
                0 if str(node.get("lane_position", "")).lower() in {"mainline", "left", "center"} else 1,
                -_safe_int(node.get("cases", 0)),
                float(node.get("center_y", 0.0)),
            )
        )
        primary_nodes.append(usable_candidates[0])
    return primary_nodes


def create_workflow_interactive_payload(
    payload: Mapping[str, Any] | pd.DataFrame | None,
    *,
    metric_coloring: str = "Conformance bucket",
    detail_level: str = "analyst",
    selected_node_id: Optional[str] = None,
    selected_edge_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a process-map explorer payload from the canonical workflow payload."""
    detail_level = str(detail_level or "analyst").lower()
    payload_mapping = payload if isinstance(payload, Mapping) else {}
    payload_summary = payload_mapping.get("summary", {}) if isinstance(payload_mapping.get("summary"), Mapping) else {}

    def _metadata_int(key: str, fallback: int = 0) -> int:
        for source in (payload_mapping, payload_summary):
            if key not in source:
                continue
            value = source.get(key)
            if value is not None:
                return _safe_int(value)
        return int(fallback)

    visible_case_count = _metadata_int("visible_case_count", _metadata_int("cases_covered", 0))
    excluded_case_count = _metadata_int("excluded_case_count", 0)
    path_denominator = _metadata_int("path_denominator", visible_case_count)
    activity_denominator = _metadata_int("activity_denominator", 0)
    transition_denominator = _metadata_int("transition_denominator", 0)
    renderer_role = str(payload_mapping.get("renderer_role") or "conformance_explorer")
    local_focus_hint = str(
        payload_mapping.get("local_focus_hint")
        or "Local graph focus stays inside the frame; use Pinned exact metrics to persist node or transition metrics."
    )
    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, None)
    ordered_nodes = _aggregate_explorer_nodes(_order_workflow_nodes(nodes_df))
    normalized_edges = _aggregate_explorer_edges(_normalize_workflow_edges(edges_df, ordered_nodes), ordered_nodes)

    if ordered_nodes.empty and normalized_edges.empty:
        return {
            "nodes": [],
            "edges": [],
            "legend": legend_df,
            "height": 520,
            "frame_height": 648,
            "width": 760,
            "content_offset_x": 0.0,
            "content_offset_y": 0.0,
            "overall_median_delay_days": overall_median,
            "content_bounds": {"min_x": 0.0, "min_y": 0.0, "max_x": 760.0, "max_y": 520.0},
            "anchor_bounds": {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0},
            "drawable_bounds": {"min_x": 12.0, "min_y": 12.0, "max_x": 748.0, "max_y": 508.0},
            "fit_padding": {"top": 14.0, "right": 12.0, "bottom": 30.0, "left": 12.0},
            "toolbar_height_hint": 116,
            "selected_node_id": str(selected_node_id) if selected_node_id else None,
            "selected_edge_id": str(selected_edge_id) if selected_edge_id else None,
            "selected_edge_uid": str(selected_edge_id) if selected_edge_id else None,
            "visible_case_count": visible_case_count,
            "excluded_case_count": excluded_case_count,
            "path_denominator": path_denominator,
            "activity_denominator": activity_denominator,
            "transition_denominator": transition_denominator,
            "local_focus_hint": local_focus_hint,
            "renderer_role": renderer_role,
        }
    if ordered_nodes.empty and not normalized_edges.empty:
        ordered_nodes = _derive_nodes_from_edges(normalized_edges)

    selected_node = str(selected_node_id) if selected_node_id else None
    selected_edge = str(selected_edge_id) if selected_edge_id else None
    node_neighbors: dict[str, set[str]] = {
        str(row.get("activity", "")): set(str(value) for value in row.get("neighbor_ids", []) if value)
        for _, row in ordered_nodes.iterrows()
    }

    step_groups: dict[int, list[pd.Series]] = defaultdict(list)
    for _, row in ordered_nodes.iterrows():
        step_groups[_workflow_layout_step_rank(row.get("step_rank", 999))].append(row)

    sorted_steps = sorted(step_groups)
    lens_value = str(payload.get("conformance_lens", "% of paths")) if isinstance(payload, Mapping) else "% of paths"
    lens_is_activity = "activit" in lens_value.lower()
    lens_is_paths = not lens_is_activity

    max_top_branches = 0
    max_bottom_branches = 0
    for rows in step_groups.values():
        top_count = 0
        bottom_count = 0
        for row in rows:
            lane = str(row.get("lane", "center") or "center").lower()
            branch_role = str(row.get("branch_role", "mainline"))
            if branch_role == "mainline":
                continue
            if lane == "right":
                bottom_count += 1
            else:
                top_count += 1
        max_top_branches = max(max_top_branches, top_count)
        max_bottom_branches = max(max_bottom_branches, bottom_count)

    has_top_branches = max_top_branches > 0
    has_bottom_branches = max_bottom_branches > 0
    max_branch_depth = max(max_top_branches, max_bottom_branches)
    max_edge_fanout = _workflow_max_edge_fanout(normalized_edges)
    render_profile = _workflow_vertical_layout_profile(
        step_count=len(sorted_steps),
        max_branch_depth=max_branch_depth,
        max_edge_fanout=max_edge_fanout,
        detail_level=detail_level,
        lens_is_paths=lens_is_paths,
    )

    def _build_node_layout(
        active_profile: Mapping[str, Any], *, extra_step_gap: float = 0.0
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], int, int, float]:
        step_gap = float(active_profile["step_gap"]) + extra_step_gap
        top_margin = float(active_profile["top_margin"])
        side_margin = float(active_profile["side_margin"])
        mainline_width = float(active_profile["mainline_width"])
        vertical_gap = float(active_profile["vertical_gap"])
        lane_gap = float(active_profile["lane_gap"])
        min_canvas_width = 680.0 if (has_top_branches or has_bottom_branches) else 620.0
        canvas_width_local = int(
            max(
                min_canvas_width,
                side_margin * 2.0
                + float(active_profile["mainline_width_max"])
                + (
                    (float(active_profile["branch_width_max"]) + lane_gap + 18.0) * 2.0
                    if (has_top_branches or has_bottom_branches)
                    else 0.0
                ),
            )
        )
        canvas_height_local = int(
            top_margin
            + max(1, len(sorted_steps) - 1) * step_gap
            + float(active_profile["mainline_min_height"])
            + max(max_top_branches, max_bottom_branches) * (float(active_profile["branch_min_height"]) + vertical_gap)
            + 96.0
        )
        center_x_local = canvas_width_local / 2.0
        center_step = (len(sorted_steps) - 1) / 2.0 if sorted_steps else 0.0
        local_nodes: list[dict[str, Any]] = []
        local_map: dict[str, dict[str, Any]] = {}
        for step_index, step_rank in enumerate(sorted_steps):
            y_center = top_margin + step_index * step_gap
            spine_phase = step_index - center_step
            x_center = center_x_local + (
                math.sin(spine_phase * 1.04) * float(active_profile["wobble"])
                + math.cos((spine_phase + 0.35) * 0.78) * float(active_profile["sway"])
                + spine_phase * float(active_profile["drift"])
            )
            rows = sorted(
                step_groups[step_rank],
                key=lambda row: (
                    0 if str(row.get("branch_role", "mainline")) == "mainline" else 1,
                    -_safe_int(row.get("cases", 0)),
                    str(row.get("display_name", row.get("activity", ""))),
                ),
            )
            mainline_rows = [row for row in rows if str(row.get("branch_role", "mainline")) == "mainline"]
            top_rows = [
                row
                for row in rows
                if str(row.get("branch_role", "mainline")) != "mainline" and str(row.get("lane", "left") or "left").lower() != "right"
            ]
            bottom_rows = [
                row
                for row in rows
                if str(row.get("branch_role", "mainline")) != "mainline" and str(row.get("lane", "left") or "left").lower() == "right"
            ]
            for main_index, row in enumerate(mainline_rows):
                activity = str(row.get("activity", f"node-{step_rank}-{main_index}"))
                palette = _workflow_metric_palette(row, metric_coloring, item_kind="node")
                is_neighbor = bool(selected_node and activity in node_neighbors.get(selected_node, set()))
                is_selected = activity == selected_node
                mix_stats = _workflow_node_mix_stats(row)
                content_layout = _workflow_prepare_explorer_node_content(
                    row,
                    branch_role="mainline",
                    detail_level=detail_level,
                    profile=active_profile,
                )
                width = float(content_layout["width"])
                height = float(content_layout["height"])
                preferred_x = x_center - width / 2.0
                y = y_center - height / 2.0 + main_index * 8.0
                node_item = {
                    "id": activity,
                    "business_label": _workflow_business_label(row),
                    "display_name": _workflow_display_name(row),
                    "cases": _safe_int(row.get("cases", 0)),
                    "occurrences": _safe_int(row.get("occurrences", 0)),
                    "path_pct": _safe_float(row.get("coverage_pct")),
                    "activity_pct": _safe_float(row.get("activity_pct")),
                    "median_days": _safe_float(row.get("median_next_delay_days")),
                    "p90_days": _safe_float(row.get("p90_next_delay_days")),
                    "severity": str(row.get("severity", "Low")),
                    "conformance_bucket": str(row.get("conformance_bucket", "Conformant")),
                    "branch_role": "mainline",
                    "lane_position": "mainline",
                    "step_rank": step_rank,
                    "x": preferred_x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "center_x": preferred_x + width / 2.0,
                    "center_y": y + height / 2.0,
                    "preferred_x": preferred_x,
                    "preferred_y": y,
                    "preferred_center_x": x_center,
                    "preferred_center_y": y_center,
                    "surface_fill": palette["surface"],
                    "stroke": palette["stroke"],
                    "ink": palette["ink"],
                    "accent": palette["accent"],
                    "accent_fill": palette["fill"],
                    "chip_fill": palette["chip_fill"],
                    "chip_ink": palette["chip_ink"],
                    "selected": is_selected,
                    "neighbor": is_neighbor,
                    "sync_cases": mix_stats["sync_cases"],
                    "log_move_cases": mix_stats["log_move_cases"],
                    "model_move_cases": mix_stats["model_move_cases"],
                    "sync_pct": mix_stats["sync_pct"],
                    "log_move_pct": mix_stats["log_move_pct"],
                    "model_move_pct": mix_stats["model_move_pct"],
                    "conformance_mix_total_cases": mix_stats["total_cases"],
                    "dominant_mix_label": mix_stats["dominant_label"],
                    "dominant_mix_pct": mix_stats["dominant_pct"],
                    "chip_height_render": float(active_profile["chip_height"]),
                    **content_layout,
                }
                _workflow_apply_explorer_text_geometry(node_item)
                local_nodes.append(node_item)
                local_map[activity] = node_item
            for lane_rows, lane_position in ((top_rows, "left"), (bottom_rows, "right")):
                row_count = len(lane_rows)
                for lane_index, row in enumerate(lane_rows):
                    activity = str(row.get("activity", f"branch-{step_rank}-{lane_position}-{lane_index}"))
                    palette = _workflow_metric_palette(row, metric_coloring, item_kind="node")
                    is_neighbor = bool(selected_node and activity in node_neighbors.get(selected_node, set()))
                    is_selected = activity == selected_node
                    mix_stats = _workflow_node_mix_stats(row)
                    content_layout = _workflow_prepare_explorer_node_content(
                        row,
                        branch_role=str(row.get("branch_role", "branch")),
                        detail_level=detail_level,
                        profile=active_profile,
                    )
                    width = float(content_layout["width"])
                    height = float(content_layout["height"])
                    y = y_center - height / 2.0 + (lane_index - ((row_count - 1) / 2.0)) * (height + vertical_gap * 0.7)
                    x = (
                        x_center - mainline_width / 2.0 - lane_gap - width
                        if lane_position == "left"
                        else x_center + mainline_width / 2.0 + lane_gap
                    )
                    node_item = {
                        "id": activity,
                        "business_label": _workflow_business_label(row),
                        "display_name": _workflow_display_name(row),
                        "cases": _safe_int(row.get("cases", 0)),
                        "occurrences": _safe_int(row.get("occurrences", 0)),
                        "path_pct": _safe_float(row.get("coverage_pct")),
                        "activity_pct": _safe_float(row.get("activity_pct")),
                        "median_days": _safe_float(row.get("median_next_delay_days")),
                        "p90_days": _safe_float(row.get("p90_next_delay_days")),
                        "severity": str(row.get("severity", "Low")),
                        "conformance_bucket": str(row.get("conformance_bucket", "Conformant")),
                        "branch_role": str(row.get("branch_role", "branch")),
                        "lane_position": lane_position,
                        "step_rank": step_rank,
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height,
                        "center_x": x + width / 2.0,
                        "center_y": y + height / 2.0,
                        "preferred_x": x,
                        "preferred_y": y,
                        "preferred_center_x": x + width / 2.0,
                        "preferred_center_y": y_center,
                        "surface_fill": palette["surface"],
                        "stroke": palette["stroke"],
                        "ink": palette["ink"],
                        "accent": palette["accent"],
                        "accent_fill": palette["fill"],
                        "chip_fill": palette["chip_fill"],
                        "chip_ink": palette["chip_ink"],
                        "selected": is_selected,
                        "neighbor": is_neighbor,
                        "sync_cases": mix_stats["sync_cases"],
                        "log_move_cases": mix_stats["log_move_cases"],
                        "model_move_cases": mix_stats["model_move_cases"],
                        "sync_pct": mix_stats["sync_pct"],
                        "log_move_pct": mix_stats["log_move_pct"],
                        "model_move_pct": mix_stats["model_move_pct"],
                        "conformance_mix_total_cases": mix_stats["total_cases"],
                        "dominant_mix_label": mix_stats["dominant_label"],
                        "dominant_mix_pct": mix_stats["dominant_pct"],
                        "chip_height_render": float(active_profile["chip_height"]),
                        **content_layout,
                    }
                    _workflow_apply_explorer_text_geometry(node_item)
                    local_nodes.append(node_item)
                    local_map[activity] = node_item
        if local_nodes:
            _workflow_relax_vertical_nodes(local_nodes, profile=active_profile)
            bounds_pad_x = 14.0
            bounds_pad_y = 16.0
            min_x = min(float(_workflow_node_collision_bounds(node)["min_x"]) for node in local_nodes)
            min_y = min(float(_workflow_node_collision_bounds(node)["min_y"]) for node in local_nodes)
            max_x = max(float(_workflow_node_collision_bounds(node)["max_x"]) for node in local_nodes)
            content_width = max_x - min_x
            canvas_width_local = int(max(min_canvas_width, content_width + bounds_pad_x * 2.0))
            shift_x = ((canvas_width_local - content_width) / 2.0) - min_x
            shift_y = bounds_pad_y - min_y
            for node in local_nodes:
                node["x"] = float(node["x"]) + shift_x
                node["y"] = float(node["y"]) + shift_y
                node["center_x"] = float(node["center_x"]) + shift_x
                node["center_y"] = float(node["center_y"]) + shift_y
                node["preferred_x"] = float(node.get("preferred_x", node["x"])) + shift_x
                node["preferred_y"] = float(node.get("preferred_y", node["y"])) + shift_y
                node["preferred_center_x"] = float(node.get("preferred_center_x", node["center_x"])) + shift_x
                node["preferred_center_y"] = float(node.get("preferred_center_y", node["center_y"])) + shift_y
                _workflow_apply_explorer_text_geometry(node)
                local_map[str(node["id"])] = node
            max_x = max(float(_workflow_node_collision_bounds(node)["max_x"]) for node in local_nodes)
            max_y = max(float(_workflow_node_collision_bounds(node)["max_y"]) for node in local_nodes)
            canvas_width_local = int(max(min_canvas_width, max_x + bounds_pad_x))
            canvas_height_local = int(max(380.0, max_y + bounds_pad_y + 60.0))
        return local_nodes, local_map, canvas_width_local, canvas_height_local, canvas_width_local / 2.0

    node_items, node_map, canvas_width, canvas_height, center_x = _build_node_layout(render_profile)
    if _workflow_nodes_overlap(node_items, padding=4.0):
        node_items, node_map, canvas_width, canvas_height, center_x = _build_node_layout(render_profile, extra_step_gap=12.0)

    edge_items: list[dict[str, Any]] = []
    edge_lane_meta: dict[str, tuple[int, int]] = {}
    grouped_edges: dict[str, list[tuple[str, pd.Series]]] = defaultdict(list)
    for _, grouped_row in normalized_edges.iterrows():
        grouped_source = str(grouped_row.get("source", ""))
        grouped_target = str(grouped_row.get("target", ""))
        grouped_edge_id = str(grouped_row.get("edge_uid", grouped_row.get("edge_id", f"{grouped_source} -> {grouped_target}")))
        if grouped_source not in node_map or grouped_target not in node_map:
            continue
        grouped_edges[grouped_source].append((grouped_edge_id, grouped_row))

    for grouped_source, grouped_rows in grouped_edges.items():
        grouped_rows.sort(
            key=lambda item: (
                node_map[str(item[1].get("target", ""))]["center_y"],
                -_safe_int(item[1].get("frequency", 0)),
                str(item[1].get("target", "")),
            )
        )
        lane_count = len(grouped_rows)
        for lane_index, (grouped_edge_id, _) in enumerate(grouped_rows):
            edge_lane_meta[grouped_edge_id] = (lane_index, lane_count)

    selected_edge_neighbors: set[str] = set()
    if selected_edge and not normalized_edges.empty:
        selected_edge_rows = normalized_edges[
            normalized_edges.get("edge_uid", normalized_edges.get("edge_id", pd.Series(dtype=str))).astype(str) == selected_edge
        ]
        if not selected_edge_rows.empty:
            selected_edge_neighbors.update(
                {
                    str(selected_edge_rows.iloc[0].get("source", "")),
                    str(selected_edge_rows.iloc[0].get("target", "")),
                }
            )
    if selected_edge_neighbors:
        for node in node_items:
            if str(node.get("id", "")) in selected_edge_neighbors:
                node["neighbor"] = True

    max_frequency = max((_safe_int(row.get("frequency", 0)) for _, row in normalized_edges.iterrows()), default=0)
    for _, row in normalized_edges.iterrows():
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if source not in node_map or target not in node_map:
            continue
        source_item = node_map[source]
        target_item = node_map[target]
        edge_id = str(row.get("edge_uid", row.get("edge_id", f"{source} -> {target}")))
        palette = _workflow_metric_palette(row, metric_coloring, item_kind="edge")
        is_mainline = str(row.get("branch_role", "mainline")) == "mainline"
        is_selected = edge_id == selected_edge
        is_neighbor = bool(selected_node and (source == selected_node or target == selected_node)) or bool(
            selected_edge_neighbors and (source in selected_edge_neighbors or target in selected_edge_neighbors)
        )
        lane_index, lane_count = edge_lane_meta.get(edge_id, (0, 1))
        sibling_unit = float(render_profile["mainline_sibling_offset"] if is_mainline else render_profile["branch_sibling_offset"])
        sibling_offset = (lane_index - ((lane_count - 1) / 2.0)) * sibling_unit

        forward = target_item["center_y"] >= source_item["center_y"]
        source_x = source_item["center_x"] + sibling_offset
        target_x = target_item["center_x"] + sibling_offset * 0.8
        if forward:
            start_y = source_item["y"] + source_item["height"] + 4.0
            end_y = target_item["y"] - 4.0
            distance = max(52.0, end_y - start_y)
            control = min(74.0, distance * 0.34)
            delta_x = target_x - source_x
            curve_push = math.copysign(
                max(10.0, min(22.0, abs(delta_x) * 0.9 + 8.0)),
                delta_x if abs(delta_x) >= 1.0 else (1.0 if lane_index % 2 == 0 else -1.0),
            )
            control1_x = source_x + curve_push
            control2_x = target_x - curve_push * 0.7
            path = (
                f"M {source_x:.1f} {start_y:.1f} "
                f"C {control1_x:.1f} {start_y + control:.1f}, {control2_x:.1f} {end_y - control:.1f}, {target_x:.1f} {end_y:.1f}"
            )
            label_x = (source_x + target_x) / 2.0 + curve_push * 0.18
            label_y = (start_y + end_y) / 2.0 - 18.0 - abs(sibling_offset) * 0.1
            path_min_x = min(source_x, target_x, control1_x, control2_x) - 5.0
            path_max_x = max(source_x, target_x, control1_x, control2_x) + 5.0
        else:
            start_y = source_item["center_y"]
            end_y = target_item["center_y"]
            arc_x = (
                min(source_x, target_x) - (60.0 + lane_index * 8.0)
                if source_item["lane_position"] != "right"
                else max(source_x, target_x) + (60.0 + lane_index * 8.0)
            )
            path = f"M {source_x:.1f} {start_y:.1f} C {arc_x:.1f} {start_y:.1f}, {arc_x:.1f} {end_y:.1f}, {target_x:.1f} {end_y:.1f}"
            label_x = arc_x
            label_y = (start_y + end_y) / 2.0 - 14.0
            path_min_x = min(source_x, target_x, arc_x) - 5.0
            path_max_x = max(source_x, target_x, arc_x) + 5.0

        label_height = float(
            render_profile["label_height_secondary"]
            if detail_level == "research" and _safe_float(row.get("share_pct")) is not None
            else render_profile["label_height"]
        )
        frequency_ratio = (_safe_int(row.get("frequency", 0)) / max(max_frequency, 1)) if max_frequency else 0.0
        base_stroke = float(render_profile["stroke_mainline"] if is_mainline else render_profile["stroke_branch"])
        edge_items.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "caption": _workflow_business_label(row),
                "frequency": _safe_int(row.get("frequency", 0)),
                "median_days": _safe_float(row.get("median_days")),
                "p90_days": _safe_float(row.get("p90_days")),
                "share_pct": _safe_float(row.get("share_pct")),
                "severity": str(row.get("severity", "Low")),
                "conformance_bucket": str(row.get("conformance_bucket", "Conformant")),
                "branch_role": str(row.get("branch_role", "mainline")),
                "stroke_style": str(row.get("stroke_style", "solid")),
                "stroke_width": max(
                    0.9 if is_mainline else 0.75,
                    min(
                        2.2 if is_mainline else 1.35,
                        base_stroke + frequency_ratio * (0.72 if is_mainline else 0.34),
                    ),
                ),
                "stroke": palette["stroke"],
                "accent": palette["accent"],
                "path": path,
                "label_x": label_x,
                "label_y": label_y,
                "selected": is_selected,
                "neighbor": is_neighbor,
                "show_label": is_mainline
                and len(edge_items) < 10
                and (
                    _safe_int(row.get("frequency", 0)) >= max(900, int(max_frequency * (0.74 if lens_is_paths else 0.86)))
                    or selected_edge == edge_id
                ),
                "label_width": float(render_profile["label_width"]),
                "label_height": label_height,
                "path_min_x": path_min_x,
                "path_max_x": path_max_x,
                "path_min_y": min(start_y, end_y) - 10.0,
                "path_max_y": max(start_y, end_y) + 10.0,
            }
        )

    _workflow_apply_label_clearance(
        edge_items,
        node_items,
        clearance=float(render_profile["label_clearance"]),
    )

    anchor_layout_nodes = _workflow_primary_path_nodes(node_items) or node_items
    first_layout_node = min(anchor_layout_nodes, key=lambda node: float(node.get("center_y", 0.0))) if anchor_layout_nodes else None
    last_layout_node = max(anchor_layout_nodes, key=lambda node: float(node.get("center_y", 0.0))) if anchor_layout_nodes else None
    top_reference_y = float(first_layout_node["y"]) if first_layout_node else float(render_profile["top_margin"])
    bottom_reference_y = (
        float(last_layout_node["y"]) + float(last_layout_node["height"])
        if last_layout_node
        else top_reference_y + float(render_profile["mainline_height"])
    )
    mainline_band_y = max(18.0, top_reference_y - 14.0)
    top_band_y = max(16.0, top_reference_y - (54.0 if has_top_branches else 18.0))
    bottom_band_y = bottom_reference_y + 14.0
    start_anchor_y = top_reference_y - 18.0
    end_anchor_y = bottom_reference_y + 32.0
    first_anchor_x = float(first_layout_node.get("center_x", center_x)) if first_layout_node else float(center_x)
    last_anchor_x = float(last_layout_node.get("center_x", center_x)) if last_layout_node else float(center_x)

    fit_min_x = float("inf")
    fit_min_y = float("inf")
    fit_max_x = float("-inf")
    fit_max_y = float("-inf")

    def _include_fit_bounds(min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        nonlocal fit_min_x, fit_min_y, fit_max_x, fit_max_y
        fit_min_x = min(fit_min_x, float(min_x))
        fit_min_y = min(fit_min_y, float(min_y))
        fit_max_x = max(fit_max_x, float(max_x))
        fit_max_y = max(fit_max_y, float(max_y))

    for node in node_items:
        node_pad = 18.0 if node.get("selected") else 10.0
        node_bounds = _workflow_node_collision_bounds(node, pad=node_pad)
        _include_fit_bounds(
            float(node_bounds["min_x"]),
            float(node_bounds["min_y"]),
            float(node_bounds["max_x"]),
            float(node_bounds["max_y"]),
        )

    for edge in edge_items:
        _include_fit_bounds(
            float(edge.get("path_min_x", 0.0)),
            float(edge.get("path_min_y", 0.0)),
            float(edge.get("path_max_x", 0.0)),
            float(edge.get("path_max_y", 0.0)),
        )
        if edge.get("show_label") and detail_level != "executive":
            label_width = float(edge.get("label_width", render_profile["label_width"]))
            label_height = float(edge.get("label_height", render_profile["label_height"]))
            _include_fit_bounds(
                float(edge["label_x"]) - (label_width / 2.0) - 6.0,
                float(edge["label_y"]) - (label_height / 2.0) - 6.0,
                float(edge["label_x"]) + (label_width / 2.0) + 6.0,
                float(edge["label_y"]) + (label_height / 2.0) + 6.0,
            )

    anchor_bounds = {
        "min_x": min(first_anchor_x - 36.0, last_anchor_x - 36.0),
        "min_y": min(start_anchor_y - 18.0, end_anchor_y - 18.0),
        "max_x": max(first_anchor_x + 36.0, last_anchor_x + 36.0),
        "max_y": max(start_anchor_y + 18.0, end_anchor_y + 40.0),
    }
    _include_fit_bounds(
        anchor_bounds["min_x"],
        anchor_bounds["min_y"],
        anchor_bounds["max_x"],
        anchor_bounds["max_y"],
    )

    if not all(math.isfinite(value) for value in (fit_min_x, fit_min_y, fit_max_x, fit_max_y)):
        fit_min_x = 10.0
        fit_min_y = 10.0
        fit_max_x = float(canvas_width - 10.0)
        fit_max_y = float(canvas_height - 10.0)

    fit_padding = {
        "top": 34.0 if has_top_branches else 30.0,
        "right": 16.0,
        "bottom": 42.0,
        "left": 16.0,
    }
    fit_width = max(1.0, fit_max_x - fit_min_x)
    fit_height = max(1.0, fit_max_y - fit_min_y)
    fit_width_with_padding = fit_width + fit_padding["left"] + fit_padding["right"]
    fit_height_with_padding = fit_height + fit_padding["top"] + fit_padding["bottom"]
    target_width = int(math.ceil(max(740.0, fit_width_with_padding + 28.0)))
    target_height = int(
        math.ceil(
            max(
                568.0,
                fit_height_with_padding + 32.0,
                fit_height_with_padding * 1.08,
            )
        )
    )
    toolbar_height_hint = 122 + (18 if detail_level == "research" else 0) + (10 if has_top_branches or has_bottom_branches else 0)
    drawable_top = 16.0
    drawable_bottom = max(
        drawable_top + 120.0,
        float(target_height) - 36.0,
    )
    drawable_bounds = {
        "min_x": 12.0,
        "min_y": round(drawable_top, 1),
        "max_x": round(float(target_width) - 12.0, 1),
        "max_y": round(max(drawable_top + 120.0, drawable_bottom), 1),
    }

    return {
        "nodes": node_items,
        "edges": edge_items,
        "legend": legend_df,
        "height": max(320, target_height),
        "frame_height": max(640, int(math.ceil(target_height)) + toolbar_height_hint + 44),
        "width": max(640, target_width),
        "content_offset_x": 0.0,
        "content_offset_y": 0.0,
        "overall_median_delay_days": overall_median,
        "selected_node_id": selected_node,
        "selected_edge_id": selected_edge,
        "selected_edge_uid": selected_edge,
        "visible_case_count": visible_case_count,
        "excluded_case_count": excluded_case_count,
        "path_denominator": path_denominator,
        "activity_denominator": activity_denominator,
        "transition_denominator": transition_denominator,
        "local_focus_hint": local_focus_hint,
        "renderer_role": renderer_role,
        "metric_coloring": metric_coloring,
        "detail_level": detail_level,
        "conformance_lens": lens_value,
        "has_top_branches": has_top_branches,
        "has_bottom_branches": has_bottom_branches,
        "density_profile": str(render_profile["name"]),
        "content_bounds": {
            "min_x": round(fit_min_x, 1),
            "min_y": round(fit_min_y, 1),
            "max_x": round(fit_max_x, 1),
            "max_y": round(fit_max_y, 1),
        },
        "anchor_bounds": {key: round(float(value), 1) for key, value in anchor_bounds.items()},
        "drawable_bounds": drawable_bounds,
        "fit_padding": fit_padding,
        "toolbar_height_hint": toolbar_height_hint,
        "render_profile": {
            "name": str(render_profile["name"]),
            "title_font_size": float(render_profile["title_font_size"]),
            "timing_font_size": float(render_profile.get("timing_font_size", render_profile["meta_font_size"])),
            "meta_font_size": float(render_profile["meta_font_size"]),
            "footer_font_size": float(render_profile.get("footer_font_size", render_profile["meta_font_size"])),
            "median_font_size": float(render_profile["median_font_size"]),
            "p90_font_size": float(render_profile["p90_font_size"]),
            "chip_width": float(render_profile["chip_width"]),
            "chip_height": float(render_profile["chip_height"]),
            "chip_font_size": float(render_profile["chip_font_size"]),
            "chip_offset_y": float(render_profile["chip_offset_y"]),
            "card_radius": float(render_profile["card_radius"]),
            "ribbon_height": float(render_profile.get("ribbon_height", 0.0)),
            "ribbon_label_font_size": float(render_profile.get("ribbon_label_font_size", 6.0)),
            "label_width": float(render_profile["label_width"]),
            "label_height": float(render_profile["label_height"]),
            "label_height_secondary": float(render_profile["label_height_secondary"]),
            "label_font": float(render_profile["label_font"]),
            "label_secondary_font": float(render_profile["label_secondary_font"]),
            "marker_width": float(render_profile["marker_width"]),
            "marker_height": float(render_profile["marker_height"]),
            "marker_ref_x": float(render_profile["marker_ref_x"]),
            "marker_ref_y": float(render_profile["marker_ref_y"]),
            "anchor_font_size": float(render_profile["anchor_font_size"]),
        },
        "lane_bands": {
            "top_y": top_band_y,
            "mainline_y": mainline_band_y,
            "bottom_y": bottom_band_y,
        },
    }


def render_workflow_explorer_html(explorer_payload: Mapping[str, Any]) -> str:
    """Render an HTML/SVG process explorer with stable lanes and lightweight zoom controls."""
    node_items = list(explorer_payload.get("nodes", []))
    edge_items = list(explorer_payload.get("edges", []))
    metric_coloring = str(explorer_payload.get("metric_coloring", "Conformance bucket"))
    detail_level = str(explorer_payload.get("detail_level", "analyst")).lower()
    conformance_lens = str(explorer_payload.get("conformance_lens", "% of paths"))
    render_profile = explorer_payload.get("render_profile", {}) if isinstance(explorer_payload.get("render_profile"), Mapping) else {}
    selected_node_id = str(explorer_payload.get("selected_node_id") or "").strip()
    selected_edge_id = str(explorer_payload.get("selected_edge_id") or "").strip()
    selected_node_js = _script_json(selected_node_id)
    selected_edge_js = _script_json(selected_edge_id)
    local_focus_hint = str(
        explorer_payload.get("local_focus_hint")
        or "Local graph focus stays inside the frame; use Pinned exact metrics to persist node or transition metrics."
    )
    local_focus_hint_js = _script_json(local_focus_hint)
    renderer_role = str(explorer_payload.get("renderer_role") or "conformance_explorer")
    visible_case_count = _safe_int(explorer_payload.get("visible_case_count", 0))
    excluded_case_count = _safe_int(explorer_payload.get("excluded_case_count", 0))
    canvas_width = int(explorer_payload.get("width", 1080))
    canvas_height = int(explorer_payload.get("height", 520))
    drawable_width = max(320.0, float(canvas_width))
    drawable_height = max(320.0, float(canvas_height))
    lane_bands = explorer_payload.get("lane_bands", {}) if isinstance(explorer_payload.get("lane_bands"), Mapping) else {}
    content_bounds = explorer_payload.get("content_bounds", {}) if isinstance(explorer_payload.get("content_bounds"), Mapping) else {}
    drawable_bounds = explorer_payload.get("drawable_bounds", {}) if isinstance(explorer_payload.get("drawable_bounds"), Mapping) else {}
    fit_padding = explorer_payload.get("fit_padding", {}) if isinstance(explorer_payload.get("fit_padding"), Mapping) else {}
    has_top_branches = bool(explorer_payload.get("has_top_branches", True))
    has_bottom_branches = bool(explorer_payload.get("has_bottom_branches", True))
    instance_id = escape(str(explorer_payload.get("instance_id", "workflow-explorer")))
    title_font_size = float(render_profile.get("title_font_size", 8.9))
    meta_font_size = float(render_profile.get("meta_font_size", 7.3))
    chip_width = float(render_profile.get("chip_width", 44.0))
    chip_height = float(render_profile.get("chip_height", 14.0))
    chip_font_size = float(render_profile.get("chip_font_size", 7.2))
    chip_offset_y = float(render_profile.get("chip_offset_y", 7.0))
    marker_width = float(render_profile.get("marker_width", 5.8))
    marker_height = float(render_profile.get("marker_height", 5.8))
    marker_ref_x = float(render_profile.get("marker_ref_x", 5.2))
    marker_ref_y = float(render_profile.get("marker_ref_y", 2.9))
    edge_label_font = float(render_profile.get("label_font", 9.0))
    edge_label_secondary_font = float(render_profile.get("label_secondary_font", 8.4))
    anchor_font_size = float(render_profile.get("anchor_font_size", 11.5))
    card_radius = float(render_profile.get("card_radius", 9.0))
    top_band_y = float(lane_bands.get("top_y", 14.0))
    mainline_band_y = float(lane_bands.get("mainline_y", 14.0))
    bottom_band_y = float(lane_bands.get("bottom_y", mainline_band_y + 156.0))
    top_band_height = max(18.0 if not has_top_branches else 52.0, mainline_band_y - top_band_y - (14.0 if has_top_branches else 8.0))
    primary_path_nodes = _workflow_primary_path_nodes(node_items)
    mainline_nodes = primary_path_nodes or [node for node in node_items if str(node.get("branch_role", "mainline")) == "mainline"]
    anchor_nodes = primary_path_nodes or node_items
    first_anchor_x = drawable_width / 2.0
    last_anchor_x = drawable_width / 2.0
    start_anchor_y = top_band_y + 16.0
    end_anchor_y = bottom_band_y + 42.0
    if anchor_nodes:
        ordered_anchor_nodes = sorted(anchor_nodes, key=lambda item: float(item.get("center_y", 0.0)))
        first_node = ordered_anchor_nodes[0]
        last_node = ordered_anchor_nodes[-1]
        first_anchor_x = float(first_node.get("center_x", drawable_width / 2.0))
        last_anchor_x = float(last_node.get("center_x", drawable_width / 2.0))
        start_anchor_y = float(first_node.get("y", 60.0)) - 18.0
        end_anchor_y = float(last_node.get("y", 60.0)) + float(last_node.get("height", 84.0)) + 32.0
    mainline_band_height = max(82.0, bottom_band_y - mainline_band_y - 10.0)
    bottom_band_height = max(18.0 if not has_bottom_branches else 52.0, (end_anchor_y + 20.0) - bottom_band_y)
    anchor_y = mainline_band_y + (mainline_band_height / 2.0)
    if not node_items and not edge_items:
        return (
            '<div class="crpm-workflow-explorer">'
            '<div style="padding:18px;border:1px solid #d8dfe8;border-radius:20px;background:#ffffff;color:#1f2c25;font-family:Segoe UI, Arial, sans-serif;">'
            "No workflow explorer could be built for this selection."
            "</div></div>"
        )

    if selected_node_id:
        selection_state = f"Pinned node: {selected_node_id.replace('_', ' ').title()}"
    elif selected_edge_id:
        selection_state = "Pinned edge"
    else:
        selection_state = "Overview mode"
    case_scope_label = ""
    if visible_case_count or excluded_case_count:
        case_scope_label = f"{visible_case_count:,} visible cases"
        if excluded_case_count:
            case_scope_label += f" · {excluded_case_count:,} excluded"
    case_scope_badge = f'<span class="crpm-explorer-badge">{escape(case_scope_label)}</span>' if case_scope_label else ""
    coloring_hint = _workflow_metric_coloring_hint(metric_coloring)
    lens_hint = "Activity lens" if "activit" in conformance_lens.lower() else "Path lens"
    mainline_backbone_points: list[tuple[float, float]] = [(first_anchor_x, start_anchor_y)]
    for node in sorted(mainline_nodes, key=lambda item: float(item.get("center_y", 0.0))):
        mainline_backbone_points.append((float(node.get("center_x", canvas_width / 2.0)), float(node.get("center_y", anchor_y))))
    mainline_backbone_points.append((last_anchor_x, end_anchor_y))
    if len(mainline_backbone_points) >= 2:
        backbone_segments = [f"M {mainline_backbone_points[0][0]:.1f} {mainline_backbone_points[0][1]:.1f}"]
        for point_x, point_y in mainline_backbone_points[1:]:
            backbone_segments.append(f"L {point_x:.1f} {point_y:.1f}")
        mainline_backbone_path = " ".join(backbone_segments)
    else:
        mainline_backbone_path = ""

    parts = [
        f'<div class="crpm-workflow-explorer" data-instance="{instance_id}" data-renderer-role="{escape(renderer_role)}" style="font-family:Segoe UI, Arial, sans-serif;">',
        "<style>"
        ".crpm-workflow-explorer{color:#1d2c34;}"
        ".crpm-explorer-shell{display:grid;gap:6px;}"
        ".crpm-explorer-toolbar{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:10px;padding:8px 10px;border:1px solid #d9dfe6;border-radius:14px;background:#ffffff;box-shadow:none;}"
        ".crpm-explorer-toolbar__copy{min-width:0;display:grid;gap:5px;}"
        ".crpm-explorer-toolbar__title-row{display:flex;align-items:center;flex-wrap:wrap;gap:7px;}"
        ".crpm-explorer-toolbar__title{font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#394b5a;}"
        ".crpm-explorer-toolbar__summary{font-size:10px;line-height:1.35;color:#5b6977;}"
        ".crpm-explorer-toolbar__sub{font-size:9px;line-height:1.25;color:#6b7886;}"
        ".crpm-explorer-badge{display:inline-flex;align-items:center;padding:2px 7px;border-radius:999px;background:#f7f9fb;border:1px solid #dde4ea;font-size:9px;font-weight:700;color:#44586b;}"
        "#crpm-explorer-selection-chip{background:#eef3f8;border-color:#cfd9e2;color:#405668;}"
        ".crpm-explorer-toolbar__actions{display:flex;flex-wrap:wrap;justify-content:flex-end;align-content:flex-start;gap:7px;}"
        ".crpm-explorer-action{border:1px solid #d6dde5;background:#ffffff;border-radius:10px;padding:5px 9px;font-size:9px;font-weight:700;color:#24343f;cursor:pointer;box-shadow:none;transition:transform .14s ease,border-color .14s ease,background .14s ease;}"
        ".crpm-explorer-action:hover{transform:translateY(-1px);border-color:#b4c0cd;background:#f7f9fb;}"
        ".crpm-explorer-action--reset{background:#f7f9fb;color:#3b5062;}"
        ".crpm-explorer-status-line{display:flex;align-items:center;gap:10px;min-width:0;flex-wrap:wrap;}"
        ".crpm-explorer-live-title{font-size:10.5px;font-weight:800;color:#20313c;line-height:1.2;min-width:0;overflow-wrap:anywhere;}"
        ".crpm-explorer-live-meta{font-size:9.5px;color:#657381;line-height:1.25;min-width:0;overflow-wrap:anywhere;}"
        ".crpm-explorer-legend{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:9px;color:#677381;}"
        ".crpm-explorer-legend__item{display:inline-flex;align-items:center;gap:6px;padding:0;border-radius:0;border:none;background:transparent;}"
        ".crpm-explorer-legend__swatch{width:8px;height:8px;border-radius:999px;display:inline-block;}"
        ".crpm-explorer-canvas{border:1px solid #d9dfe6;border-radius:18px;background:#ffffff;overflow:visible;box-shadow:none;}"
        ".crpm-explorer-figure{margin:0 auto;width:100%;}"
        ".crpm-explorer-canvas svg{display:block;width:100%;height:auto;}"
        ".crpm-explorer-node,.crpm-explorer-edge{transition:opacity .16s ease,filter .16s ease;}"
        ".crpm-explorer-node.is-muted{opacity:.32;}"
        ".crpm-explorer-edge.is-muted{opacity:.24;}"
        ".crpm-explorer-node.is-neighbor{opacity:.97;}"
        ".crpm-explorer-edge.is-neighbor{opacity:.74;}"
        ".crpm-explorer-node.is-focus,.crpm-explorer-edge.is-focus{opacity:1;filter:drop-shadow(0 9px 18px rgba(64,105,180,.24));}"
        "@media (max-width: 920px){.crpm-explorer-toolbar{grid-template-columns:minmax(0,1fr);}.crpm-explorer-toolbar__actions{justify-content:flex-start;}.crpm-explorer-action{flex:0 1 auto;}}"
        "</style>",
        '<div class="crpm-explorer-shell">',
        '<div class="crpm-explorer-toolbar" id="crpm-explorer-toolbar">',
        '<div class="crpm-explorer-toolbar__copy">',
        '<div class="crpm-explorer-toolbar__title-row">'
        '<div class="crpm-explorer-toolbar__title">Active process flow</div>'
        f'<span id="crpm-explorer-selection-chip" class="crpm-explorer-badge">{escape(selection_state)}</span>'
        f'<span class="crpm-explorer-badge">{escape(metric_coloring)}</span>'
        f'<span class="crpm-explorer-badge">{escape(lens_hint)}</span>'
        f"{case_scope_badge}"
        "</div>",
        f'<div class="crpm-explorer-toolbar__summary">{escape(coloring_hint)}</div>',
        '<div class="crpm-explorer-status-line">'
        '<div id="crpm-explorer-live-title" class="crpm-explorer-live-title">Overview mode</div>'
        f'<div id="crpm-explorer-live-meta" class="crpm-explorer-live-meta">{escape(local_focus_hint)}</div>'
        "</div>",
        '<div class="crpm-explorer-legend">'
        '<span class="crpm-explorer-legend__item"><span class="crpm-explorer-legend__swatch" style="background:#9ed2a2;"></span>Conformance class</span>'
        '<span class="crpm-explorer-legend__item"><span class="crpm-explorer-legend__swatch" style="background:#7c98bd;"></span>Timing burden on links</span>'
        '<span class="crpm-explorer-toolbar__sub">Top to bottom reference flow.</span>'
        "</div>",
        "</div>",
        '<div class="crpm-explorer-toolbar__actions">',
        '<button id="crpm-explorer-zoom-in" class="crpm-explorer-action" type="button">Zoom in</button>',
        '<button id="crpm-explorer-zoom-out" class="crpm-explorer-action" type="button">Zoom out</button>',
        '<button id="crpm-explorer-clear-focus" class="crpm-explorer-action" type="button">Clear local focus</button>',
        '<button id="crpm-explorer-reset-view" class="crpm-explorer-action crpm-explorer-action--reset" type="button">Reset graph view</button>',
        "</div></div>",
        '<div class="crpm-explorer-canvas">',
        '<div class="crpm-explorer-figure" style="width:100%;">',
        f'<svg id="crpm-workflow-explorer-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_width} {canvas_height}" preserveAspectRatio="xMidYMin meet" aria-label="Workflow process explorer" style="display:block;width:100%;height:auto;aspect-ratio:{canvas_width}/{canvas_height};overflow:visible;margin:0 auto;" data-content-min-x="{float(content_bounds.get("min_x", 0.0)):.1f}" data-content-min-y="{float(content_bounds.get("min_y", 0.0)):.1f}" data-content-max-x="{float(content_bounds.get("max_x", float(canvas_width))):.1f}" data-content-max-y="{float(content_bounds.get("max_y", float(canvas_height))):.1f}" data-drawable-min-x="{float(drawable_bounds.get("min_x", 12.0)):.1f}" data-drawable-min-y="{float(drawable_bounds.get("min_y", 12.0)):.1f}" data-drawable-max-x="{float(drawable_bounds.get("max_x", float(canvas_width) - 12.0)):.1f}" data-drawable-max-y="{float(drawable_bounds.get("max_y", float(canvas_height) - 12.0)):.1f}" data-fit-pad-top="{float(fit_padding.get("top", 18.0)):.1f}" data-fit-pad-right="{float(fit_padding.get("right", 16.0)):.1f}" data-fit-pad-bottom="{float(fit_padding.get("bottom", 30.0)):.1f}" data-fit-pad-left="{float(fit_padding.get("left", 16.0)):.1f}" data-testid="explorer-svg">',
        "<defs>",
        '<filter id="workflow-explorer-shadow" x="-18%" y="-18%" width="150%" height="150%">',
        '<feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#4c5d78" flood-opacity="0.08"/>',
        "</filter>",
        '<filter id="workflow-explorer-glow" x="-24%" y="-24%" width="168%" height="168%">',
        '<feDropShadow dx="0" dy="0" stdDeviation="7" flood-color="#7e9dc4" flood-opacity="0.18"/>',
        "</filter>",
        (
            f'<marker id="workflow-explorer-arrow-mainline" markerWidth="{max(marker_width, 6.4):.1f}" markerHeight="{max(marker_height, 6.4):.1f}" '
            f'refX="{max(marker_ref_x, 5.7):.1f}" refY="{max(marker_ref_y, 3.2):.1f}" orient="auto" markerUnits="strokeWidth">'
        ),
        f'<path d="M 0.4 0.6 L {max(marker_width, 6.4):.1f} {max(marker_ref_y, 3.2):.1f} L 0.4 {max(1.0, max(marker_height, 6.4) - 0.6):.1f} z" fill="#5f9074" fill-opacity="0.96"/>',
        "</marker>",
        (
            f'<marker id="workflow-explorer-arrow-log" markerWidth="{max(marker_width, 6.4):.1f}" markerHeight="{max(marker_height, 6.4):.1f}" '
            f'refX="{max(marker_ref_x, 5.7):.1f}" refY="{max(marker_ref_y, 3.2):.1f}" orient="auto" markerUnits="strokeWidth">'
        ),
        f'<path d="M 0.4 0.6 L {max(marker_width, 6.4):.1f} {max(marker_ref_y, 3.2):.1f} L 0.4 {max(1.0, max(marker_height, 6.4) - 0.6):.1f} z" fill="#c69334" fill-opacity="0.96"/>',
        "</marker>",
        (
            f'<marker id="workflow-explorer-arrow-model" markerWidth="{max(marker_width, 6.4):.1f}" markerHeight="{max(marker_height, 6.4):.1f}" '
            f'refX="{max(marker_ref_x, 5.7):.1f}" refY="{max(marker_ref_y, 3.2):.1f}" orient="auto" markerUnits="strokeWidth">'
        ),
        f'<path d="M 0.4 0.6 L {max(marker_width, 6.4):.1f} {max(marker_ref_y, 3.2):.1f} L 0.4 {max(1.0, max(marker_height, 6.4) - 0.6):.1f} z" fill="#b57ea8" fill-opacity="0.96"/>',
        "</marker>",
        (
            f'<marker id="workflow-explorer-arrow-neutral" markerWidth="{max(marker_width, 6.1):.1f}" markerHeight="{max(marker_height, 6.1):.1f}" '
            f'refX="{max(marker_ref_x, 5.5):.1f}" refY="{max(marker_ref_y, 3.0):.1f}" orient="auto" markerUnits="strokeWidth">'
        ),
        f'<path d="M 0.4 0.6 L {max(marker_width, 6.1):.1f} {max(marker_ref_y, 3.0):.1f} L 0.4 {max(1.0, max(marker_height, 6.1) - 0.6):.1f} z" fill="#9aabb5" fill-opacity="0.9"/>',
        "</marker>",
        "</defs>",
        '<g id="crpm-workflow-static-frame" data-testid="explorer-frame" data-qa="explorer-frame">',
        f'<rect x="4" y="4" width="{drawable_width - 8:.1f}" height="{drawable_height - 8:.1f}" rx="18" ry="18" fill="#ffffff" stroke="#e6ebf0" stroke-width="1.1"/>',
    ]

    if has_top_branches:
        parts.extend(
            [
                f'<rect x="6" y="{top_band_y:.1f}" width="{drawable_width - 12:.1f}" height="{top_band_height:.1f}" rx="12" ry="12" fill="#fbfcfd" fill-opacity="1"/>',
                f'<line x1="24" y1="{top_band_y + top_band_height:.1f}" x2="{drawable_width - 24:.1f}" y2="{top_band_y + top_band_height:.1f}" stroke="#dddbe4" stroke-width="1" stroke-dasharray="6 8"/>',
                f'<text x="24" y="{top_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#8a8097">Upper variation</text>',
            ]
        )
    if has_bottom_branches:
        parts.extend(
            [
                f'<rect x="6" y="{bottom_band_y:.1f}" width="{drawable_width - 12:.1f}" height="{bottom_band_height:.1f}" rx="12" ry="12" fill="#fbfcfd" fill-opacity="1"/>',
                f'<line x1="24" y1="{bottom_band_y:.1f}" x2="{drawable_width - 24:.1f}" y2="{bottom_band_y:.1f}" stroke="#dddbe4" stroke-width="1" stroke-dasharray="6 8"/>',
                f'<text x="24" y="{bottom_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#8a8097">Lower variation</text>',
            ]
        )

    parts.extend(
        [
            f'<rect id="crpm-workflow-mainline-band" x="6" y="{mainline_band_y:.1f}" width="{drawable_width - 12:.1f}" height="{mainline_band_height:.1f}" rx="12" ry="12" fill="#ffffff" fill-opacity="1" stroke="#d8dfe6" stroke-width="1.15" data-testid="explorer-mainline-band" data-qa="explorer-mainline-band"/>',
            f'<text x="22" y="{mainline_band_y - 8:.1f}" font-size="10.5" font-weight="800" fill="#5c6d7b">Reference flow</text>',
            "</g>",
            '<g id="crpm-workflow-content" data-testid="explorer-content" data-qa="explorer-content">',
        ]
    )

    start_width = 48.0
    start_height = 28.0
    parts.extend(
        [
            (
                f'<path d="{mainline_backbone_path}" fill="none" stroke="#f4f7f8" stroke-width="3.8" '
                'stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>'
                if mainline_backbone_path
                else ""
            ),
            (
                f'<path d="{mainline_backbone_path}" fill="none" stroke="#c8d4d8" stroke-width="0.8" '
                'stroke-linecap="round" stroke-linejoin="round" opacity="0.42"/>'
                if mainline_backbone_path
                else ""
            ),
            f'<g id="crpm-workflow-start-anchor" data-testid="explorer-start-anchor" data-qa="explorer-start-anchor"><rect x="{first_anchor_x - start_width / 2:.1f}" y="{start_anchor_y - start_height / 2:.1f}" width="{start_width:.1f}" height="{start_height:.1f}" rx="14" ry="14" fill="#ffffff" stroke="#243744" stroke-width="1.5"/><text x="{first_anchor_x:.1f}" y="{start_anchor_y + 4.8:.1f}" text-anchor="middle" font-size="{anchor_font_size:.1f}" font-weight="700" fill="#243744">Start</text></g>',
            f'<g id="crpm-workflow-end-anchor" data-testid="explorer-end-anchor" data-qa="explorer-end-anchor"><rect x="{last_anchor_x - start_width / 2:.1f}" y="{end_anchor_y - start_height / 2:.1f}" width="{start_width:.1f}" height="{start_height:.1f}" rx="14" ry="14" fill="#ffffff" stroke="#243744" stroke-width="1.5"/><text x="{last_anchor_x:.1f}" y="{end_anchor_y + 4.8:.1f}" text-anchor="middle" font-size="{anchor_font_size:.1f}" font-weight="700" fill="#243744">End</text></g>',
        ]
    )

    for edge in edge_items:
        is_mainline_edge = str(edge.get("branch_role", "mainline")) == "mainline"
        opacity = "0.98" if edge["selected"] else "0.78" if edge["neighbor"] else ("0.6" if is_mainline_edge else "0.42")
        dash = ' stroke-dasharray="9 6"' if str(edge.get("stroke_style", "solid")).lower() == "dashed" else ""
        if "activit" in conformance_lens.lower():
            label = [
                f"{edge['caption']}",
                f"{edge['share_pct']:.1f}% activity support" if edge.get("share_pct") is not None else f"{edge['frequency']:,} events",
            ]
        else:
            label = [f"{edge['caption']}", f"{edge['frequency']:,} paths"]
        if detail_level == "research" and edge.get("median_days") is not None:
            label.append(f"median {edge['median_days']:.1f} d")
        if detail_level == "research" and edge.get("p90_days") is not None:
            label.append(f"p90 {edge['p90_days']:.1f} d")
        if detail_level != "executive" and edge.get("share_pct") is not None:
            label.append(f"{edge['share_pct']:.1f}% share")
        edge_classes = ["crpm-explorer-edge"]
        if edge["selected"]:
            edge_classes.append("is-focus")
        elif edge["neighbor"]:
            edge_classes.append("is-neighbor")
        edge_stroke = str(edge.get("stroke", "#86ae9b")) if is_mainline_edge else "#a9b5c0"
        base_stroke_width = float(edge["stroke_width"]) + (1.0 if edge["selected"] else (0.18 if is_mainline_edge else 0.06))
        conformance_bucket = str(edge.get("conformance_bucket", "Conformant"))
        if edge["selected"]:
            marker_id = "workflow-explorer-arrow-mainline"
        elif conformance_bucket == "Log deviation":
            marker_id = "workflow-explorer-arrow-log"
        elif conformance_bucket == "Model deviation":
            marker_id = "workflow-explorer-arrow-model"
        elif is_mainline_edge:
            marker_id = "workflow-explorer-arrow-mainline"
        else:
            marker_id = "workflow-explorer-arrow-neutral"
        edge_median = _safe_float(edge.get("median_days"))
        edge_p90 = _safe_float(edge.get("p90_days"))
        edge_share = _safe_float(edge.get("share_pct"))
        edge_median_label = "" if edge_median is None else f"{edge_median:.1f}"
        edge_p90_label = "" if edge_p90 is None else f"{edge_p90:.1f}"
        edge_share_label = "" if edge_share is None else f"{edge_share:.1f}"
        parts.append(
            f'<g><path class="{" ".join(edge_classes)}" d="{edge["path"]}" fill="none" stroke="{edge_stroke}" stroke-width="{base_stroke_width:.1f}" stroke-linecap="round" opacity="{opacity}" marker-end="url(#{marker_id})"{dash} '
            f'data-edge-id="{escape(str(edge.get("id", "")))}" '
            f'data-source="{escape(str(edge.get("source", "")))}" '
            f'data-target="{escape(str(edge.get("target", "")))}" '
            f'data-caption="{escape(str(edge.get("caption", "")))}" '
            f'data-frequency="{escape(str(edge.get("frequency", "")))}" '
            f'data-median="{escape(edge_median_label)}" '
            f'data-p90="{escape(edge_p90_label)}" '
            f'data-share="{escape(edge_share_label)}" '
            f'data-bucket="{escape(str(edge.get("conformance_bucket", "")))}" '
            f'data-severity="{escape(str(edge.get("severity", "")))}" '
            f'data-base-opacity="{opacity}" '
            f'data-base-stroke="{base_stroke_width:.1f}" '
            f'data-marker-id="{escape(marker_id)}" '
            'style="cursor:pointer;">'
            f"<title>{escape(' | '.join(label))}</title></path>"
        )
        if edge.get("show_label") and detail_level != "executive":
            freq_label = (
                f"{edge['share_pct']:.1f}%"
                if "activit" in conformance_lens.lower() and edge.get("share_pct") is not None
                else f"{edge['frequency']:,}"
            )
            secondary_label = (
                f"{edge['share_pct']:.1f}% share" if detail_level == "research" and edge.get("share_pct") is not None else None
            )
            label_width = float(edge.get("label_width", render_profile.get("label_width", 76.0)))
            label_height = float(edge.get("label_height", 32.0 if secondary_label else 20.0))
            label_y = -label_height / 2
            parts.append(
                f'<g transform="translate({edge["label_x"]:.1f},{edge["label_y"]:.1f})">'
                f'<rect x="{-label_width / 2.0:.1f}" y="{label_y:.1f}" width="{label_width:.1f}" height="{label_height:.1f}" rx="6" ry="6" fill="#ffffff" fill-opacity="0.97" stroke="#d4dce4" stroke-width="0.8"/>'
                f'<text x="0" y="3" text-anchor="middle" font-size="{edge_label_font:.1f}" font-weight="700" fill="#20313c">{escape(freq_label)}</text>'
            )
            if secondary_label:
                parts.append(
                    f'<text x="0" y="14" text-anchor="middle" font-size="{edge_label_secondary_font:.1f}" fill="#697887">{escape(secondary_label)}</text>'
                )
            parts.append("</g>")
        parts.append("</g>")

    for node in node_items:
        stroke_width = 2.1 if node["selected"] else 1.55 if node["neighbor"] else 1.15
        mix_summary = f"Sync {float(node.get('sync_pct', 0.0)):.0f}% · Log {float(node.get('log_move_pct', 0.0)):.0f}% · Model {float(node.get('model_move_pct', 0.0)):.0f}%"
        if "activit" in conformance_lens.lower():
            title_lines = [
                node["business_label"],
                f"{node['cases']:,} cases",
                f"Path {float(node.get('path_pct', 0.0)):.1f}% · Activity {float(node.get('activity_pct', 0.0)):.1f}%",
                f"{node['occurrences']:,} occurrences" if node.get("occurrences") is not None else f"Severity: {node['severity']}",
                f"Conformance: {node['conformance_bucket']}",
            ]
        else:
            title_lines = [
                node["business_label"],
                f"{node['cases']:,} cases",
                f"Path {float(node.get('path_pct', 0.0)):.1f}% · Activity {float(node.get('activity_pct', 0.0)):.1f}%",
                f"Severity: {node['severity']}",
                f"Conformance: {node['conformance_bucket']}",
            ]
        if detail_level != "executive":
            title_lines.append(mix_summary)
        if detail_level != "executive" and node.get("median_days") is not None:
            title_lines.append(f"Median next delay: {node['median_days']:.1f} d")
        if detail_level == "research" and node.get("p90_days") is not None:
            title_lines.append(f"P90 next delay: {node['p90_days']:.1f} d")
        node_classes = ["crpm-explorer-node"]
        if node["selected"]:
            node_classes.append("is-focus")
        elif node["neighbor"]:
            node_classes.append("is-neighbor")
        node_median = _safe_float(node.get("median_days"))
        node_p90 = _safe_float(node.get("p90_days"))
        node_median_label = "" if node_median is None else f"{node_median:.1f}"
        node_p90_label = "" if node_p90 is None else f"{node_p90:.1f}"
        parts.append(
            f'<g class="{" ".join(node_classes)}" filter="url(#workflow-explorer-shadow)" '
            f'data-node-id="{escape(str(node.get("id", "")))}" '
            f'data-label="{escape(str(node.get("business_label", "")))}" '
            f'data-cases="{escape(str(node.get("cases", "")))}" '
            f'data-median="{escape(node_median_label)}" '
            f'data-p90="{escape(node_p90_label)}" '
            f'data-bucket="{escape(str(node.get("conformance_bucket", "")))}" '
            f'data-severity="{escape(str(node.get("severity", "")))}" '
            f'data-branch="{escape(str(node.get("branch_role", "mainline")))}" '
            'style="cursor:pointer;">'
        )
        if node["selected"]:
            parts.append(
                f'<rect x="{node["x"] - 5:.1f}" y="{node["y"] - 5:.1f}" width="{node["width"] + 10:.1f}" height="{node["height"] + 10:.1f}" rx="{card_radius + 2.5:.1f}" ry="{card_radius + 2.5:.1f}" fill="none" stroke="{node["stroke"]}" stroke-width="2.4" opacity="0.46" filter="url(#workflow-explorer-glow)"/>'
            )
        card_fill = node.get("surface_fill", "#ffffff")
        chip_label = node["conformance_bucket"] if metric_coloring == "Conformance bucket" else node["severity"]
        node_chip_width = min(max(40.0, float(node["width"]) - 22.0), max(chip_width, min(86.0, len(chip_label) * 5.1 + 18.0)))
        chip_x = node["x"] + node["width"] - node_chip_width - 10.0
        chip_y = node["y"] + chip_offset_y
        parts.append(
            f'<rect x="{node["x"]:.1f}" y="{node["y"]:.1f}" width="{node["width"]:.1f}" height="{node["height"]:.1f}" rx="{card_radius:.1f}" ry="{card_radius:.1f}" fill="{card_fill}" stroke="{node["stroke"]}" stroke-width="{stroke_width:.1f}" opacity="0.998">'
            f"<title>{escape(' | '.join(title_lines))}</title></rect>"
            f'<rect x="{node["x"] + 9:.1f}" y="{node["y"] + 7:.1f}" width="2.2" height="{node["height"] - 14:.1f}" rx="1.1" ry="1.1" fill="{node["stroke"]}" fill-opacity="0.74"/>'
            f'<rect x="{chip_x:.1f}" y="{chip_y:.1f}" width="{node_chip_width:.1f}" height="{chip_height:.1f}" rx="{chip_height / 2.0:.1f}" ry="{chip_height / 2.0:.1f}" fill="{node["chip_fill"]}" fill-opacity="0.94" stroke="none"/>'
            f'<text x="{chip_x + node_chip_width / 2.0:.1f}" y="{chip_y + chip_height * 0.7:.2f}" text-anchor="middle" font-size="{chip_font_size:.1f}" font-weight="700" fill="{node["chip_ink"]}">{escape(chip_label)}</text>'
        )
        title_origin_y = float(node.get("title_origin_y", node["y"] + 22.0))
        timing_origin_y = float(node.get("timing_origin_y", title_origin_y + float(node.get("title_line_gap", 11.0)) + 6.0))
        text_origin_x = float(node.get("text_origin_x", node["x"] + 17.0))
        timing_origin_x = float(node.get("timing_origin_x", text_origin_x))
        footer_origin_y = float(node.get("footer_origin_y", timing_origin_y + float(node.get("timing_line_gap", 9.0)) + 6.0))
        title_gap = float(node.get("title_line_gap", 11.0))
        timing_gap = float(node.get("timing_line_gap", node.get("meta_line_gap", 9.2)))
        footer_gap = float(node.get("footer_line_gap", node.get("meta_line_gap", 9.8)))
        for line_index, line in enumerate(node.get("title_lines_render", [node["business_label"]])):
            parts.append(
                f'<text x="{text_origin_x:.1f}" y="{title_origin_y + line_index * title_gap:.1f}" font-size="{title_font_size:.1f}" font-weight="700" fill="{node["ink"]}">{escape(str(line))}</text>'
            )
        for line_index, line in enumerate(node.get("timing_lines_render", [])):
            parts.append(
                f'<text x="{timing_origin_x:.1f}" y="{timing_origin_y + line_index * timing_gap:.1f}" font-size="{float(node.get("timing_font_size", meta_font_size)):.1f}" fill="{node["ink"]}" fill-opacity="0.82">{escape(str(line))}</text>'
            )
        if node.get("show_ribbon") and float(node.get("ribbon_height_render", 0.0)) > 0.0:
            ribbon_x = float(node.get("ribbon_x", text_origin_x))
            ribbon_y = float(node.get("ribbon_y", timing_origin_y + 8.0))
            ribbon_width = float(node.get("ribbon_width_render", node["width"] - 28.0))
            ribbon_height = float(node.get("ribbon_height_render", 12.0))
            parts.append(
                f'<rect x="{ribbon_x:.1f}" y="{ribbon_y:.1f}" width="{ribbon_width:.1f}" height="{ribbon_height:.1f}" rx="{ribbon_height / 2.0:.1f}" ry="{ribbon_height / 2.0:.1f}" fill="#eef2f5" fill-opacity="0.96" stroke="#dde4ea" stroke-width="0.6"/>'
            )
            positive_segments = [segment for segment in node.get("mix_segments", []) if float(segment.get("pct", 0.0)) > 0.0]
            total_mix_pct = sum(float(segment.get("pct", 0.0)) for segment in positive_segments) or 100.0
            segment_cursor = ribbon_x
            for segment_index, segment in enumerate(positive_segments):
                remaining = (ribbon_x + ribbon_width) - segment_cursor
                if remaining <= 0.0:
                    break
                if segment_index == len(positive_segments) - 1:
                    segment_width = remaining
                else:
                    segment_width = max(4.0, ribbon_width * (float(segment.get("pct", 0.0)) / total_mix_pct))
                    segment_width = min(segment_width, remaining)
                parts.append(
                    f'<rect x="{segment_cursor:.1f}" y="{ribbon_y:.1f}" width="{segment_width:.1f}" height="{ribbon_height:.1f}" rx="{ribbon_height / 2.0:.1f}" ry="{ribbon_height / 2.0:.1f}" fill="{segment.get("fill", "#dce4ea")}" fill-opacity="0.96"/>'
                )
                if node.get("show_ribbon_labels") and segment_width >= 22.0:
                    ribbon_label = segment.get("short", "")
                    label_font = float(node.get("ribbon_label_font_size", 5.8))
                    parts.append(
                        f'<text x="{segment_cursor + segment_width / 2.0:.1f}" y="{ribbon_y + ribbon_height * 0.68:.1f}" text-anchor="middle" font-size="{label_font:.1f}" font-weight="700" fill="{segment.get("ink", "#20313c")}">{escape(str(ribbon_label))}</text>'
                    )
                segment_cursor += segment_width
        for line_index, line in enumerate(node.get("footer_lines_render", [])):
            parts.append(
                f'<text x="{text_origin_x:.1f}" y="{footer_origin_y + line_index * footer_gap:.1f}" font-size="{float(node.get("footer_font_size", meta_font_size)):.1f}" fill="{node["ink"]}" fill-opacity="0.8">{escape(str(line))}</text>'
            )
        parts.append("</g>")

    parts.extend(
        [
            "</g></svg></div></div>",
            "<script>",
            "(() => {",
            "const svg = document.getElementById('crpm-workflow-explorer-svg');",
            "const viewport = document.getElementById('crpm-workflow-content');",
            "const staticFrame = document.getElementById('crpm-workflow-static-frame');",
            "const selectionChip = document.getElementById('crpm-explorer-selection-chip');",
            "const liveTitle = document.getElementById('crpm-explorer-live-title');",
            "const liveMeta = document.getElementById('crpm-explorer-live-meta');",
            "const zoomInButton = document.getElementById('crpm-explorer-zoom-in');",
            "const zoomOutButton = document.getElementById('crpm-explorer-zoom-out');",
            "const clearFocusButton = document.getElementById('crpm-explorer-clear-focus');",
            "const resetViewButton = document.getElementById('crpm-explorer-reset-view');",
            "if (!svg || !viewport || !staticFrame || !liveTitle || !liveMeta) return;",
            "const shell = document.querySelector('.crpm-explorer-shell');",
            "const nodeEls = Array.from(svg.querySelectorAll('.crpm-explorer-node'));",
            "const edgeEls = Array.from(svg.querySelectorAll('.crpm-explorer-edge'));",
            "const viewBox = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal : { width: svg.clientWidth || 0, height: svg.clientHeight || 0 };",
            "const contentMinX = Number(svg.getAttribute('data-content-min-x') || '0');",
            "const contentMinY = Number(svg.getAttribute('data-content-min-y') || '0');",
            "const contentMaxX = Number(svg.getAttribute('data-content-max-x') || String(viewBox.width || 0));",
            "const contentMaxY = Number(svg.getAttribute('data-content-max-y') || String(viewBox.height || 0));",
            "const drawableMinX = Number(svg.getAttribute('data-drawable-min-x') || '12');",
            "const drawableMinY = Number(svg.getAttribute('data-drawable-min-y') || '12');",
            "const drawableMaxX = Number(svg.getAttribute('data-drawable-max-x') || String((viewBox.width || 0) - 12));",
            "const drawableMaxY = Number(svg.getAttribute('data-drawable-max-y') || String((viewBox.height || 0) - 12));",
            "let baselineScale = 1.0;",
            "let baselineTx = 0.0;",
            "let baselineTy = 0.0;",
            "let zoomFactor = 1.0;",
            "const localFocusHint = " + local_focus_hint_js + ";",
            "const computeBaselineFit = () => {",
            "  const availableWidth = Math.max(1, drawableMaxX - drawableMinX);",
            "  const availableHeight = Math.max(1, drawableMaxY - drawableMinY);",
            "  const boundsWidth = Math.max(1, contentMaxX - contentMinX);",
            "  const boundsHeight = Math.max(1, contentMaxY - contentMinY);",
            "  baselineScale = Math.min(availableWidth / boundsWidth, availableHeight / boundsHeight);",
            "  const fittedWidth = boundsWidth * baselineScale;",
            "  const fittedHeight = boundsHeight * baselineScale;",
            "  baselineTx = drawableMinX + ((availableWidth - fittedWidth) / 2) - (contentMinX * baselineScale);",
            "  baselineTy = drawableMinY + ((availableHeight - fittedHeight) / 2) - (contentMinY * baselineScale);",
            "};",
            "const apply = () => { viewport.setAttribute('transform', `translate(${baselineTx} ${baselineTy}) scale(${baselineScale * zoomFactor})`); };",
            "const setChip = (value) => { if (selectionChip) selectionChip.textContent = value; };",
            "const setOverview = () => {",
            "  setChip('Overview mode');",
            "  liveTitle.textContent = 'Overview mode';",
            "  liveMeta.textContent = localFocusHint;",
            "};",
            "const resetFocusClasses = () => {",
            "  nodeEls.forEach((el) => el.classList.remove('is-focus', 'is-neighbor', 'is-muted'));",
            "  edgeEls.forEach((el) => {",
            "    el.classList.remove('is-focus', 'is-neighbor', 'is-muted');",
            "    const baseOpacity = Number(el.getAttribute('data-base-opacity') || '0.4');",
            "    const baseStroke = Number(el.getAttribute('data-base-stroke') || '2');",
            "    el.setAttribute('opacity', String(baseOpacity));",
            "    el.setAttribute('stroke-width', String(baseStroke));",
            "  });",
            "};",
            "const fmtDays = (value) => { if (!value) return 'n/a'; return `${value} d`; };",
            "const focusNode = (nodeEl) => {",
            "  const nodeId = nodeEl.getAttribute('data-node-id') || '';",
            "  const relatedNodes = new Set([nodeId]);",
            "  resetFocusClasses();",
            "  edgeEls.forEach((edgeEl) => {",
            "    const source = edgeEl.getAttribute('data-source') || '';",
            "    const target = edgeEl.getAttribute('data-target') || '';",
            "    const touchesNode = source === nodeId || target === nodeId;",
            "    const baseStroke = Number(edgeEl.getAttribute('data-base-stroke') || '2');",
            "    if (touchesNode) {",
            "      edgeEl.classList.add('is-focus');",
            "      edgeEl.setAttribute('opacity', '0.98');",
            "      edgeEl.setAttribute('stroke-width', String(baseStroke + 1.4));",
            "      if (source) relatedNodes.add(source);",
            "      if (target) relatedNodes.add(target);",
            "    } else {",
            "      edgeEl.classList.add('is-muted');",
            "      edgeEl.setAttribute('opacity', '0.22');",
            "    }",
            "  });",
            "  nodeEls.forEach((el) => {",
            "    const id = el.getAttribute('data-node-id') || '';",
            "    if (id === nodeId) { el.classList.add('is-focus'); return; }",
            "    if (relatedNodes.has(id)) { el.classList.add('is-neighbor'); return; }",
            "    el.classList.add('is-muted');",
            "  });",
            "  const label = nodeEl.getAttribute('data-label') || 'Selected node';",
            "  const cases = nodeEl.getAttribute('data-cases') || '0';",
            "  const bucket = nodeEl.getAttribute('data-bucket') || 'Conformant';",
            "  const median = fmtDays(nodeEl.getAttribute('data-median'));",
            "  const neighborCount = Math.max(0, relatedNodes.size - 1);",
            "  setChip('Local node focus');",
            "  liveTitle.textContent = label;",
            "  liveMeta.textContent = `${cases} cases · ${bucket} · median ${median} · ${neighborCount} neighboring step${neighborCount === 1 ? '' : 's'}`;",
            "};",
            "const focusEdge = (edgeEl) => {",
            "  const source = edgeEl.getAttribute('data-source') || '';",
            "  const target = edgeEl.getAttribute('data-target') || '';",
            "  resetFocusClasses();",
            "  edgeEls.forEach((el) => {",
            "    const baseStroke = Number(el.getAttribute('data-base-stroke') || '2');",
            "    if (el === edgeEl) {",
            "      el.classList.add('is-focus');",
            "      el.setAttribute('opacity', '0.98');",
            "      el.setAttribute('stroke-width', String(baseStroke + 1.6));",
            "      return;",
            "    }",
            "    const sameSource = source && (el.getAttribute('data-source') || '') === source;",
            "    const sameTarget = target && (el.getAttribute('data-target') || '') === target;",
            "    if (sameSource || sameTarget) {",
            "      el.classList.add('is-neighbor');",
            "      el.setAttribute('opacity', '0.68');",
            "      return;",
            "    }",
            "    el.classList.add('is-muted');",
            "    el.setAttribute('opacity', '0.22');",
            "  });",
            "  nodeEls.forEach((el) => {",
            "    const id = el.getAttribute('data-node-id') || '';",
            "    if (id === source || id === target) { el.classList.add('is-neighbor'); return; }",
            "    el.classList.add('is-muted');",
            "  });",
            "  const caption = edgeEl.getAttribute('data-caption') || 'Selected edge';",
            "  const freq = edgeEl.getAttribute('data-frequency') || '0';",
            "  const bucket = edgeEl.getAttribute('data-bucket') || 'Conformant';",
            "  const median = fmtDays(edgeEl.getAttribute('data-median'));",
            "  setChip('Local edge focus');",
            "  liveTitle.textContent = caption;",
            "  liveMeta.textContent = `${freq} events · ${bucket} · median ${median} · endpoints ${source || 'n/a'} / ${target || 'n/a'}`;",
            "};",
            "nodeEls.forEach((nodeEl) => {",
            "  nodeEl.addEventListener('click', (event) => { event.stopPropagation(); focusNode(nodeEl); });",
            "});",
            "edgeEls.forEach((edgeEl) => {",
            "  edgeEl.addEventListener('click', (event) => { event.stopPropagation(); focusEdge(edgeEl); });",
            "});",
            "svg.addEventListener('click', () => { resetFocusClasses(); setOverview(); });",
            "const zoomBy = (factor) => { zoomFactor = Math.max(0.56, Math.min(1.7, zoomFactor * factor)); apply(); };",
            "const clearFocus = () => { resetFocusClasses(); setOverview(); };",
            "const resetView = () => { zoomFactor = 1.0; computeBaselineFit(); apply(); clearFocus(); };",
            "if (zoomInButton) zoomInButton.addEventListener('click', (event) => { event.stopPropagation(); zoomBy(1.14); });",
            "if (zoomOutButton) zoomOutButton.addEventListener('click', (event) => { event.stopPropagation(); zoomBy(0.88); });",
            "if (clearFocusButton) clearFocusButton.addEventListener('click', (event) => { event.stopPropagation(); clearFocus(); });",
            "if (resetViewButton) resetViewButton.addEventListener('click', (event) => { event.stopPropagation(); resetView(); });",
            "window.crpmZoom = zoomBy;",
            "window.crpmClearFocus = clearFocus;",
            "window.crpmReset = resetView;",
            "computeBaselineFit();",
            "apply();",
            "window.addEventListener('resize', () => { computeBaselineFit(); apply(); });",
            "if (window.ResizeObserver) {",
            "  const resizeObserver = new ResizeObserver(() => { computeBaselineFit(); apply(); });",
            "  resizeObserver.observe(shell || document.body);",
            "}",
            "const initialNode = nodeEls.find((el) => (el.getAttribute('data-node-id') || '') === " + selected_node_js + ");",
            "const initialEdge = edgeEls.find((el) => (el.getAttribute('data-edge-id') || '') === " + selected_edge_js + ");",
            "if (initialNode) { focusNode(initialNode); setChip('Pinned node'); liveMeta.textContent = `Pinned exact metrics · ${liveMeta.textContent}`; }",
            "else if (initialEdge) { focusEdge(initialEdge); setChip('Pinned edge'); liveMeta.textContent = `Pinned exact metrics · ${liveMeta.textContent}`; }",
            "else { setOverview(); }",
            "})();",
            "</script>",
            "</div></div>",
        ]
    )
    return "".join(parts)


def _script_json(value: Any) -> str:
    """Serialize a value for an inline script without allowing script termination."""

    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")


def _workflow_metric_coloring_hint(metric_coloring: str) -> str:
    hints = {
        "Conformance bucket": "Conformance color surfaces deviations first.",
        "Frequency": "Traffic color separates dominant and rare paths.",
        "Median delay": "Median-delay color highlights waiting burden.",
        "P90 delay": "P90-delay color highlights tail burden.",
    }
    return hints.get(metric_coloring, "Color follows the selected metric.")


def create_workflow_cytoscape_payload(payload: Mapping[str, Any] | pd.DataFrame) -> dict[str, Any]:
    """Build Cytoscape-compatible workflow elements from the conformance payload."""
    try:
        from streamlit_cytoscape import EdgeStyle, Event, NodeStyle
    except Exception:  # pragma: no cover - optional dependency handled by caller
        EdgeStyle = Event = NodeStyle = None

    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, None)
    ordered_nodes = _order_workflow_nodes(nodes_df)
    normalized_edges = _normalize_workflow_edges(edges_df, ordered_nodes)

    node_gap_y = 190
    base_x = 180
    elements_nodes: list[dict[str, Any]] = []
    node_style_map: dict[str, dict[str, str]] = {}
    for idx, (_, row) in enumerate(ordered_nodes.iterrows()):
        activity = str(row.get("activity", f"node-{idx}"))
        severity = str(row.get("severity", "Low"))
        conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
        style_key = f"node::{severity.lower()}::{conformance_bucket.lower().replace(' ', '-')}"
        node_style_map.setdefault(style_key, {"severity": severity, "conformance_bucket": conformance_bucket})
        elements_nodes.append(
            {
                "data": {
                    "id": activity,
                    "label": style_key,
                    "caption": str(row.get("display_name", activity)),
                    "activity": activity,
                    "cases": _safe_int(row.get("cases", 0)),
                    "occurrences": _safe_int(row.get("occurrences", 0)),
                    "median_days": _safe_float(row.get("median_next_delay_days")),
                    "p90_days": _safe_float(row.get("p90_next_delay_days")),
                    "severity": severity,
                    "conformance_bucket": conformance_bucket,
                },
                "position": {"x": base_x, "y": 100 + (idx * node_gap_y)},
            }
        )

    elements_edges: list[dict[str, Any]] = []
    edge_style_map: dict[str, dict[str, Any]] = {}
    for _, row in normalized_edges.iterrows():
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if not source or not target:
            continue
        severity = str(row.get("severity", "Low"))
        conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
        frequency = _safe_int(row.get("frequency", 0))
        median_days = _safe_float(row.get("median_days"))
        style_key = (
            f"edge::{severity.lower()}::{conformance_bucket.lower().replace(' ', '-')}"
            f"::{'deviating' if bool(row.get('is_deviating', False)) else 'conformant'}"
        )
        edge_style_map.setdefault(
            style_key,
            {
                "severity": severity,
                "conformance_bucket": conformance_bucket,
                "is_deviating": bool(row.get("is_deviating", False)),
            },
        )
        caption = f"{frequency:,} cases"
        elements_edges.append(
            {
                "data": {
                    "id": str(row.get("edge_uid", f"{source} -> {target}")),
                    "source": source,
                    "target": target,
                    "label": style_key,
                    "edge_uid": str(row.get("edge_uid", f"{source} -> {target}")),
                    "caption": caption,
                    "frequency": frequency,
                    "median_days": median_days,
                    "p90_days": _safe_float(row.get("p90_days")),
                    "severity": severity,
                    "conformance_bucket": conformance_bucket,
                    "share_pct": _safe_float(row.get("share_pct")),
                },
            }
        )

    node_styles = []
    edge_styles = []
    events = []
    if NodeStyle is not None and EdgeStyle is not None and Event is not None:
        node_color_map = {
            ("low", "conformant"): ("#edf4ef", "#5abf7a"),
            ("moderate", "conformant"): ("#f7f2dc", "#d3b14e"),
            ("high", "conformant"): ("#f7e7d8", "#cf8b61"),
            ("critical", "conformant"): ("#f5e3ea", "#b96f6a"),
            ("low", "log-deviation"): ("#f9f1dd", "#c9964a"),
            ("moderate", "log-deviation"): ("#f9f1dd", "#c9964a"),
            ("high", "log-deviation"): ("#f9e8d2", "#cf8b61"),
            ("critical", "log-deviation"): ("#f5e3ea", "#b96f6a"),
            ("low", "model-deviation"): ("#f5e3ea", "#b96f6a"),
            ("moderate", "model-deviation"): ("#f5e3ea", "#b96f6a"),
            ("high", "model-deviation"): ("#f5e3ea", "#b96f6a"),
            ("critical", "model-deviation"): ("#f5e3ea", "#b96f6a"),
        }
        edge_color_map = {
            "low": "#88b998",
            "moderate": "#d3b14e",
            "high": "#cf8b61",
            "critical": "#b96f6a",
        }

        for label, style_info in node_style_map.items():
            severity_key = str(style_info["severity"]).lower()
            bucket_key = str(style_info["conformance_bucket"]).lower().replace(" ", "-")
            background_color, border_color = node_color_map.get((severity_key, bucket_key), ("#edf4ef", "#5abf7a"))
            node_styles.append(
                NodeStyle(
                    label=label,
                    caption="caption",
                    custom_styles={
                        "background-color": background_color,
                        "border-width": 2,
                        "border-color": border_color,
                        "shape": "roundrectangle",
                        "width": 196,
                        "height": 94,
                        "text-wrap": "wrap",
                        "text-max-width": 156,
                        "font-size": 14,
                        "font-weight": 700,
                        "color": "#1f2c25",
                    },
                )
            )

        for label, style_info in edge_style_map.items():
            severity_key = str(style_info["severity"]).lower()
            color = edge_color_map.get(severity_key, "#88b998")
            edge_styles.append(
                EdgeStyle(
                    label=label,
                    caption="caption",
                    directed=True,
                    curve_style="bezier",
                    custom_styles={
                        "line-color": color,
                        "target-arrow-color": color,
                        "text-background-color": "#ffffff",
                        "text-background-opacity": 0.94,
                        "text-background-padding": 4,
                        "text-rotation": "autorotate",
                        "font-size": 11.5,
                        "color": "#f4f7fb",
                        "width": 3,
                        "line-style": "dashed" if style_info["is_deviating"] else "solid",
                    },
                )
            )

        events = [
            Event("selected_node", "tap", "node"),
            Event("selected_edge", "tap", "edge"),
        ]

    return {
        "elements": {"nodes": elements_nodes, "edges": elements_edges},
        "node_styles": node_styles,
        "edge_styles": edge_styles,
        "events": events,
        "layout": {"name": "preset", "fit": True, "padding": 32},
        "legend": legend_df,
        "overall_median_delay_days": overall_median,
    }


def create_workflow_conformance_sankey(nodes: pd.DataFrame, edges: pd.DataFrame) -> str:
    """Compatibility wrapper for older callers."""
    return render_workflow_conformance_svg({"nodes": nodes, "edges": edges, "legend": pd.DataFrame()})


def _coerce_workflow_payload(
    payload: Mapping[str, Any] | pd.DataFrame | None,
    edges: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Optional[float]]:
    if edges is not None:
        nodes_df = _ensure_workflow_df(payload)
        edges_df = _ensure_workflow_df(edges)
        return nodes_df, edges_df, pd.DataFrame(), None
    if isinstance(payload, Mapping):
        nodes_df = _ensure_workflow_df(payload.get("nodes"))
        edges_df = _ensure_workflow_df(payload.get("edges"))
        legend_df = _ensure_workflow_df(payload.get("legend"))
        overall_median = _safe_float(payload.get("overall_median_delay_days"))
        return nodes_df, edges_df, legend_df, overall_median
    nodes_df = _ensure_workflow_df(payload)
    return nodes_df, pd.DataFrame(), pd.DataFrame(), None


def _ensure_workflow_df(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    try:
        return pd.DataFrame(value).copy()
    except Exception:
        return pd.DataFrame()


def _order_workflow_nodes(nodes_df: pd.DataFrame) -> pd.DataFrame:
    if nodes_df.empty:
        return nodes_df
    working = nodes_df.copy()
    if "activity" not in working.columns:
        working["activity"] = working.get("display_name", working.index.astype(str))
    if "display_name" not in working.columns:
        working["display_name"] = working["activity"]
    _ensure_workflow_string_column(working, "conformance_bucket", "Conformant")
    _ensure_workflow_string_column(working, "severity", "Low")
    _ensure_workflow_string_column(working, "branch_role", "mainline")
    _ensure_workflow_string_column(working, "coverage_group", "dominant")
    if "coverage_pct" not in working.columns:
        case_values = pd.to_numeric(working.get("cases", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        max_cases = float(case_values.max() or 0.0)
        working["coverage_pct"] = (case_values / max_cases * 100.0) if max_cases > 0 else 0.0
    if "activity_pct" not in working.columns:
        occurrence_values = pd.to_numeric(working.get("occurrences", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        max_occurrences = float(occurrence_values.max() or 0.0)
        working["activity_pct"] = (
            occurrence_values / max_occurrences * 100.0
            if max_occurrences > 0
            else pd.to_numeric(working.get("coverage_pct", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        )
    if "lane" not in working.columns:
        working["lane"] = working["branch_role"].map(lambda value: "center" if str(value).strip().lower() == "mainline" else "left")
    else:
        working["lane"] = working["lane"].where(working["lane"].notna(), "")
        missing_lane_mask = working["lane"].astype(str).str.strip().eq("")
        if missing_lane_mask.any():
            working.loc[missing_lane_mask, "lane"] = working.loc[missing_lane_mask, "branch_role"].map(
                lambda value: "center" if str(value).strip().lower() == "mainline" else "left"
            )

    from crpm.screening import STEP_ORDER

    step_rank = {step: idx for idx, step in enumerate(STEP_ORDER)}
    existing_step_rank = (
        pd.to_numeric(working["step_rank"], errors="coerce")
        if "step_rank" in working.columns
        else pd.Series([float("nan")] * len(working), index=working.index, dtype=float)
    )
    if "step" in working.columns:
        step_values = working["step"].fillna("unmapped")
        mapped_step_rank = step_values.map(lambda value: step_rank.get(str(value), len(step_rank) + 1)).astype(float)
    else:
        mapped_step_rank = pd.Series([float("nan")] * len(working), index=working.index, dtype=float)
    missing_rank = existing_step_rank.isna()
    if missing_rank.any():
        existing_step_rank.loc[missing_rank] = mapped_step_rank.loc[missing_rank]
    still_missing_rank = existing_step_rank.isna()
    if still_missing_rank.any():
        LOGGER.warning(
            "Workflow explorer payload missing step_rank/step for %s node(s); using deterministic index fallback.",
            int(still_missing_rank.sum()),
        )
        existing_step_rank.loc[still_missing_rank] = pd.Series(
            range(int(still_missing_rank.sum())), index=existing_step_rank.index[still_missing_rank], dtype=float
        ) + float(len(step_rank) + 2)
    working["step_rank"] = existing_step_rank.astype(int)
    sort_cols = ["step_rank"]
    ascending = [True]
    if "cases" in working.columns:
        sort_cols.append("cases")
        ascending.append(False)
    if "occurrences" in working.columns:
        sort_cols.append("occurrences")
        ascending.append(False)
    if "display_name" in working.columns:
        sort_cols.append("display_name")
        ascending.append(True)
    return working.sort_values(by=sort_cols, ascending=ascending, kind="stable").reset_index(drop=True)


def workflow_edge_uid(
    edge_id: object, conformance_bucket: object = "Conformant", edge_type: object = "expected", branch_family: object = "mainline"
) -> str:
    """Build the semantic workflow edge identifier used by runtime and renderers."""
    return "|".join(
        token
        for token in (
            str(edge_id or "").strip(),
            str(conformance_bucket or "Conformant").strip(),
            str(edge_type or "expected").strip(),
            str(branch_family or "mainline").strip(),
        )
        if token
    )


def _select_analyst_workflow_edges(edges_df: pd.DataFrame, *, selected_edge_uid: str = "", limit: int = 18) -> pd.DataFrame:
    if edges_df.empty or len(edges_df) <= limit:
        return edges_df.copy()

    working = edges_df.copy()
    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    branch_roles = working.get("branch_role", pd.Series(["side"] * len(working), index=working.index)).astype(str).str.lower()
    buckets = working.get("conformance_bucket", pd.Series(["Conformant"] * len(working), index=working.index)).astype(str)
    edge_uids = working.get("edge_uid", pd.Series([""] * len(working), index=working.index)).astype(str)
    selected_mask = edge_uids.eq(str(selected_edge_uid)) if selected_edge_uid else pd.Series([False] * len(working), index=working.index)
    retained = working.loc[selected_mask | branch_roles.eq("mainline")].copy()

    remaining = working.drop(index=retained.index, errors="ignore").copy()
    if not remaining.empty:
        remaining_severity = remaining.get("severity", pd.Series(["Low"] * len(remaining), index=remaining.index))
        remaining_frequency = remaining.get("frequency", pd.Series([0] * len(remaining), index=remaining.index))
        remaining_share = remaining.get("share_pct", pd.Series([0] * len(remaining), index=remaining.index))
        remaining["_deviation_rank"] = buckets.loc[remaining.index].ne("Conformant").map({True: 0, False: 1})
        remaining["_severity_rank"] = remaining_severity.astype(str).map(severity_rank).fillna(3)
        remaining["_frequency_rank"] = remaining_frequency.fillna(0).astype(float) * -1
        remaining["_share_rank"] = remaining_share.fillna(0).astype(float) * -1
        remaining = remaining.sort_values(
            by=["_deviation_rank", "_severity_rank", "_frequency_rank", "_share_rank", "edge_id"],
            ascending=[True, True, True, True, True],
        ).drop(columns=["_deviation_rank", "_severity_rank", "_frequency_rank", "_share_rank"], errors="ignore")

    combined = pd.concat([retained, remaining], ignore_index=False)
    if len(combined) > limit and selected_edge_uid:
        selected_rows = combined.loc[combined.get("edge_uid", pd.Series(dtype=str)).astype(str).eq(str(selected_edge_uid))]
        rest = combined.drop(index=selected_rows.index, errors="ignore").head(max(limit - len(selected_rows), 0))
        combined = pd.concat([selected_rows, rest], ignore_index=False)
    return combined.head(limit).copy()


def _normalize_workflow_edges(edges_df: pd.DataFrame, nodes_df: pd.DataFrame) -> pd.DataFrame:
    if edges_df.empty:
        return edges_df
    working = edges_df.copy()
    if "source" not in working.columns or "target" not in working.columns:
        return pd.DataFrame()
    node_names = set(str(value) for value in nodes_df.get("activity", pd.Series(dtype=str)).astype(str).tolist())
    if node_names:
        working = working[working["source"].astype(str).isin(node_names) & working["target"].astype(str).isin(node_names)]
    working = working.reset_index(drop=True)
    if working.empty:
        return working
    if "frequency" not in working.columns:
        working["frequency"] = 0
    if "edge_id" not in working.columns:
        working["edge_id"] = working.apply(
            lambda row: f"{row.get('source', '')} -> {row.get('target', '')}",
            axis=1,
        )
    else:
        working["edge_id"] = working["edge_id"].astype(str)
    _ensure_workflow_string_column(working, "severity", "Low")
    _ensure_workflow_string_column(working, "conformance_bucket", "Conformant")
    _ensure_workflow_string_column(working, "coverage_group", "dominant")
    _ensure_workflow_string_column(working, "branch_role", "mainline")
    _ensure_workflow_string_column(working, "stroke_style", "solid")
    if "edge_uid" not in working.columns:
        working["edge_uid"] = working.apply(
            lambda row: workflow_edge_uid(
                (
                    str(row.get("edge_id", "")).strip()
                    if str(row.get("edge_id", "")).strip()
                    else f"{str(row.get('source', '')).strip()} -> {str(row.get('target', '')).strip()}"
                ),
                row.get("conformance_bucket", "Conformant"),
                row.get("edge_type", "expected"),
                row.get("branch_family", "mainline"),
            ),
            axis=1,
        )
    else:
        working["edge_uid"] = working["edge_uid"].astype(str)
    duplicate_uid_mask = working["edge_uid"].duplicated(keep=False)
    if duplicate_uid_mask.any():
        working.loc[duplicate_uid_mask, "edge_uid"] = working.loc[duplicate_uid_mask].apply(
            lambda row: workflow_edge_uid(
                row.get("edge_uid"),
                row.get("severity", "Low"),
                row.get("coverage_group", "dominant"),
                row.get("branch_role", "mainline"),
            ),
            axis=1,
        )
    if "share_pct" not in working.columns:
        total_edges = float(working["frequency"].sum() or 1.0)
        working["share_pct"] = working["frequency"].fillna(0).astype(float) / total_edges * 100.0
    return working


def _derive_nodes_from_edges(edges_df: pd.DataFrame) -> pd.DataFrame:
    if edges_df.empty:
        return pd.DataFrame()
    rows = []
    node_order: list[str] = []
    counters: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"cases": 0.0, "occurrences": 0.0})
    for _, row in edges_df.iterrows():
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        frequency = float(row.get("frequency", 0) or 0)
        for name in (source, target):
            if name and name not in node_order:
                node_order.append(name)
        if source:
            counters[source]["cases"] += frequency
            counters[source]["occurrences"] += frequency
        if target:
            counters[target]["cases"] += frequency * 0.5
            counters[target]["occurrences"] += frequency * 0.5
    for name in node_order:
        rows.append(
            {
                "step": "unmapped",
                "activity": name,
                "display_name": name,
                "cases": int(round(counters[name]["cases"])),
                "occurrences": int(round(counters[name]["occurrences"])),
                "median_next_delay_days": None,
                "p90_next_delay_days": None,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "coverage_pct": 0.0,
                "activity_pct": 0.0,
                "coverage_group": "dominant",
                "lane": "center",
            }
        )
    return pd.DataFrame(rows)


def _aggregate_explorer_nodes(nodes_df: pd.DataFrame) -> pd.DataFrame:
    if nodes_df.empty or "activity" not in nodes_df.columns:
        return nodes_df.copy()
    working = nodes_df.copy()
    working["activity"] = working["activity"].astype(str)
    if not working["activity"].duplicated().any():
        return working

    severity_rank = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
    bucket_rank = {"conformant": 1, "log deviation": 2, "model deviation": 3}

    rows: list[dict[str, Any]] = []
    for activity, group in working.groupby("activity", sort=False):
        group = group.copy()
        if "cases" in group.columns:
            case_weights = pd.to_numeric(group["cases"], errors="coerce").fillna(0.0)
        else:
            case_weights = pd.Series([0.0] * len(group.index), index=group.index)
        anchor_idx = case_weights.idxmax() if float(case_weights.max()) > 0 else group.index[0]
        anchor = group.loc[anchor_idx]

        if "severity" in group.columns:
            sev_idx = group["severity"].astype(str).str.lower().map(severity_rank).fillna(0).idxmax()
            severity_value = str(group.loc[sev_idx].get("severity", anchor.get("severity", "Low")))
        else:
            severity_value = str(anchor.get("severity", "Low"))

        if "conformance_bucket" in group.columns:
            bucket_idx = group["conformance_bucket"].astype(str).str.lower().map(bucket_rank).fillna(0).idxmax()
            bucket_value = str(group.loc[bucket_idx].get("conformance_bucket", anchor.get("conformance_bucket", "Conformant")))
        else:
            bucket_value = str(anchor.get("conformance_bucket", "Conformant"))

        branch_role = str(anchor.get("branch_role", "mainline"))
        lane_value = str(anchor.get("lane", "center" if branch_role == "mainline" else "left")).lower()
        step_rank_value = _safe_int(anchor.get("step_rank", 999))

        neighbor_union: set[str] = set()
        if "neighbor_ids" in group.columns:
            for values in group["neighbor_ids"]:
                if isinstance(values, (list, tuple, set)):
                    neighbor_union.update(str(value) for value in values if value)

        def _sum_column(name: str) -> int:
            if name not in group.columns:
                return _safe_int(anchor.get(name))
            return _safe_int(pd.to_numeric(group[name], errors="coerce").fillna(0).sum())

        def _median_column(name: str) -> Optional[float]:
            if name not in group.columns:
                return _safe_float(anchor.get(name))
            numeric = pd.to_numeric(group[name], errors="coerce").dropna()
            return _safe_float(numeric.median()) if not numeric.empty else _safe_float(anchor.get(name))

        rows.append(
            {
                **anchor.to_dict(),
                "activity": activity,
                "display_name": anchor.get("display_name", activity),
                "business_label": anchor.get("business_label", anchor.get("display_name", activity)),
                "cases": _sum_column("cases"),
                "occurrences": _sum_column("occurrences"),
                "median_next_delay_days": _median_column("median_next_delay_days"),
                "p90_next_delay_days": _median_column("p90_next_delay_days"),
                "severity": severity_value,
                "conformance_bucket": bucket_value,
                "branch_role": branch_role,
                "lane": lane_value,
                "step_rank": step_rank_value,
                "sync_cases": _sum_column("sync_cases"),
                "log_move_cases": _sum_column("log_move_cases"),
                "model_move_cases": _sum_column("model_move_cases"),
                "conformance_mix_total_cases": _sum_column("conformance_mix_total_cases"),
                "sync_pct": 0.0,
                "log_move_pct": 0.0,
                "model_move_pct": 0.0,
                "neighbor_ids": sorted(neighbor_union),
            }
        )
    aggregated = pd.DataFrame(rows)
    if not aggregated.empty:
        totals = pd.to_numeric(aggregated.get("conformance_mix_total_cases", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        sync_counts = pd.to_numeric(aggregated.get("sync_cases", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        log_counts = pd.to_numeric(aggregated.get("log_move_cases", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        model_counts = pd.to_numeric(aggregated.get("model_move_cases", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        totals = totals.where(totals > 0.0, sync_counts + log_counts + model_counts)
        totals = totals.where(totals > 0.0, 1.0)
        aggregated["sync_pct"] = (sync_counts / totals * 100.0).round(1)
        aggregated["log_move_pct"] = (log_counts / totals * 100.0).round(1)
        aggregated["model_move_pct"] = (model_counts / totals * 100.0).round(1)
        aggregated["conformance_mix_total_cases"] = totals
    return _order_workflow_nodes(aggregated)


def _aggregate_explorer_edges(edges_df: pd.DataFrame, nodes_df: pd.DataFrame) -> pd.DataFrame:
    if edges_df.empty:
        return edges_df.copy()
    working = edges_df.copy()
    if "source" not in working.columns or "target" not in working.columns:
        return working

    working["source"] = working["source"].astype(str)
    working["target"] = working["target"].astype(str)
    node_ids = set(nodes_df.get("activity", pd.Series(dtype=str)).astype(str).tolist())
    if node_ids:
        working = working[working["source"].isin(node_ids) & working["target"].isin(node_ids)].copy()
    if working.empty:
        return working

    if "frequency" in working.columns:
        freq_series = pd.to_numeric(working["frequency"], errors="coerce").fillna(0.0)
    else:
        freq_series = pd.Series([1.0] * len(working.index), index=working.index)
    working["_freq_weight"] = freq_series.where(freq_series > 0, 1.0)

    severity_rank = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
    bucket_rank = {"conformant": 1, "log deviation": 2, "model deviation": 3}

    rows: list[dict[str, Any]] = []
    for edge_key, group in working.groupby(working.get("edge_uid", pd.Series(dtype=str)).astype(str), sort=False):
        group = group.copy()
        anchor_idx = group["_freq_weight"].idxmax()
        anchor = group.loc[anchor_idx]

        sev_idx = (
            group.get("severity", pd.Series(["Low"] * len(group.index), index=group.index))
            .astype(str)
            .str.lower()
            .map(severity_rank)
            .fillna(0)
            .idxmax()
        )
        severity_value = str(group.loc[sev_idx].get("severity", anchor.get("severity", "Low")))
        bucket_idx = (
            group.get("conformance_bucket", pd.Series(["Conformant"] * len(group.index), index=group.index))
            .astype(str)
            .str.lower()
            .map(bucket_rank)
            .fillna(0)
            .idxmax()
        )
        bucket_value = str(group.loc[bucket_idx].get("conformance_bucket", anchor.get("conformance_bucket", "Conformant")))

        total_frequency = _safe_int(pd.to_numeric(group.get("frequency", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if total_frequency <= 0:
            total_frequency = _safe_int(anchor.get("frequency", 0))

        def _weighted_avg(name: str) -> Optional[float]:
            if name not in group.columns:
                return _safe_float(anchor.get(name))
            values = pd.to_numeric(group[name], errors="coerce")
            valid_mask = values.notna()
            if not valid_mask.any():
                return _safe_float(anchor.get(name))
            weights = pd.to_numeric(group["_freq_weight"], errors="coerce").fillna(1.0)
            denom = float(weights[valid_mask].sum())
            if denom <= 0:
                return _safe_float(values[valid_mask].mean())
            return _safe_float(float((values[valid_mask] * weights[valid_mask]).sum()) / denom)

        rows.append(
            {
                **anchor.to_dict(),
                "source": str(anchor.get("source", "")),
                "target": str(anchor.get("target", "")),
                "edge_id": f"{anchor.get('source', '')} -> {anchor.get('target', '')}",
                "edge_uid": str(edge_key),
                "frequency": total_frequency,
                "median_days": _weighted_avg("median_days"),
                "p90_days": _weighted_avg("p90_days"),
                "stroke_weight": _weighted_avg("stroke_weight"),
                "severity": severity_value,
                "conformance_bucket": bucket_value,
            }
        )

    aggregated = pd.DataFrame(rows)
    if aggregated.empty:
        return aggregated
    total_edges = float(pd.to_numeric(aggregated.get("frequency", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() or 1.0)
    aggregated["share_pct"] = (
        pd.to_numeric(aggregated.get("frequency", pd.Series(dtype=float)), errors="coerce").fillna(0.0) / total_edges * 100.0
    )
    return aggregated.reset_index(drop=True)


def _ensure_workflow_string_column(df: pd.DataFrame, column: str, default: str) -> None:
    if column not in df.columns:
        df[column] = default
        return
    if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
        df[column] = df[column].astype("object")
    series = df[column]
    missing_mask = series.isna() | series.astype(str).str.strip().eq("")
    if missing_mask.any():
        df.loc[missing_mask, column] = default


def _workflow_svg_empty(message: str) -> str:
    return (
        '<div class="crpm-workflow-board">'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 300" width="100%" height="100%" '
        'style="display:block;width:100%;height:auto;" role="img" aria-label="Workflow conformance board empty state">'
        '<rect x="0" y="0" width="1080" height="300" rx="18" ry="18" fill="#ffffff" stroke="#d8d2e0" stroke-width="1.2"/>'
        '<text x="540" y="132" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700" fill="#21342b">'
        f"{escape(message)}"
        "</text>"
        '<text x="540" y="160" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#5d6a63">'
        "Load a filtered log to build the pathway board."
        "</text>"
        "</svg>"
        "</div>"
    )


def _workflow_display_name(row: pd.Series) -> str:
    from crpm.screening import humanize_activity_label

    return humanize_activity_label(str(row.get("display_name") or row.get("activity") or "Node")) or "Node"


def _workflow_business_label(row: pd.Series) -> str:
    from crpm.screening import humanize_activity_label

    label = str(row.get("business_label") or "").strip()
    if label:
        if "→" in label:
            left, right = [part.strip() for part in label.split("→", 1)]
            return f"{humanize_activity_label(left) or left} → {humanize_activity_label(right) or right}"
        return humanize_activity_label(label) or label
    if row.get("source") is not None or row.get("target") is not None:
        source = humanize_activity_label(str(row.get("source_label") or row.get("source") or "?")) or "?"
        target = humanize_activity_label(str(row.get("target_label") or row.get("target") or "?")) or "?"
        return f"{source} → {target}"
    return _workflow_display_name(row)


def _workflow_text_lines(lines: list[str], *, max_chars: int) -> list[str]:
    output: list[str] = []
    for line in lines:
        if not line:
            continue
        wrapped = wrap(line, width=max_chars, break_long_words=False, break_on_hyphens=False) or [line]
        output.extend(wrapped)
    return output or [""]


def _workflow_truncate_text(text: str, *, max_chars: int) -> str:
    text = str(text or "").strip()
    if max_chars <= 3 or len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _workflow_fit_text_lines(lines: list[str], *, max_chars: int, max_lines: int) -> list[str]:
    wrapped = _workflow_text_lines(lines, max_chars=max_chars)
    if len(wrapped) <= max_lines:
        return wrapped
    visible = wrapped[:max_lines]
    overflow = " ".join(segment for segment in wrapped[max_lines - 1 :] if segment).strip()
    visible[-1] = _workflow_truncate_text(overflow or visible[-1], max_chars=max_chars)
    return visible


def _legend_rows_from_payload(legend_df: pd.DataFrame, *, group: str | None = None) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if not legend_df.empty:
        filtered = legend_df
        if group and "group" in legend_df.columns:
            filtered = legend_df[legend_df["group"].astype(str) == group]
        for _, row in filtered.iterrows():
            rows.append(
                (
                    str(row.get("bucket", "Legend")),
                    str(row.get("meaning", "")),
                    str(row.get("severity", "Low")),
                )
            )
    if rows:
        return rows
    if group == "Conformance":
        return [
            ("Conformant", "Expected screening progression", "Conformant"),
            ("Log deviation", "Observed skip, loop, or reorder", "Log deviation"),
            ("Model deviation", "Unmapped or off-pathway activity", "Model deviation"),
        ]
    return [
        ("Low", "Delay near cohort baseline", "Low"),
        ("Moderate", "Delay requires monitoring", "Moderate"),
        ("High", "Delay materially above baseline", "High"),
        ("Critical", "Delay requires immediate attention", "Critical"),
    ]


def _workflow_metric_palette(row: Mapping[str, Any], metric_coloring: str, *, item_kind: str) -> dict[str, str]:
    metric_key = str(metric_coloring or "Conformance bucket").lower()
    severity = str(row.get("severity", "Low"))
    conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
    coverage_group = str(row.get("coverage_group", "mixed")).lower()
    severity_theme = _WORKFLOW_SEVERITY_THEME.get(severity, _WORKFLOW_SEVERITY_THEME["Low"])
    conformance_theme = _WORKFLOW_CONFORMANCE_THEME.get(conformance_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
    coverage_theme = {
        "dominant": {"fill": "#e8f0fd", "stroke": "#4f87d6", "ink": "#1d2e4b", "accent": "#8db6ef"},
        "mixed": {"fill": "#f7f1df", "stroke": "#d2a43e", "ink": "#3a311a", "accent": "#f1d48a"},
        "rare": {"fill": "#f8e5ec", "stroke": "#c96a8f", "ink": "#492533", "accent": "#efb1c7"},
    }.get(coverage_group, {"fill": "#f1eef5", "stroke": "#8f80a6", "ink": "#2f2740", "accent": "#cbc0dc"})

    if metric_key == "conformance bucket":
        theme = conformance_theme
    elif metric_key in {"frequency", "coverage"}:
        theme = coverage_theme
    elif metric_key in {"median delay", "median delay (days)", "p90 delay", "p90 delay (days)"}:
        theme = severity_theme
    else:
        theme = conformance_theme if item_kind == "edge" else severity_theme

    if item_kind == "edge":
        return {
            "fill": theme["fill"],
            "surface": theme["fill"],
            "stroke": theme["stroke"],
            "ink": theme["ink"],
            "accent": theme["accent"],
            "chip_fill": theme["fill"],
            "chip_ink": theme["ink"],
        }

    return {
        "fill": theme["fill"],
        "surface": "#ffffff",
        "stroke": theme["stroke"],
        "ink": "#20303a",
        "accent": theme["accent"],
        "chip_fill": theme["fill"],
        "chip_ink": theme["stroke"] if metric_key == "conformance bucket" else "#314150",
    }


def _legend_column(x: float, y: float, heading: str, rows: list[Any]) -> str:
    parts = [
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="700" fill="#21342b">{escape(heading)}</text>'
    ]
    row_y = y + 18
    for row in rows:
        if len(row) == 3 and row[2] in _WORKFLOW_SEVERITY_THEME:
            label, meaning, severity = row
            palette = _WORKFLOW_SEVERITY_THEME[str(severity)]
            parts.append(
                f'<rect x="{x:.1f}" y="{row_y - 10:.1f}" width="12" height="12" rx="3" ry="3" fill="{palette["stroke"]}"/>'
                f'<text x="{x + 18:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10.5" font-weight="700" fill="#21342b">{escape(str(label))}</text>'
                f'<text x="{x + 124:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="#5d6a63">{escape(str(meaning))}</text>'
            )
            row_y += 22
        elif len(row) == 3 and row[2] in _WORKFLOW_CONFORMANCE_THEME:
            label, meaning, severity = row
            palette = _WORKFLOW_CONFORMANCE_THEME[str(severity)]
            parts.append(
                f'<rect x="{x:.1f}" y="{row_y - 10:.1f}" width="12" height="12" rx="3" ry="3" fill="{palette["stroke"]}"/>'
                f'<text x="{x + 18:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10.5" font-weight="700" fill="#21342b">{escape(str(label))}</text>'
                f'<text x="{x + 124:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="#5d6a63">{escape(str(meaning))}</text>'
            )
            row_y += 22
        else:
            label, meaning, stroke = row
            parts.append(
                f'<rect x="{x:.1f}" y="{row_y - 10:.1f}" width="12" height="12" rx="3" ry="3" fill="{stroke}"/>'
                f'<text x="{x + 18:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10.5" font-weight="700" fill="#21342b">{escape(str(label))}</text>'
                f'<text x="{x + 124:.1f}" y="{row_y:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="#5d6a63">{escape(str(meaning))}</text>'
            )
            row_y += 22
    return "".join(parts)


def _safe_int(value: Any) -> int:
    try:
        if value is None or pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


__all__ = [
    "create_bottleneck_chart",
    "create_activity_duration_chart",
    "create_case_duration_histogram",
    "create_operational_flow_chart",
    "create_queue_stock_chart",
    "create_stage_aging_chart",
    "create_variant_frequency_chart",
    "create_variant_coverage_chart",
    "create_variant_coverage_comparison",
    "create_model_comparison_radar",
    "create_model_comparison_heatmap",
    "create_fitness_precision_scatter",
    "render_workflow_conformance_svg",
    "filter_workflow_payload",
    "create_workflow_interactive_payload",
    "render_workflow_explorer_html",
    "create_workflow_cytoscape_payload",
    "create_workflow_conformance_sankey",
    "workflow_edge_uid",
]
