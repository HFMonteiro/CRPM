"""Discovery page for the staged CRPM refactor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import render_empty_state, render_html_card_grid, render_html_ranked_table, render_metric_card_grid


def render_discovery_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Discovery")
    if not snapshot.discovery_results:
        render_empty_state("No discovered models yet. Run the analysis from the sidebar to populate this page.")
        return

    recommended_name = _recommended_model_name(snapshot)

    render_metric_card_grid(_discovery_kpi_cards(snapshot, recommended_name))

    models = list(snapshot.discovery_results.items())
    model_col, signal_col = st.columns(2)
    with model_col:
        st.markdown("#### Candidate detail")
        with st.expander("Discovery candidates", expanded=False):
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

    with signal_col:
        st.markdown("#### Discovery signals")
        render_html_card_grid(_discovery_signal_cards(snapshot, recommended_name))

    rows = []
    for model_name, result in snapshot.discovery_results.items():
        model_row = {
            "Model": model_name,
            "Algorithm": getattr(result, "algorithm", "N/A"),
            "Variant": getattr(result, "variant", "N/A"),
            "Discovery time (s)": round(float(getattr(result, "discovery_time_s", 0.0)), 3),
            "Transitions": getattr(result, "num_transitions", 0),
            "Places": getattr(result, "num_places", 0),
            "Arcs": getattr(result, "num_arcs", 0),
        }
        if not snapshot.comparison_df.empty and "model_name" in snapshot.comparison_df.columns:
            row_df = snapshot.comparison_df[snapshot.comparison_df["model_name"] == model_name]
            if not row_df.empty:
                row = row_df.iloc[0]
                quality_score = row.get("quality_score")
                quality_band = row.get("quality_band")
                parameter_profile_name = row.get("parameter_profile_name")
                pm4py_variant = row.get("pm4py_variant")
                fitness_quality = row.get("fitness_quality")
                precision_quality = row.get("precision_quality")
                quadrant = row.get("quadrant")
                if pd.notna(quality_score):
                    model_row["Quality score"] = round(float(quality_score), 3)
                if pd.notna(quality_band):
                    model_row["Quality band"] = str(quality_band)
                if pd.notna(parameter_profile_name):
                    model_row["Parameter profile"] = str(parameter_profile_name)
                if pd.notna(pm4py_variant):
                    model_row["PM4Py variant"] = str(pm4py_variant)
                if pd.notna(fitness_quality):
                    model_row["Fitness quality"] = str(fitness_quality)
                if pd.notna(precision_quality):
                    model_row["Precision quality"] = str(precision_quality)
                if pd.notna(quadrant):
                    model_row["Quadrant"] = str(quadrant)
        rows.append(model_row)

    st.markdown("#### Model summary table")
    render_html_ranked_table(pd.DataFrame(rows), title="Discovered model summary", label_column="Model")


def _discovery_kpi_cards(snapshot: AnalysisSnapshot, recommended_name: str | None) -> list[dict[str, str]]:
    best_tradeoff = None
    fastest = None
    leanest = None
    results = list(snapshot.discovery_results.items())
    if results:
        best_tradeoff = _recommended_model_name(snapshot)
        fastest = min(results, key=lambda item: float(getattr(item[1], "discovery_time_s", 0.0)))[0]
        leanest = min(results, key=lambda item: int(getattr(item[1], "num_arcs", 0) or 0))[0]

    return [
        {
            "eyebrow": "Scope",
            "title": "Discovered models",
            "value": f"{snapshot.model_count:,}",
            "body": "Current run.",
            "tone": "neutral",
        },
        {
            "eyebrow": "Scope",
            "title": "Cases",
            "value": f"{snapshot.case_count:,}",
            "body": "Filtered cohort.",
            "tone": "accent",
        },
        {
            "eyebrow": "Flow",
            "title": "Transitions",
            "value": _best_model_size(snapshot, attr="num_transitions"),
            "body": "Across discovery candidates.",
            "tone": "success",
        },
        {
            "eyebrow": "Guide",
            "title": "Inspect first",
            "value": recommended_name or "N/A",
            "body": f"Best balance {best_tradeoff or 'Unavailable'} · Fastest {fastest or 'N/A'} · Leanest {leanest or 'N/A'}",
            "tone": "neutral",
            "title_attr": recommended_name or "No recommendation",
        },
    ]


def _discovery_signal_cards(snapshot: AnalysisSnapshot, recommended_name: str | None) -> list[dict[str, str]]:
    results = list(snapshot.discovery_results.items())
    if not results:
        return []

    fastest_name, fastest_result = min(results, key=lambda item: float(getattr(item[1], "discovery_time_s", 0.0)))
    richest_name, richest_result = max(results, key=lambda item: int(getattr(item[1], "num_arcs", 0) or 0))
    recommended_result = snapshot.discovery_results.get(recommended_name) if recommended_name else None

    cards = [
        {
            "eyebrow": "Recommended",
            "title": recommended_name or "No recommendation",
            "value": f"{float(getattr(recommended_result, 'discovery_time_s', 0.0)):.2f}s" if recommended_result else "N/A",
            "body": (
                _model_tradeoff_summary(recommended_name or "N/A", recommended_result or fastest_result, snapshot)
                if recommended_result
                else "Use the comparison page when the trade-off is not obvious."
            ),
            "tone": "accent",
            "title_attr": recommended_name or "No recommendation",
        },
        {
            "eyebrow": "Fastest",
            "title": fastest_name,
            "value": f"{float(getattr(fastest_result, 'discovery_time_s', 0.0)):.2f}s",
            "body": "Lowest discovery time in the current run.",
            "tone": "success",
        },
        {
            "eyebrow": "Richest",
            "title": richest_name,
            "value": f"{int(getattr(richest_result, 'num_arcs', 0) or 0):,} arcs",
            "body": "Most structural detail in the current candidates.",
            "tone": "neutral",
        },
    ]
    return cards


def _best_model_size(snapshot: AnalysisSnapshot, *, attr: str) -> str:
    values = [int(getattr(result, attr, 0) or 0) for _, result in snapshot.discovery_results.items()]
    if not values:
        return "N/A"
    return f"{max(values):,}"


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
