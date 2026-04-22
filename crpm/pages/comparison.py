"""Comparison page for the staged CRPM refactor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.formatting import format_metric_value
from crpm.interpretations import assess_balanced_quality, assess_fitness, assess_precision
from crpm.pages.common import render_empty_state, render_html_ranked_table, render_metric_card_grid, render_plotly_chart, render_quiet_note
from crpm.visualization import create_fitness_precision_scatter, create_model_comparison_heatmap


def render_comparison_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Model Comparison")
    st.caption("Compare discovery candidates across fitness, precision, and model complexity with a human-first decision surface.")
    if snapshot.comparison_df.empty:
        render_empty_state("No comparison results yet. Run the analysis from the sidebar to populate this page.")
        return

    comparison_df = snapshot.comparison_df.copy()
    display_df = comparison_df.copy()
    if "discovery_time_s" in display_df.columns:
        display_df["discovery_time_s"] = display_df["discovery_time_s"].map(lambda value: format_metric_value(value, kind="seconds"))

    best_fitness = comparison_df.loc[comparison_df["alignment_fitness"].idxmax()] if "alignment_fitness" in comparison_df.columns and comparison_df["alignment_fitness"].notna().any() else None
    best_precision = comparison_df.loc[comparison_df["precision"].idxmax()] if "precision" in comparison_df.columns and comparison_df["precision"].notna().any() else None
    best_balanced = None
    if {"alignment_fitness", "precision"}.issubset(comparison_df.columns):
        balanced_index = (comparison_df["alignment_fitness"].fillna(0) + comparison_df["precision"].fillna(0)).idxmax()
        best_balanced = comparison_df.loc[balanced_index]

    if best_fitness is not None and best_precision is not None and best_balanced is not None:
        render_metric_card_grid(
            [
                {
                    "eyebrow": "Fitness",
                    "title": str(best_fitness["model_name"]),
                    "value": format_metric_value(best_fitness["alignment_fitness"], kind="score"),
                    "body": assess_fitness(best_fitness["alignment_fitness"])[2],
                    "tone": "accent",
                },
                {
                    "eyebrow": "Precision",
                    "title": str(best_precision["model_name"]),
                    "value": format_metric_value(best_precision["precision"], kind="score"),
                    "body": assess_precision(best_precision["precision"])[2],
                    "tone": "neutral",
                },
                {
                    "eyebrow": "Balance",
                    "title": str(best_balanced["model_name"]),
                    "value": format_metric_value(
                        (best_balanced.get("alignment_fitness", 0) + best_balanced.get("precision", 0)) / 2,
                        kind="score",
                    ),
                    "body": assess_balanced_quality(best_balanced.get("alignment_fitness", 0), best_balanced.get("precision", 0))[2],
                    "tone": "success",
                },
            ]
        )

    if best_balanced is not None:
        render_quiet_note(
            f"Recommended starting point: {best_balanced['model_name']}. Use the scatter for trade-offs and the table for exact metrics."
        )

    if len(comparison_df) > 1:
        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("#### Fitness versus precision")
            render_plotly_chart(create_fitness_precision_scatter(comparison_df), key="shell_comparison_scatter")
        with chart_cols[1]:
            st.markdown("#### Metrics heatmap")
            render_plotly_chart(
                create_model_comparison_heatmap(comparison_df, ["alignment_fitness", "token_fitness", "precision"]),
                key="shell_comparison_heatmap",
            )

    comparison_table = display_df.rename(
        columns={
            "model_name": "Model",
            "alignment_fitness": "Alignment fitness",
            "token_fitness": "Token fitness",
            "precision": "Precision",
            "discovery_time_s": "Discovery time",
            "num_places": "Places",
            "num_transitions": "Transitions",
            "num_arcs": "Arcs",
        }
    )
    st.markdown("#### Comparison table")
    render_html_ranked_table(comparison_table, title="Model comparison", label_column="Model")
