"""Visualization helpers for process mining analytics.

This module provides functions for creating interactive charts using Plotly.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Dict, List, Optional, Any, Mapping
from textwrap import wrap
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


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
        return _empty_figure("No bottleneck data available")

    df = bottleneck_df.head(top_n).copy()
    df["transition_label"] = df["transition"].map(_humanize_transition_label)

    # Convert to days for readability
    df["median_days"] = df["median_duration_s"] / 86400
    df["p90_days"] = df["p90_duration_s"] / 86400

    # Sort by median duration
    df = df.sort_values("median_days", ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df["transition_label"],
        x=df["median_days"],
        name="Median delay",
        orientation="h",
        marker=dict(color=CHART_THEME["warning"]),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Median delay: %{x:.1f} days<br>"
            "P90 delay: %{customdata[0]:.1f} days<extra></extra>"
        ),
        customdata=df[["p90_days"]].to_numpy(),
    ))

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

        fig.add_trace(go.Scatter(
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
        ))

    fig.add_trace(go.Scatter(
        x=df["median_duration_s_hours"],
        y=df["activity_label"],
        mode="markers",
        name="Median",
        marker=dict(color=CHART_THEME["median"], size=12, symbol="diamond"),
        hovertemplate="<b>%{y}</b><br>Median: %{x:.1f} h<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=df.get("avg_duration_s_hours", df["median_duration_s_hours"]),
        y=df["activity_label"],
        mode="markers",
        name="Average",
        marker=dict(color=CHART_THEME["warning"], size=9, symbol="circle"),
        hovertemplate="<b>%{y}</b><br>Average: %{x:.1f} h<extra></extra>",
    ))

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

    fig.add_trace(go.Violin(
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
        points=False
    ))

    # Add median, mean, and P90 lines
    fig.add_vline(x=median_val, line_dash="dash", line_color=CHART_THEME["accent"], line_width=2,
                  annotation_text=f"Median: {median_val:.4f} {unit_label}",
                  annotation_position="top")
    fig.add_vline(x=mean_val, line_dash="dot", line_color=CHART_THEME["secondary"], line_width=2,
                  annotation_text=f"Mean: {mean_val:.4f} {unit_label}",
                  annotation_position="top")
    fig.add_vline(x=p90_val, line_dash="dash", line_color=CHART_THEME["warning"], line_width=2,
                  annotation_text=f"P90: {p90_val:.4f} {unit_label}",
                  annotation_position="top")

    # Add interpretation text box
    outlier_pct = ((case_durations[duration_col] > p90_val).sum() / len(case_durations)) * 100
    p90_to_median_ratio = p90_val / median_val if median_val > 0 else 0

    interpretation = ""
    if p90_to_median_ratio >= 2.5:
        interpretation = (
            f"High outlier rate: {outlier_pct:.1f}% of cases exceed the P90 threshold."
        )
    elif p90_to_median_ratio >= 1.5:
        interpretation = (
            f"Moderate outlier rate: {outlier_pct:.1f}% of cases exceed the P90 threshold."
        )
    else:
        interpretation = "Stable duration profile: minimal outlier behaviour detected."

    fig.add_annotation(
        text=interpretation,
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=12, color=CHART_THEME["font_color"]),
        bgcolor=CHART_THEME["annotation_bg"],
        bordercolor=CHART_THEME["warning"],
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
    df["variant_short"] = df["variant_str"].apply(
        lambda x: (x[:40] + "...") if len(str(x)) > 40 else x
    )

    fig = go.Figure()

    # Use variant names as x-axis for better readability
    fig.add_trace(go.Bar(
        x=df["variant_short"],
        y=df["percentage"],
        marker=dict(
            color=df["percentage"],
            colorscale=[[0, "#e8e0f0"], [0.5, "#8e7aa8"], [1, "#365348"]],
            showscale=False,
            line=dict(color=CHART_THEME["surface_border"], width=1.5)
        ),
        customdata=df["frequency"],
        hovertemplate="<b>%{x}</b><br>Frequency: %{y:.2f}%<br>Cases: %{customdata:,}<extra></extra>",
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
    fig.add_trace(go.Scatter(
        x=variant_coverage.index + 1,
        y=variant_coverage["cumulative_percentage"],
        mode="lines+markers",
        marker=dict(size=8, color=CHART_THEME["secondary"], line=dict(width=2, color="white")),
        line=dict(width=3, color=CHART_THEME["secondary"]),
        fill="tozeroy",
        fillcolor="rgba(142, 122, 168, 0.18)",
        hovertemplate="<b>%{x} variants</b><br>Coverage: %{y:.2f}%<extra></extra>"
    ))

    # Add reference lines for coverage milestones
    fig.add_hline(y=50, line_dash="dot", line_color=CHART_THEME["muted_text"], opacity=0.5,
                  annotation_text="50%", annotation_position="right")
    fig.add_hline(y=80, line_dash="dash", line_color=CHART_THEME["warning"], line_width=2,
                  annotation_text="80% Coverage", annotation_position="right")
    fig.add_hline(y=90, line_dash="dot", line_color=CHART_THEME["muted_text"], opacity=0.5,
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

    fig.add_trace(go.Scatter(
        x=chart_df[fitness_col],
        y=chart_df[precision_col],
        mode="markers",
        marker=dict(size=12, color=CHART_THEME["secondary"], line=dict(color="#ffffff", width=1.2)),
        customdata=model_names,
        hovertemplate="<b>%{customdata}</b><br>Fitness: %{x:.3f}<br>Precision: %{y:.3f}<extra></extra>",
        name="Candidates",
        showlegend=False,
    ))

    if not highlight_df.empty:
        fig.add_trace(go.Scatter(
            x=highlight_df[fitness_col],
            y=highlight_df[precision_col],
            mode="markers",
            marker=dict(size=16, color=CHART_THEME["accent"], line=dict(color="#ffffff", width=1.8), symbol="diamond"),
            customdata=highlight_df.get("model_name", highlight_df.index).tolist(),
            hovertemplate="<b>%{customdata}</b><br>Fitness: %{x:.3f}<br>Precision: %{y:.3f}<extra></extra>",
            name="Recommended focus",
            showlegend=False,
        ))

    # Add quadrant shading and reference lines
    fitness_threshold = 0.85
    precision_threshold = 0.75

    # Ideal zone (top-right) - green
    fig.add_shape(type="rect",
                  x0=fitness_threshold, y0=precision_threshold, x1=1.0, y1=1.0,
                  fillcolor="rgba(86, 115, 104, 0.18)", opacity=0.18,
                  line=dict(width=0))

    # Overfitting zone (bottom-right) - yellow
    fig.add_shape(type="rect",
                  x0=fitness_threshold, y0=0, x1=1.0, y1=precision_threshold,
                  fillcolor="rgba(176, 122, 61, 0.10)", opacity=0.10,
                  line=dict(width=0))

    # Underfitting zone (top-left) - yellow
    fig.add_shape(type="rect",
                  x0=0, y0=precision_threshold, x1=fitness_threshold, y1=1.0,
                  fillcolor="rgba(176, 122, 61, 0.10)", opacity=0.10,
                  line=dict(width=0))

    # Poor quality zone (bottom-left) - red
    fig.add_shape(type="rect",
                  x0=0, y0=0, x1=fitness_threshold, y1=precision_threshold,
                  fillcolor="rgba(157, 95, 107, 0.12)", opacity=0.12,
                  line=dict(width=0))

    # Add reference lines
    fig.add_hline(y=precision_threshold, line_dash="dash", line_color=CHART_THEME["muted_text"],
                  annotation_text="Precision threshold (0.75)",
                  annotation_position="right")
    fig.add_vline(x=fitness_threshold, line_dash="dash", line_color=CHART_THEME["muted_text"],
                  annotation_text="Fitness threshold (0.85)",
                  annotation_position="top")

    # Add quadrant labels
    fig.add_annotation(x=0.925, y=0.875, text="Ideal zone",
                       showarrow=False, font=dict(size=10, color=CHART_THEME["accent"]))
    fig.add_annotation(x=0.925, y=0.35, text="Overfitting zone",
                       showarrow=False, font=dict(size=9, color=CHART_THEME["warning"]))
    fig.add_annotation(x=0.40, y=0.875, text="Underfitting zone",
                       showarrow=False, font=dict(size=9, color=CHART_THEME["warning"]))
    fig.add_annotation(x=0.40, y=0.35, text="Low quality zone",
                       showarrow=False, font=dict(size=9, color=CHART_THEME["danger"]))

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
    "Conformant": {"fill": "#dff1db", "stroke": "#7ab889"},
    "Log deviation": {"fill": "#f0db77", "stroke": "#d0a23f"},
    "Model deviation": {"fill": "#e39ac3", "stroke": "#c56f9f"},
}

_WORKFLOW_TIMING_THEME = [
    ("Very fast", "Below the cohort median band", "#4d7f56"),
    ("Fast-moderate", "Near the cohort median band", "#7ca15f"),
    ("Moderate-slow", "Above the cohort median band", "#d2a43e"),
    ("Very slow", "Well above the cohort median band", "#cf5b69"),
]


def render_workflow_conformance_svg(
    payload: Mapping[str, Any] | pd.DataFrame | None,
    edges: pd.DataFrame | None = None,
) -> str:
    """Render a deterministic SVG workflow board from workflow conformance payloads."""
    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, edges)
    ordered_nodes = _order_workflow_nodes(nodes_df)
    normalized_edges = _normalize_workflow_edges(edges_df, ordered_nodes)

    if ordered_nodes.empty and normalized_edges.empty:
        return _workflow_svg_empty("No workflow conformance structure available")

    if ordered_nodes.empty and not normalized_edges.empty:
        ordered_nodes = _derive_nodes_from_edges(normalized_edges)

    board_width = 1180
    center_x = board_width / 2
    lane_x = {
        "left": center_x - 285,
        "center": center_x,
        "right": center_x + 285,
    }
    mainline_width = 448.0
    branch_width = 208.0
    mainline_height = 110.0
    branch_height = 64.0
    top_margin = 44
    step_gap = 168
    branch_gap = 82

    step_groups: dict[int, list[pd.Series]] = defaultdict(list)
    for _, row in ordered_nodes.iterrows():
        step_groups[int(row.get("step_rank", 999) or 999)].append(row)

    nodes_layout: list[dict[str, Any]] = []
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

        for main_index, row in enumerate(mainline_rows):
            activity = str(row.get("activity", row.get("display_name", f"node-{step_rank}-{main_index}")))
            nodes_layout.append(
                {
                    "row": row,
                    "index": len(nodes_layout),
                    "activity": activity,
                    "x": lane_x["center"] - mainline_width / 2,
                    "y": base_y + (main_index * 12.0),
                    "width": mainline_width,
                    "height": mainline_height,
                }
            )

        for branch_index, row in enumerate(branch_rows):
            activity = str(row.get("activity", row.get("display_name", f"branch-{step_rank}-{branch_index}")))
            lane = str(row.get("lane", "left") or "left").lower()
            x = lane_x["right"] if lane == "right" else lane_x["left"]
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
        group.sort(key=lambda item: (
            node_positions[item["target"]]["index"],
            -_safe_int(item["row"].get("frequency", 0)),
            item["target"],
        ))
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
        '<marker id="workflow-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#51645a"/>',
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
        p90_days = _safe_float(row.get("p90_days"))
        share_pct = _safe_float(row.get("share_pct"))
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
            control_offset = 50.0 if str(row.get("branch_role", "mainline")) == "mainline" else 78.0
            bend_x = (source_x + target_x) / 2
            if source_lane == "left" or target_lane == "left":
                bend_x = min(bend_x, center_x - 66)
            if source_lane == "right" or target_lane == "right":
                bend_x = max(bend_x, center_x + 66)
            path = (
                f"M {source_x:.1f} {source_y:.1f} "
                f"C {source_x:.1f} {source_y + control_offset:.1f}, {bend_x:.1f} {((source_y + target_y) / 2) - 28:.1f}, {bend_x:.1f} {((source_y + target_y) / 2):.1f} "
                f"C {bend_x:.1f} {((source_y + target_y) / 2) + 28:.1f}, {target_x:.1f} {target_y - control_offset:.1f}, {target_x:.1f} {target_y:.1f}"
            )
            label_x = bend_x
            label_y = ((source_y + target_y) / 2) - 8

        is_deviating = bool(row.get("is_deviating")) or str(row.get("stroke_style", "")).lower() == "dashed"
        dash = ' stroke-dasharray="9 6"' if is_deviating else ""
        is_mainline_edge = str(row.get("branch_role", "mainline")) == "mainline"
        opacity = "0.94" if is_mainline_edge else "0.66"
        stroke_width = (3.0 if is_mainline_edge else 1.7) + min(freq / 25000.0, 4.2 if is_mainline_edge else 1.8)
        conf_bucket = str(row.get("conformance_bucket", "Conformant"))
        conf_theme = _WORKFLOW_CONFORMANCE_THEME.get(conf_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
        show_label = is_mainline_edge and freq >= max(220, int(max_frequency * 0.6))

        edge_id = str(row.get("edge_id", f'{item["source"]} -> {item["target"]}'))
        svg_parts.append(
            f'<path d="{path}" fill="none" stroke="{palette["stroke"]}" stroke-width="{stroke_width:.1f}" stroke-linecap="round"{dash} opacity="{opacity}" marker-end="url(#workflow-arrow)" data-edge-id="{escape(edge_id)}" data-edge-role="{escape(str(row.get("edge_type", "expected")))}"/>'
        )
        if show_label:
            edge_label = [f"{freq:,} cases" if freq else "0 cases"]
            if median_days is not None and freq >= 200:
                edge_label.append(f"{median_days:.1f} d")
            text_lines = _workflow_text_lines(edge_label, max_chars=14)
            label_width = max(84, min(152, max((len(line) for line in edge_label), default=8) * 8 + 16))
            label_height = 18 + max(0, len(text_lines) - 1) * 12 + 8
            svg_parts.append(
                f'<g transform="translate({label_x:.1f},{label_y:.1f})">'
                f'<rect x="{-label_width/2:.1f}" y="{-label_height/2:.1f}" width="{label_width:.1f}" height="{label_height:.1f}" rx="9" ry="9" fill="#ffffff" fill-opacity="0.95" stroke="{conf_theme["stroke"]}" stroke-width="1.0"/>'
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
        occurrences = _safe_int(row.get("occurrences", 0))
        median_delay = _safe_float(row.get("median_next_delay_days"))
        conformance_bucket = str(row.get("conformance_bucket", "Conformant"))
        conformance_theme = _WORKFLOW_CONFORMANCE_THEME.get(conformance_bucket, _WORKFLOW_CONFORMANCE_THEME["Conformant"])
        branch_role = str(row.get("branch_role", "mainline"))
        branch_family = str(row.get("branch_family", "mainline"))
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
    return f'<div class="crpm-workflow-board">{"".join(svg_parts)}</div>'


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
            normalized_edges.get("coverage_group", pd.Series(["dominant"] * len(normalized_edges))).astype(str).str.lower().isin(allowed_groups)
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
        if active_nodes:
            ordered_nodes = ordered_nodes[ordered_nodes["activity"].astype(str).isin(active_nodes)].copy()

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
            normalized_edges = normalized_edges.head(min(len(normalized_edges), 18)).copy()
        if not ordered_nodes.empty and not normalized_edges.empty:
            active_nodes = set(normalized_edges["source"].astype(str).tolist()) | set(normalized_edges["target"].astype(str).tolist())
            ordered_nodes = ordered_nodes[ordered_nodes["activity"].astype(str).isin(active_nodes)].copy()

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

    return {
        "nodes": ordered_nodes.reset_index(drop=True),
        "edges": normalized_edges.reset_index(drop=True),
        "legend": legend_df.copy(),
        "trace_profiles": filtered_trace_profiles.reset_index(drop=True),
        "overall_median_delay_days": overall_median,
        "summary": filtered_summary,
        "renderer_capabilities": dict(payload.get("renderer_capabilities", {})) if isinstance(payload, Mapping) else {},
        "detail_level": detail_key,
        "requested_coverage_view": coverage_key,
        "applied_coverage_view": coverage_key,
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
        return bool(node_ids & visible_node_ids) or bool(edge_ids & visible_edge_ids)

    return trace_profiles_df[trace_profiles_df.apply(_matches, axis=1)].copy()


def _workflow_view_summary(
    base_summary: Mapping[str, Any],
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    trace_profiles_df: pd.DataFrame,
) -> dict[str, Any]:
    if trace_profiles_df.empty:
        return {
            "cases_covered": 0,
            "events_covered": int(nodes_df.get("occurrences", pd.Series(dtype=float)).fillna(0).sum()) if not nodes_df.empty else 0,
            "dominant_path_share": 0.0,
            "deviation_share": 0.0,
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

    return {
        "cases_covered": int(len(trace_profiles_df.index)),
        "events_covered": int(pd.to_numeric(trace_profiles_df.get("event_count", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
        "dominant_path_share": dominant_variant_share,
        "deviation_share": deviation_share,
        "median_throughput_days": round(float(throughput_series.median()), 1) if not throughput_series.empty else base_summary.get("median_throughput_days"),
        "visible_nodes": int(len(nodes_df.index)),
        "visible_edges": int(len(edges_df.index)),
    }


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
    nodes_df, edges_df, legend_df, overall_median = _coerce_workflow_payload(payload, None)
    ordered_nodes = _order_workflow_nodes(nodes_df)
    normalized_edges = _normalize_workflow_edges(edges_df, ordered_nodes)

    if ordered_nodes.empty and normalized_edges.empty:
        return {"nodes": [], "edges": [], "legend": legend_df, "height": 520, "overall_median_delay_days": overall_median}
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
        step_groups[int(row.get("step_rank", 999) or 999)].append(row)

    sorted_steps = sorted(step_groups)
    step_gap = 248.0
    left_margin = 96.0
    mainline_width = 188.0 if detail_level == "executive" else 198.0
    branch_width = 156.0 if detail_level == "executive" else 166.0
    mainline_height = 76.0 if detail_level == "executive" else 88.0
    branch_height = 56.0 if detail_level == "executive" else 64.0
    vertical_gap = 20.0

    max_top_branches = 1
    max_bottom_branches = 1
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

    top_block_height = max(84.0, max_top_branches * (branch_height + vertical_gap))
    mainline_y = top_block_height + 72.0
    bottom_y = mainline_y + mainline_height + 96.0
    canvas_height = int(bottom_y + max_bottom_branches * (branch_height + vertical_gap) + 104.0)
    canvas_width = int(max(1160.0, left_margin * 2 + max(1, len(sorted_steps) - 1) * step_gap + mainline_width + 80.0))

    node_items: list[dict[str, Any]] = []
    node_map: dict[str, dict[str, Any]] = {}
    for step_index, step_rank in enumerate(sorted_steps):
        x_center = left_margin + step_index * step_gap + mainline_width / 2
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
            if str(row.get("branch_role", "mainline")) != "mainline"
            and str(row.get("lane", "left") or "left").lower() != "right"
        ]
        bottom_rows = [
            row
            for row in rows
            if str(row.get("branch_role", "mainline")) != "mainline"
            and str(row.get("lane", "left") or "left").lower() == "right"
        ]

        for main_index, row in enumerate(mainline_rows):
            activity = str(row.get("activity", f"node-{step_rank}-{main_index}"))
            palette = _workflow_metric_palette(row, metric_coloring, item_kind="node")
            is_neighbor = bool(selected_node and activity in node_neighbors.get(selected_node, set()))
            is_selected = activity == selected_node
            y = mainline_y + main_index * 10.0
            node_item = {
                "id": activity,
                "business_label": _workflow_business_label(row),
                "display_name": _workflow_display_name(row),
                "cases": _safe_int(row.get("cases", 0)),
                "occurrences": _safe_int(row.get("occurrences", 0)),
                "median_days": _safe_float(row.get("median_next_delay_days")),
                "p90_days": _safe_float(row.get("p90_next_delay_days")),
                "severity": str(row.get("severity", "Low")),
                "conformance_bucket": str(row.get("conformance_bucket", "Conformant")),
                "branch_role": "mainline",
                "lane_position": "mainline",
                "step_rank": step_rank,
                "x": x_center - mainline_width / 2,
                "y": y,
                "width": mainline_width,
                "height": mainline_height,
                "center_x": x_center,
                "center_y": y + mainline_height / 2,
                "stroke": palette["stroke"],
                "ink": palette["ink"],
                "accent": palette["accent"],
                "accent_fill": palette["fill"],
                "selected": is_selected,
                "neighbor": is_neighbor,
            }
            node_items.append(node_item)
            node_map[activity] = node_item

        for lane_rows, lane_position in ((top_rows, "top"), (bottom_rows, "bottom")):
            row_count = len(lane_rows)
            for lane_index, row in enumerate(lane_rows):
                activity = str(row.get("activity", f"branch-{step_rank}-{lane_position}-{lane_index}"))
                palette = _workflow_metric_palette(row, metric_coloring, item_kind="node")
                is_neighbor = bool(selected_node and activity in node_neighbors.get(selected_node, set()))
                is_selected = activity == selected_node
                if lane_position == "top":
                    y = mainline_y - 94.0 - (row_count - 1 - lane_index) * (branch_height + vertical_gap)
                else:
                    y = bottom_y + lane_index * (branch_height + vertical_gap)
                node_item = {
                    "id": activity,
                    "business_label": _workflow_business_label(row),
                    "display_name": _workflow_display_name(row),
                    "cases": _safe_int(row.get("cases", 0)),
                    "occurrences": _safe_int(row.get("occurrences", 0)),
                    "median_days": _safe_float(row.get("median_next_delay_days")),
                    "p90_days": _safe_float(row.get("p90_next_delay_days")),
                    "severity": str(row.get("severity", "Low")),
                    "conformance_bucket": str(row.get("conformance_bucket", "Conformant")),
                    "branch_role": str(row.get("branch_role", "branch")),
                    "lane_position": lane_position,
                    "step_rank": step_rank,
                    "x": x_center - branch_width / 2,
                    "y": y,
                    "width": branch_width,
                    "height": branch_height,
                    "center_x": x_center,
                    "center_y": y + branch_height / 2,
                    "stroke": palette["stroke"],
                    "ink": palette["ink"],
                    "accent": palette["accent"],
                    "accent_fill": palette["fill"],
                    "selected": is_selected,
                    "neighbor": is_neighbor,
                }
                node_items.append(node_item)
                node_map[activity] = node_item

    edge_items: list[dict[str, Any]] = []
    selected_edge_neighbors: set[str] = set()
    if selected_edge and not normalized_edges.empty:
        selected_edge_rows = normalized_edges[normalized_edges.get("edge_id", pd.Series(dtype=str)).astype(str) == selected_edge]
        if not selected_edge_rows.empty:
            selected_edge_neighbors.update(
                {
                    str(selected_edge_rows.iloc[0].get("source", "")),
                    str(selected_edge_rows.iloc[0].get("target", "")),
                }
            )

    max_frequency = max((_safe_int(row.get("frequency", 0)) for _, row in normalized_edges.iterrows()), default=0)
    for _, row in normalized_edges.iterrows():
        source = str(row.get("source", ""))
        target = str(row.get("target", ""))
        if source not in node_map or target not in node_map:
            continue
        source_item = node_map[source]
        target_item = node_map[target]
        edge_id = str(row.get("edge_id", f"{source} -> {target}"))
        palette = _workflow_metric_palette(row, metric_coloring, item_kind="edge")
        is_mainline = str(row.get("branch_role", "mainline")) == "mainline"
        is_selected = edge_id == selected_edge
        is_neighbor = bool(selected_node and (source == selected_node or target == selected_node)) or bool(
            selected_edge_neighbors and (source in selected_edge_neighbors or target in selected_edge_neighbors)
        )

        forward = target_item["center_x"] >= source_item["center_x"]
        source_y = source_item["center_y"]
        target_y = target_item["center_y"]
        if forward:
            start_x = source_item["x"] + source_item["width"]
            end_x = target_item["x"]
            distance = max(50.0, end_x - start_x)
            control = min(84.0, distance * 0.42)
            path = (
                f"M {start_x:.1f} {source_y:.1f} "
                f"C {start_x + control:.1f} {source_y:.1f}, {end_x - control:.1f} {target_y:.1f}, {end_x:.1f} {target_y:.1f}"
            )
            label_x = (start_x + end_x) / 2
            label_y = min(source_y, target_y) - (20.0 if is_mainline else 10.0)
        else:
            start_x = source_item["center_x"]
            end_x = target_item["center_x"]
            arc_y = min(source_y, target_y) - 88.0 if source_item["lane_position"] != "bottom" else max(source_y, target_y) + 88.0
            path = (
                f"M {start_x:.1f} {source_y:.1f} "
                f"C {start_x + 44:.1f} {arc_y:.1f}, {end_x - 44:.1f} {arc_y:.1f}, {end_x:.1f} {target_y:.1f}"
            )
            label_x = (start_x + end_x) / 2
            label_y = arc_y - 12.0 if arc_y < source_y else arc_y + 16.0

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
                "stroke_width": max(2.0, min(8.2, _safe_float(row.get("stroke_weight")) or (3.2 if is_mainline else 2.3))),
                "stroke": palette["stroke"],
                "accent": palette["accent"],
                "path": path,
                "label_x": label_x,
                "label_y": label_y,
                "selected": is_selected,
                "neighbor": is_neighbor,
                "show_label": is_mainline and _safe_int(row.get("frequency", 0)) >= max(220, int(max_frequency * 0.55)),
            }
        )

    return {
        "nodes": node_items,
        "edges": edge_items,
        "legend": legend_df,
        "height": max(600, canvas_height),
        "width": canvas_width,
        "overall_median_delay_days": overall_median,
        "selected_node_id": selected_node,
        "selected_edge_id": selected_edge,
        "metric_coloring": metric_coloring,
        "detail_level": detail_level,
        "lane_bands": {
            "top_y": max(56.0, mainline_y - 132.0),
            "mainline_y": mainline_y - 22.0,
            "bottom_y": bottom_y - 22.0,
        },
    }


def render_workflow_explorer_html(explorer_payload: Mapping[str, Any]) -> str:
    """Render an HTML/SVG process explorer with stable lanes and lightweight zoom controls."""
    node_items = list(explorer_payload.get("nodes", []))
    edge_items = list(explorer_payload.get("edges", []))
    metric_coloring = str(explorer_payload.get("metric_coloring", "Conformance bucket"))
    detail_level = str(explorer_payload.get("detail_level", "analyst")).lower()
    selected_node_id = str(explorer_payload.get("selected_node_id") or "").strip()
    selected_edge_id = str(explorer_payload.get("selected_edge_id") or "").strip()
    canvas_width = int(explorer_payload.get("width", 1080))
    canvas_height = int(explorer_payload.get("height", 520))
    lane_bands = explorer_payload.get("lane_bands", {}) if isinstance(explorer_payload.get("lane_bands"), Mapping) else {}
    top_band_y = float(lane_bands.get("top_y", 56.0))
    mainline_band_y = float(lane_bands.get("mainline_y", max(144.0, canvas_height * 0.44)))
    bottom_band_y = float(lane_bands.get("bottom_y", min(canvas_height - 120.0, mainline_band_y + 150.0)))
    top_band_height = max(72.0, mainline_band_y - top_band_y - 34.0)
    mainline_band_height = max(92.0, bottom_band_y - mainline_band_y - 26.0)
    bottom_band_height = max(72.0, canvas_height - bottom_band_y - 56.0)
    if not node_items and not edge_items:
        return (
            '<div class="crpm-workflow-explorer">'
            '<div style="padding:18px;border:1px solid #d8d2e0;border-radius:18px;background:#ffffff;color:#1f2c25;font-family:Segoe UI, Arial, sans-serif;">'
            "No workflow explorer could be built for this selection."
            "</div></div>"
        )

    if selected_node_id:
        selection_state = f"Focused node: {selected_node_id.replace('_', ' ').title()}"
    elif selected_edge_id:
        selection_state = "Focused edge"
    else:
        selection_state = "Overview mode"
    coloring_hint = _workflow_metric_coloring_hint(metric_coloring)
    density_hint = _workflow_density_hint(detail_level)

    parts = [
        '<div class="crpm-workflow-explorer" style="font-family:Segoe UI, Arial, sans-serif;">',
        "<style>"
        ".crpm-workflow-explorer{color:#1f2c25;}"
        ".crpm-explorer-shell{display:grid;gap:8px;}"
        ".crpm-explorer-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:0;padding:10px 12px;border:1px solid #d8d2e0;border-radius:18px;background:linear-gradient(180deg,#ffffff 0%,#f6f4fa 100%);box-shadow:0 10px 24px rgba(55,43,74,.06);}"
        ".crpm-explorer-toolbar__copy{min-width:0;display:grid;gap:5px;}"
        ".crpm-explorer-toolbar__title-row{display:flex;align-items:center;flex-wrap:wrap;gap:8px;}"
        ".crpm-explorer-toolbar__title{font-size:13px;font-weight:800;letter-spacing:.01em;color:#21342b;}"
        ".crpm-explorer-toolbar__sub{font-size:11px;line-height:1.4;color:#5d6a63;}"
        ".crpm-explorer-badge{display:inline-flex;align-items:center;padding:4px 9px;border-radius:999px;background:#eef2f8;border:1px solid #d5dae6;font-size:10px;font-weight:700;color:#30435f;}"
        "#crpm-explorer-selection-chip{background:linear-gradient(135deg,#e8eef8 0%,#eef4ff 100%);border-color:#c6d3ea;color:#2f4466;}"
        ".crpm-explorer-toolbar__actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;}"
        ".crpm-explorer-action{border:1px solid #d6d2df;background:#ffffff;border-radius:11px;padding:7px 11px;font-size:11px;font-weight:700;color:#22352d;cursor:pointer;box-shadow:0 6px 14px rgba(60,46,83,.05);transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease;}"
        ".crpm-explorer-action:hover{transform:translateY(-1px);box-shadow:0 10px 18px rgba(60,46,83,.09);border-color:#bcc6d7;}"
        ".crpm-explorer-action--reset{background:linear-gradient(135deg,#f6f8fc 0%,#edf3fb 100%);color:#29425e;}"
        ".crpm-explorer-status-line{display:flex;align-items:center;gap:8px;min-width:0;}"
        ".crpm-explorer-live-title{font-size:11px;font-weight:800;color:#22352d;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".crpm-explorer-live-meta{font-size:11px;color:#5d6a63;line-height:1.38;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".crpm-explorer-canvas{border:1px solid #d8d2e0;border-radius:20px;background:linear-gradient(180deg,#f8f6fb 0%,#ffffff 100%);overflow:hidden;box-shadow:0 10px 26px rgba(55,43,74,.05);}"
        ".crpm-explorer-node,.crpm-explorer-edge{transition:opacity .16s ease,filter .16s ease;}"
        ".crpm-explorer-node.is-muted,.crpm-explorer-edge.is-muted{opacity:.14;}"
        ".crpm-explorer-node.is-neighbor{opacity:.96;}"
        ".crpm-explorer-edge.is-neighbor{opacity:.78;}"
        ".crpm-explorer-node.is-focus,.crpm-explorer-edge.is-focus{opacity:1;filter:drop-shadow(0 0 10px rgba(82,113,170,.18));}"
        "</style>",
        '<div class="crpm-explorer-shell">',
        '<div class="crpm-explorer-toolbar" id="crpm-explorer-toolbar">',
        '<div class="crpm-explorer-toolbar__copy">',
        '<div class="crpm-explorer-toolbar__title-row">'
        '<div class="crpm-explorer-toolbar__title">Interactive workflow explorer</div>'
        f'<span id="crpm-explorer-selection-chip" class="crpm-explorer-badge">{escape(selection_state)}</span>'
        "</div>",
        f'<div class="crpm-explorer-toolbar__sub">{escape(coloring_hint)} · {escape(density_hint)} · layout stays left to right.</div>',
        '<div class="crpm-explorer-status-line">'
        '<div id="crpm-explorer-live-title" class="crpm-explorer-live-title">Overview mode</div>'
        '<div id="crpm-explorer-live-meta" class="crpm-explorer-live-meta">Click a node or edge in the canvas for quick local context. Exact ranked metrics remain in the inspector.</div>'
        "</div>",
        "</div>",
        '<div class="crpm-explorer-toolbar__actions">',
        '<button id="crpm-explorer-zoom-in" class="crpm-explorer-action" type="button">Zoom in</button>',
        '<button id="crpm-explorer-zoom-out" class="crpm-explorer-action" type="button">Zoom out</button>',
        '<button id="crpm-explorer-clear-focus" class="crpm-explorer-action" type="button">Clear focus</button>',
        '<button id="crpm-explorer-reset-view" class="crpm-explorer-action crpm-explorer-action--reset" type="button">Reset view</button>',
        "</div></div>",
        '<div class="crpm-explorer-canvas">'
        f'<svg id="crpm-workflow-explorer-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_width} {canvas_height}" width="100%" height="{canvas_height}" aria-label="Workflow process explorer" style="display:block;width:100%;height:{canvas_height}px;">',
        "<defs>",
        '<filter id="workflow-explorer-shadow" x="-20%" y="-20%" width="160%" height="160%">',
        '<feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#433655" flood-opacity="0.10"/>',
        "</filter>",
        '<filter id="workflow-explorer-glow" x="-30%" y="-30%" width="180%" height="180%">',
        '<feDropShadow dx="0" dy="0" stdDeviation="8" flood-color="#6d87b5" flood-opacity="0.26"/>',
        "</filter>",
        '<marker id="workflow-explorer-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#728179"/>',
        "</marker>",
        "</defs>",
        '<g id="crpm-workflow-viewport">',
        f'<rect x="24" y="{top_band_y:.1f}" width="{canvas_width - 48:.1f}" height="{top_band_height:.1f}" rx="22" ry="22" fill="#f3f0f8" fill-opacity="0.62"/>',
        f'<rect x="24" y="{mainline_band_y:.1f}" width="{canvas_width - 48:.1f}" height="{mainline_band_height:.1f}" rx="24" ry="24" fill="#eef4ff" fill-opacity="0.82"/>',
        f'<rect x="24" y="{bottom_band_y:.1f}" width="{canvas_width - 48:.1f}" height="{bottom_band_height:.1f}" rx="22" ry="22" fill="#f3f0f8" fill-opacity="0.62"/>',
        f'<line x1="40" y1="{top_band_y + top_band_height:.1f}" x2="{canvas_width - 40:.1f}" y2="{top_band_y + top_band_height:.1f}" stroke="#d8d3e3" stroke-width="1" stroke-dasharray="6 8"/>',
        f'<line x1="40" y1="{mainline_band_y + (mainline_band_height / 2):.1f}" x2="{canvas_width - 40:.1f}" y2="{mainline_band_y + (mainline_band_height / 2):.1f}" stroke="#a7b9d8" stroke-width="2" stroke-dasharray="9 8"/>',
        f'<line x1="40" y1="{bottom_band_y:.1f}" x2="{canvas_width - 40:.1f}" y2="{bottom_band_y:.1f}" stroke="#d8d3e3" stroke-width="1" stroke-dasharray="6 8"/>',
        f'<text x="44" y="{top_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#7c748a">Upper branches</text>',
        f'<text x="44" y="{mainline_band_y - 8:.1f}" font-size="11" font-weight="800" fill="#35527c">Mainline backbone</text>',
        f'<text x="44" y="{bottom_band_y - 8:.1f}" font-size="10.5" font-weight="700" fill="#7c748a">Lower branches</text>',
    ]

    for edge in edge_items:
        opacity = "1.0" if edge["selected"] else "0.78" if edge["neighbor"] else "0.40"
        dash = ' stroke-dasharray="9 6"' if str(edge.get("stroke_style", "solid")).lower() == "dashed" else ""
        label = [f'{edge["caption"]}', f'{edge["frequency"]:,} events']
        if detail_level == "research" and edge.get("median_days") is not None:
            label.append(f'median {edge["median_days"]:.1f} d')
        if detail_level == "research" and edge.get("p90_days") is not None:
            label.append(f'p90 {edge["p90_days"]:.1f} d')
        if detail_level != "executive" and edge.get("share_pct") is not None:
            label.append(f'{edge["share_pct"]:.1f}% share')
        edge_classes = ["crpm-explorer-edge"]
        if edge["selected"]:
            edge_classes.append("is-focus")
        elif edge["neighbor"]:
            edge_classes.append("is-neighbor")
        base_stroke_width = edge["stroke_width"] + (1.6 if edge["selected"] else 0)
        parts.append(
            f'<g><path class="{" ".join(edge_classes)}" d="{edge["path"]}" fill="none" stroke="{edge["stroke"]}" stroke-width="{base_stroke_width:.1f}" stroke-linecap="round" opacity="{opacity}" marker-end="url(#workflow-explorer-arrow)"{dash} '
            f'data-edge-id="{escape(str(edge.get("id", "")))}" '
            f'data-source="{escape(str(edge.get("source", "")))}" '
            f'data-target="{escape(str(edge.get("target", "")))}" '
            f'data-caption="{escape(str(edge.get("caption", "")))}" '
            f'data-frequency="{escape(str(edge.get("frequency", "")))}" '
            f'data-median="{escape("" if edge.get("median_days") is None else f"{edge["median_days"]:.1f}")}" '
            f'data-p90="{escape("" if edge.get("p90_days") is None else f"{edge["p90_days"]:.1f}")}" '
            f'data-share="{escape("" if edge.get("share_pct") is None else f"{edge["share_pct"]:.1f}")}" '
            f'data-bucket="{escape(str(edge.get("conformance_bucket", "")))}" '
            f'data-severity="{escape(str(edge.get("severity", "")))}" '
            f'data-base-opacity="{opacity}" '
            f'data-base-stroke="{base_stroke_width:.1f}" '
            'style="cursor:pointer;">'
            f'<title>{escape(" | ".join(label))}</title></path>'
        )
        if edge.get("show_label") and detail_level != "executive":
            freq_label = f"{edge['frequency']:,}"
            secondary_label = f"{edge['share_pct']:.1f}% share" if detail_level == "research" and edge.get("share_pct") is not None else None
            label_height = 36 if secondary_label else 24
            parts.append(
                f'<g transform="translate({edge["label_x"]:.1f},{edge["label_y"]:.1f})">'
                f'<rect x="-46" y="{-label_height/2:.1f}" width="92" height="{label_height}" rx="8" ry="8" fill="#ffffff" fill-opacity="0.96" stroke="{edge["stroke"]}" stroke-width="1"/>'
                f'<text x="0" y="4" text-anchor="middle" font-size="11" font-weight="700" fill="#20312a">{escape(freq_label)}</text>'
            )
            if secondary_label:
                parts.append(f'<text x="0" y="16" text-anchor="middle" font-size="9.5" fill="#5d6a63">{escape(secondary_label)}</text>')
            parts.append("</g>")
        parts.append("</g>")

    for node in node_items:
        stroke_width = 3.0 if node["selected"] else 2.4 if node["neighbor"] else 1.8
        cases_label = f"{node['cases']:,} cases"
        median_label = f"median {node['median_days']:.1f} d" if node.get("median_days") is not None else None
        p90_label = f"p90 {node['p90_days']:.1f} d" if node.get("p90_days") is not None else None
        title_lines = [
            node["business_label"],
            f'{node["cases"]:,} cases',
            f'Severity: {node["severity"]}',
            f'Conformance: {node["conformance_bucket"]}',
        ]
        if detail_level != "executive" and node.get("median_days") is not None:
            title_lines.append(f'Median next delay: {node["median_days"]:.1f} d')
        if detail_level == "research" and node.get("p90_days") is not None:
            title_lines.append(f'P90 next delay: {node["p90_days"]:.1f} d')
        node_classes = ["crpm-explorer-node"]
        if node["selected"]:
            node_classes.append("is-focus")
        elif node["neighbor"]:
            node_classes.append("is-neighbor")
        parts.append(
            f'<g class="{" ".join(node_classes)}" filter="url(#workflow-explorer-shadow)" '
            f'data-node-id="{escape(str(node.get("id", "")))}" '
            f'data-label="{escape(str(node.get("business_label", "")))}" '
            f'data-cases="{escape(str(node.get("cases", "")))}" '
            f'data-median="{escape("" if node.get("median_days") is None else f"{node["median_days"]:.1f}")}" '
            f'data-p90="{escape("" if node.get("p90_days") is None else f"{node["p90_days"]:.1f}")}" '
            f'data-bucket="{escape(str(node.get("conformance_bucket", "")))}" '
            f'data-severity="{escape(str(node.get("severity", "")))}" '
            f'data-branch="{escape(str(node.get("branch_role", "mainline")))}" '
            'style="cursor:pointer;">'
        )
        if node["selected"] or node["neighbor"]:
            halo_stroke = node["stroke"] if node["selected"] else "#b6b0c6"
            halo_opacity = "0.24" if node["selected"] else "0.14"
            parts.append(
                f'<rect x="{node["x"] - 6:.1f}" y="{node["y"] - 6:.1f}" width="{node["width"] + 12:.1f}" height="{node["height"] + 12:.1f}" rx="22" ry="22" fill="none" stroke="{halo_stroke}" stroke-width="2.8" opacity="{halo_opacity}" filter="url(#workflow-explorer-glow)"/>'
            )
        card_fill = "#ffffff" if str(node.get("branch_role", "mainline")) == "mainline" else "#f8f6fb"
        parts.append(
            f'<rect x="{node["x"]:.1f}" y="{node["y"]:.1f}" width="{node["width"]:.1f}" height="{node["height"]:.1f}" rx="18" ry="18" fill="{card_fill}" stroke="{node["stroke"]}" stroke-width="{stroke_width:.1f}" opacity="0.99">'
            f'<title>{escape(" | ".join(title_lines))}</title></rect>'
            f'<rect x="{node["x"]:.1f}" y="{node["y"]:.1f}" width="{node["width"]:.1f}" height="10" rx="18" ry="18" fill="{node["accent_fill"]}" fill-opacity="0.92"/>'
            f'<rect x="{node["x"] + 14:.1f}" y="{node["y"] + 16:.1f}" width="5" height="{node["height"] - 32:.1f}" rx="2.5" ry="2.5" fill="{node["stroke"]}" fill-opacity="0.75"/>'
            f'<text x="{node["x"] + 16:.1f}" y="{node["y"] + 30:.1f}" font-size="16" font-weight="700" fill="{node["ink"]}">{escape(node["business_label"])}</text>'
            f'<text x="{node["x"] + 28:.1f}" y="{node["y"] + 50:.1f}" font-size="12" fill="{node["ink"]}" fill-opacity="0.88">{escape(cases_label)}</text>'
        )
        if detail_level != "executive" and median_label is not None:
            parts.append(
                f'<text x="{node["x"] + 28:.1f}" y="{node["y"] + 68:.1f}" font-size="11" fill="{node["ink"]}" fill-opacity="0.76">{escape(median_label)}</text>'
            )
        if detail_level == "research" and p90_label is not None and node["height"] >= 92:
            parts.append(
                f'<text x="{node["x"] + 28:.1f}" y="{node["y"] + 84:.1f}" font-size="11" fill="{node["ink"]}" fill-opacity="0.72">{escape(p90_label)}</text>'
            )
        parts.append(
            f'<rect x="{node["x"] + node["width"] - 92:.1f}" y="{node["y"] + 14:.1f}" width="76" height="24" rx="12" ry="12" fill="{node["stroke"]}"/>'
            f'<text x="{node["x"] + node["width"] - 54:.1f}" y="{node["y"] + 30:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">{escape(node["severity"] if detail_level != "executive" else node["conformance_bucket"])}</text>'
            "</g>"
        )

    parts.extend(
        [
            "</g></svg></div>",
            "<script>",
            "(() => {",
            "const svg = document.getElementById('crpm-workflow-explorer-svg');",
            "const viewport = document.getElementById('crpm-workflow-viewport');",
            "const selectionChip = document.getElementById('crpm-explorer-selection-chip');",
            "const liveTitle = document.getElementById('crpm-explorer-live-title');",
            "const liveMeta = document.getElementById('crpm-explorer-live-meta');",
            "const zoomInButton = document.getElementById('crpm-explorer-zoom-in');",
            "const zoomOutButton = document.getElementById('crpm-explorer-zoom-out');",
            "const clearFocusButton = document.getElementById('crpm-explorer-clear-focus');",
            "const resetViewButton = document.getElementById('crpm-explorer-reset-view');",
            "if (!svg || !viewport || !liveTitle || !liveMeta) return;",
            "const nodeEls = Array.from(svg.querySelectorAll('.crpm-explorer-node'));",
            "const edgeEls = Array.from(svg.querySelectorAll('.crpm-explorer-edge'));",
            "let scale = 1;",
            "let tx = 0;",
            "let ty = 0;",
            "const apply = () => { viewport.setAttribute('transform', `translate(${tx} ${ty}) scale(${scale})`); };",
            "const setChip = (value) => { if (selectionChip) selectionChip.textContent = value; };",
            "const setOverview = () => {",
            "  setChip('Overview mode');",
            "  liveTitle.textContent = 'Overview mode';",
            "  liveMeta.textContent = 'Click a node or edge in the canvas for quick local context. Use the inspector for pinned detail.';",
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
            "      edgeEl.setAttribute('opacity', '1');",
            "      edgeEl.setAttribute('stroke-width', String(baseStroke + 1.7));",
            "      if (source) relatedNodes.add(source);",
            "      if (target) relatedNodes.add(target);",
            "    } else {",
            "      edgeEl.classList.add('is-muted');",
            "      edgeEl.setAttribute('opacity', '0.15');",
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
            "  setChip('Focused node');",
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
            "      el.setAttribute('opacity', '1');",
            "      el.setAttribute('stroke-width', String(baseStroke + 1.9));",
            "      return;",
            "    }",
            "    const sameSource = source && (el.getAttribute('data-source') || '') === source;",
            "    const sameTarget = target && (el.getAttribute('data-target') || '') === target;",
            "    if (sameSource || sameTarget) {",
            "      el.classList.add('is-neighbor');",
            "      el.setAttribute('opacity', '0.75');",
            "      return;",
            "    }",
            "    el.classList.add('is-muted');",
            "    el.setAttribute('opacity', '0.14');",
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
            "  setChip('Focused edge');",
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
            "const zoomBy = (factor) => { scale = Math.max(0.65, Math.min(1.85, scale * factor)); apply(); };",
            "const clearFocus = () => { resetFocusClasses(); setOverview(); };",
            "const resetView = () => { scale = 1; tx = 0; ty = 0; apply(); clearFocus(); };",
            "if (zoomInButton) zoomInButton.addEventListener('click', (event) => { event.stopPropagation(); zoomBy(1.15); });",
            "if (zoomOutButton) zoomOutButton.addEventListener('click', (event) => { event.stopPropagation(); zoomBy(0.87); });",
            "if (clearFocusButton) clearFocusButton.addEventListener('click', (event) => { event.stopPropagation(); clearFocus(); });",
            "if (resetViewButton) resetViewButton.addEventListener('click', (event) => { event.stopPropagation(); resetView(); });",
            "window.crpmZoom = zoomBy;",
            "window.crpmClearFocus = clearFocus;",
            "window.crpmReset = resetView;",
            "apply();",
            "const initialNode = nodeEls.find((el) => (el.getAttribute('data-node-id') || '') === "
            + repr(selected_node_id)
            + ");",
            "const initialEdge = edgeEls.find((el) => (el.getAttribute('data-edge-id') || '') === "
            + repr(selected_edge_id)
            + ");",
            "if (initialNode) { focusNode(initialNode); }",
            "else if (initialEdge) { focusEdge(initialEdge); }",
            "else { setOverview(); }",
            "})();",
            "</script>",
            "</div></div>",
        ]
    )
    return "".join(parts)


def _workflow_metric_coloring_hint(metric_coloring: str) -> str:
    hints = {
        "Conformance bucket": "Coloring emphasizes conformance buckets so deviations surface immediately.",
        "Frequency": "Coloring emphasizes traffic density so dominant branches stand out from rare paths.",
        "Median delay": "Coloring emphasizes median delay so queue-heavy steps read hotter than fast transitions.",
        "P90 delay": "Coloring emphasizes tail delay so volatile or long-wait branches stand out.",
    }
    return hints.get(metric_coloring, "Coloring follows the selected analytical metric.")


def _workflow_density_hint(detail_level: str) -> str:
    hints = {
        "executive": "Executive density keeps cards quiet and count-first for presentation.",
        "analyst": "Analyst density balances counts and timing for investigation.",
        "research": "Research density keeps richer delay labels visible on cards and links.",
    }
    return hints.get(str(detail_level).lower(), "Density follows the selected inspection level.")


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
            f"::{ 'deviating' if bool(row.get('is_deviating', False)) else 'conformant' }"
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
                    "id": f"{source} -> {target}",
                    "source": source,
                    "target": target,
                    "label": style_key,
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
    if "lane" not in working.columns:
        working["lane"] = working["branch_role"].map(
            lambda value: "center" if str(value).strip().lower() == "mainline" else "left"
        )
    else:
        working["lane"] = working["lane"].where(working["lane"].notna(), "")
        missing_lane_mask = working["lane"].astype(str).str.strip().eq("")
        if missing_lane_mask.any():
            working.loc[missing_lane_mask, "lane"] = working.loc[missing_lane_mask, "branch_role"].map(
                lambda value: "center" if str(value).strip().lower() == "mainline" else "left"
            )

    from crpm.screening import STEP_ORDER

    step_rank = {step: idx for idx, step in enumerate(STEP_ORDER)}
    if "step" in working.columns:
        step_values = working["step"].fillna("unmapped")
    else:
        step_values = pd.Series(["unmapped"] * len(working), index=working.index)
    working["_step_rank"] = step_values.map(lambda value: step_rank.get(str(value), len(step_rank) + 1))
    sort_cols = ["_step_rank"]
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
    return working.sort_values(by=sort_cols, ascending=ascending, kind="stable").drop(columns=["_step_rank"], errors="ignore").reset_index(drop=True)


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
    _ensure_workflow_string_column(working, "severity", "Low")
    _ensure_workflow_string_column(working, "conformance_bucket", "Conformant")
    _ensure_workflow_string_column(working, "coverage_group", "dominant")
    _ensure_workflow_string_column(working, "branch_role", "mainline")
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
                "coverage_group": "dominant",
                "lane": "center",
            }
        )
    return pd.DataFrame(rows)


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
        f'{escape(message)}'
        '</text>'
        '<text x="540" y="160" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#5d6a63">'
        'Load a filtered log to build the pathway board.'
        '</text>'
        '</svg>'
        '</div>'
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
        return {
            "fill": conformance_theme["fill"],
            "stroke": conformance_theme["stroke"],
            "ink": severity_theme["ink"],
            "accent": severity_theme["accent"],
        }
    if metric_key in {"frequency", "coverage"}:
        return coverage_theme
    if metric_key in {"median delay", "median delay (days)", "p90 delay", "p90 delay (days)"}:
        return severity_theme
    return {
        "fill": severity_theme["fill"] if item_kind == "node" else conformance_theme["fill"],
        "stroke": severity_theme["stroke"] if item_kind == "edge" else conformance_theme["stroke"],
        "ink": severity_theme["ink"],
        "accent": severity_theme["accent"],
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
]
