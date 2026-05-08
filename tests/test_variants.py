"""Tests for crpm.variants — variant statistics, coverage, filtering."""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog, Trace

from crpm.variants import (
    _build_variant_index,
    _manual_variant_statistics,
    compute_variant_conformance,
    compute_variant_coverage,
    get_variant_statistics,
)

LOG_PATH = "examples/running-example.xes"


@pytest.fixture(scope="module")
def log():
    return xes_importer.apply(LOG_PATH)


def test_variant_statistics_returns_dataframe(log):
    df = get_variant_statistics(log)
    assert not df.empty
    assert "variant" in df.columns
    assert "frequency" in df.columns
    assert df["frequency"].sum() == len(log)


def test_variant_statistics_top_n_limits(log):
    df = get_variant_statistics(log, top_n=2)
    assert len(df) <= 2


def test_variant_coverage_is_monotonic(log):
    stats = get_variant_statistics(log)
    coverage = compute_variant_coverage(stats)
    assert not coverage.empty
    assert "cumulative_percentage" in coverage.columns
    values = coverage["cumulative_percentage"].tolist()
    assert all(a <= b for a, b in zip(values, values[1:]))
    assert values[-1] == pytest.approx(100.0)


def test_manual_variant_statistics_handles_empty_log() -> None:
    stats = _manual_variant_statistics(EventLog())

    assert stats.empty
    assert list(stats.columns) == ["variant", "variant_str", "frequency", "percentage"]


def test_compute_variant_conformance_uses_deterministic_shared_sampling(monkeypatch) -> None:
    trace_a = Trace()
    trace_a.attributes["case_id"] = "case-a"
    trace_a.append({"concept:name": "A"})
    trace_a.append({"concept:name": "B"})
    trace_b = Trace()
    trace_b.attributes["case_id"] = "case-b"
    trace_b.append({"concept:name": "A"})
    trace_b.append({"concept:name": "B"})
    trace_c = Trace()
    trace_c.attributes["case_id"] = "case-c"
    trace_c.append({"concept:name": "A"})
    trace_c.append({"concept:name": "B"})
    trace_d = Trace()
    trace_d.attributes["case_id"] = "case-d"
    trace_d.append({"concept:name": "A"})
    trace_d.append({"concept:name": "B"})
    log = EventLog([trace_a, trace_b, trace_c, trace_d])
    variant_index = _build_variant_index(log)

    seen: dict[str, list[list[str]]] = defaultdict(list)

    class FakeTokenReplay:
        @staticmethod
        def apply(variant_log, net, im, fm):
            seen["token"].append([trace.attributes.get("case_id") for trace in variant_log])
            return [{"trace_fitness": 1.0} for _ in variant_log]

    class FakeAlignments:
        @staticmethod
        def apply_log(variant_log, net, im, fm):
            seen["align"].append([trace.attributes.get("case_id") for trace in variant_log])
            return [{"fitness": 1.0, "cost": 0.0, "bwc": 0.0, "bwt": 0.0} for _ in variant_log]

    monkeypatch.setattr("pm4py.algo.conformance.tokenreplay.algorithm", FakeTokenReplay)
    monkeypatch.setattr("pm4py.algo.conformance.alignments.petri_net.algorithm", FakeAlignments)

    result_one = compute_variant_conformance(
        log,
        net=SimpleNamespace(),
        im=SimpleNamespace(),
        fm=SimpleNamespace(),
        top_n=1,
        sample_alignments=True,
        max_alignment_samples=2,
        variant_index=variant_index,
        random_seed=17,
    )
    result_two = compute_variant_conformance(
        log,
        net=SimpleNamespace(),
        im=SimpleNamespace(),
        fm=SimpleNamespace(),
        top_n=1,
        sample_alignments=True,
        max_alignment_samples=2,
        variant_index=variant_index,
        random_seed=17,
    )

    assert not result_one.empty
    assert result_one.equals(result_two)
    assert seen["token"][0] == seen["align"][0]
    assert seen["token"][1] == seen["align"][1]
    assert seen["token"][0] == seen["token"][1]
    assert len(seen["token"][0]) == 2
