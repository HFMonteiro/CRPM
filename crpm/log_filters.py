"""Shared event-log filtering helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pm4py.objects.log.obj import EventLog, Trace


def _coerce_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def filter_date_range(
    log: EventLog,
    start: date | None,
    end: date | None,
    *,
    mode: str = "case",
) -> EventLog:
    """Filter traces by inclusive case-anchor date range or clip events."""
    if mode not in {"case", "event"}:
        raise ValueError(f"Unknown date filter mode: {mode}")
    if start is not None and end is not None and start > end:
        raise ValueError("Start date must be on or before end date.")
    if start is None and end is None:
        return log

    start_dt = datetime.combine(start, datetime.min.time()) if start else datetime.min
    end_dt = datetime.combine(end, datetime.max.time()) if end else datetime.max

    if mode == "event":
        filtered = EventLog()
        for trace in log:
            new_trace = Trace(attributes=dict(trace.attributes))
            for event in trace:
                timestamp = _coerce_timestamp(event.get("time:timestamp"))
                if timestamp is not None and start_dt <= timestamp <= end_dt:
                    new_trace.append(event)
            if new_trace:
                filtered.append(new_trace)
        return filtered

    filtered = EventLog()
    for trace in log:
        anchor_ts = None
        for event in trace:
            timestamp = _coerce_timestamp(event.get("time:timestamp"))
            if timestamp is not None and (anchor_ts is None or timestamp < anchor_ts):
                anchor_ts = timestamp
        if anchor_ts is not None and start_dt <= anchor_ts <= end_dt:
            filtered.append(trace)
    return filtered


__all__ = ["filter_date_range"]
