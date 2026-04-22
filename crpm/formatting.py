"""Shared display-formatting helpers for CRPM presentation surfaces."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd


def coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def format_decimal(value: Any, *, decimals: int = 3, thousands: bool = False) -> str:
    numeric = coerce_float(value)
    if numeric is None:
        return "N/A" if value is None else str(value)

    if abs(numeric) < 10 ** (-(decimals + 1)):
        numeric = 0.0

    if float(numeric).is_integer():
        return f"{int(round(numeric)):,}" if thousands else str(int(round(numeric)))

    template = f"{{:{',' if thousands else ''}.{decimals}f}}"
    formatted = template.format(numeric)
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def format_metric_value(value: Any, *, kind: str = "generic") -> str:
    try:
        if value is None or pd.isna(value):
            return "N/A"
    except Exception:
        if value is None:
            return "N/A"

    numeric = coerce_float(value)
    if numeric is None:
        return str(value)

    if kind == "count":
        return f"{int(round(numeric)):,}"
    if kind == "percent":
        return f"{format_decimal(numeric, decimals=3, thousands=True)}%"
    if kind in {"days", "hours", "seconds"}:
        return f"{format_decimal(numeric, decimals=3, thousands=True)} {kind}"
    if kind == "score":
        return format_decimal(numeric, decimals=3)
    return format_decimal(numeric, decimals=3, thousands=True)
