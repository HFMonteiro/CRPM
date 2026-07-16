from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, date, timezone
from pathlib import Path

import pytest
import pandas as pd

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.obj import EventLog, Trace

from crpm import pipeline


def make_trace(case_id: str, events: list[tuple[str, datetime]]) -> Trace:
    trace = Trace(attributes={"concept:name": case_id})
    for activity, timestamp in events:
        trace.append({"concept:name": activity, "time:timestamp": timestamp})
    return trace


def test_split_by_date_is_non_overlapping() -> None:
    log = EventLog(
        [
            make_trace("before", [("A", datetime(2023, 12, 31, 10, 0)), ("B", datetime(2023, 12, 31, 12, 0))]),
            make_trace("after", [("A", datetime(2024, 1, 1, 10, 0)), ("B", datetime(2024, 1, 2, 12, 0))]),
        ]
    )

    before, after = pipeline.split_by_date(log, date(2024, 1, 1))

    assert len(before) == 1
    assert len(after) == 1
    assert before[0].attributes["concept:name"] == "before"
    assert after[0].attributes["concept:name"] == "after"


def test_token_replay_fitness_uses_trace_fitness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pipeline.token_replay,
        "apply",
        lambda *_args, **_kwargs: [
            {"trace_fitness": 0.25},
            {"trace_fitness": 0.75},
        ],
    )

    result = pipeline.token_replay_fitness(EventLog(), object(), object(), object())

    assert result == pytest.approx(0.5)


def test_filter_date_range_keeps_whole_trace_in_case_mode() -> None:
    log = EventLog(
        [
            make_trace("case-1", [("A", datetime(2024, 1, 1, 10, 0)), ("B", datetime(2024, 2, 1, 12, 0))]),
            make_trace("case-2", [("A", datetime(2024, 3, 1, 10, 0)), ("B", datetime(2024, 3, 2, 12, 0))]),
        ]
    )

    filtered = pipeline.filter_date_range(log, date(2024, 1, 1), date(2024, 1, 31))

    assert len(filtered) == 1
    assert len(filtered[0]) == 2
    assert filtered[0].attributes["concept:name"] == "case-1"


def test_filter_date_range_can_clip_events_in_event_mode() -> None:
    log = EventLog(
        [
            make_trace("case-1", [("A", datetime(2024, 1, 1, 10, 0)), ("B", datetime(2024, 2, 1, 12, 0))]),
        ]
    )

    filtered = pipeline.filter_date_range(log, date(2024, 1, 1), date(2024, 1, 31), mode="event")

    assert len(filtered) == 1
    assert len(filtered[0]) == 1
    assert filtered[0][0]["concept:name"] == "A"


def test_filter_date_range_uses_earliest_timezone_aware_event() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("late", datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc)),
                    ("early", datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)),
                ],
            )
        ]
    )

    filtered = pipeline.filter_date_range(log, date(2024, 1, 1), date(2024, 1, 31))

    assert len(filtered) == 1
    assert filtered[0].attributes["concept:name"] == "case-1"


def test_filter_date_range_rejects_invalid_mode_without_bounds() -> None:
    with pytest.raises(ValueError, match="Unknown date filter mode"):
        pipeline.filter_date_range(EventLog(), None, None, mode="invalid")


def test_filter_date_range_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="Start date must be on or before end date"):
        pipeline.filter_date_range(EventLog(), date(2024, 2, 1), date(2024, 1, 1))


def test_csv_to_event_log_rejects_null_case_ids() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "case-1", "activity": "A", "timestamp": "2024-01-01T10:00:00"},
            {"case_id": None, "activity": "B", "timestamp": "2024-01-01T11:00:00"},
        ]
    )

    with pytest.raises(ValueError, match="case IDs"):
        pipeline.csv_to_event_log(df, "case_id", "activity", "timestamp")


def test_csv_to_event_log_rejects_invalid_timestamps() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "case-1", "activity": "A", "timestamp": "2024-01-01T10:00:00"},
            {"case_id": "case-1", "activity": "B", "timestamp": "not-a-date"},
        ]
    )

    with pytest.raises(ValueError, match="timestamp column"):
        pipeline.csv_to_event_log(df, "case_id", "activity", "timestamp")


def test_csv_to_event_log_rejects_mixed_timezone_semantics() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "case-1", "activity": "A", "timestamp": "2024-01-01T10:00:00"},
            {"case_id": "case-1", "activity": "B", "timestamp": "2024-01-01T11:00:00Z"},
        ]
    )

    with pytest.raises(ValueError, match="timezone"):
        pipeline.csv_to_event_log(df, "case_id", "activity", "timestamp")


def test_csv_to_event_log_sorts_by_case_and_timestamp() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "case-b", "activity": "B2", "timestamp": "2024-01-02T10:00:00"},
            {"case_id": "case-a", "activity": "A2", "timestamp": "2024-01-01T11:00:00"},
            {"case_id": "case-a", "activity": "A1", "timestamp": "2024-01-01T10:00:00"},
        ]
    )

    log = pipeline.csv_to_event_log(df, "case_id", "activity", "timestamp")

    assert [trace.attributes["concept:name"] for trace in log] == ["case-a", "case-b"]
    assert [event["concept:name"] for event in log[0]] == ["A1", "A2"]


def test_load_csv_preserves_leading_zero_identifiers(tmp_path) -> None:
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "case_id,activity,timestamp\n0001,A,2024-01-01T10:00:00Z\n",
        encoding="utf-8",
    )

    dataframe = pipeline.load_csv(csv_path)

    assert dataframe.iloc[0]["case_id"] == "0001"


def test_csv_to_event_log_normalizes_aware_timestamps_to_utc() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "case-1", "activity": "A", "timestamp": "2024-01-01T10:00:00+01:00"},
            {"case_id": "case-1", "activity": "B", "timestamp": "2024-01-01T10:30:00+00:00"},
        ]
    )

    log = pipeline.csv_to_event_log(df, "case_id", "activity", "timestamp")

    first_timestamp = log[0][0]["time:timestamp"]
    assert first_timestamp.hour == 9
    assert first_timestamp.utcoffset().total_seconds() == 0


def test_split_log_random_is_reproducible_across_python_hash_seeds() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = """
from datetime import datetime
from pm4py.objects.log.obj import EventLog, Trace
from crpm.pipeline import split_log_random

log = EventLog()
for case_id in ["c", "a", "d", "b", "e"]:
    trace = Trace(attributes={"concept:name": case_id})
    trace.append({"concept:name": "A", "time:timestamp": datetime(2024, 1, 1)})
    log.append(trace)

train_log, test_log, _ = split_log_random(log, train_ratio=0.6, random_seed=7)
print(",".join(trace.attributes["concept:name"] for trace in train_log))
print(",".join(trace.attributes["concept:name"] for trace in test_log))
""".strip()

    outputs = []
    for hash_seed in ("0", "1"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(result.stdout.strip())

    assert outputs[0] == outputs[1]
