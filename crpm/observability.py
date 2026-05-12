"""Observability helpers for local CRPM runs."""

from __future__ import annotations

from collections.abc import Mapping, Sized
from typing import Any


def build_cache_telemetry(
    *,
    caches: Mapping[str, Sized],
    cache_limits: Mapping[str, int],
    stage_timings: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize bounded cache posture and stage timings without exposing cache keys."""

    rows = []
    total_entries = 0
    total_capacity = 0
    for name in sorted(caches):
        entries = _safe_len(caches[name])
        limit = _safe_int(cache_limits.get(name))
        total_entries += entries
        total_capacity += limit
        rows.append(
            {
                "name": str(name),
                "entries": entries,
                "limit": limit,
                "utilization_pct": _percent(entries, limit),
            }
        )
    rows.sort(key=lambda row: (-int(row["entries"]), str(row["name"])))
    safe_stage_timings = {str(name): round(float(value), 3) for name, value in sorted(stage_timings.items()) if _is_number(value)}
    runtime_s = round(sum(safe_stage_timings.values()), 3)
    return {
        "summary": {
            "cache_count": len(rows),
            "total_entries": total_entries,
            "total_capacity": total_capacity,
            "utilization_pct": _percent(total_entries, total_capacity),
            "runtime_s": runtime_s,
        },
        "caches": rows,
        "stage_timings_s": safe_stage_timings,
    }


def _safe_len(value: Sized) -> int:
    try:
        return int(len(value))
    except Exception:
        return 0


def _safe_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 1)


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


__all__ = ["build_cache_telemetry"]
