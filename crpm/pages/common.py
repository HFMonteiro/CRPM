"""Shared helpers for refactor preview pages."""

from __future__ import annotations

import html
import logging
from typing import Any, Mapping, MutableMapping

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crpm.formatting import format_metric_value as shared_format_metric_value

logger = logging.getLogger(__name__)


def render_empty_state(message: str) -> None:
    st.markdown(f'<div class="crpm-empty-state">{html.escape(str(message))}</div>', unsafe_allow_html=True)


def render_quiet_note(message: str) -> None:
    st.markdown(f'<div class="crpm-note">{html.escape(str(message))}</div>', unsafe_allow_html=True)


def render_legend_note(message: str) -> None:
    st.markdown(f'<div class="crpm-legend-note">{html.escape(str(message))}</div>', unsafe_allow_html=True)


def render_inline_empty(message: str) -> None:
    st.markdown(f'<div class="crpm-inline-empty">{html.escape(str(message))}</div>', unsafe_allow_html=True)


def short_label(value: str, *, max_chars: int = 32) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def format_metric_value(value: Any, *, kind: str = "generic") -> str:
    return shared_format_metric_value(value, kind=kind)


def render_html_card_grid(cards: list[Mapping[str, Any]], *, grid_class: str = "crpm-bi-card-grid") -> None:
    if not cards:
        return
    chunks: list[str] = []
    for card in cards:
        tone = _slugify(str(card.get("tone", "neutral")))
        eyebrow = html.escape(str(card.get("eyebrow", "")).strip())
        title = html.escape(str(card.get("title", "")).strip())
        value = html.escape(str(card.get("value", "")).strip())
        body = html.escape(str(card.get("body", "")).strip())
        title_attr = html.escape(str(card.get("title_attr", card.get("value", ""))).strip())
        chunks.append(
            (
                f"<div class='crpm-bi-card crpm-bi-card--{tone}'>"
                "<div class='crpm-bi-card__header'>"
                f"<div class='crpm-bi-card__eyebrow'>{eyebrow}</div>"
                f"<div class='crpm-bi-card__title' title='{title_attr}'>{title}</div>"
                "</div>"
                f"<div class='crpm-bi-card__value'>{value}</div>"
                f"<div class='crpm-bi-card__body'>{body}</div>"
                "</div>"
            )
        )
    st.markdown(f"<div class='{grid_class}'>{''.join(chunks)}</div>", unsafe_allow_html=True)


def render_metric_card_grid(cards: list[Mapping[str, Any]]) -> None:
    render_html_card_grid(cards, grid_class="crpm-kpi-grid")


def render_html_ranked_table(
    df: pd.DataFrame,
    *,
    title: str,
    label_column: str,
    chip_column: str | None = None,
    max_label_chars: int = 34,
) -> None:
    if df.empty:
        render_inline_empty(f"No {title.lower()} are available for this selection.")
        return

    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in df.columns)
    numeric_keywords = ("rank", "cases", "events", "delay", "share", "coverage", "fitness", "precision", "balance")
    rows: list[str] = []
    for _, row in df.iterrows():
        cells: list[str] = []
        for column in df.columns:
            raw_value = row.get(column, "N/A")
            display_value = format_metric_value(raw_value)
            class_name = "crpm-table__cell"
            if column == label_column:
                full_value = str(raw_value)
                class_name += " crpm-table__cell--label"
                cell_html = (
                    f"<td class='{class_name}' title='{html.escape(full_value)}'>"
                    f"{html.escape(short_label(full_value, max_chars=max_label_chars))}</td>"
                )
            elif chip_column and column == chip_column:
                class_name += " crpm-table__cell--chip"
                chip_slug = _slugify(str(raw_value))
                cell_html = (
                    f"<td class='{class_name}'><span class='crpm-chip crpm-chip--{chip_slug}'>"
                    f"{html.escape(str(raw_value))}</span></td>"
                )
            else:
                if any(keyword in column.lower() for keyword in numeric_keywords):
                    class_name += " crpm-table__cell--num"
                cell_html = f"<td class='{class_name}'>{html.escape(str(display_value))}</td>"
            cells.append(cell_html)
        rows.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        (
            "<div class='crpm-ranked-table'>"
            f"<div class='crpm-ranked-table__title'>{html.escape(title)}</div>"
            "<div class='crpm-ranked-table__scroller'>"
            f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "neutral"


def cache_index_frame(cache: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for cache_key, value in cache.items():
        rows.append(
            {
                "Cache key": cache_key,
                "Value type": type(value).__name__,
                "Fields": ", ".join(sorted(value.keys())) if isinstance(value, Mapping) else "",
            }
        )
    return pd.DataFrame(rows)


def latest_cache_entry(cache: Mapping[str, Any]) -> tuple[str, Any] | tuple[None, None]:
    if not cache:
        return None, None
    cache_key = next(reversed(cache))
    return cache_key, cache[cache_key]


def store_cache_entry(cache: MutableMapping[str, Any], key: str, value: Any, *, limit: int = 8) -> None:
    """Store a page-level cache entry while bounding growth when possible."""
    cache[key] = value
    if hasattr(cache, "move_to_end"):
        cache.move_to_end(key)
    while len(cache) > limit and hasattr(cache, "popitem"):
        cache.popitem(last=False)


def render_plotly_chart(fig: go.Figure, *, key: str) -> None:
    try:
        st.plotly_chart(fig, use_container_width=True, key=key)
    except Exception:
        logger.exception("Failed to render Plotly chart with key %s", key)
        st.warning("This chart could not be displayed. Please rerun the analysis or use the table below.")
