"""Convenience re-exports from crpm.conformance.

This module is **deprecated**.  Import directly from :mod:`crpm.conformance`
instead.  It is kept only for backward compatibility.
"""

from crpm.conformance import load_log as _load_log
from crpm.conformance import filter_start_event as filter_by_first_event
from crpm.conformance import filter_date_range

from pm4py.objects.log.obj import EventLog


def load_log(file_path):
    """Load a XES event log, returning ``None`` on failure.

    .. deprecated::
        Use :func:`crpm.conformance.load_log` instead.
    """
    try:
        return _load_log(file_path)
    except Exception:
        return None


def first_event_names(log: EventLog) -> list[str]:
    """Return sorted unique first-event names.

    .. deprecated::
        Use the identically-named helper in ``app.py`` or
        :func:`crpm.conformance.filter_start_event`.
    """
    return sorted({trace[0]["concept:name"] for trace in log if trace})


__all__ = [
    "load_log",
    "first_event_names",
    "filter_by_first_event",
    "filter_date_range",
]
