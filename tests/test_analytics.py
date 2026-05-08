"""Tests for crpm.analytics — activity stats, transitions, bottlenecks, durations."""

from __future__ import annotations

import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog

from crpm.analytics import (
    collect_timing_buckets,
    compute_activity_statistics,
    compute_case_durations,
    compute_case_statistics,
    compute_transition_statistics,
    detect_bottlenecks,
)

LOG_PATH = "examples/running-example.xes"


@pytest.fixture(scope="module")
def log():
    return xes_importer.apply(LOG_PATH)


def test_activity_statistics_returns_dataframe(log):
    df = compute_activity_statistics(log)
    assert not df.empty
    assert "activity" in df.columns
    assert "frequency" in df.columns
    assert df["frequency"].sum() > 0


def test_transition_statistics_returns_dataframe(log):
    df = compute_transition_statistics(log, min_occurrences=1)
    assert not df.empty
    assert "activity" in df.columns
    assert "next_activity" in df.columns
    assert "frequency" in df.columns


def test_detect_bottlenecks_returns_ranked_transitions(log):
    trans_df = compute_transition_statistics(log, min_occurrences=1)
    if trans_df.empty:
        pytest.skip("No transitions found in running example")
    bottlenecks = detect_bottlenecks(trans_df, top_n=5)
    assert len(bottlenecks) <= 5
    assert "bottleneck_score" in bottlenecks.columns


def test_case_durations_returns_one_row_per_case(log):
    df = compute_case_durations(log)
    assert not df.empty
    assert "case_id" in df.columns
    assert "duration_days" in df.columns
    assert len(df) == len(log)


def test_case_statistics_computes_aggregates(log):
    durations = compute_case_durations(log)
    stats = compute_case_statistics(durations)
    assert "avg_duration_s" in stats
    assert "median_duration_s" in stats
    assert stats["avg_duration_s"] >= 0


def test_activity_statistics_handles_empty_log() -> None:
    df = compute_activity_statistics(EventLog())
    assert df.empty
    assert "frequency" in df.columns


def test_collect_timing_buckets_includes_case_durations(log):
    buckets = collect_timing_buckets(log)
    assert "case_durations" in buckets
    assert len(buckets["case_durations"]) == len(compute_case_durations(log))


def test_compute_case_durations_reuses_provided_buckets(log):
    buckets = collect_timing_buckets(log)
    df = compute_case_durations(log, timing_buckets=buckets)
    assert not df.empty
    assert len(df) == len(buckets["case_durations"])
