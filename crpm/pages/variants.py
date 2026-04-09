"""Variant analysis page — native execution from the filtered log."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from crpm.app_state import AnalysisSnapshot
from crpm.pages.common import (
    format_metric_value,
    render_empty_state,
    render_html_card_grid,
    render_html_ranked_table,
    render_inline_empty,
    render_legend_note,
    render_plotly_chart,
    store_cache_entry,
)
from crpm.variants import build_variant_index, compute_variant_conformance, compute_variant_coverage, get_variant_statistics
from crpm.visualization import create_variant_coverage_chart, create_variant_frequency_chart


def render_variant_page(snapshot: AnalysisSnapshot) -> None:
    st.subheader("Variant Analysis")

    if not snapshot.analysis_complete or snapshot.filtered_log is None:
        render_empty_state("No variant results yet. Run the analysis from the sidebar to populate this page.")
        return

    log = snapshot.filtered_log
    model_name = next(iter(snapshot.discovery_results)) if snapshot.discovery_results else None
    cache_key = f"{snapshot.filter_key or 'current'}::variants::{model_name or 'none'}"
    cached_payload = snapshot.variant_cache.get(cache_key) if hasattr(snapshot.variant_cache, "get") else None

    if cached_payload is None:
        with st.spinner("Computing variant statistics…"):
            started = time.perf_counter()
            variant_index = build_variant_index(log)
            variant_stats = get_variant_statistics(log, variant_index=variant_index)
            coverage = compute_variant_coverage(variant_stats) if not variant_stats.empty else pd.DataFrame()
            conformance_df = pd.DataFrame()
            if snapshot.discovery_results:
                disc_result = snapshot.discovery_results[model_name]
                net = getattr(disc_result, "net", None)
                im = getattr(disc_result, "initial_marking", None)
                fm = getattr(disc_result, "final_marking", None)
                if net is not None and im is not None and fm is not None:
                    conformance_df = compute_variant_conformance(log, net, im, fm, variant_index=variant_index, random_seed=42)
            cached_payload = {
                "variant_stats": variant_stats,
                "coverage": coverage,
                "conformance_df": conformance_df,
                "variant_index": variant_index,
                "timings": {"variant_page_s": time.perf_counter() - started},
            }
            try:
                store_cache_entry(snapshot.variant_cache, cache_key, cached_payload)
            except Exception:
                pass
    variant_stats = cached_payload["variant_stats"]

    if variant_stats.empty:
        render_inline_empty("No variants found in the filtered log.")
        return

    coverage = cached_payload["coverage"]

    stat_cols = st.columns(3)
    stat_cols[0].metric("Unique variants", f"{len(variant_stats):,}")
    stat_cols[1].metric("Total cases", f"{int(variant_stats['frequency'].sum()):,}" if "frequency" in variant_stats.columns else "0")
    top_pct = f"{variant_stats['percentage'].iloc[0]:.1f}%" if "percentage" in variant_stats.columns and len(variant_stats) > 0 else "—"
    stat_cols[2].metric("Top variant share", top_pct)
    render_legend_note("Variant coverage is cumulative. The conformance table below uses the first discovered model only.")

    conformance_df = cached_payload["conformance_df"]
    dominant_col, insight_col = st.columns([1.4, 1.0], gap="large")

    with dominant_col:
        st.markdown("#### Dominant variants")
        render_html_ranked_table(
            _format_variant_ranked_table(coverage),
            title="Variant concentration",
            label_column="Variant",
            max_label_chars=42,
        )

    with insight_col:
        st.markdown("#### Variant signals")
        render_html_card_grid(_variant_signal_cards(coverage, conformance_df))

    frequency_tab, coverage_tab, conformance_tab = st.tabs(["Frequency", "Coverage", "Conformance"])
    with frequency_tab:
        render_plotly_chart(create_variant_frequency_chart(variant_stats), key="variant_freq_chart")
    with coverage_tab:
        if "cumulative_percentage" in coverage.columns:
            render_plotly_chart(create_variant_coverage_chart(coverage), key="variant_cov_chart")
        else:
            render_inline_empty("Variant coverage could not be derived for the current selection.")
    with conformance_tab:
        if model_name and not conformance_df.empty:
            st.caption(f"Per-variant conformance using {model_name}.")
            render_html_ranked_table(
                _format_variant_conformance_table(conformance_df),
                title="Variant conformance",
                label_column="Variant",
                chip_column="Fit status",
                max_label_chars=38,
            )
        elif model_name:
            render_inline_empty("Per-variant conformance is not available for the selected model.")


def _format_variant_ranked_table(coverage: pd.DataFrame) -> pd.DataFrame:
    if coverage.empty:
        return pd.DataFrame(columns=["Rank", "Variant", "Cases", "Share (%)", "Coverage (%)"])

    working = coverage.copy().head(8).reset_index(drop=True)
    return pd.DataFrame(
        {
            "Rank": [index + 1 for index in range(len(working))],
            "Variant": working.get("variant_str", pd.Series([""] * len(working))),
            "Cases": working.get("frequency", pd.Series([0] * len(working))).map(lambda value: format_metric_value(value, kind="count")),
            "Share (%)": working.get("percentage", pd.Series([None] * len(working))).map(lambda value: format_metric_value(value, kind="percent")),
            "Coverage (%)": working.get("cumulative_percentage", pd.Series([None] * len(working))).map(lambda value: format_metric_value(value, kind="percent")),
        }
    )


def _format_variant_conformance_table(conformance_df: pd.DataFrame) -> pd.DataFrame:
    if conformance_df.empty:
        return pd.DataFrame(columns=["Rank", "Variant", "Cases", "Alignment", "Token", "Perfect fit", "Fit status"])

    working = conformance_df.copy()
    sort_cols = [column for column in ("perfect_fit_pct", "frequency") if column in working.columns]
    ascending = [False for _ in sort_cols]
    if sort_cols:
        working = working.sort_values(by=sort_cols, ascending=ascending, kind="stable")
    working = working.head(8).reset_index(drop=True)
    fit_status = []
    for _, row in working.iterrows():
        perfect_fit = row.get("perfect_fit_pct")
        if perfect_fit is None or pd.isna(perfect_fit):
            fit_status.append("Overview")
        elif float(perfect_fit) >= 95:
            fit_status.append("Conformant")
        elif float(perfect_fit) >= 75:
            fit_status.append("Watch")
        else:
            fit_status.append("Deviation-heavy")

    return pd.DataFrame(
        {
            "Rank": [index + 1 for index in range(len(working))],
            "Variant": working.get("variant", pd.Series([""] * len(working))),
            "Cases": working.get("frequency", pd.Series([0] * len(working))).map(lambda value: format_metric_value(value, kind="count")),
            "Alignment": working.get("align_fitness", pd.Series([None] * len(working))).map(lambda value: format_metric_value(value, kind="score")),
            "Token": working.get("token_fitness", pd.Series([None] * len(working))).map(lambda value: format_metric_value(value, kind="score")),
            "Perfect fit": working.get("perfect_fit_pct", pd.Series([None] * len(working))).map(lambda value: format_metric_value(value, kind="percent")),
            "Fit status": fit_status,
        }
    )


def _variant_signal_cards(coverage: pd.DataFrame, conformance_df: pd.DataFrame) -> list[dict[str, str]]:
    if coverage.empty:
        return []

    top_row = coverage.iloc[0]
    eighty_cutoff = coverage[coverage.get("cumulative_percentage", pd.Series(dtype=float)) >= 80]
    rare_variants = coverage[coverage.get("percentage", pd.Series(dtype=float)).fillna(0) <= 5]
    cards = [
        {
            "eyebrow": "Dominant path",
            "title": "Top variant",
            "value": format_metric_value(top_row.get("percentage"), kind="percent"),
            "body": str(top_row.get("variant_str", "Top variant")),
            "tone": "accent",
            "title_attr": str(top_row.get("variant_str", "Top variant")),
        },
        {
            "eyebrow": "Coverage concentration",
            "title": "Variants needed for 80%",
            "value": format_metric_value(len(eighty_cutoff) if not eighty_cutoff.empty else len(coverage), kind="count"),
            "body": "Fewer variants to reach 80% usually means the pathway is concentrated and easier to explain operationally.",
            "tone": "neutral",
        },
        {
            "eyebrow": "Rare-path tail",
            "title": "Rare variants",
            "value": format_metric_value(len(rare_variants), kind="count"),
            "body": "Rare variants are often the best place to look for exceptional behaviours and conformance deviations.",
            "tone": "success",
        },
    ]

    if not conformance_df.empty and "perfect_fit_pct" in conformance_df.columns:
        best_fit = conformance_df["perfect_fit_pct"].dropna()
        cards.append(
            {
                "eyebrow": "Conformance",
                "title": "Best perfect-fit share",
                "value": format_metric_value(best_fit.max() if not best_fit.empty else None, kind="percent"),
                "body": "Use the conformance tab to review the most stable variants against the first discovered model.",
                "tone": "neutral",
            }
        )
    return cards
