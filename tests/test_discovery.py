"""Tests for crpm.discovery — algorithm wrappers and utilities."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.algo.discovery.inductive import algorithm as inductive_algorithm
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.petri_net.utils import petri_utils

from crpm.discovery import (
    compute_model_complexity,
    discover_all_algorithms,
    discover_inductive_imd,
    discover_inductive_imf,
    discover_with_algorithm,
)

LOG_PATH = "examples/running-example.xes"


@pytest.fixture(scope="module")
def log():
    return xes_importer.apply(LOG_PATH)


@pytest.mark.parametrize(
    "algorithm",
    [
        "Heuristics (Classic)",
        "Heuristics (PLUS)",
        "Inductive (IM)",
        "Inductive (IMf)",
        "Inductive (IMd)",
    ],
)
def test_discover_with_algorithm_returns_result(log, algorithm):
    result = discover_with_algorithm(log, algorithm)
    assert result is not None
    assert result.net is not None
    assert result.num_transitions > 0
    assert result.num_places > 0
    assert result.num_arcs > 0
    assert result.discovery_time_s >= 0


def test_discover_with_unknown_algorithm_raises_on_invalid(log):
    with pytest.raises(ValueError):
        discover_with_algorithm(log, "NonExistent Miner")


def test_discover_all_algorithms_returns_selected(log):
    selected = ["Heuristics (Classic)", "Inductive (IMf)"]
    results = discover_all_algorithms(log, selected_algorithms=selected)
    assert len(results) == 2
    assert "Heuristics (Classic)" in results
    assert "Inductive (IMf)" in results


def test_compute_model_complexity(log):
    result = discover_with_algorithm(log, "Inductive (IMf)")
    complexity = compute_model_complexity(result)
    assert "num_transitions" in complexity
    assert "num_places" in complexity
    assert "num_arcs" in complexity
    assert all(v >= 0 for v in complexity.values())


@pytest.mark.parametrize(
    ("discover_fn", "expected_variant"),
    [
        (discover_inductive_imf, "IM (fallback from IMf)"),
        (discover_inductive_imd, "IM (fallback from IMd)"),
    ],
)
def test_inductive_variant_fallback_reports_actual_execution_path(log, monkeypatch, discover_fn, expected_variant):
    class _Place:
        def __init__(self, name: str):
            self.name = name

    fake_net = SimpleNamespace(
        transitions=[object(), object()],
        places=[_Place("p0"), _Place("p1")],
        arcs=[object(), object(), object()],
    )

    def _fake_apply(event_log, variant=None):
        if variant is not None:
            raise RuntimeError("variant unavailable")
        return "fallback-tree"

    monkeypatch.setattr(inductive_algorithm, "apply", _fake_apply)
    monkeypatch.setattr(pt_converter, "apply", lambda tree: (fake_net, [_Place("p0")], [_Place("p1")]))
    monkeypatch.setattr(petri_utils, "get_final_marking", lambda net: [_Place("p1")], raising=False)

    result = discover_fn(log)

    assert result.variant == expected_variant
