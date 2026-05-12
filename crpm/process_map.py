"""Shared process-map payload helpers for dashboard renderers."""

from __future__ import annotations

from typing import Any, Mapping


_KPI_LABELS = {
    "visible_case_count": "Visible cases",
    "excluded_case_count": "Excluded cases",
    "path_denominator": "Path denominator",
    "activity_denominator": "Activities",
    "transition_denominator": "Transitions",
}


def build_process_map_kpis(denominators: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return compact KPI rows for any normalized process-map payload."""

    rows: list[dict[str, Any]] = []
    for key in (
        "visible_case_count",
        "excluded_case_count",
        "path_denominator",
        "activity_denominator",
        "transition_denominator",
    ):
        if key not in denominators:
            continue
        value = _safe_int(denominators.get(key))
        rows.append(
            {
                "key": key,
                "label": _KPI_LABELS[key],
                "value": value,
                "display": f"{value:,}",
            }
        )
    return rows


def build_selection_context(
    *,
    source_page: str,
    renderer_role: str,
    selected_node_id: Any = None,
    selected_edge_uid: Any = None,
    local_focus_hint: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the safe selection context shared across process-map renderers."""

    context = {
        "source_page": str(source_page),
        "renderer_role": str(renderer_role),
        "selected_node_id": str(selected_node_id) if selected_node_id is not None else None,
        "selected_edge_uid": str(selected_edge_uid) if selected_edge_uid is not None else None,
        "local_focus_hint": str(local_focus_hint) if local_focus_hint else None,
    }
    return {key: value for key, value in context.items() if value is not None}


def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0


__all__ = ["build_process_map_kpis", "build_selection_context"]
