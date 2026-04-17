"""Tests for crpm.visualization — Plotly chart builders."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from crpm.visualization import (
    create_workflow_interactive_payload,
    create_activity_duration_chart,
    create_bottleneck_chart,
    create_case_duration_histogram,
    create_fitness_precision_scatter,
    filter_workflow_payload,
    create_model_comparison_heatmap,
    create_operational_flow_chart,
    create_queue_stock_chart,
    create_stage_aging_chart,
    create_variant_coverage_chart,
    create_variant_frequency_chart,
    create_workflow_cytoscape_payload,
    create_workflow_conformance_sankey,
    render_workflow_explorer_html,
    render_workflow_conformance_svg,
)


def test_bottleneck_chart_returns_figure():
    df = pd.DataFrame(
        {
            "transition": ["A → B", "B → C"],
            "bottleneck_score": [0.8, 0.5],
            "median_duration_s": [86400, 43200],
            "p90_duration_s": [172800, 86400],
            "frequency": [10, 5],
        }
    )
    fig = create_bottleneck_chart(df)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "bar"
    assert fig.layout.barmode is None


def test_bottleneck_chart_collapses_equal_median_and_p90_values():
    df = pd.DataFrame(
        {
            "transition": ["A → B", "B → C"],
            "bottleneck_score": [0.8, 0.5],
            "median_duration_s": [86400, 43200],
            "p90_duration_s": [86400, 86400],
            "frequency": [10, 5],
        }
    )
    fig = create_bottleneck_chart(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.data[0].type == "bar"
    assert fig.data[1].type == "scatter"
    assert any("Flat interval" in annotation.text for annotation in fig.layout.annotations)


def test_activity_duration_chart_returns_figure():
    df = pd.DataFrame(
        {
            "activity": ["A", "B", "C"],
            "frequency": [20, 10, 5],
            "mean_duration_s": [3600, 7200, 1800],
            "median_duration_s": [3000, 6000, 1500],
        }
    )
    fig = create_activity_duration_chart(df)
    assert isinstance(fig, go.Figure)


def test_case_duration_histogram_returns_figure():
    df = pd.DataFrame({"case_id": [f"c{i}" for i in range(50)], "duration_days": list(range(50))})
    fig = create_case_duration_histogram(df)
    assert isinstance(fig, go.Figure)


def test_variant_frequency_chart_returns_figure():
    df = pd.DataFrame(
        {
            "variant": ["A → B → C", "A → C"],
            "variant_str": ["A → B → C", "A → C"],
            "frequency": [5, 3],
            "percentage": [62.5, 37.5],
        }
    )
    fig = create_variant_frequency_chart(df)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].text is None
    assert fig.data[0].hovertemplate is not None


def test_variant_coverage_chart_returns_figure():
    df = pd.DataFrame(
        {
            "variant_rank": [1, 2, 3],
            "cumulative_coverage": [0.5, 0.8, 1.0],
        }
    )
    fig = create_variant_coverage_chart(df)
    assert isinstance(fig, go.Figure)


def test_fitness_precision_scatter_returns_figure():
    df = pd.DataFrame(
        {
            "model_name": ["IM", "IMf"],
            "alignment_fitness": [0.9, 0.95],
            "precision": [0.8, 0.85],
        }
    )
    fig = create_fitness_precision_scatter(df)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].mode == "markers"
    if len(fig.data) > 1:
        assert fig.data[1].mode == "markers"
    assert fig.layout.width is None


def test_model_comparison_heatmap_returns_figure():
    df = pd.DataFrame(
        {
            "model_name": ["IM", "IMf"],
            "alignment_fitness": [0.9, 0.95],
            "precision": [0.8, 0.85],
        }
    )
    fig = create_model_comparison_heatmap(df, metrics=["alignment_fitness", "precision"])
    assert isinstance(fig, go.Figure)
    assert fig.layout.width is None


def test_operational_flow_chart_returns_figure():
    df = pd.DataFrame(
        {
            "Invitation": [10, 8, 7],
            "FIT mail": [9, 7, 6],
            "FIT return": [6, 5, 4],
        },
        index=[0, 1, 2],
    )
    fig = create_operational_flow_chart(df)
    assert isinstance(fig, go.Figure)
    assert fig.layout.font.color
    assert fig.layout.hoverlabel.font.color == "#ffffff"
    assert fig.layout.legend.font.color == "#1f2c25"
    assert fig.layout.legend.bgcolor == "rgba(251, 249, 253, 0.99)"


def test_queue_stock_chart_returns_figure():
    df = pd.DataFrame(
        {
            "Pending FIT return": [5, 7, 6],
            "Awaiting lab result": [2, 3, 4],
            "Awaiting colonoscopy": [1, 2, 3],
        },
        index=[0, 1, 2],
    )
    fig = create_queue_stock_chart(df)
    assert isinstance(fig, go.Figure)
    assert fig.layout.plot_bgcolor
    assert fig.layout.font.color


def test_stage_aging_chart_returns_figure():
    df = pd.DataFrame(
        {
            "transition": ["FIT_mail → FIT_return", "PCC_observation → Colonoscopy_center"],
            "frequency": [10, 5],
            "median_days": [7.0, 32.0],
            "p90_days": [14.0, 60.0],
        }
    )
    fig = create_stage_aging_chart(df)
    assert isinstance(fig, go.Figure)
    assert fig.layout.font.color == "#1f2c25"
    assert fig.layout.plot_bgcolor == "#f4f0f8"
    assert len(fig.data) >= 2
    assert fig.layout.legend.font.color == "#1f2c25"
    assert fig.layout.annotationdefaults.font.color == "#1f2c25"


def test_empty_chart_annotation_uses_readable_theme():
    fig = create_stage_aging_chart(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert fig.layout.font.color == "#1f2c25"
    assert fig.layout.annotations[0].font.color == "#1f2c25"
    assert fig.layout.annotations[0].bgcolor


def test_workflow_board_svg_returns_markup():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "step": "invitation",
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 140,
                    "occurrences": 145,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 45.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "node_type": "start",
                },
                {
                    "step": "fit_mail",
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 136,
                    "occurrences": 140,
                    "median_next_delay_days": 56.0,
                    "p90_next_delay_days": 63.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Log deviation",
                    "branch_role": "mainline",
                    "lane": "center",
                    "node_type": "mainline",
                },
                {
                    "step": "reminder",
                    "activity": "Reminder_mail",
                    "display_name": "Reminder",
                    "cases": 42,
                    "occurrences": 42,
                    "median_next_delay_days": 12.0,
                    "p90_next_delay_days": 18.0,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "lane": "left",
                    "branch_family": "reminder",
                    "node_type": "deviation",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"edge_id": "Invitation_mail -> FIT_mail", "source": "Invitation_mail", "target": "FIT_mail", "frequency": 145128, "median_days": 35.0, "p90_days": 45.0, "severity": "Low", "share_pct": 82.5, "conformance_bucket": "Conformant", "is_deviating": False, "stroke_style": "solid", "branch_role": "mainline", "edge_type": "expected"},
                {"edge_id": "FIT_mail -> FIT_mail", "source": "FIT_mail", "target": "FIT_mail", "frequency": 61, "median_days": 56.0, "p90_days": 63.0, "severity": "Critical", "share_pct": 0.1, "conformance_bucket": "Log deviation", "is_deviating": True, "stroke_style": "dashed", "branch_role": "side", "edge_type": "loop"},
                {"edge_id": "FIT_mail -> Reminder_mail", "source": "FIT_mail", "target": "Reminder_mail", "frequency": 42, "median_days": 12.0, "p90_days": 18.0, "severity": "High", "share_pct": 1.8, "conformance_bucket": "Model deviation", "is_deviating": True, "stroke_style": "dashed", "branch_role": "side", "edge_type": "skip"},
            ]
        ),
        "legend": pd.DataFrame(
            [
                {"group": "Conformance", "bucket": "Conformant", "meaning": "No meaningful deviation detected", "severity": "Conformant"},
                {"group": "Conformance", "bucket": "Log deviation", "meaning": "Observed skip or loop", "severity": "Log deviation"},
                {"group": "Performance", "bucket": "High", "meaning": "Delay materially above the cohort baseline", "severity": "High"},
            ]
        ),
        "overall_median_delay_days": 35.0,
    }
    svg = render_workflow_conformance_svg(payload)
    assert '<div class="crpm-workflow-board">' in svg
    assert "<svg" in svg
    assert "Invitation" in svg
    assert "FIT mail" in svg
    assert "stroke-dasharray" in svg
    assert 'data-branch-role="mainline"' in svg
    assert 'data-branch-role="side"' in svg
    assert 'aria-label="Workflow conformance board"' in svg
    assert "Deviation &amp; Timing Legend" not in svg
    assert "Editorial board view" not in svg
    assert "Mainline backbone</text>" not in svg
    assert "Conformance: Log deviation" not in svg


def test_workflow_board_svg_handles_empty_inputs():
    svg = render_workflow_conformance_svg({"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()})
    assert '<div class="crpm-workflow-board">' in svg
    assert "<svg" in svg
    assert "No workflow conformance structure available" in svg


def test_workflow_board_svg_handles_partial_nodes_only():
    svg = render_workflow_conformance_svg(
        {
            "nodes": pd.DataFrame(
                [
                    {"activity": "Invitation_mail", "display_name": "Invitation", "cases": 10, "occurrences": 10, "severity": "Low"}
                ]
            ),
            "edges": pd.DataFrame(),
            "legend": pd.DataFrame(),
        }
    )
    assert "Invitation" in svg
    assert "No transition links were available" in svg


def test_workflow_board_svg_handles_partial_edges_only():
    svg = render_workflow_conformance_svg(
        {
            "nodes": pd.DataFrame(),
            "edges": pd.DataFrame(
                [
                    {"source": "Invitation_mail", "target": "FIT_mail", "frequency": 9, "median_days": 3.0, "severity": "Moderate"}
                ]
            ),
            "legend": pd.DataFrame(),
        }
    )
    assert "Invitation_mail" in svg
    assert "FIT_mail" in svg


def test_compatibility_wrapper_returns_svg_markup():
    svg = create_workflow_conformance_sankey(
        pd.DataFrame([{"activity": "Invitation_mail", "display_name": "Invitation", "cases": 10, "occurrences": 10, "severity": "Low"}]),
        pd.DataFrame([{"source": "Invitation_mail", "target": "Invitation_mail", "frequency": 5, "severity": "Low"}]),
    )
    assert '<div class="crpm-workflow-board">' in svg


def test_workflow_cytoscape_payload_returns_nodes_edges_and_styles():
    payload = create_workflow_cytoscape_payload(
        {
            "nodes": pd.DataFrame(
                [
                    {
                        "activity": "Invitation_mail",
                        "display_name": "Invitation",
                        "cases": 1000,
                        "occurrences": 1000,
                        "median_next_delay_days": 35.0,
                        "p90_next_delay_days": 45.0,
                        "severity": "High",
                        "conformance_bucket": "Conformant",
                    },
                    {
                        "activity": "FIT_mail",
                        "display_name": "FIT mail",
                        "cases": 662,
                        "occurrences": 662,
                        "median_next_delay_days": 15.0,
                        "p90_next_delay_days": 15.0,
                        "severity": "Low",
                        "conformance_bucket": "Conformant",
                    }
                ]
            ),
            "edges": pd.DataFrame(
                [
                    {
                        "source": "Invitation_mail",
                        "target": "FIT_mail",
                        "frequency": 662,
                        "median_days": 15.0,
                        "p90_days": 15.0,
                        "severity": "Low",
                        "conformance_bucket": "Conformant",
                    }
                ]
            ),
            "legend": pd.DataFrame(),
        }
    )
    assert payload["elements"]["nodes"]
    assert payload["elements"]["edges"]
    assert payload["node_styles"]
    assert payload["edge_styles"]
    assert payload["events"]
    assert payload["layout"]["name"] == "preset"


def test_filter_workflow_payload_respects_coverage_and_deviation_filters():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "Invitation_mail", "display_name": "Invitation", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "coverage_group": "dominant"},
                {"activity": "Lab_return", "display_name": "Lab return", "cases": 22, "occurrences": 22, "severity": "High", "conformance_bucket": "Model deviation", "coverage_group": "rare"},
                {"activity": "Lab_result", "display_name": "Lab result", "cases": 22, "occurrences": 22, "severity": "High", "conformance_bucket": "Model deviation", "coverage_group": "rare"},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"edge_id": "Invitation_mail -> FIT_mail", "source": "Invitation_mail", "target": "FIT_mail", "frequency": 662, "severity": "Low", "conformance_bucket": "Conformant", "coverage_group": "dominant"},
                {"edge_id": "Lab_return -> Lab_result", "source": "Lab_return", "target": "Lab_result", "frequency": 12, "severity": "High", "conformance_bucket": "Model deviation", "coverage_group": "rare"},
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="Executive")

    assert list(filtered["edges"]["edge_id"]) == ["Lab_return -> Lab_result"]
    assert filtered["detail_level"] == "executive"


def test_workflow_interactive_payload_and_html_use_business_labels_only():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "step": "invitation",
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "business_label": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 45.0,
                    "severity": "High",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "coverage_group": "dominant",
                    "neighbor_ids": ["FIT_mail"],
                    "step_rank": 0,
                },
                {
                    "step": "fit_mail",
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "business_label": "FIT mail",
                    "cases": 662,
                    "occurrences": 662,
                    "median_next_delay_days": 15.0,
                    "p90_next_delay_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "coverage_group": "dominant",
                    "neighbor_ids": ["Invitation_mail"],
                    "step_rank": 1,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "source_label": "Invitation",
                    "target_label": "FIT mail",
                    "business_label": "Invitation → FIT mail",
                    "frequency": 662,
                    "median_days": 15.0,
                    "p90_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "stroke_style": "solid",
                    "stroke_weight": 4.0,
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Research", selected_node_id="FIT_mail")
    html = render_workflow_explorer_html(explorer)

    assert explorer["nodes"]
    assert explorer["edges"]
    assert explorer["detail_level"] == "research"
    assert "Interactive workflow explorer" in html
    assert 'id="crpm-explorer-selection-chip"' in html
    assert "Research density keeps richer delay labels visible" in html
    assert "Clear focus" in html
    assert "Reset view" in html
    assert 'id="crpm-explorer-live-title"' in html
    assert 'id="crpm-explorer-reset-view"' in html
    assert "layout stays left to right" in html
    assert "Mainline backbone" in html
    assert "Invitation" in html
    assert "FIT mail" in html
    assert "neighbor_ids" not in html
    assert "node::" not in html


def test_workflow_interactive_payload_keeps_mainline_nodes_spaced_apart():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 40.0,
                    "severity": "High",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 15.0,
                    "p90_next_delay_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 2,
                },
                {
                    "activity": "FIT_return",
                    "display_name": "FIT return",
                    "cases": 662,
                    "occurrences": 662,
                    "median_next_delay_days": 7.0,
                    "p90_next_delay_days": 7.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 3,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "source_label": "Invitation",
                    "target_label": "FIT mail",
                    "business_label": "Invitation → FIT mail",
                    "frequency": 662,
                    "median_days": 15.0,
                    "p90_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "stroke_style": "solid",
                    "stroke_weight": 4.0,
                },
                {
                    "edge_id": "FIT_mail -> FIT_return",
                    "source": "FIT_mail",
                    "target": "FIT_return",
                    "source_label": "FIT mail",
                    "target_label": "FIT return",
                    "business_label": "FIT mail → FIT return",
                    "frequency": 662,
                    "median_days": 7.0,
                    "p90_days": 7.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "stroke_style": "solid",
                    "stroke_weight": 4.0,
                },
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Analyst")
    mainline_nodes = [node for node in explorer["nodes"] if node.get("branch_role") == "mainline"]
    ordered = sorted(mainline_nodes, key=lambda node: node["x"])

    assert len(ordered) >= 3
    for left, right in zip(ordered, ordered[1:]):
        assert left["x"] + left["width"] <= right["x"]


def test_filter_workflow_payload_summary_matches_visible_subset():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "invitation", "display_name": "Invitation", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "coverage_group": "dominant", "branch_role": "mainline"},
                {"activity": "admin_review", "display_name": "Admin review", "cases": 50, "occurrences": 60, "severity": "High", "conformance_bucket": "Model deviation", "coverage_group": "rare", "branch_role": "side"},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"edge_id": "invitation -> fit_mail", "source": "invitation", "target": "fit_mail", "frequency": 900, "severity": "Low", "conformance_bucket": "Conformant", "coverage_group": "dominant", "branch_role": "mainline"},
                {"edge_id": "fit_mail -> admin_review", "source": "fit_mail", "target": "admin_review", "frequency": 50, "severity": "High", "conformance_bucket": "Model deviation", "coverage_group": "rare", "branch_role": "side"},
            ]
        ),
        "trace_profiles": pd.DataFrame(
            [
                {"case_id": "case-1", "event_count": 4, "throughput_days": 20.0, "variant_signature": "Invitation → FIT mail", "has_deviation": False, "node_ids": ["invitation", "fit_mail"], "edge_ids": ["invitation -> fit_mail"]},
                {"case_id": "case-2", "event_count": 6, "throughput_days": 42.0, "variant_signature": "Invitation → FIT mail → Admin review", "has_deviation": True, "node_ids": ["invitation", "fit_mail", "admin_review"], "edge_ids": ["invitation -> fit_mail", "fit_mail -> admin_review"]},
            ]
        ),
        "summary": {
            "cases_covered": 2,
            "events_covered": 10,
            "dominant_path_share": 50.0,
            "deviation_share": 50.0,
            "median_throughput_days": 31.0,
        },
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="analyst")

    assert filtered["summary"]["cases_covered"] == 1
    assert filtered["summary"]["events_covered"] == 6
    assert filtered["summary"]["deviation_share"] == 100.0
    assert filtered["summary"]["median_throughput_days"] == 42.0


def test_filter_workflow_payload_derives_nodes_when_edges_survive_filtering():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "invitation", "display_name": "Invitation", "cases": 1000, "coverage_group": "legacy", "conformance_bucket": "Conformant"},
                {"activity": "fit_mail", "display_name": "FIT mail", "cases": 900, "coverage_group": "legacy", "conformance_bucket": "Conformant"},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "invitation -> fit_mail",
                    "source": "invitation",
                    "target": "fit_mail",
                    "frequency": 900,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="dominant", deviation_view="all", detail_level="analyst")

    assert list(filtered["nodes"]["activity"]) == ["invitation", "fit_mail"]
    assert list(filtered["edges"]["edge_id"]) == ["invitation -> fit_mail"]


def test_filter_workflow_payload_falls_back_to_all_when_requested_slice_is_empty():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "invitation", "display_name": "Invitation", "cases": 1000, "coverage_group": "rare", "conformance_bucket": "Conformant"},
                {"activity": "fit_mail", "display_name": "FIT mail", "cases": 900, "coverage_group": "rare", "conformance_bucket": "Conformant"},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "invitation -> fit_mail",
                    "source": "invitation",
                    "target": "fit_mail",
                    "frequency": 900,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "rare",
                    "branch_role": "mainline",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="dominant", deviation_view="all", detail_level="analyst")

    assert filtered["requested_coverage_view"] == "dominant"
    assert filtered["applied_coverage_view"] == "all"
    assert not filtered["nodes"].empty
    assert not filtered["edges"].empty


def test_filter_workflow_payload_fills_missing_defaults_for_nodes_and_edges():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "invitation",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                },
                {
                    "activity": "fit_mail",
                    "display_name": "FIT mail",
                    "cases": 900,
                    "occurrences": 900,
                    "conformance_bucket": "",
                    "severity": None,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "source": "invitation",
                    "target": "fit_mail",
                    "frequency": 900,
                    "conformance_bucket": "",
                    "severity": None,
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="all", deviation_view="all", detail_level="research")

    assert set(filtered["nodes"]["conformance_bucket"]) == {"Conformant"}
    assert set(filtered["nodes"]["severity"]) == {"Low"}
    assert set(filtered["nodes"]["branch_role"]) == {"mainline"}
    assert set(filtered["nodes"]["coverage_group"]) == {"dominant"}
    assert set(filtered["edges"]["conformance_bucket"]) == {"Conformant"}
    assert set(filtered["edges"]["severity"]) == {"Low"}
    assert set(filtered["edges"]["coverage_group"]) == {"dominant"}
