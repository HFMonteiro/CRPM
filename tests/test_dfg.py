"""Tests for crpm.dfg_utils — DFG discovery, filtering, statistics."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.importer.xes import importer as xes_importer

from crpm.dfg_utils import (
    discover_dfg_frequency,
    discover_dfg_performance,
    filter_dfg_by_frequency,
    filter_dfg_by_coverage,
    get_dfg_statistics,
    rank_dfg_edges,
    render_dfg_to_svg,
)
from crpm.pages import dfg as dfg_page

LOG_PATH = "examples/running-example.xes"


@pytest.fixture(scope="module")
def log():
    return xes_importer.apply(LOG_PATH)


def test_discover_dfg_frequency_returns_triple(log):
    dfg, start, end = discover_dfg_frequency(log)
    assert isinstance(dfg, dict)
    assert isinstance(start, dict)
    assert isinstance(end, dict)
    assert len(dfg) > 0


def test_discover_dfg_performance_returns_triple(log):
    dfg, start, end = discover_dfg_performance(log)
    assert isinstance(dfg, dict)
    assert len(dfg) > 0


def test_filter_dfg_removes_low_frequency_edges(log):
    dfg, start, end = discover_dfg_frequency(log)
    total_edges = len(dfg)
    filtered_dfg, _, _ = filter_dfg_by_frequency(dfg, start, end, min_frequency=2)
    assert len(filtered_dfg) <= total_edges


def test_rank_dfg_edges_orders_by_descending_value():
    dfg = {
        ("A", "B"): 10,
        ("B", "C"): 6,
        ("C", "D"): 3,
        ("D", "E"): 1,
    }

    ranked = rank_dfg_edges(dfg)
    assert [row["rank"] for row in ranked] == [1, 2, 3, 4]
    assert ranked[0]["coverage_pct"] == 100.0
    assert ranked[-1]["coverage_pct"] == 0.0
    assert ranked[0]["value"] == 10


def test_filter_dfg_by_coverage_keeps_full_range():
    dfg = {
        ("A", "B"): 10,
        ("B", "C"): 6,
        ("C", "D"): 3,
        ("D", "E"): 1,
    }
    start = {"A": 10}
    end = {"E": 1}

    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_coverage(dfg, start, end, coverage_range=(0, 100))

    assert filtered_dfg == dfg
    assert filtered_start == start
    assert filtered_end == end


def test_filter_dfg_by_coverage_selects_dominant_edges():
    dfg = {
        ("A", "B"): 10,
        ("B", "C"): 6,
        ("C", "D"): 3,
        ("D", "E"): 1,
    }
    start = {"A": 10}
    end = {"E": 1}

    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_coverage(dfg, start, end, coverage_range=(50, 100))

    assert set(filtered_dfg) == {("A", "B"), ("B", "C")}
    assert filtered_start == {"A": 10}
    assert filtered_end == {}


def test_filter_dfg_by_coverage_selects_rare_edges():
    dfg = {
        ("A", "B"): 10,
        ("B", "C"): 6,
        ("C", "D"): 3,
        ("D", "E"): 1,
    }
    start = {"A": 10, "D": 1}
    end = {"E": 1}

    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_coverage(dfg, start, end, coverage_range=(0, 25))

    assert set(filtered_dfg) == {("D", "E")}
    assert filtered_start == {"D": 1}
    assert filtered_end == {"E": 1}


def test_filter_dfg_by_coverage_returns_empty_when_over_restricted():
    dfg = {
        ("A", "B"): 10,
        ("B", "C"): 6,
        ("C", "D"): 3,
        ("D", "E"): 1,
    }

    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_coverage(dfg, {"A": 10}, {"E": 1}, coverage_range=(25, 25))

    assert filtered_dfg == {}
    assert filtered_start == {}
    assert filtered_end == {}


def test_filter_dfg_by_coverage_handles_empty_input():
    filtered_dfg, filtered_start, filtered_end = filter_dfg_by_coverage({}, {}, {}, coverage_range=(0, 100))

    assert filtered_dfg == {}
    assert filtered_start == {}
    assert filtered_end == {}


def test_dfg_statistics_returns_expected_keys(log):
    dfg, start, end = discover_dfg_frequency(log)
    stats = get_dfg_statistics(dfg, start, end)
    assert "num_activities" in stats
    assert "num_edges" in stats
    assert stats["num_activities"] > 0
    assert stats["num_edges"] > 0


def test_render_dfg_page_uses_coverage_slider_and_ranked_table(monkeypatch):
    calls = {"labels": [], "charts": 0, "tables": [], "notes": [], "captions": [], "metrics": [], "markdown": []}

    class _Column:
        def __init__(self, index: int):
            self.index = index

        def selectbox(self, label, options, **kwargs):
            calls["labels"].append(label)
            return "Frequency"

        def slider(self, label, **kwargs):
            calls["labels"].append(label)
            return (50, 100)

        def metric(self, *args, **kwargs):
            calls["metrics"].append(args)
            return None

        def dataframe(self, df, **kwargs):
            calls["tables"].append(df)
            return None

    class _Spinner:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    snapshot = SimpleNamespace(
        analysis_complete=True,
        filtered_log=[[{"concept:name": "A"}, {"concept:name": "B"}]],
        filter_key="sample",
        dfg_cache={},
    )

    monkeypatch.setattr(dfg_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "caption", lambda text, **kwargs: calls["captions"].append(text))
    monkeypatch.setattr(dfg_page.st, "columns", lambda spec, **kwargs: [_Column(i) for i in range(len(spec) if not isinstance(spec, int) else spec)])
    monkeypatch.setattr(dfg_page.st, "spinner", lambda *args, **kwargs: _Spinner())
    monkeypatch.setattr(dfg_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "image", lambda *args, **kwargs: calls.__setitem__("charts", calls["charts"] + 1))
    monkeypatch.setattr(dfg_page.st, "dataframe", lambda df, **kwargs: calls["tables"].append(df))
    monkeypatch.setattr(dfg_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(dfg_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(dfg_page, "render_inline_empty", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(dfg_page, "discover_dfg_frequency", lambda log: ({("A", "B"): 10, ("B", "C"): 6, ("C", "D"): 3, ("D", "E"): 1}, {"A": 1}, {"E": 1}))
    monkeypatch.setattr(dfg_page, "discover_dfg_performance", lambda log: ({("A", "B"): 10, ("B", "C"): 6, ("C", "D"): 3, ("D", "E"): 1}, {"A": 1}, {"E": 1}))
    monkeypatch.setattr(dfg_page, "render_dfg_to_svg", lambda *args, **kwargs: "<svg><text>demo</text></svg>")
    monkeypatch.setattr(dfg_page, "render_dfg_to_png", lambda *args, **kwargs: b"png")

    dfg_page.render_dfg_page(snapshot)

    assert "Edge frequency coverage (%)" in calls["labels"]
    assert any("Coverage (%)" in list(table.columns) for table in calls["tables"])
    assert any("ranked band of edges" in text.lower() for text in calls["notes"])
    assert any("Most frequent edge" == metric[0] for metric in calls["metrics"])
    assert any("Frequency" in list(table.columns) for table in calls["tables"])
    assert any("crpm-dfg-vector" in text for text in calls["markdown"])
    assert calls["charts"] == 0


def test_render_dfg_page_supports_performance_mode(monkeypatch):
    calls = {"labels": [], "variant": None, "metrics": [], "tables": [], "markdown": []}

    class _Column:
        def selectbox(self, label, options, **kwargs):
            calls["labels"].append(label)
            return "Performance"

        def slider(self, label, **kwargs):
            calls["labels"].append(label)
            return (0, 100)

        def metric(self, *args, **kwargs):
            calls["metrics"].append(args)
            return None

        def dataframe(self, df, **kwargs):
            calls["tables"].append(df)
            return None

    class _Spinner:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    snapshot = SimpleNamespace(
        analysis_complete=True,
        filtered_log=[[{"concept:name": "A"}, {"concept:name": "B"}]],
        filter_key="sample",
        dfg_cache={},
    )

    monkeypatch.setattr(dfg_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "columns", lambda spec, **kwargs: [_Column() for _ in range(len(spec) if not isinstance(spec, int) else spec)])
    monkeypatch.setattr(dfg_page.st, "spinner", lambda *args, **kwargs: _Spinner())
    monkeypatch.setattr(dfg_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "dataframe", lambda df, **kwargs: calls["tables"].append(df))
    monkeypatch.setattr(dfg_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(dfg_page, "render_quiet_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page, "render_inline_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page, "discover_dfg_frequency", lambda log: ({("A", "B"): 10}, {"A": 1}, {"B": 1}))
    monkeypatch.setattr(dfg_page, "discover_dfg_performance", lambda log: ({("A", "B"): 10}, {"A": 1}, {"B": 1}))
    monkeypatch.setattr(
        dfg_page,
        "render_dfg_to_svg",
        lambda *args, **kwargs: calls.__setitem__("variant", kwargs.get("variant")) or "<svg><text>demo</text></svg>",
    )
    monkeypatch.setattr(dfg_page, "render_dfg_to_png", lambda *args, **kwargs: b"png")

    dfg_page.render_dfg_page(snapshot)

    assert "DFG type" in calls["labels"]
    assert any("Slowest edge" == metric[0] for metric in calls["metrics"])
    assert any("Median delay (days)" in list(table.columns) for table in calls["tables"])
    assert calls["variant"] == "performance"
    assert any("crpm-dfg-vector" in text for text in calls["markdown"])


def test_render_dfg_page_falls_back_to_png_when_svg_fails(monkeypatch):
    calls = {"image": [], "warnings": [], "variant": None}

    class _Column:
        def selectbox(self, label, options, **kwargs):
            return "Frequency"

        def slider(self, label, **kwargs):
            return (0, 100)

        def metric(self, *args, **kwargs):
            return None

        def dataframe(self, *args, **kwargs):
            return None

    class _Spinner:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    snapshot = SimpleNamespace(
        analysis_complete=True,
        filtered_log=[[{"concept:name": "A"}, {"concept:name": "B"}]],
        filter_key="sample",
        dfg_cache={},
    )

    monkeypatch.setattr(dfg_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "columns", lambda spec, **kwargs: [_Column() for _ in range(len(spec) if not isinstance(spec, int) else spec)])
    monkeypatch.setattr(dfg_page.st, "spinner", lambda *args, **kwargs: _Spinner())
    monkeypatch.setattr(dfg_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "image", lambda *args, **kwargs: calls["image"].append(args[0]))
    monkeypatch.setattr(dfg_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page.st, "warning", lambda text, **kwargs: calls["warnings"].append(text))
    monkeypatch.setattr(dfg_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page, "render_quiet_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page, "render_inline_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(dfg_page, "discover_dfg_frequency", lambda log: ({("A", "B"): 10, ("B", "C"): 6}, {"A": 1}, {"C": 1}))
    monkeypatch.setattr(dfg_page, "discover_dfg_performance", lambda log: ({("A", "B"): 10, ("B", "C"): 6}, {"A": 1}, {"C": 1}))
    monkeypatch.setattr(dfg_page, "render_dfg_to_svg", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("svg boom")))
    monkeypatch.setattr(dfg_page, "render_dfg_to_png", lambda *args, **kwargs: calls.__setitem__("variant", kwargs.get("variant")) or b"png")

    dfg_page.render_dfg_page(snapshot)

    assert calls["image"]
    assert calls["variant"] == "frequency"
    assert any("svg rendering failed" in text.lower() for text in calls["warnings"])


def test_render_dfg_to_svg_returns_vector_markup():
    svg = render_dfg_to_svg(
        {
            ("A", "B"): 10,
            ("B", "C"): 4,
        },
        {"A": 2},
        {"C": 1},
    )
    assert svg.startswith("<")
    assert "<svg" in svg
    assert "width:100%" in svg


def test_render_dfg_to_svg_uses_pipe_output_and_responsive_wrapper(monkeypatch):
    class _Gviz:
        def pipe(self, format):
            assert format == "svg"
            return b"<svg xmlns='http://www.w3.org/2000/svg'><text>demo</text></svg>"

    monkeypatch.setattr("crpm.dfg_utils.dfg_visualizer.apply", lambda *args, **kwargs: _Gviz())

    svg = render_dfg_to_svg({("A", "B"): 1}, {"A": 1}, {"B": 1})

    assert svg.startswith("<svg ")
    assert "style=\"width:100%; height:auto; display:block;\"" in svg
    assert "demo" in svg
