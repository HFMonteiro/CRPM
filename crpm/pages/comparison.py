"""Comparison page for the staged CRPM refactor."""

from __future__ import annotations

import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.formatting import format_metric_value
from crpm.interpretations import assess_balanced_quality, assess_fitness, assess_precision
from crpm.pages.common import (
    render_empty_state,
    render_html_ranked_table,
    render_metric_card_grid,
    render_page_cockpit_topbar,
    render_plotly_chart,
    render_quiet_note,
)
from crpm.visualization import create_fitness_precision_scatter, create_model_comparison_heatmap


def render_comparison_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Model Comparison")
    st.caption("Compare discovery candidates across fitness, precision, and model complexity in one decision view.")
    if snapshot.comparison_df.empty:
        render_empty_state("No comparison results yet. Run the analysis from the sidebar to populate this page.")
        return

    comparison_df = snapshot.comparison_df.copy()
    sparse_comparison = len(comparison_df) < 4
    render_page_cockpit_topbar(
        snapshot,
        title="Model comparison cockpit",
        subtitle=(
            "Use the heatmap and exact table for small candidate sets; the scatter is more useful with four or more models."
            if sparse_comparison
            else "Use the scatter as the primary comparison view, then confirm exact values in the report table."
        ),
        meta=[
            snapshot.input_name or "No log loaded",
            f"{len(comparison_df):,} {'model candidate' if len(comparison_df) == 1 else 'model candidates'}",
        ],
    )
    display_df = comparison_df.copy()
    if "discovery_time_s" in display_df.columns:
        display_df["discovery_time_s"] = display_df["discovery_time_s"].map(lambda value: format_metric_value(value, kind="seconds"))

    best_fitness = (
        comparison_df.loc[comparison_df["alignment_fitness"].idxmax()]
        if "alignment_fitness" in comparison_df.columns and comparison_df["alignment_fitness"].notna().any()
        else None
    )
    best_precision = (
        comparison_df.loc[comparison_df["precision"].idxmax()]
        if "precision" in comparison_df.columns and comparison_df["precision"].notna().any()
        else None
    )
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
            f"Recommended starting point: {best_balanced['model_name']}. "
            + (
                "With so few models, use the heatmap and exact table rather than over-reading a scatter."
                if sparse_comparison
                else "Use the scatter for trade-offs and the table for exact metrics."
            )
        )

    if len(comparison_df) > 3:
        scatter_col, evidence_col = st.columns(2)
        with scatter_col:
            st.markdown("#### Fitness versus precision")
            render_plotly_chart(create_fitness_precision_scatter(comparison_df), key="shell_comparison_scatter")
        with evidence_col:
            st.markdown("#### Metrics heatmap")
            render_plotly_chart(
                create_model_comparison_heatmap(comparison_df, ["alignment_fitness", "token_fitness", "precision"]),
                key="shell_comparison_heatmap",
            )
    elif len(comparison_df) > 1:
        st.markdown("#### Metrics heatmap")
        render_plotly_chart(
            create_model_comparison_heatmap(comparison_df, ["alignment_fitness", "token_fitness", "precision"]),
            key="shell_comparison_heatmap",
        )

    comparison_table = display_df.rename(
        columns={
            "model_name": "Model",
            "algorithm": "Algorithm",
            "variant": "Variant",
            "parameter_profile_name": "Parameter profile",
            "parameter_profile_intended_use": "Intended use",
            "pm4py_variant": "PM4Py variant",
            "alignment_fitness": "Alignment fitness",
            "token_fitness": "Token fitness",
            "precision": "Precision",
            "discovery_time_s": "Discovery time",
            "num_places": "Places",
            "num_transitions": "Transitions",
            "num_arcs": "Arcs",
        }
    )
    with st.expander("Report/detail view", expanded=False):
        st.markdown("#### Comparison table")
        render_html_ranked_table(comparison_table, title="Model comparison", label_column="Model")
        _render_comparison_variable_guide()


def _render_comparison_variable_guide() -> None:
    """Explain the comparison table without making users infer metric semantics."""
    st.markdown(
        """
        <section class="crpm-variable-guide" aria-labelledby="comparison-variable-guide-title" data-qa="comparison-variable-guide">
            <div class="crpm-variable-guide__header">
                <div>
                    <h5 id="comparison-variable-guide-title">How to read the variables</h5>
                    <p>Scores range from 0 to 1. Higher is generally better for fitness and precision; read both together. Counts describe model structure, not model quality.</p>
                </div>
            </div>
            <div class="crpm-variable-guide__grid">
                <article class="crpm-variable-guide__group crpm-variable-guide__group--quality">
                    <h6>Quality</h6>
                    <dl>
                        <div><dt>Alignment fitness</dt><dd>How well the model replays the observed cases using alignments. 1.000 is a perfect fit.</dd></div>
                        <div><dt>Token fitness</dt><dd>Replay fitness based on token consumption and production. Use it as a complementary fitness check.</dd></div>
                        <div><dt>Precision</dt><dd>How much of the behaviour allowed by the model is actually seen in the log. Lower values suggest over-generalisation.</dd></div>
                    </dl>
                </article>
                <article class="crpm-variable-guide__group crpm-variable-guide__group--structure">
                    <h6>Structure</h6>
                    <dl>
                        <div><dt>Transitions</dt><dd>Number of transitions in the discovered Petri net, including activity and possible invisible transitions.</dd></div>
                        <div><dt>Places</dt><dd>Number of places used to represent state, routing and synchronisation in the Petri net.</dd></div>
                        <div><dt>Arcs</dt><dd>Number of directed connections between places and transitions. More arcs usually mean more structural detail.</dd></div>
                    </dl>
                </article>
                <article class="crpm-variable-guide__group crpm-variable-guide__group--configuration">
                    <h6>Configuration</h6>
                    <dl>
                        <div><dt>Model</dt><dd>Named discovery candidate produced from the current log, algorithm and parameter settings.</dd></div>
                        <div><dt>Algorithm / Variant</dt><dd>Discovery family and its selected implementation variant.</dd></div>
                        <div><dt>Parameter profile</dt><dd>Named preset controlling discovery parameters and making runs reproducible.</dd></div>
                        <div><dt>PM4Py variant</dt><dd>Variant identifier passed to the PM4Py discovery implementation.</dd></div>
                        <div><dt>Intended use</dt><dd>Short operational guidance for when the selected profile is a sensible starting point.</dd></div>
                        <div><dt>Discovery time</dt><dd>Elapsed time required to discover the model for the current filtered log.</dd></div>
                    </dl>
                </article>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
