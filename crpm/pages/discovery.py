"""Discovery page for the staged CRPM refactor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import render_empty_state, render_quiet_note


def render_discovery_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Discovery")
    if not snapshot.discovery_results:
        render_empty_state("No discovered models yet. Run the analysis from the sidebar to populate this page.")
        return

    st.caption(
        f"Current analysis contains {snapshot.model_count} discovered models across {snapshot.case_count:,} cases and {snapshot.event_count:,} events."
    )
    recommended_name = _recommended_model_name(snapshot)
    if recommended_name:
        render_quiet_note(
            f"Recommended model to inspect first: {recommended_name}. Start there, then compare alternatives when you need a different fitness/precision trade-off."
        )

    models = list(snapshot.discovery_results.items())
    columns_per_row = 2 if len(models) <= 4 else 3
    for start_index in range(0, len(models), columns_per_row):
        row_items = models[start_index : start_index + columns_per_row]
        row_cols = st.columns(len(row_items))
        for column, (model_name, result) in zip(row_cols, row_items):
            with column:
                with st.container(border=True):
                    heading = f"{model_name} ⭐" if model_name == recommended_name else model_name
                    st.markdown(f"**{heading}**")
                    st.caption(f"{getattr(result, 'algorithm', 'N/A')} | {getattr(result, 'variant', 'N/A')}")
                    metric_cols = st.columns(2)
                    metric_cols[0].metric("Transitions", getattr(result, "num_transitions", 0))
                    metric_cols[1].metric("Places", getattr(result, "num_places", 0))
                    metric_cols = st.columns(2)
                    metric_cols[0].metric("Arcs", getattr(result, "num_arcs", 0))
                    metric_cols[1].metric(
                        "Discovery time",
                        f"{float(getattr(result, 'discovery_time_s', 0.0)):.2f}s",
                    )
                    st.caption(_model_tradeoff_summary(model_name, result, snapshot))

    rows = []
    for model_name, result in snapshot.discovery_results.items():
        rows.append(
            {
                "Model": model_name,
                "Algorithm": getattr(result, "algorithm", "N/A"),
                "Variant": getattr(result, "variant", "N/A"),
                "Discovery time (s)": round(float(getattr(result, "discovery_time_s", 0.0)), 3),
                "Transitions": getattr(result, "num_transitions", 0),
                "Places": getattr(result, "num_places", 0),
                "Arcs": getattr(result, "num_arcs", 0),
            }
        )

    st.markdown("#### Model summary table")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _recommended_model_name(snapshot: AnalysisSnapshot) -> str | None:
    if not snapshot.comparison_df.empty and {"model_name", "alignment_fitness", "precision"}.issubset(snapshot.comparison_df.columns):
        scores = snapshot.comparison_df["alignment_fitness"].fillna(0) + snapshot.comparison_df["precision"].fillna(0)
        if not scores.empty:
            return str(snapshot.comparison_df.loc[scores.idxmax(), "model_name"])
    if snapshot.discovery_results:
        return min(
            snapshot.discovery_results.items(),
            key=lambda item: (
                float(getattr(item[1], "discovery_time_s", 0.0)),
                getattr(item[1], "num_arcs", 0),
            ),
        )[0]
    return None


def _model_tradeoff_summary(model_name: str, result: object, snapshot: AnalysisSnapshot) -> str:
    if not snapshot.comparison_df.empty and "model_name" in snapshot.comparison_df.columns:
        row_df = snapshot.comparison_df[snapshot.comparison_df["model_name"] == model_name]
        if not row_df.empty:
            row = row_df.iloc[0]
            fitness = row.get("alignment_fitness")
            precision = row.get("precision")
            recommendation = row.get("recommendation")
            if pd.notna(fitness) and pd.notna(precision):
                return f"Fitness {float(fitness):.3f} · Precision {float(precision):.3f} · {recommendation or 'Compare against downstream needs.'}"
    arcs = int(getattr(result, "num_arcs", 0) or 0)
    transitions = int(getattr(result, "num_transitions", 0) or 0)
    if arcs <= 12:
        complexity_note = "lean structure"
    elif arcs <= 24:
        complexity_note = "moderate complexity"
    else:
        complexity_note = "richer structure"
    return f"{complexity_note.capitalize()} with {transitions} transitions and {arcs} arcs."
