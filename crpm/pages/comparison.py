"""Comparison page for the staged CRPM refactor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.interpretations import assess_balanced_quality, assess_fitness, assess_precision
from crpm.pages.common import render_empty_state, render_plotly_chart, render_quiet_note
from crpm.visualization import create_fitness_precision_scatter, create_model_comparison_heatmap


def render_comparison_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Model Comparison")
    st.caption("Compare discovery candidates across fitness, precision, and model complexity with a human-first decision surface.")
    if snapshot.comparison_df.empty:
        render_empty_state("No comparison results yet. Run the analysis from the sidebar to populate this page.")
        return

    comparison_df = snapshot.comparison_df.copy()
    display_df = comparison_df.copy()
    for column in ("alignment_fitness", "token_fitness", "precision"):
        if column in display_df.columns:
            display_df[column] = display_df[column].map(lambda value: f"{value:.4f}" if pd.notna(value) else "N/A")
    if "discovery_time_s" in display_df.columns:
        display_df["discovery_time_s"] = display_df["discovery_time_s"].map(lambda value: f"{value:.2f}s")

    best_fitness = comparison_df.loc[comparison_df["alignment_fitness"].idxmax()] if "alignment_fitness" in comparison_df.columns and comparison_df["alignment_fitness"].notna().any() else None
    best_precision = comparison_df.loc[comparison_df["precision"].idxmax()] if "precision" in comparison_df.columns and comparison_df["precision"].notna().any() else None
    best_balanced = None
    if {"alignment_fitness", "precision"}.issubset(comparison_df.columns):
        balanced_index = (comparison_df["alignment_fitness"].fillna(0) + comparison_df["precision"].fillna(0)).idxmax()
        best_balanced = comparison_df.loc[balanced_index]

    st.markdown("#### Recommendation strip")
    metric_cols = st.columns(3)
    with metric_cols[0]:
        if best_fitness is not None:
            fitness_assessment = assess_fitness(best_fitness["alignment_fitness"])
            st.metric("Best fitness", best_fitness["model_name"], f"{best_fitness['alignment_fitness']:.4f}")
            st.caption(fitness_assessment[2])
    with metric_cols[1]:
        if best_precision is not None:
            precision_assessment = assess_precision(best_precision["precision"])
            st.metric("Best precision", best_precision["model_name"], f"{best_precision['precision']:.4f}")
            st.caption(precision_assessment[2])
    with metric_cols[2]:
        if best_balanced is not None:
            balanced_score = (best_balanced.get("alignment_fitness", 0) + best_balanced.get("precision", 0)) / 2
            balanced_assessment = assess_balanced_quality(best_balanced.get("alignment_fitness", 0), best_balanced.get("precision", 0))
            st.metric("Best balance", best_balanced["model_name"], f"{balanced_score:.4f}")
            st.caption(balanced_assessment[2])

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

    st.markdown("#### Comparison table")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
