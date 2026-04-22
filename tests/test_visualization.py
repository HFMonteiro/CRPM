"""Tests for crpm.visualization — Plotly chart builders."""
from __future__ import annotations

import re

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
    _workflow_primary_path_nodes,
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
    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")
    assert 'class="crpm-workflow-board crpm-workflow-board--horizontal"' in svg
    assert "<svg" in svg
    assert "min-width:100%;height:auto;" in svg
    assert "Invitation" in svg
    assert "FIT mail" in svg
    assert "stroke-dasharray" in svg
    assert 'data-branch-role="mainline"' in svg
    assert 'data-branch-role="side"' in svg
    assert 'aria-label="Workflow conformance board"' in svg
    assert "Upper variation" in svg
    assert "Deviation &amp; Timing Legend" not in svg
    assert "Editorial board view" not in svg
    assert "Mainline backbone</text>" not in svg
    assert "Conformance: Log deviation" not in svg
    match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    assert match is not None
    assert int(match.group(1)) > int(match.group(2))


def test_workflow_board_svg_preserves_horizontal_layout_with_upper_and_lower_variation():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "Start_node", "display_name": "Start", "cases": 100, "occurrences": 100, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 0},
                {"activity": "Main_node", "display_name": "Main", "cases": 90, "occurrences": 90, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 1},
                {"activity": "Upper_branch", "display_name": "Upper branch", "cases": 12, "occurrences": 12, "severity": "High", "conformance_bucket": "Model deviation", "branch_role": "side", "lane": "left", "step_rank": 1},
                {"activity": "Lower_branch", "display_name": "Lower branch", "cases": 8, "occurrences": 8, "severity": "Moderate", "conformance_bucket": "Log deviation", "branch_role": "side", "lane": "right", "step_rank": 1},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"edge_id": "Start_node -> Main_node", "source": "Start_node", "target": "Main_node", "frequency": 90, "median_days": 3.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"edge_id": "Main_node -> Upper_branch", "source": "Main_node", "target": "Upper_branch", "frequency": 12, "median_days": 6.0, "severity": "High", "conformance_bucket": "Model deviation", "branch_role": "side", "stroke_style": "dashed"},
                {"edge_id": "Main_node -> Lower_branch", "source": "Main_node", "target": "Lower_branch", "frequency": 8, "median_days": 7.0, "severity": "Moderate", "conformance_bucket": "Log deviation", "branch_role": "side", "stroke_style": "dashed"},
            ]
        ),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")

    assert "Upper variation" in svg
    assert "Lower variation" in svg
    assert "Upper branch" in svg
    assert "Lower branch" in svg
    assert "crpm-workflow-explorer" not in svg


def test_workflow_board_svg_simple_mainline_export_uses_compact_content_height():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "Invitation_mail", "display_name": "Invitation", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 0},
                {"activity": "FIT_mail", "display_name": "FIT mail", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 1},
                {"activity": "FIT_return", "display_name": "FIT return", "cases": 662, "occurrences": 662, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 2},
                {"activity": "Lab_result", "display_name": "Lab result", "cases": 662, "occurrences": 662, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 3},
                {"activity": "PCC_observation", "display_name": "PCC observation", "cases": 28, "occurrences": 28, "severity": "Moderate", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 4},
                {"activity": "Colonoscopy", "display_name": "Colonoscopy", "cases": 28, "occurrences": 28, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 5},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"source": "Invitation_mail", "target": "FIT_mail", "frequency": 1000, "median_days": 35.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "FIT_mail", "target": "FIT_return", "frequency": 662, "median_days": 15.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "FIT_return", "target": "Lab_result", "frequency": 662, "median_days": 7.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "Lab_result", "target": "PCC_observation", "frequency": 28, "median_days": 2.0, "severity": "Moderate", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "PCC_observation", "target": "Colonoscopy", "frequency": 28, "median_days": 45.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
            ]
        ),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")

    viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    invitation_match = re.search(
        r'data-activity="Invitation_mail".*?<rect x="[^"]+" y="([^"]+)" width="([^"]+)" height="([^"]+)"',
        svg,
        re.S,
    )
    invitation_chip_match = re.search(
        r'data-activity="Invitation_mail".*?<rect x="[^"]+" y="([^"]+)" width="([^"]+)" height="([^"]+)" rx="[^"]+" ry="[^"]+" fill="[^"]+" data-qa="workflow-board-chip" />'
        r'.*?<text x="[^"]+" y="([^"]+)" font-family="Segoe UI, Arial, sans-serif" font-size="[^"]+" font-weight="700" fill="[^"]+" data-qa="workflow-board-title">Invitation</text>',
        svg,
        re.S,
    )

    assert viewbox_match is not None
    assert invitation_match is not None
    assert invitation_chip_match is not None
    assert 'data-fit-mode="shelf"' in svg
    assert 'style="display:block;width:100%;max-width:100%;height:auto;"' in svg
    assert 'data-qa="workflow-board-card"' in svg
    assert 'data-qa="workflow-board-chip"' in svg
    board_height = int(viewbox_match.group(2))
    node_y = float(invitation_match.group(1))
    node_height = float(invitation_match.group(3))
    node_center_y = node_y + (node_height / 2.0)
    chip_y = float(invitation_chip_match.group(1))
    chip_height = float(invitation_chip_match.group(3))
    title_y = float(invitation_chip_match.group(4))

    assert int(viewbox_match.group(1)) > board_height
    assert 110 <= board_height <= 190
    assert node_height <= 96.0
    assert node_y <= 24.0
    assert board_height - (node_y + node_height) <= 56.0
    assert title_y >= chip_y + chip_height + 6.0
    assert "35.0 d me..." not in svg
    node_rects = re.findall(
        r'data-activity="([^\"]+)".*?<rect x="([^"]+)" y="[^"]+" width="([^"]+)" height="([^"]+)"',
        svg,
        re.S,
    )
    ordered_rects = sorted(
        [(label, float(x), float(width)) for label, x, width, _ in node_rects],
        key=lambda item: item[1],
    )
    for (_, left_x, left_width), (_, right_x, _) in zip(ordered_rects, ordered_rects[1:]):
        assert left_x + left_width + 8.0 <= right_x


def test_workflow_board_svg_two_step_simple_export_does_not_collapse_into_strip():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "Invitation_mail", "display_name": "Invitation", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 0},
                {"activity": "FIT_mail", "display_name": "FIT mail", "cases": 1000, "occurrences": 1000, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 1},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"source": "Invitation_mail", "target": "FIT_mail", "frequency": 1000, "median_days": 35.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
            ]
        ),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")
    viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)

    assert viewbox_match is not None
    assert 'data-fit-mode="shelf"' in svg
    assert int(viewbox_match.group(2)) >= 110
    assert int(viewbox_match.group(1)) > int(viewbox_match.group(2)) * 2
    assert "Upper variation" not in svg
    assert "Lower variation" not in svg


def test_workflow_board_svg_handles_empty_inputs():
    svg = render_workflow_conformance_svg({"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()})
    assert 'class="crpm-workflow-board' in svg
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
    assert 'class="crpm-workflow-board' in svg


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
    if payload["node_styles"] or payload["edge_styles"] or payload["events"]:
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
    assert explorer["conformance_lens"] == "% of paths"
    assert explorer["frame_height"] > explorer["height"]
    assert explorer["content_offset_x"] == 0.0
    assert explorer["content_offset_y"] == 0.0
    assert explorer["frame_height"] - explorer["height"] >= 120
    assert explorer["content_bounds"]["max_y"] > explorer["anchor_bounds"]["min_y"]
    assert explorer["drawable_bounds"]["max_y"] > explorer["drawable_bounds"]["min_y"]
    assert explorer["fit_padding"]["bottom"] >= 24.0
    assert explorer["toolbar_height_hint"] >= 126
    assert "Active process flow" in html
    assert 'id="crpm-explorer-selection-chip"' in html
    assert "Timing burden on links" in html
    assert "Clear focus" in html
    assert "Reset view" in html
    assert 'id="crpm-explorer-live-title"' in html
    assert 'id="crpm-explorer-reset-view"' in html
    assert "Start" in html
    assert "End" in html
    assert "top to bottom" in html.lower()
    assert "Invitation" in html
    assert "FIT mail" in html
    assert "neighbor_ids" not in html
    assert "node::" not in html


def test_workflow_interactive_html_uses_compact_shell_defaults():
    explorer = {
        "nodes": [
            {
                "id": "Invitation_mail",
                "business_label": "Invitation",
                "display_name": "Invitation",
                "cases": 100,
                "occurrences": 100,
                "median_days": 3.0,
                "p90_days": 4.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "lane_position": "mainline",
                "x": 220.0,
                "y": 120.0,
                "width": 224.0,
                "height": 86.0,
                "center_x": 332.0,
                "center_y": 163.0,
                "surface_fill": "#ffffff",
                "stroke": "#7aa08a",
                "ink": "#22313b",
                "accent": "#7aa08a",
                "accent_fill": "#edf5ef",
                "chip_fill": "#edf5ef",
                "chip_ink": "#2d6a3f",
                "selected": False,
                "neighbor": False,
            }
        ],
        "edges": [],
        "width": 760,
        "height": 520,
        "content_offset_x": 16.0,
        "content_offset_y": 16.0,
        "detail_level": "analyst",
        "metric_coloring": "Conformance bucket",
        "conformance_lens": "% of paths",
    }
    html = render_workflow_explorer_html(explorer)
    assert "const computeBaselineFit = () => {" in html
    assert "baselineScale = Math.min(availableWidth / boundsWidth, availableHeight / boundsHeight);" in html
    assert "Math.max(0.56, Math.min(1.7, zoomFactor * factor))" in html
    assert 'class="crpm-explorer-figure" style="width:100%;"' in html
    assert 'style="display:block;width:100%;height:auto;aspect-ratio:760/520;overflow:visible;margin:0 auto;"' in html
    assert 'id="crpm-workflow-static-frame"' in html
    assert 'id="crpm-workflow-content"' in html
    assert 'data-drawable-min-x="' in html
    assert "const drawableMinX = Number(svg.getAttribute('data-drawable-min-x') || '12');" in html
    assert "type: 'streamlit:setFrameHeight'" in html
    assert "requestAnimationFrame(() => notifyFrameHeight());" in html
    assert 'preserveAspectRatio="xMidYMin meet"' in html


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
                    "step_rank": 0,
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
    ordered = sorted(mainline_nodes, key=lambda node: node["y"])

    assert len(ordered) >= 2
    assert ordered[0]["display_name"] == "Invitation"
    for top, bottom in zip(ordered, ordered[1:]):
        gap = bottom["y"] - (top["y"] + top["height"])
        assert gap >= 8.0
        top_text_box = top.get("text_box", {})
        bottom_text_box = bottom.get("text_box", {})
        assert float(top_text_box.get("max_y", top["y"] + top["height"])) + 4.0 <= float(
            bottom_text_box.get("min_y", bottom["y"])
        )


def test_workflow_interactive_payload_text_boxes_stay_inside_node_rectangles():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation with a longer clinical title",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 40.0,
                    "severity": "High",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "PCC_observation",
                    "display_name": "PCC observation with extended wording",
                    "cases": 28,
                    "occurrences": 28,
                    "median_next_delay_days": 45.0,
                    "p90_next_delay_days": 55.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "source": "Invitation_mail",
                    "target": "PCC_observation",
                    "frequency": 28,
                    "median_days": 45.0,
                    "p90_days": 55.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "mainline",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Analyst")

    for node in explorer["nodes"]:
        text_box = node.get("text_box")
        assert text_box is not None
        assert float(text_box["min_x"]) >= float(node["x"]) + 8.0
        assert float(text_box["max_x"]) <= float(node["x"]) + float(node["width"]) - 8.0
        assert float(text_box["min_y"]) >= float(node["y"]) + 6.0
        assert float(text_box["max_y"]) <= float(node["y"]) + float(node["height"]) - 4.0


def test_workflow_interactive_payload_prefers_wider_single_line_mainline_cards():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "Invitation_mail", "display_name": "Invitation", "cases": 1000, "occurrences": 1000, "median_next_delay_days": 35.0, "p90_next_delay_days": 40.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 0},
                {"activity": "FIT_mail", "display_name": "FIT mail", "cases": 1000, "occurrences": 1000, "median_next_delay_days": 15.0, "p90_next_delay_days": 15.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 1},
                {"activity": "FIT_return", "display_name": "FIT return", "cases": 662, "occurrences": 662, "median_next_delay_days": 7.0, "p90_next_delay_days": 7.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 2},
                {"activity": "Lab_result", "display_name": "Lab result", "cases": 662, "occurrences": 662, "median_next_delay_days": 2.0, "p90_next_delay_days": 4.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 3},
                {"activity": "PCC_observation", "display_name": "PCC observation", "cases": 28, "occurrences": 28, "median_next_delay_days": 45.0, "p90_next_delay_days": 55.0, "severity": "Moderate", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 4},
                {"activity": "Colonoscopy", "display_name": "Colonoscopy", "cases": 28, "occurrences": 28, "median_next_delay_days": None, "p90_next_delay_days": None, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline", "lane": "center", "step_rank": 5},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {"source": "Invitation_mail", "target": "FIT_mail", "frequency": 1000, "median_days": 35.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "FIT_mail", "target": "FIT_return", "frequency": 662, "median_days": 15.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "FIT_return", "target": "Lab_result", "frequency": 662, "median_days": 7.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "Lab_result", "target": "PCC_observation", "frequency": 28, "median_days": 2.0, "severity": "Moderate", "conformance_bucket": "Conformant", "branch_role": "mainline"},
                {"source": "PCC_observation", "target": "Colonoscopy", "frequency": 28, "median_days": 45.0, "severity": "Low", "conformance_bucket": "Conformant", "branch_role": "mainline"},
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Analyst")
    mainline_nodes = [node for node in explorer["nodes"] if node.get("branch_role") == "mainline"]

    assert mainline_nodes
    assert max(float(node["width"]) for node in mainline_nodes) >= 300.0
    assert all(len(node.get("title_lines_render", [])) == 1 for node in mainline_nodes)
    assert all(len(node.get("timing_lines_render", [])) <= 1 for node in mainline_nodes)
    assert all(len(node.get("footer_lines_render", [])) <= 1 for node in mainline_nodes)
    assert all("path " in str(node.get("timing_lines_render", [""])[0]).lower() for node in mainline_nodes if node.get("timing_lines_render"))
    assert all("activity " in str(node.get("timing_lines_render", [""])[0]).lower() for node in mainline_nodes if node.get("timing_lines_render"))


def test_workflow_interactive_payload_bounds_cover_labels_and_anchors():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "business_label": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 40.0,
                    "severity": "High",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "business_label": "FIT mail",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 15.0,
                    "p90_next_delay_days": 18.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
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
                    "frequency": 1000,
                    "median_days": 15.0,
                    "p90_days": 18.0,
                    "share_pct": 100.0,
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

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Research")
    drawable_height = explorer["height"] - explorer["content_offset_y"]
    max_node_bottom = max(node["y"] + node["height"] for node in explorer["nodes"])
    visible_labels = [edge for edge in explorer["edges"] if edge.get("show_label")]
    last_mainline_bottom = max(
        node["y"] + node["height"]
        for node in explorer["nodes"]
        if node.get("branch_role") == "mainline"
    )
    end_anchor_y = last_mainline_bottom + 30.0

    assert explorer["height"] > max_node_bottom + 24.0
    if visible_labels:
        max_label_extent = max(
            edge["label_y"] + (float(edge.get("label_height", 18.0)) / 2.0)
            for edge in visible_labels
        )
        assert explorer["height"] > max_label_extent + 24.0
    else:
        assert all(not edge.get("show_label") for edge in explorer["edges"])
    assert explorer["height"] >= end_anchor_y + 24.0
    assert drawable_height >= end_anchor_y + 24.0
    assert explorer["fit_padding"]["bottom"] >= 24.0
    assert explorer["anchor_bounds"]["max_y"] >= end_anchor_y + 20.0
    assert explorer["content_bounds"]["max_y"] >= end_anchor_y + 24.0
    assert explorer["width"] > max(node["x"] + node["width"] for node in explorer["nodes"])
    assert explorer["height"] >= explorer["width"] * 0.76


def test_workflow_explorer_html_uses_lighter_arrowheads():
    payload = {
        "nodes": [
            {
                "id": "invitation",
                "business_label": "Invitation",
                "display_name": "Invitation",
                "cases": 1000,
                "occurrences": 1000,
                "median_days": 35.0,
                "p90_days": 45.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "lane_position": "mainline",
                "x": 120.0,
                "y": 140.0,
                "width": 186.0,
                "height": 84.0,
                "center_x": 213.0,
                "center_y": 182.0,
                "surface_fill": "#ffffff",
                "stroke": "#7cbf89",
                "ink": "#24343f",
                "accent": "#7cbf89",
                "accent_fill": "#cfead5",
                "chip_fill": "#8bc89c",
                "chip_ink": "#ffffff",
                "selected": False,
                "neighbor": False,
            },
            {
                "id": "fit_mail",
                "business_label": "FIT mail",
                "display_name": "FIT mail",
                "cases": 1000,
                "occurrences": 1000,
                "median_days": 15.0,
                "p90_days": 15.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "lane_position": "mainline",
                "x": 392.0,
                "y": 140.0,
                "width": 186.0,
                "height": 84.0,
                "center_x": 485.0,
                "center_y": 182.0,
                "surface_fill": "#ffffff",
                "stroke": "#7cbf89",
                "ink": "#24343f",
                "accent": "#7cbf89",
                "accent_fill": "#cfead5",
                "chip_fill": "#8bc89c",
                "chip_ink": "#ffffff",
                "selected": False,
                "neighbor": False,
            },
        ],
        "edges": [
            {
                "id": "invitation->fit_mail",
                "source": "invitation",
                "target": "fit_mail",
                "caption": "Invitation → FIT mail",
                "frequency": 900,
                "median_days": 15.0,
                "p90_days": 18.0,
                "share_pct": 90.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "stroke_style": "solid",
                "stroke_width": 3.2,
                "stroke": "#7cbf89",
                "accent": "#7cbf89",
                "path": "M 312 182 C 340 182, 358 182, 386 182",
                "label_x": 349.0,
                "label_y": 152.0,
                "selected": False,
                "neighbor": False,
                "show_label": True,
            }
        ],
        "legend": pd.DataFrame(),
        "height": 420,
        "frame_height": 676,
        "width": 900,
        "content_offset_x": 18.0,
        "content_offset_y": 22.0,
        "overall_median_delay_days": 15.0,
        "selected_node_id": None,
        "selected_edge_id": None,
        "metric_coloring": "Conformance bucket",
        "detail_level": "analyst",
        "has_top_branches": False,
        "has_bottom_branches": False,
        "lane_bands": {"top_y": 48.0, "mainline_y": 124.0, "bottom_y": 292.0},
    }

    html = render_workflow_explorer_html(payload)

    assert re.search(r'markerWidth="6\.4"', html)
    assert re.search(r'markerHeight="6\.4"', html)
    assert 'id="workflow-explorer-arrow-mainline"' in html
    assert 'id="workflow-explorer-arrow-log"' in html
    assert 'id="workflow-explorer-arrow-model"' in html
    assert 'id="workflow-explorer-arrow-neutral"' in html
    assert 'marker-end="url(#workflow-explorer-arrow-mainline)"' in html
    assert 'stroke="#c8d4d8" stroke-width="0.8"' in html
    assert 'preserveAspectRatio="xMidYMin meet"' in html
    assert "aspect-ratio:900/420" in html
    assert 'class="crpm-explorer-figure" style="width:100%;"' in html
    assert 'style="display:block;width:100%;height:auto;aspect-ratio:900/420;overflow:visible;margin:0 auto;"' in html
    assert 'data-content-min-x="' in html
    assert 'data-drawable-min-x="' in html
    assert 'data-fit-pad-bottom="' in html
    assert "const computeBaselineFit = () => {" in html
    assert "const drawableMaxY = Number(svg.getAttribute('data-drawable-max-y') || String((viewBox.height || 0) - 12));" in html
    assert "translate(${baselineTx} ${baselineTy}) scale(${baselineScale * zoomFactor})" in html
    assert "type: 'streamlit:setFrameHeight'" in html
    assert "window.setTimeout(notifyFrameHeight, 280);" in html
    end_text_match = re.search(
        r'<text x="[^"]+" y="([^"]+)" text-anchor="middle" font-size="11.5" font-weight="700" fill="#243744">End</text>',
        html,
    )
    assert end_text_match is not None
    assert 420.0 >= (float(end_text_match.group(1)) - 4.0) + 24.0


def test_workflow_primary_path_nodes_prefers_dominant_left_lane_when_mainline_missing():
    nodes = [
        {"id": "invitation", "step_rank": 0, "lane_position": "left", "cases": 1000, "center_y": 80.0, "branch_role": "side"},
        {"id": "fit_mail", "step_rank": 1, "lane_position": "left", "cases": 1000, "center_y": 220.0, "branch_role": "side"},
        {"id": "rejection", "step_rank": 1, "lane_position": "right", "cases": 40, "center_y": 320.0, "branch_role": "side"},
        {"id": "colonoscopy", "step_rank": 5, "lane_position": "left", "cases": 28, "center_y": 760.0, "branch_role": "side"},
        {"id": "reminder", "step_rank": 6, "lane_position": "right", "cases": 12, "center_y": 920.0, "branch_role": "side"},
    ]

    primary = _workflow_primary_path_nodes(nodes)

    assert [node["id"] for node in primary] == ["invitation", "fit_mail", "colonoscopy"]


def test_workflow_interactive_payload_collapses_duplicate_nodes_and_edges():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Lab_result",
                    "display_name": "Lab result",
                    "cases": 331,
                    "occurrences": 331,
                    "median_next_delay_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 2,
                },
                {
                    "activity": "Lab_result",
                    "display_name": "Lab result",
                    "cases": 280,
                    "occurrences": 280,
                    "median_next_delay_days": 16.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 2,
                },
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "severity": "High",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "source": "Invitation_mail",
                    "target": "Lab_result",
                    "frequency": 331,
                    "median_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                },
                {
                    "source": "Invitation_mail",
                    "target": "Lab_result",
                    "frequency": 280,
                    "median_days": 16.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                },
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, metric_coloring="Conformance bucket", detail_level="Analyst")
    node_ids = [node["id"] for node in explorer["nodes"]]
    edge_ids = [edge["id"] for edge in explorer["edges"]]

    assert node_ids.count("Lab_result") == 1
    assert len(edge_ids) == 2
    assert any("Invitation_mail -> Lab_result|" in edge_id and "|Low" in edge_id for edge_id in edge_ids)
    assert any("Invitation_mail -> Lab_result|" in edge_id and "|Moderate" in edge_id for edge_id in edge_ids)


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
