"""Shared helpers for refactor preview pages."""

from __future__ import annotations

import html
import logging
from pathlib import PurePosixPath
from typing import Any, Mapping, MutableMapping

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crpm.formatting import format_metric_value as shared_format_metric_value

logger = logging.getLogger(__name__)


def render_empty_state(message: str) -> None:
    st.markdown(
        f'<div class="crpm-empty-state">{html.escape(str(message))}</div>',
        unsafe_allow_html=True,
    )


def render_quiet_note(message: str) -> None:
    st.markdown(
        f'<div class="crpm-note">{html.escape(str(message))}</div>',
        unsafe_allow_html=True,
    )


def render_legend_note(message: str) -> None:
    st.markdown(
        f'<div class="crpm-legend-note">{html.escape(str(message))}</div>',
        unsafe_allow_html=True,
    )


def render_inline_empty(message: str) -> None:
    st.markdown(
        f'<div class="crpm-inline-empty">{html.escape(str(message))}</div>',
        unsafe_allow_html=True,
    )


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


def redact_dashboard_value(value: Any, *, max_chars: int = 80) -> str:
    """Return a UI-safe display value without local path context."""

    text = str(value or "").strip()
    if not text:
        return "N/A"
    normalized = text.replace("\\", "/").rstrip("/")
    is_windows_path = "\\" in text or (len(text) > 2 and text[1] == ":" and text[2] in {"/", "\\"})
    is_posix_path = normalized.startswith(("/", "~/")) or ("/" in normalized and bool(PurePosixPath(normalized).suffix))
    if is_windows_path or is_posix_path:
        text = PurePosixPath(normalized).name or "redacted"
    return short_label(text, max_chars=max_chars)


def render_dashboard_topbar(
    *,
    title: str,
    subtitle: str,
    badges: list[Mapping[str, Any] | tuple[Any, ...]] | None = None,
    meta: list[Any] | tuple[Any, ...] | None = None,
) -> None:
    badge_chunks: list[str] = []
    for badge in badges or []:
        if isinstance(badge, Mapping):
            label = badge.get("label", "")
            value = badge.get("value", "")
            tone = badge.get("tone", "neutral")
        else:
            values = list(badge)
            label = values[0] if values else ""
            value = values[1] if len(values) > 1 else ""
            tone = values[2] if len(values) > 2 else "neutral"
        badge_chunks.append(
            (
                f"<span class='crpm-dashboard-badge crpm-dashboard-badge--{_slugify(str(tone))}'>"
                f"<span>{html.escape(redact_dashboard_value(label, max_chars=28))}</span>"
                f"<strong>{html.escape(redact_dashboard_value(value, max_chars=42))}</strong>"
                "</span>"
            )
        )

    meta_values = [html.escape(redact_dashboard_value(item, max_chars=54)) for item in meta or [] if str(item or "").strip()]
    meta_markup = ""
    if meta_values:
        meta_markup = "<div class='crpm-dashboard-topbar__meta'>" + " · ".join(meta_values) + "</div>"

    st.markdown(
        (
            "<div class='crpm-dashboard-topbar'>"
            "<div class='crpm-dashboard-topbar__copy'>"
            f"<div class='crpm-dashboard-topbar__label'>Process intelligence cockpit</div>"
            f"<div class='crpm-dashboard-topbar__title'>{html.escape(redact_dashboard_value(title, max_chars=72))}</div>"
            f"<div class='crpm-dashboard-topbar__subtitle'>{html.escape(redact_dashboard_value(subtitle, max_chars=140))}</div>"
            f"{meta_markup}"
            "</div>"
            f"<div class='crpm-dashboard-topbar__badges'>{''.join(badge_chunks)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_dashboard_bar_list(
    title: str,
    rows: list[Mapping[str, Any]],
    *,
    value_label: str = "%",
    max_value: float | None = None,
) -> None:
    if not rows:
        render_inline_empty(f"No {str(title).lower()} are available for this selection.")
        return

    numeric_values = [_coerce_float(row.get("value")) for row in rows]
    valid_values = [value for value in numeric_values if value is not None and value >= 0]
    if max_value is None:
        if value_label == "%" and valid_values and max(valid_values) <= 100:
            max_value = 100.0
        else:
            max_value = max(valid_values) if valid_values else 1.0
    max_value = max(float(max_value or 1.0), 1.0)

    row_chunks: list[str] = []
    for row, numeric_value in zip(rows, numeric_values):
        value = max(float(numeric_value or 0.0), 0.0)
        width_pct = min(max((value / max_value) * 100, 0.0), 100.0)
        display = str(row.get("display") or _format_bar_value(value, value_label)).strip()
        label = redact_dashboard_value(row.get("label", "N/A"), max_chars=46)
        tone = _slugify(str(row.get("tone", "neutral")))
        row_chunks.append(
            (
                f"<div class='crpm-dashboard-bar-row crpm-dashboard-bar-row--{tone}'>"
                "<div class='crpm-dashboard-bar-row__head'>"
                f"<span class='crpm-dashboard-bar-row__label' title='{html.escape(label)}'>{html.escape(label)}</span>"
                f"<span class='crpm-dashboard-bar-row__value'>{html.escape(display)}</span>"
                "</div>"
                "<div class='crpm-dashboard-bar-row__track'>"
                f"<span class='crpm-dashboard-bar-row__fill' style='width:{width_pct:.1f}%'></span>"
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        (
            "<div class='crpm-dashboard-bar-list'>"
            f"<div class='crpm-dashboard-bar-list__title'>{html.escape(redact_dashboard_value(title, max_chars=64))}</div>"
            f"{''.join(row_chunks)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


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
    numeric_keywords = (
        "rank",
        "cases",
        "events",
        "delay",
        "share",
        "coverage",
        "fitness",
        "precision",
        "balance",
    )
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
                    f"<td class='{class_name}'><span class='crpm-chip crpm-chip--{chip_slug}'>{html.escape(str(raw_value))}</span></td>"
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


def _coerce_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def _format_bar_value(value: float, value_label: str) -> str:
    formatted = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
    return f"{formatted}{value_label}" if value_label else formatted


def cache_index_frame(cache: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for cache_key, value in cache.items():
        rows.append(
            {
                "Cache key": cache_key,
                "Value type": type(value).__name__,
                "Fields": (", ".join(sorted(value.keys())) if isinstance(value, Mapping) else ""),
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
