from __future__ import annotations

from datetime import datetime, timezone

from pm4py.objects.log.obj import EventLog, Trace

from crpm.conformance import filter_date_range


def _trace(*events: tuple[str, datetime]) -> Trace:
    trace = Trace()
    for activity, timestamp in events:
        trace.append({"concept:name": activity, "time:timestamp": timestamp})
    return trace


def test_case_date_filter_uses_earliest_timestamp_not_trace_order() -> None:
    log = EventLog(
        [
            _trace(
                ("Later", datetime(2024, 2, 1)),
                ("Earlier", datetime(2024, 1, 1)),
            )
        ]
    )

    filtered = filter_date_range(log, datetime(2024, 1, 1).date(), datetime(2024, 1, 31).date(), mode="case")

    assert len(filtered) == 1


def test_date_filter_accepts_timezone_aware_timestamps() -> None:
    log = EventLog([_trace(("Start", datetime(2024, 1, 1, 8, 30, tzinfo=timezone.utc)))])

    filtered = filter_date_range(log, datetime(2024, 1, 1).date(), datetime(2024, 1, 1).date(), mode="case")

    assert len(filtered) == 1


def test_event_date_filter_preserves_matching_events_with_timezone_aware_timestamps() -> None:
    log = EventLog(
        [
            _trace(
                ("Before", datetime(2023, 12, 31, 23, 59, tzinfo=timezone.utc)),
                ("Inside", datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)),
                ("After", datetime(2024, 1, 2, 0, 1, tzinfo=timezone.utc)),
            )
        ]
    )

    filtered = filter_date_range(log, datetime(2024, 1, 1).date(), datetime(2024, 1, 1).date(), mode="event")

    assert len(filtered) == 1
    assert [event["concept:name"] for event in filtered[0]] == ["Inside"]
