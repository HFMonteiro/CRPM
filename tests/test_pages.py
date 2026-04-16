from types import SimpleNamespace

import pandas as pd

from crpm.app_state import AnalysisSnapshot
from crpm.pages import conformance as conformance_page
from crpm.pages import comparison as comparison_page
from crpm.pages import common as common_page
from crpm.pages.common import render_plotly_chart
from crpm.pages import discovery as discovery_page
from crpm.pages import overview as overview_page
from crpm.pages import performance as performance_page
from crpm.pages import operational_flow as operational_flow_page
from crpm.pages import variants as variants_page


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None

    def dataframe(self, *args, **kwargs):
        return None

    def markdown(self, *args, **kwargs):
        return None


def _snapshot(*, discovery_results=None, comparison_df=None) -> AnalysisSnapshot:
    return AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=[[{"concept:name": "Start"}, {"concept:name": "End"}]],
        discovery_results=discovery_results or {},
        comparison_df=comparison_df if comparison_df is not None else pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="Full available follow-up",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )


def _columns(spec, **kwargs):
    count = spec if isinstance(spec, int) else len(spec)
    return [_DummyContext() for _ in range(count)]


def _guarded_selectbox(expected_values):
    def _selectbox(label, *args, **kwargs):
        if label in {"Operational lens", "Comparison lens"}:
            raise AssertionError(f"Unexpected selectbox call for {label}")
        return expected_values[label]

    return _selectbox


def test_render_discovery_page_renders_summary_table(monkeypatch) -> None:
    calls = {"notes": []}
    monkeypatch.setattr(discovery_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(discovery_page.st, "caption", lambda text: calls.setdefault("caption", text))
    monkeypatch.setattr(discovery_page.st, "columns", lambda n: [_DummyContext() for _ in range(n)])
    monkeypatch.setattr(discovery_page.st, "container", lambda border=False: _DummyContext())
    monkeypatch.setattr(discovery_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(discovery_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(discovery_page.st, "dataframe", lambda df, **kwargs: calls.setdefault("dataframe", df))
    monkeypatch.setattr(discovery_page, "render_quiet_note", lambda message: calls["notes"].append(message))

    result = SimpleNamespace(algorithm="Inductive Miner", variant="IMf", discovery_time_s=0.5, num_transitions=3, num_places=2, num_arcs=4)
    discovery_page.render_discovery_page(_snapshot(discovery_results={"Inductive": result}))

    assert calls["subheader"] == "Discovery"
    assert not calls["dataframe"].empty
    assert calls["notes"]


def test_render_overview_page_uses_cards_instead_of_status_dataframe(monkeypatch) -> None:
    calls = {"markdown": [], "notes": [], "metrics": []}
    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="screening_conformance_demo.xes",
        filter_key="filter",
        filtered_log=[[{"concept:name": "Start"}, {"concept:name": "End"}]],
        discovery_results={"Inductive": object(), "Heuristics": object()},
        comparison_df=pd.DataFrame([{"model_name": "Inductive"}]),
        split_info={},
        analysis_summary={
            "cases": 1000,
            "events": 3436,
            "unique_activities": 8,
            "period_label": "2024-01-01 → 2024-05-21",
            "model_count": 2,
            "best_model": "Heuristics (Classic)",
            "best_fitness": 1.0,
            "best_precision": 1.0,
            "best_balance": 1.0,
            "dominant_path_share": 63.4,
            "deviation_share": 66.2,
            "median_throughput_days": 57.0,
            "workflow_nodes": 8,
            "workflow_edges": 7,
            "analysis_runtime_s": 1.3,
        },
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={"p": {}},
        variant_cache={"v": {}},
        dfg_cache={"d": {}},
        conformance_results={},
        conformance_workspace={"workflow": {"nodes": pd.DataFrame(), "edges": pd.DataFrame()}},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    monkeypatch.setattr(overview_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(overview_page.st, "columns", _columns)
    monkeypatch.setattr(overview_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(overview_page, "render_quiet_note", lambda message: calls["notes"].append(message))

    overview_page.render_overview_page(snapshot)

    assert calls["notes"]
    assert any("crpm-overview-hero" in text for text in calls["markdown"])
    assert any("crpm-page-card-grid" in text for text in calls["markdown"])


def test_render_comparison_page_renders_dataframe_and_charts(monkeypatch) -> None:
    calls = {"charts": []}
    monkeypatch.setattr(comparison_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(comparison_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(comparison_page.st, "dataframe", lambda df, **kwargs: calls.setdefault("dataframe", df))
    monkeypatch.setattr(comparison_page.st, "columns", lambda n: [_DummyContext() for _ in range(n)])
    monkeypatch.setattr(comparison_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(comparison_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(comparison_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))
    monkeypatch.setattr(comparison_page, "create_fitness_precision_scatter", lambda df: object())
    monkeypatch.setattr(comparison_page, "create_model_comparison_heatmap", lambda df, metrics: object())

    comparison_df = pd.DataFrame(
        [
            {
                "model_name": "Inductive",
                "alignment_fitness": 0.92,
                "token_fitness": 0.9,
                "precision": 0.85,
                "discovery_time_s": 0.5,
            },
            {
                "model_name": "Heuristics",
                "alignment_fitness": 0.88,
                "token_fitness": 0.86,
                "precision": 0.8,
                "discovery_time_s": 0.3,
            },
        ]
    )
    comparison_page.render_comparison_page(_snapshot(comparison_df=comparison_df))

    assert calls["subheader"] == "Model Comparison"
    assert not calls["dataframe"].empty
    assert len(calls["charts"]) == 2


def test_render_operational_flow_page_renders_charts(monkeypatch) -> None:
    calls = {"charts": [], "notes": [], "captions": []}
    log = [
        [
            {"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")},
            {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-03")},
            {"concept:name": "FIT_return", "time:timestamp": pd.Timestamp("2024-01-10")},
        ]
    ]

    monkeypatch.setattr(operational_flow_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(operational_flow_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "columns", _columns)
    monkeypatch.setattr(operational_flow_page.st, "selectbox", _guarded_selectbox({"View": "Full log"}))
    monkeypatch.setattr(operational_flow_page.st, "segmented_control", lambda label, options, **kwargs: "Stage flow")
    monkeypatch.setattr(operational_flow_page.st, "checkbox", lambda *args, **kwargs: False)
    monkeypatch.setattr(operational_flow_page.st, "slider", lambda *args, **kwargs: 13)
    monkeypatch.setattr(operational_flow_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(operational_flow_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "caption", lambda text, **kwargs: calls["captions"].append(text))
    monkeypatch.setattr(operational_flow_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(operational_flow_page, "render_inline_empty", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(operational_flow_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=log,
        discovery_results={},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    operational_flow_page.render_operational_flow_page(snapshot)

    assert calls["subheader"] == "Operational Flow"
    assert len(calls["charts"]) == 1
    assert any("weekly case volumes" in text.lower() for text in calls["captions"])


def test_render_operational_flow_page_uses_data_driven_period_defaults(monkeypatch) -> None:
    calls = {"charts": [], "date_inputs": [], "notes": []}
    log = [
        [
            {"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2010-12-30")},
            {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2010-12-31")},
        ],
        [
            {"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2011-01-12")},
            {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2011-01-24")},
        ],
    ]

    def _date_input(label, value=None, **kwargs):
        calls["date_inputs"].append((label, value))
        return value

    monkeypatch.setattr(operational_flow_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(operational_flow_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "columns", _columns)
    monkeypatch.setattr(operational_flow_page.st, "selectbox", _guarded_selectbox({"View": "PRE vs POST"}))
    monkeypatch.setattr(operational_flow_page.st, "segmented_control", lambda label, options, **kwargs: "Stage flow")
    monkeypatch.setattr(operational_flow_page.st, "checkbox", lambda *args, **kwargs: False)
    monkeypatch.setattr(operational_flow_page.st, "slider", lambda *args, **kwargs: 13)
    monkeypatch.setattr(operational_flow_page.st, "date_input", _date_input)
    monkeypatch.setattr(operational_flow_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(operational_flow_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(operational_flow_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=log,
        discovery_results={},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    operational_flow_page.render_operational_flow_page(snapshot)

    assert ("PRE start", pd.Timestamp("2010-12-30").date()) in calls["date_inputs"]
    assert ("POST end", pd.Timestamp("2011-01-12").date()) in calls["date_inputs"]
    assert len(calls["charts"]) == 2
    assert any("default pre/post windows are derived" in text.lower() for text in calls["notes"])


def test_render_operational_flow_page_uses_inline_placeholder_for_empty_aging(monkeypatch) -> None:
    calls = {"charts": [], "inline_empty": []}

    monkeypatch.setattr(operational_flow_page.st, "subheader", lambda text: None)
    monkeypatch.setattr(operational_flow_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "columns", _columns)
    monkeypatch.setattr(operational_flow_page.st, "selectbox", _guarded_selectbox({"View": "Full log"}))
    monkeypatch.setattr(operational_flow_page.st, "segmented_control", lambda label, options, **kwargs: "Stage aging")
    monkeypatch.setattr(operational_flow_page.st, "checkbox", lambda *args, **kwargs: False)
    monkeypatch.setattr(operational_flow_page.st, "slider", lambda *args, **kwargs: 13)
    monkeypatch.setattr(operational_flow_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(operational_flow_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page, "render_quiet_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(operational_flow_page, "render_inline_empty", lambda message: calls["inline_empty"].append(message))
    monkeypatch.setattr(operational_flow_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))

    monkeypatch.setattr(
        operational_flow_page,
        "build_operational_view",
        lambda *args, **kwargs: {
            "kpis": {
                "total_cases": 1,
                "fit_return_rate": 0.5,
                "colonoscopy_completion_rate": 0.5,
                "current_awaiting_colonoscopy": 0,
            },
            "weekly_counts": pd.DataFrame(),
            "stock_levels": pd.DataFrame(),
            "aging_metrics": pd.DataFrame(),
        },
    )

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=[
            [
                {"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")},
                {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")},
            ]
        ],
        discovery_results={},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="Full available follow-up",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    operational_flow_page.render_operational_flow_page(snapshot)

    assert calls["inline_empty"] == ["No stage-aging transitions were observed in this selection."]


def test_render_conformance_page_renders_workspace(monkeypatch) -> None:
    calls = {"dataframes": [], "metrics": [], "captions": [], "markdown": [], "notes": [], "inline_empty": [], "workflow": [], "selectbox": [], "html": [], "tabs": []}
    workspace = {
        "model_summary_df": pd.DataFrame(
            [
                {
                    "model": "Inductive",
                    "algorithm": "Inductive Miner",
                    "variant": "IMf",
                    "alignment_fitness": 0.91,
                    "token_fitness": 0.89,
                    "precision": 0.85,
                    "quadrant": "Ideal Zone",
                    "fitness_quality": "Good",
                    "precision_quality": "Good",
                    "recommendation": "Recommended",
                    "summary": "log_fitness=0.91",
                }
            ]
        ),
        "deviation_summary_df": pd.DataFrame(
            [
                {
                    "model": "Inductive",
                    "alignment_summary": "log_fitness=0.91",
                    "token_summary": "log_fitness=0.89",
                    "precision": 0.85,
                    "deviation_note": "Alignment and token replay are in close agreement.",
                }
            ]
        ),
        "trace_deviation_df": pd.DataFrame(
            [
                {
                    "model": "Inductive",
                    "trace_index": 0,
                    "alignment_fitness": 0.75,
                    "token_trace_fitness": 0.70,
                    "alignment_cost": 2.0,
                    "missing_tokens": 1,
                    "remaining_tokens": 0,
                    "trace_status": "Deviating",
                }
            ]
        ),
        "workflow": {
            "nodes": pd.DataFrame(
                [
                    {
                        "step": "invitation",
                        "activity": "Invitation_mail",
                        "display_name": "Invitation",
                        "cases": 2,
                        "occurrences": 2,
                        "median_next_delay_days": 1.0,
                        "p90_next_delay_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "edges": pd.DataFrame(
                [
                    {
                        "source": "Invitation_mail",
                        "target": "FIT_mail",
                        "frequency": 2,
                        "share_pct": 100.0,
                        "median_days": 1.0,
                        "p90_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "legend": pd.DataFrame(
                [
                    {"bucket": "Conformant", "meaning": "No meaningful delay deviation detected", "severity": "Low"}
                ]
            ),
        },
    }

    monkeypatch.setattr(conformance_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(conformance_page.st, "caption", lambda text: calls["captions"].append(text))
    monkeypatch.setattr(conformance_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(conformance_page.st, "dataframe", lambda df, **kwargs: calls["dataframes"].append(df))
    monkeypatch.setattr(conformance_page.st, "metric", lambda *args, **kwargs: calls["metrics"].append(args))
    monkeypatch.setattr(conformance_page.st, "columns", lambda n, **kwargs: [_DummyContext() for _ in range(n if isinstance(n, int) else len(n))])
    monkeypatch.setattr(conformance_page.st, "container", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "tabs", lambda labels: calls["tabs"].append(tuple(labels)) or [_DummyContext() for _ in labels])
    monkeypatch.setattr(conformance_page.st, "radio", lambda *args, **kwargs: "Board mode")
    monkeypatch.setattr(conformance_page.st, "selectbox", lambda label, options, index=0, **kwargs: calls["selectbox"].append((label, tuple(options))) or options[index])
    monkeypatch.setattr(conformance_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(conformance_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(conformance_page, "render_legend_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(conformance_page, "render_inline_empty", lambda message: calls["inline_empty"].append(message))
    monkeypatch.setattr(conformance_page, "render_workflow_conformance_svg", lambda workflow: calls["workflow"].append(workflow) or "<svg>mock</svg>")
    monkeypatch.setattr(conformance_page.components, "html", lambda html, **kwargs: calls["html"].append(html))

    snapshot = _snapshot(comparison_df=pd.DataFrame())
    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name=snapshot.input_name,
        filter_key=snapshot.filter_key,
        filtered_log=snapshot.filtered_log,
        discovery_results={"Inductive": SimpleNamespace(algorithm="Inductive Miner", variant="IMf", num_transitions=3)},
        comparison_df=pd.DataFrame(),
        split_info=snapshot.split_info,
        analysis_summary={},
        active_followup_label=snapshot.active_followup_label,
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace=workspace,
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    conformance_page.render_conformance_page(snapshot)

    assert calls["subheader"] == "Conformance Analytics"
    assert calls["metrics"]
    assert "<svg>mock</svg>" in calls["markdown"]
    assert calls["workflow"]
    assert calls["notes"]
    assert ("Activities", "Transitions", "Models") in calls["tabs"]
    explanatory_text = " ".join(str(text).lower() for text in [*calls["captions"], *calls["markdown"], *calls["notes"]])
    assert "workflow pathway board" in explanatory_text
    assert any(label == "Coverage" for label, _ in calls["selectbox"])
    assert any(label == "Detail level" for label, _ in calls["selectbox"])
    assert any(label == "Selected node" for label, _ in calls["selectbox"])
    assert any("crpm-selection-card" in text for text in calls["markdown"])
    assert any("crpm-model-card-grid" in text for text in calls["markdown"])
    assert any("crpm-ranked-table" in text for text in calls["markdown"])
    assert any("crpm-mode-banner" in text for text in calls["markdown"])


def test_conformance_label_helpers_humanize_raw_workflow_labels() -> None:
    node_row = pd.Series({"display_name": "PCC_observation"})
    edge_row = pd.Series({"business_label": "Lab_return → Admin_review"})

    assert conformance_page._node_display_label(node_row) == "PCC observation"
    assert conformance_page._edge_display_label(edge_row) == "Lab return → Admin review"


def test_conformance_label_helpers_humanize_raw_workflow_names() -> None:
    node_row = pd.Series({"display_name": "PCC_observation", "activity": "PCC_observation"})
    edge_row = pd.Series({"business_label": "Lab_return → PCC_observation"})

    assert conformance_page._node_display_label(node_row) == "PCC observation"
    assert conformance_page._edge_display_label(edge_row) == "Lab return → PCC observation"


def test_conformance_option_labels_humanize_raw_activity_names() -> None:
    node_row = pd.Series({"activity": "PCC_observation", "cases": 28, "conformance_bucket": "Model deviation"})
    edge_row = pd.Series({"source": "Lab_return", "target": "PCC_observation", "frequency": 28, "conformance_bucket": "Model deviation"})

    assert conformance_page._node_option_label(node_row).startswith("PCC observation")
    assert conformance_page._edge_option_label(edge_row).startswith("Lab return → PCC observation")


def test_render_conformance_page_falls_back_to_comparison_dataframe(monkeypatch) -> None:
    calls = {"dataframes": [], "metrics": [], "markdown": [], "workflow": [], "inline_empty": [], "tabs": []}
    comparison_df = pd.DataFrame(
        [
            {
                "model_name": "Inductive",
                "alignment_fitness": 0.91,
                "token_fitness": 0.89,
                "precision": 0.85,
                "quadrant": "Ideal Zone",
                "fitness_quality": "Good",
                "precision_quality": "Good",
            }
        ]
    )

    monkeypatch.setattr(conformance_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(conformance_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(conformance_page.st, "dataframe", lambda df, **kwargs: calls["dataframes"].append(df))
    monkeypatch.setattr(conformance_page.st, "metric", lambda *args, **kwargs: calls["metrics"].append(args))
    monkeypatch.setattr(conformance_page.st, "columns", lambda n, **kwargs: [_DummyContext() for _ in range(n if isinstance(n, int) else len(n))])
    monkeypatch.setattr(conformance_page.st, "container", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "tabs", lambda labels: calls["tabs"].append(tuple(labels)) or [_DummyContext() for _ in labels])
    monkeypatch.setattr(conformance_page.st, "radio", lambda *args, **kwargs: "Board mode")
    monkeypatch.setattr(conformance_page.st, "selectbox", lambda label, options, index=0, **kwargs: options[index])
    monkeypatch.setattr(conformance_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(conformance_page, "render_legend_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page, "render_inline_empty", lambda message: calls["inline_empty"].append(message))
    monkeypatch.setattr(conformance_page, "render_workflow_conformance_svg", lambda workflow: calls["workflow"].append(workflow) or "<svg>mock</svg>")

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=[[{"concept:name": "Invitation_mail"}]],
        discovery_results={"Inductive": SimpleNamespace(algorithm="Inductive Miner", variant="IMf", num_transitions=3)},
        comparison_df=comparison_df,
        split_info={},
        analysis_summary={},
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    conformance_page.render_conformance_page(snapshot)

    assert calls["subheader"] == "Conformance Analytics"
    assert calls["metrics"]
    assert not calls["workflow"]
    assert calls["inline_empty"]
    assert ("Activities", "Transitions", "Models") in calls["tabs"]


def test_render_conformance_page_interactive_mode_degrades_gracefully(monkeypatch) -> None:
    calls = {"dataframes": [], "notes": [], "warnings": [], "workflow": [], "markdown": []}

    workspace = {
        "model_summary_df": pd.DataFrame(
            [
                {
                    "model": "Inductive",
                    "algorithm": "Inductive Miner",
                    "variant": "IMf",
                    "alignment_fitness": 0.91,
                    "token_fitness": 0.89,
                    "precision": 0.85,
                    "quadrant": "Ideal Zone",
                    "fitness_quality": "Good",
                    "precision_quality": "Good",
                }
            ]
        ),
        "deviation_summary_df": pd.DataFrame(),
        "trace_deviation_df": pd.DataFrame(),
        "workflow": {
            "nodes": pd.DataFrame(
                [
                    {
                        "step": "invitation",
                        "activity": "Invitation_mail",
                        "display_name": "Invitation",
                        "cases": 2,
                        "occurrences": 2,
                        "median_next_delay_days": 1.0,
                        "p90_next_delay_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "edges": pd.DataFrame(
                [
                    {
                        "source": "Invitation_mail",
                        "target": "FIT_mail",
                        "frequency": 2,
                        "share_pct": 100.0,
                        "median_days": 1.0,
                        "p90_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "legend": pd.DataFrame(),
        },
    }

    monkeypatch.setattr(conformance_page.st, "subheader", lambda text: calls.setdefault("subheader", text))
    monkeypatch.setattr(conformance_page.st, "caption", lambda text: None)
    monkeypatch.setattr(conformance_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(conformance_page.st, "dataframe", lambda df, **kwargs: calls["dataframes"].append(df))
    monkeypatch.setattr(conformance_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "warning", lambda text, **kwargs: calls["warnings"].append(text))
    monkeypatch.setattr(conformance_page.st, "columns", lambda n, **kwargs: [_DummyContext() for _ in range(n if isinstance(n, int) else len(n))])
    monkeypatch.setattr(conformance_page.st, "container", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "tabs", lambda labels: [_DummyContext() for _ in labels])
    monkeypatch.setattr(conformance_page.st, "radio", lambda *args, **kwargs: "Interactive mode")
    monkeypatch.setattr(conformance_page.st, "selectbox", lambda label, options, index=0, **kwargs: options[index])
    monkeypatch.setattr(conformance_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(conformance_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(conformance_page, "render_legend_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(conformance_page, "render_inline_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page, "create_workflow_interactive_payload", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(conformance_page, "render_workflow_conformance_svg", lambda workflow: calls["workflow"].append(workflow) or "<svg>mock</svg>")

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=[[{"concept:name": "Invitation_mail"}]],
        discovery_results={"Inductive": SimpleNamespace(algorithm="Inductive Miner", variant="IMf", num_transitions=3)},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace=workspace,
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    conformance_page.render_conformance_page(snapshot)

    assert calls["subheader"] == "Conformance Analytics"
    assert calls["notes"]
    assert calls["warnings"]
    assert calls["workflow"]
    assert any("interactive workflow mode could not be rendered" in text.lower() for text in calls["warnings"])


def test_render_conformance_page_renders_html_explorer_without_selection(monkeypatch) -> None:
    calls = {"workflow": [], "html": [], "warnings": []}

    workspace = {
        "model_summary_df": pd.DataFrame(
            [
                {
                    "model": "Inductive",
                    "algorithm": "Inductive Miner",
                    "variant": "IMf",
                    "alignment_fitness": 0.91,
                    "token_fitness": 0.89,
                    "precision": 0.85,
                    "quadrant": "Ideal Zone",
                    "fitness_quality": "Good",
                    "precision_quality": "Good",
                }
            ]
        ),
        "deviation_summary_df": pd.DataFrame(),
        "trace_deviation_df": pd.DataFrame(),
        "workflow": {
            "nodes": pd.DataFrame(
                [
                    {
                        "step": "invitation",
                        "activity": "Invitation_mail",
                        "display_name": "Invitation",
                        "cases": 2,
                        "occurrences": 2,
                        "median_next_delay_days": 1.0,
                        "p90_next_delay_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "edges": pd.DataFrame(
                [
                    {
                        "source": "Invitation_mail",
                        "target": "FIT_mail",
                        "frequency": 2,
                        "share_pct": 100.0,
                        "median_days": 1.0,
                        "p90_days": 2.0,
                        "severity": "Low",
                    }
                ]
            ),
            "legend": pd.DataFrame(),
        },
    }

    monkeypatch.setattr(conformance_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "markdown", lambda text, **kwargs: calls["workflow"].append(text))
    monkeypatch.setattr(conformance_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.st, "warning", lambda text, **kwargs: calls["warnings"].append(text))
    monkeypatch.setattr(conformance_page.st, "columns", lambda n, **kwargs: [_DummyContext() for _ in range(n if isinstance(n, int) else len(n))])
    monkeypatch.setattr(conformance_page.st, "container", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "expander", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(conformance_page.st, "tabs", lambda labels: [_DummyContext() for _ in labels])
    monkeypatch.setattr(conformance_page.st, "radio", lambda *args, **kwargs: "Interactive mode")
    monkeypatch.setattr(conformance_page.st, "selectbox", lambda label, options, index=0, **kwargs: options[index])
    monkeypatch.setattr(conformance_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(conformance_page, "render_quiet_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page, "render_legend_note", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page, "render_inline_empty", lambda *args, **kwargs: None)
    monkeypatch.setattr(conformance_page.components, "html", lambda html, **kwargs: calls["html"].append(html))
    monkeypatch.setattr(conformance_page, "create_workflow_interactive_payload", lambda *args, **kwargs: {"nodes": [], "edges": [], "height": 520, "metric_coloring": "Conformance bucket"})
    monkeypatch.setattr(conformance_page, "render_workflow_explorer_html", lambda payload: "<div>interactive explorer</div>")
    monkeypatch.setattr(conformance_page, "render_workflow_conformance_svg", lambda workflow: "<svg>fallback</svg>")

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=[[{"concept:name": "Invitation_mail"}]],
        discovery_results={"Inductive": SimpleNamespace(algorithm="Inductive Miner", variant="IMf", num_transitions=3)},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="365-day follow-up window",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace=workspace,
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
        workflow_view_mode="interactive",
    )

    conformance_page.render_conformance_page(snapshot)

    assert calls["html"] == ["<div>interactive explorer</div>"]
    assert not any("fallback" in text for text in calls["workflow"])
    assert calls["warnings"] == []


def test_render_variant_page_renders_guidance_and_charts(monkeypatch) -> None:
    calls = {"guidance": [], "charts": [], "markdown": [], "tabs": []}
    variant_stats = pd.DataFrame(
        [
            {"variant_str": "A,B", "frequency": 5, "percentage": 50.0, "cumulative_percentage": 50.0},
            {"variant_str": "A,C", "frequency": 5, "percentage": 50.0, "cumulative_percentage": 100.0},
        ]
    )
    coverage = variant_stats.copy()
    conformance_df = pd.DataFrame()

    monkeypatch.setattr(variants_page.st, "subheader", lambda text: None)
    monkeypatch.setattr(variants_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(variants_page.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(variants_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(variants_page.st, "columns", _columns)
    monkeypatch.setattr(variants_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(variants_page.st, "tabs", lambda labels: calls["tabs"].append(tuple(labels)) or [_DummyContext() for _ in labels])
    monkeypatch.setattr(variants_page, "render_legend_note", lambda text: calls["guidance"].append(text))
    monkeypatch.setattr(variants_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))
    monkeypatch.setattr(variants_page, "store_cache_entry", lambda *args, **kwargs: None)
    monkeypatch.setattr(variants_page, "build_variant_index", lambda log: ("grouped", {"A": 5}))
    monkeypatch.setattr(variants_page, "get_variant_statistics", lambda log, variant_index=None: variant_stats)
    monkeypatch.setattr(variants_page, "compute_variant_coverage", lambda stats: coverage)
    monkeypatch.setattr(variants_page, "compute_variant_conformance", lambda *args, **kwargs: conformance_df)

    snapshot = _snapshot(discovery_results={"Inductive": SimpleNamespace(net=object(), initial_marking=object(), final_marking=object())})

    variants_page.render_variant_page(snapshot)

    assert calls["guidance"]
    assert len(calls["charts"]) == 2
    assert ("Frequency", "Coverage", "Conformance") in calls["tabs"]
    assert any("crpm-ranked-table" in text for text in calls["markdown"])


def test_render_plotly_chart_shows_user_warning_on_failure(monkeypatch) -> None:
    calls = {"warnings": []}

    monkeypatch.setattr(render_plotly_chart.__module__.split(".")[-1] == "common" and render_plotly_chart.__globals__["st"], "plotly_chart", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(render_plotly_chart.__globals__["st"], "warning", lambda text, **kwargs: calls["warnings"].append(text))

    render_plotly_chart(object(), key="demo-chart")

    assert calls["warnings"] == ["This chart could not be displayed. Please rerun the analysis or use the table below."]


def test_note_helpers_escape_html_content(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(common_page.st, "markdown", lambda text, **kwargs: calls.append(text))

    payload = '<script>alert("x")</script>'
    common_page.render_empty_state(payload)
    common_page.render_quiet_note(payload)
    common_page.render_legend_note(payload)
    common_page.render_inline_empty(payload)

    assert len(calls) == 4
    assert all("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in text for text in calls)
    assert all('<script>alert("x")</script>' not in text for text in calls)


def test_render_performance_page_reuses_timing_buckets(monkeypatch) -> None:
    calls = {"timing_buckets": 0, "case_buckets": None, "charts": [], "notes": [], "empties": []}
    log = [
        [
            {"concept:name": "A", "time:timestamp": pd.Timestamp("2024-01-01")},
            {"concept:name": "B", "time:timestamp": pd.Timestamp("2024-01-02")},
        ]
    ]

    monkeypatch.setattr(performance_page.st, "subheader", lambda text: None)
    monkeypatch.setattr(performance_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page.st, "columns", _columns)
    monkeypatch.setattr(performance_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))
    monkeypatch.setattr(performance_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(performance_page, "render_inline_empty", lambda message: calls["empties"].append(message))

    real_collect = performance_page.collect_timing_buckets
    real_compute_case_durations = performance_page.compute_case_durations

    def _collect_wrapper(current_log):
        calls["timing_buckets"] += 1
        return real_collect(current_log)

    def _case_wrapper(current_log, timing_buckets=None):
        calls["case_buckets"] = timing_buckets
        return real_compute_case_durations(current_log, timing_buckets=timing_buckets)

    monkeypatch.setattr(performance_page, "collect_timing_buckets", _collect_wrapper)
    monkeypatch.setattr(performance_page, "compute_case_durations", _case_wrapper)

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=log,
        discovery_results={},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="Full available follow-up",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    performance_page.render_performance_page(snapshot)

    assert calls["timing_buckets"] == 1
    assert calls["case_buckets"] is not None
    assert calls["charts"]
    assert any("bottlenecks are ranked" in text.lower() for text in calls["notes"])


def test_render_performance_page_uses_bi_case_duration_summary(monkeypatch) -> None:
    calls = {"markdown": [], "charts": [], "notes": []}
    log = [
        [
            {"concept:name": "Invitation", "time:timestamp": pd.Timestamp("2024-01-01")},
            {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-15")},
            {"concept:name": "FIT_return", "time:timestamp": pd.Timestamp("2024-02-10")},
        ],
        [
            {"concept:name": "Invitation", "time:timestamp": pd.Timestamp("2024-01-03")},
            {"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-12")},
            {"concept:name": "FIT_return", "time:timestamp": pd.Timestamp("2024-03-10")},
        ],
    ]

    monkeypatch.setattr(performance_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page.st, "columns", _columns)
    monkeypatch.setattr(performance_page.st, "markdown", lambda text, **kwargs: calls["markdown"].append(text))
    monkeypatch.setattr(performance_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(performance_page, "render_plotly_chart", lambda fig, key: calls["charts"].append(key))
    monkeypatch.setattr(performance_page, "render_quiet_note", lambda message: calls["notes"].append(message))
    monkeypatch.setattr(performance_page, "render_inline_empty", lambda *args, **kwargs: None)

    snapshot = AnalysisSnapshot(
        analysis_complete=True,
        input_name="sample.xes",
        filter_key="filter",
        filtered_log=log,
        discovery_results={},
        comparison_df=pd.DataFrame(),
        split_info={},
        analysis_summary={},
        active_followup_label="Full available follow-up",
        config_change_message=None,
        filter_error_message=None,
        performance_cache={},
        variant_cache={},
        dfg_cache={},
        conformance_results={},
        conformance_workspace={},
        selected_algorithms=("Heuristics (Classic)",),
        stage_timings={},
    )

    performance_page.render_performance_page(snapshot)

    assert any("crpm-bi-card-grid" in text for text in calls["markdown"])
    assert any("Distribution detail" in text for text in calls["markdown"])
    assert any("median and p90" in text.lower() for text in calls["notes"])
