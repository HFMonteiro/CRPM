"""Tests for crpm.visualization â€” Plotly chart builders."""

from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go

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
    render_performance_bpmn_svg,
    render_pan_zoom_svg_html,
    render_workflow_bpmn_style_svg,
    render_workflow_explorer_html,
    render_workflow_conformance_svg,
    workflow_edge_uid,
)


def test_pan_zoom_svg_wrapper_exposes_desktop_controls() -> None:
    html = render_pan_zoom_svg_html('<svg viewBox="0 0 100 50"></svg>')
    assert ".crpm-map-tools { position:absolute; top:56px;" in html

    assert "addEventListener('wheel'" in html
    assert "pointerdown" in html
    assert 'data-action="reset"' in html
    assert "Reset filters" not in html


def test_bottleneck_chart_returns_figure():
    df = pd.DataFrame(
        {
            "transition": ["A â†’ B", "B â†’ C"],
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
            "transition": ["A â†’ B", "B â†’ C"],
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


def test_performance_bpmn_svg_encodes_transfer_speed_and_volume():
    transitions = pd.DataFrame(
        {
            "activity": ["invitation", "fit_mail", "fit_return", "pcc_observation"],
            "next_activity": ["fit_mail", "fit_return", "pcc_observation", "colonoscopy"],
            "frequency": [1000, 900, 800, 120],
            "median_duration_s": [86400, 3 * 86400, 10 * 86400, 30 * 86400],
            "p90_duration_s": [2 * 86400, 5 * 86400, 15 * 86400, 45 * 86400],
        }
    )
    activities = pd.DataFrame(
        {
            "activity": ["invitation", "fit_mail", "fit_return", "pcc_observation", "colonoscopy"],
            "frequency": [1000, 1000, 900, 800, 120],
            "median_duration_s": [3600, 7200, 14400, 28800, 43200],
            "p90_duration_s": [7200, 14400, 28800, 57600, 86400],
        }
    )

    svg = render_performance_bpmn_svg(transitions, activity_stats=activities)

    assert 'data-qa="performance-bpmn-board"' in svg
    assert svg.count('data-qa="performance-bpmn-task"') == 5
    assert svg.count('data-qa="performance-sequence-flow"') == 4
    assert 'data-qa="performance-bpmn-start"' in svg
    assert 'data-qa="performance-bpmn-end"' in svg
    assert "Speed of transfer" in svg
    assert "speed of transfer" in svg
    assert "transfers/day" in svg
    assert "Pre-primary care" in svg
    assert "Primary care" in svg
    assert "Hospital care" in svg
    assert "#3f8f6b" in svg
    assert "#c95d68" in svg
    assert (
        'id="performance-arrow-fast" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse"' in svg
    )


def test_performance_bpmn_svg_reduces_variation_spaghetti():
    transitions = pd.DataFrame(
        {
            "activity": [
                "invitation",
                "fit_mail",
                "fit_return",
                "lab_result",
                "pcc_observation",
                "reminder_mail",
                "admin_review",
                "reschedule_mail",
                "pcc_observation",
            ],
            "next_activity": [
                "fit_mail",
                "fit_return",
                "lab_result",
                "pcc_observation",
                "colonoscopy",
                "fit_return",
                "colonoscopy",
                "colonoscopy",
                "admin_review",
            ],
            "frequency": [1000, 900, 800, 700, 600, 80, 70, 60, 40],
            "median_duration_s": [86400, 2 * 86400, 3 * 86400, 4 * 86400, 5 * 86400, 6 * 86400, 7 * 86400, 8 * 86400, 9 * 86400],
            "p90_duration_s": [2 * 86400, 3 * 86400, 4 * 86400, 5 * 86400, 6 * 86400, 7 * 86400, 8 * 86400, 9 * 86400, 10 * 86400],
        }
    )

    svg = render_performance_bpmn_svg(transitions)

    assert svg.count('data-qa="performance-sequence-flow"') <= 10
    assert svg.count('data-qa="performance-edge-label"') <= 6
    assert 'data-edge-kind="variation"' in svg
    assert "showing" in svg


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
            "variant": ["A â†’ B â†’ C", "A â†’ C"],
            "variant_str": ["A â†’ B â†’ C", "A â†’ C"],
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
    assert fig.layout.height == 340
    assert fig.layout.margin.l == 148
    assert fig.layout.title.text is None
    assert tuple(fig.data[0].y) == ("Alignment fitness", "Precision")
    assert fig.layout.yaxis.autorange == "reversed"
    assert fig.layout.xaxis.tickfont.size == 14
    assert fig.data[0].colorscale[0] == (0.0, "#b57a3e")
    assert fig.data[0].textfont.size == 16
    assert fig.data[0].xgap == 3
    assert fig.data[0].ygap == 3
    assert fig.data[0].zmin == 0
    assert fig.data[0].zmax == 1
    assert fig.data[0].colorbar.title.text == "Score"


def test_model_comparison_heatmap_preserves_missing_metrics_as_gaps():
    df = pd.DataFrame(
        {
            "model_name": ["IM", "IMf"],
            "alignment_fitness": [0.9, None],
        }
    )

    fig = create_model_comparison_heatmap(df, metrics=["alignment_fitness", "precision"])

    assert fig.data[0].z[0][1] is None
    assert tuple(fig.data[0].z[1]) == (None, None)
    assert fig.data[0].text[0][1] == "N/A"
    assert tuple(fig.data[0].text[1]) == ("N/A", "N/A")


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
    assert fig.layout.hoverlabel.bgcolor == "#ffffff"
    assert fig.layout.hoverlabel.font.color == "#1f2c25"
    assert fig.layout.hoverlabel.namelength == -1
    assert fig.layout.legend.font.color == "#1f2c25"
    assert fig.layout.legend.bgcolor == "rgba(251, 249, 253, 0.99)"
    assert fig.layout.legend.y == -0.18
    assert fig.layout.margin.b == 92


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
            "transition": ["FIT_mail â†’ FIT_return", "PCC_observation â†’ Colonoscopy_center"],
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


def _bpmn_style_workflow_payload() -> dict:
    rare_edge_uid = workflow_edge_uid("FIT_mail -> Reminder_mail", "Model deviation", "skip", "reminder")
    return {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 140,
                    "occurrences": 145,
                    "median_next_delay_days": 35.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "coverage_group": "dominant",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 136,
                    "occurrences": 140,
                    "median_next_delay_days": 56.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "coverage_group": "dominant",
                    "lane": "center",
                    "step_rank": 1,
                },
                {
                    "activity": "Reminder_mail",
                    "display_name": "Reminder",
                    "cases": 42,
                    "occurrences": 42,
                    "median_next_delay_days": 12.0,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "coverage_group": "rare",
                    "lane": "left",
                    "branch_family": "reminder",
                    "node_type": "deviation",
                    "step_rank": 2,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 145128,
                    "median_days": 35.0,
                    "severity": "Low",
                    "share_pct": 82.5,
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "edge_type": "expected",
                },
                {
                    "edge_id": "FIT_mail -> Reminder_mail",
                    "edge_uid": rare_edge_uid,
                    "source": "FIT_mail",
                    "target": "Reminder_mail",
                    "frequency": 42,
                    "median_days": 12.0,
                    "severity": "High",
                    "share_pct": 1.8,
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                    "branch_role": "side",
                    "branch_family": "reminder",
                    "edge_type": "skip",
                    "stroke_style": "dashed",
                },
            ]
        ),
        "legend": pd.DataFrame(),
        "trace_profiles": pd.DataFrame(
            [
                {
                    "trace_ref": "RAW-CASE-ID-42",
                    "case_path": "sensitive-source://private-log.xes",
                    "representative_edge_uid": rare_edge_uid,
                }
            ]
        ),
        "summary": {"visible_case_count": 140, "excluded_case_count": 5, "median_throughput_days": 35.0, "deviation_share": 30.0},
        "overall_median_delay_days": 35.0,
    }


def test_workflow_bpmn_style_svg_returns_bpmn_notation_without_trace_leaks():
    svg = render_workflow_bpmn_style_svg(_bpmn_style_workflow_payload(), metric_coloring="Conformance bucket")

    assert 'class="crpm-bpmn-style-board"' in svg
    assert 'data-qa="bpmn-start-event"' in svg
    assert 'data-qa="bpmn-end-event"' in svg
    assert 'data-qa="bpmn-task"' in svg
    assert 'data-qa="bpmn-gateway"' in svg
    assert 'data-qa="bpmn-sequence-flow"' in svg
    assert 'data-qa="bpmn-swimlane-main"' in svg
    assert 'id="crpm-bpmn-arrow-main" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse"' in svg
    assert "Reminder" in svg
    assert "RAW-CASE-ID-42" not in svg
    assert "private-log.xes" not in svg


def test_workflow_bpmn_style_svg_highlights_pinned_node_and_edge():
    payload = _bpmn_style_workflow_payload()
    rare_edge_uid = str(payload["edges"].loc[1, "edge_uid"])
    payload["selected_node_id"] = "Reminder_mail"
    payload["selected_edge_uid"] = rare_edge_uid

    svg = render_workflow_bpmn_style_svg(payload, metric_coloring="Frequency", detail_level="research")

    assert 'class="crpm-bpmn-node crpm-bpmn-gateway is-selected"' in svg
    assert 'class="crpm-bpmn-sequence-flow is-selected"' in svg
    assert f'data-edge-uid="{rare_edge_uid.replace(">", "&gt;")}"' in svg


def test_filtered_payload_drives_bpmn_style_view():
    payload = _bpmn_style_workflow_payload()
    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="research")
    svg = render_workflow_bpmn_style_svg(filtered)

    assert "Reminder" in svg
    assert "Invitation" not in svg
    assert "FIT mail" not in svg
    assert 'data-qa="bpmn-gateway"' in svg
    assert "RAW-CASE-ID-42" not in svg


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
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 145128,
                    "median_days": 35.0,
                    "p90_days": 45.0,
                    "severity": "Low",
                    "share_pct": 82.5,
                    "conformance_bucket": "Conformant",
                    "is_deviating": False,
                    "stroke_style": "solid",
                    "branch_role": "mainline",
                    "edge_type": "expected",
                },
                {
                    "edge_id": "FIT_mail -> FIT_mail",
                    "source": "FIT_mail",
                    "target": "FIT_mail",
                    "frequency": 61,
                    "median_days": 56.0,
                    "p90_days": 63.0,
                    "severity": "Critical",
                    "share_pct": 0.1,
                    "conformance_bucket": "Log deviation",
                    "is_deviating": True,
                    "stroke_style": "dashed",
                    "branch_role": "side",
                    "edge_type": "loop",
                },
                {
                    "edge_id": "FIT_mail -> Reminder_mail",
                    "source": "FIT_mail",
                    "target": "Reminder_mail",
                    "frequency": 42,
                    "median_days": 12.0,
                    "p90_days": 18.0,
                    "severity": "High",
                    "share_pct": 1.8,
                    "conformance_bucket": "Model deviation",
                    "is_deviating": True,
                    "stroke_style": "dashed",
                    "branch_role": "side",
                    "edge_type": "skip",
                },
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
    assert 'data-fit-mode="shelf"' in svg
    assert 'style="display:block;width:100%;max-width:100%;height:auto;"' in svg
    assert "Invitation" in svg
    assert "FIT mail" in svg
    assert "stroke-dasharray" in svg
    assert 'data-branch-role="mainline"' in svg
    assert 'data-branch-role="side"' in svg
    assert 'aria-label="Workflow conformance board"' in svg
    assert "Upstream activities" in svg
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
                {
                    "activity": "Start_node",
                    "display_name": "Start",
                    "cases": 100,
                    "occurrences": 100,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "Main_node",
                    "display_name": "Main",
                    "cases": 90,
                    "occurrences": 90,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
                },
                {
                    "activity": "Upper_branch",
                    "display_name": "Upper branch",
                    "cases": 12,
                    "occurrences": 12,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "lane": "left",
                    "step_rank": 1,
                },
                {
                    "activity": "Lower_branch",
                    "display_name": "Lower branch",
                    "cases": 8,
                    "occurrences": 8,
                    "severity": "Moderate",
                    "conformance_bucket": "Log deviation",
                    "branch_role": "side",
                    "lane": "right",
                    "step_rank": 1,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Start_node -> Main_node",
                    "source": "Start_node",
                    "target": "Main_node",
                    "frequency": 90,
                    "median_days": 3.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "edge_id": "Main_node -> Upper_branch",
                    "source": "Main_node",
                    "target": "Upper_branch",
                    "frequency": 12,
                    "median_days": 6.0,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "stroke_style": "dashed",
                },
                {
                    "edge_id": "Main_node -> Lower_branch",
                    "source": "Main_node",
                    "target": "Lower_branch",
                    "frequency": 8,
                    "median_days": 7.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Log deviation",
                    "branch_role": "side",
                    "stroke_style": "dashed",
                },
            ]
        ),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")

    assert "Upstream activities" in svg
    assert "Related activities" in svg
    assert "Upper branch" in svg
    assert "Lower branch" in svg
    assert 'data-layout-band="upper"' in svg
    assert 'data-layout-band="lower"' in svg
    assert 'data-qa="workflow-variation-band"' in svg
    assert "crpm-workflow-explorer" not in svg


def test_workflow_board_svg_uses_compact_shelves_for_related_activities():
    mainline = [
        ("Invitation_mail", "Invitation", "invitation"),
        ("FIT_mail", "FIT mail", "fit_mail"),
        ("FIT_return", "FIT return", "fit_return"),
        ("Lab_result", "Lab result", "lab_result"),
        ("PCC_observation", "PCC observation", "pcc_observation"),
        ("Colonoscopy", "Colonoscopy", "colonoscopy"),
    ]
    related = [
        ("Reminder_mail", "Reminder", 1),
        ("PCC_FIT_rejection", "PCC FIT rejection", 2),
        ("Admin_review", "Admin review", 3),
        ("Reschedule_mail", "Rescheduled", 5),
    ]
    nodes = [
        {
            "step": step,
            "activity": activity,
            "display_name": label,
            "cases": 900,
            "occurrences": 900,
            "severity": "Low",
            "conformance_bucket": "Conformant",
            "branch_role": "mainline",
            "lane": "center",
            "step_rank": rank,
        }
        for rank, (activity, label, step) in enumerate(mainline)
    ]
    nodes.extend(
        {
            "activity": activity,
            "display_name": label,
            "cases": 20,
            "occurrences": 20,
            "severity": "Moderate",
            "conformance_bucket": "Model deviation",
            "branch_role": "side",
            "lane": "right",
            "step_rank": rank,
        }
        for activity, label, rank in related
    )
    edges = [
        {
            "source": source[0],
            "target": target[0],
            "frequency": 800,
            "severity": "Low",
            "conformance_bucket": "Conformant",
            "branch_role": "mainline",
        }
        for source, target in zip(mainline, mainline[1:])
    ]
    edges.extend(
        [
            {"source": "Invitation_mail", "target": "Reminder_mail", "frequency": 22, "branch_role": "side"},
            {"source": "Reminder_mail", "target": "FIT_mail", "frequency": 20, "branch_role": "side"},
            {"source": "Reminder_mail", "target": "Reminder_mail", "frequency": 4, "branch_role": "side"},
            {"source": "FIT_return", "target": "PCC_FIT_rejection", "frequency": 18, "branch_role": "side"},
            {"source": "PCC_FIT_rejection", "target": "Admin_review", "frequency": 16, "branch_role": "side"},
            {"source": "Admin_review", "target": "Lab_result", "frequency": 14, "branch_role": "side"},
            {"source": "Colonoscopy", "target": "Reschedule_mail", "frequency": 12, "branch_role": "side"},
        ]
    )

    svg = render_workflow_conformance_svg(
        {"nodes": pd.DataFrame(nodes), "edges": pd.DataFrame(edges), "legend": pd.DataFrame()},
        layout_mode="horizontal",
        detail_level="analyst",
    )

    viewbox = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    assert viewbox is not None
    assert int(viewbox.group(1)) <= 1120
    assert int(viewbox.group(2)) <= 300
    assert 'data-fit-mode="shelf"' in svg
    assert svg.count('data-layout-band="mainline"') == 6
    assert svg.count('data-layout-band="lower"') == 4
    assert "Related activities" in svg
    assert "PCC FIT rejection" in svg
    assert "PCC FIT rej..." not in svg

    mainline_y = re.findall(
        r'data-activity="[^"]+" data-branch-role="mainline"[^>]*>\s*<rect x="[^"]+" y="([^"]+)"',
        svg,
    )
    related_rects = re.findall(
        r'data-activity="([^"]+)" data-branch-role="side" data-layout-band="lower"[^>]*>\s*<rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"',
        svg,
    )
    assert len(set(mainline_y)) == 1
    assert len(related_rects) == 4
    assert len({y for _, _, y, _, _ in related_rects}) == 1
    ordered_related = sorted((float(x), float(width)) for _, x, _, width, _ in related_rects)
    for (left_x, left_width), (right_x, _) in zip(ordered_related, ordered_related[1:]):
        assert left_x + left_width + 8.0 <= right_x

    related_content = re.findall(
        r'<g[^>]*data-activity="([^"]+)"[^>]*data-branch-role="side"[^>]*>'
        r'.*?<rect x="[^"]+" y="([^"]+)" width="[^"]+" height="([^"]+)"[^>]*/>'
        r'.*?<text x="[^"]+" y="([^"]+)"[^>]*data-qa="workflow-board-meta">',
        svg,
        re.S,
    )
    assert len(related_content) == 4
    for _, node_y, node_height, meta_y in related_content:
        assert float(meta_y) <= float(node_y) + float(node_height) - 14.0

    phase_heights = [
        float(value)
        for value in re.findall(
            r'<rect[^>]*height="([^"]+)"[^>]*data-qa="workflow-phase-band"[^>]*/>',
            svg,
        )
    ]
    assert len(phase_heights) == 3
    assert all(height < int(viewbox.group(2)) * 0.7 for height in phase_heights)
    reminder_loop = re.search(r'<path d="([^"]+)"[^>]*data-edge-id="Reminder_mail -&gt; Reminder_mail"', svg)
    assert reminder_loop is not None
    loop_coordinates = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", reminder_loop.group(1))]
    assert len(loop_coordinates) % 2 == 0
    assert max(loop_coordinates[1::2]) <= int(viewbox.group(2)) - 8.0


def test_workflow_board_svg_simple_mainline_export_uses_compact_content_height():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
                },
                {
                    "activity": "FIT_return",
                    "display_name": "FIT return",
                    "cases": 662,
                    "occurrences": 662,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 2,
                },
                {
                    "activity": "Lab_result",
                    "display_name": "Lab result",
                    "cases": 662,
                    "occurrences": 662,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 3,
                },
                {
                    "activity": "PCC_observation",
                    "display_name": "PCC observation",
                    "cases": 28,
                    "occurrences": 28,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 4,
                },
                {
                    "activity": "Colonoscopy",
                    "display_name": "Colonoscopy",
                    "cases": 28,
                    "occurrences": 28,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 5,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 1000,
                    "median_days": 35.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "FIT_mail",
                    "target": "FIT_return",
                    "frequency": 662,
                    "median_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "FIT_return",
                    "target": "Lab_result",
                    "frequency": 662,
                    "median_days": 7.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "Lab_result",
                    "target": "PCC_observation",
                    "frequency": 28,
                    "median_days": 2.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "PCC_observation",
                    "target": "Colonoscopy",
                    "frequency": 28,
                    "median_days": 45.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
            ]
        ),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="executive")
    analyst_svg = render_workflow_conformance_svg(payload, layout_mode="horizontal", detail_level="analyst")
    vertical_svg = render_workflow_conformance_svg(payload, layout_mode="vertical", detail_level="analyst")
    explorer_html = render_workflow_explorer_html(create_workflow_interactive_payload(payload))

    viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    analyst_viewbox_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', analyst_svg)
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
    assert analyst_viewbox_match is not None
    assert invitation_match is not None
    assert invitation_chip_match is not None
    assert 'data-fit-mode="shelf"' in svg
    assert 'style="display:block;width:100%;max-width:100%;height:auto;"' in svg
    assert 'data-qa="workflow-board-card"' in svg
    assert 'data-qa="workflow-board-chip"' in svg
    assert svg.count('data-qa="workflow-phase-band"') == 3
    assert vertical_svg.count('data-qa="workflow-phase-band"') == 3
    assert explorer_html.count('data-qa="explorer-phase-band"') == 3
    for phase_label in ("Pre-primary care", "Primary care", "Hospital care"):
        assert phase_label in svg
        assert phase_label in vertical_svg
        assert phase_label in explorer_html
    assert 'data-qa="explorer-mainline-band"' not in explorer_html
    assert "Reference flow" not in explorer_html
    board_height = int(viewbox_match.group(2))
    node_y = float(invitation_match.group(1))
    node_height = float(invitation_match.group(3))
    chip_y = float(invitation_chip_match.group(1))
    chip_height = float(invitation_chip_match.group(3))
    title_y = float(invitation_chip_match.group(4))

    assert int(viewbox_match.group(1)) > board_height
    assert 110 <= board_height <= 190
    assert 200 <= int(analyst_viewbox_match.group(2)) <= 250
    assert node_height <= 96.0
    assert node_y <= 40.0
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
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 0,
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
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
                    "target": "FIT_mail",
                    "frequency": 1000,
                    "median_days": 35.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
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


def test_workflow_phase_classification_ignores_missing_step_values():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "step": pd.NA,
                    "activity": "PCC_observation",
                    "display_name": "PCC observation",
                    "cases": 10,
                    "occurrences": 10,
                    "step_rank": 4,
                    "branch_role": "mainline",
                    "lane": "center",
                }
            ]
        ),
        "edges": pd.DataFrame(),
        "legend": pd.DataFrame(),
    }

    svg = render_workflow_conformance_svg(payload, layout_mode="horizontal")

    assert 'data-phase="primary"' in svg
    assert "Primary care" in svg


def test_workflow_board_svg_handles_partial_nodes_only():
    svg = render_workflow_conformance_svg(
        {
            "nodes": pd.DataFrame(
                [{"activity": "Invitation_mail", "display_name": "Invitation", "cases": 10, "occurrences": 10, "severity": "Low"}]
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
                [{"source": "Invitation_mail", "target": "FIT_mail", "frequency": 9, "median_days": 3.0, "severity": "Moderate"}]
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
                    },
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
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                },
                {
                    "activity": "Lab_return",
                    "display_name": "Lab return",
                    "cases": 22,
                    "occurrences": 22,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                },
                {
                    "activity": "Lab_result",
                    "display_name": "Lab result",
                    "cases": 22,
                    "occurrences": 22,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 662,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                },
                {
                    "edge_id": "Lab_return -> Lab_result",
                    "source": "Lab_return",
                    "target": "Lab_result",
                    "frequency": 12,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                },
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="Executive")

    assert list(filtered["edges"]["edge_id"]) == ["Lab_return -> Lab_result"]
    assert filtered["detail_level"] == "executive"


def test_filter_workflow_payload_all_keeps_mixed_reference_flow():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "coverage_group": "dominant",
                    "conformance_bucket": "Mixed",
                    "branch_role": "mainline",
                },
                {
                    "activity": "FIT_mail",
                    "display_name": "FIT mail",
                    "cases": 980,
                    "coverage_group": "dominant",
                    "conformance_bucket": "Mixed",
                    "branch_role": "mainline",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "Invitation_mail -> FIT_mail",
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 980,
                    "severity": "Low",
                    "conformance_bucket": "Mixed",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="all", deviation_view="all", detail_level="analyst")

    assert list(filtered["nodes"]["activity"]) == ["Invitation_mail", "FIT_mail"]
    assert list(filtered["edges"]["edge_id"]) == ["Invitation_mail -> FIT_mail"]


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
                    "business_label": "Invitation â†’ FIT mail",
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

    explorer = create_workflow_interactive_payload(
        payload, metric_coloring="Conformance bucket", detail_level="Research", selected_node_id="FIT_mail"
    )
    html = render_workflow_explorer_html(explorer)

    assert explorer["nodes"]
    assert explorer["edges"]
    assert explorer["selected_node_id"] == "FIT_mail"
    assert explorer["selected_edge_uid"] is None
    assert explorer["renderer_role"] == "conformance_explorer"
    assert next(node for node in explorer["nodes"] if node["id"] == "FIT_mail")["selected"] is True
    assert next(node for node in explorer["nodes"] if node["id"] == "Invitation_mail")["neighbor"] is True
    assert next(edge for edge in explorer["edges"] if edge["target"] == "FIT_mail")["neighbor"] is True
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
    assert "Clear local focus" in html
    assert "Reset graph view" in html
    assert "Pinned node" in html
    assert "Local node focus" in html
    assert '"FIT_mail"' in html
    assert 'id="crpm-explorer-live-title"' in html
    assert 'id="crpm-explorer-reset-view"' in html
    assert "Start" in html
    assert "End" in html
    assert "top to bottom" in html.lower()
    assert "Invitation" in html
    assert "FIT mail" in html
    assert "neighbor_ids" not in html
    assert "node::" not in html


def test_workflow_interactive_payload_selects_edge_by_edge_uid():
    edge_uid = "Invitation_mail -> FIT_mail|Conformant|expected|mainline"
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "business_label": "Invitation",
                    "cases": 10,
                    "occurrences": 10,
                    "severity": "Low",
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
                    "cases": 10,
                    "occurrences": 10,
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
                    "edge_uid": edge_uid,
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "business_label": "Invitation â†’ FIT mail",
                    "frequency": 10,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                    "stroke_style": "solid",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload, selected_edge_id=edge_uid)
    html = render_workflow_explorer_html(explorer)

    assert explorer["selected_edge_id"] == edge_uid
    assert explorer["selected_edge_uid"] == edge_uid
    assert next(edge for edge in explorer["edges"] if edge["id"] == edge_uid)["selected"] is True
    assert all(node["neighbor"] is True for node in explorer["nodes"])
    assert 'data-edge-id="Invitation_mail -&gt; FIT_mail|Conformant|expected|mainline"' in html
    assert '"Invitation_mail -> FIT_mail|Conformant|expected|mainline"' in html
    assert "Pinned edge" in html


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
    assert "baselineScale = Math.min(1.0, availableWidth / boundsWidth, availableHeight / boundsHeight);" in html
    assert "Math.max(0.56, Math.min(2.4, nextZoom))" in html
    assert 'class="crpm-explorer-figure" style="width:100%;height:100%;"' in html
    assert 'style="display:block;width:100%;height:100%;overflow:visible;margin:0 auto;"' in html
    assert "Wheel to zoom | drag to pan | hover for detail." in html
    assert 'data-testid="crpm-explorer-tooltip"' in html
    assert "figure.addEventListener('wheel'" in html
    assert "figure.addEventListener('pointerdown'" in html
    assert "figure.addEventListener('pointermove'" in html
    assert "const zoomAt = (factor, event) =>" in html
    assert "is-hover" in html
    assert 'id="crpm-workflow-static-frame"' in html
    assert 'id="crpm-workflow-content"' in html
    assert 'data-drawable-min-x="' in html
    assert "const drawableMinX = Number(svg.getAttribute('data-drawable-min-x') || '12');" in html
    assert "streamlit:setFrameHeight" not in html
    assert "window.setTimeout(notifyFrameHeight" not in html
    assert 'preserveAspectRatio="xMidYMin meet"' in html


def test_workflow_interactive_html_serializes_selected_ids_safely():
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
        "selected_node_id": '</script><script>alert("x")</script>',
        "selected_edge_id": '</script><script>alert("y")</script>',
        "detail_level": "analyst",
        "metric_coloring": "Conformance bucket",
        "conformance_lens": "% of paths",
    }

    html = render_workflow_explorer_html(explorer)

    assert '</script><script>alert("x")' not in html
    assert '</script><script>alert("y")' not in html
    assert '<\\/script><script>alert(\\"x\\")<\\/script>' in html
    assert '<\\/script><script>alert(\\"y\\")<\\/script>' in html


def test_workflow_explorer_html_escapes_node_and_edge_labels():
    explorer = {
        "nodes": [
            {
                "id": "unsafe_node",
                "business_label": '<script>alert("node")</script> & "quoted"',
                "display_name": '<script>alert("node")</script>',
                "cases": 7,
                "occurrences": 8,
                "median_days": 2.0,
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
            },
            {
                "id": "safe_target",
                "business_label": "Safe target",
                "display_name": "Safe target",
                "cases": 7,
                "occurrences": 8,
                "median_days": 2.0,
                "p90_days": 4.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "lane_position": "mainline",
                "x": 220.0,
                "y": 260.0,
                "width": 224.0,
                "height": 86.0,
                "center_x": 332.0,
                "center_y": 303.0,
                "surface_fill": "#ffffff",
                "stroke": "#7aa08a",
                "ink": "#22313b",
                "accent": "#7aa08a",
                "accent_fill": "#edf5ef",
                "chip_fill": "#edf5ef",
                "chip_ink": "#2d6a3f",
                "selected": False,
                "neighbor": False,
            },
        ],
        "edges": [
            {
                "id": "unsafe_edge",
                "source": "unsafe_node",
                "target": "safe_target",
                "caption": '<img src=x onerror=alert("edge")> & edge',
                "frequency": 7,
                "median_days": 2.0,
                "p90_days": 4.0,
                "share_pct": 100.0,
                "severity": "Low",
                "conformance_bucket": "Conformant",
                "branch_role": "mainline",
                "stroke_style": "solid",
                "stroke_width": 1.4,
                "stroke": "#7aa08a",
                "accent": "#7aa08a",
                "path": "M 332 206 C 332 230, 332 240, 332 256",
                "label_x": 360.0,
                "label_y": 230.0,
                "selected": False,
                "neighbor": False,
                "show_label": True,
                "label_width": 80.0,
                "label_height": 20.0,
            }
        ],
        "width": 760,
        "height": 420,
        "content_bounds": {"min_x": 180.0, "min_y": 80.0, "max_x": 460.0, "max_y": 360.0},
        "drawable_bounds": {"min_x": 12.0, "min_y": 12.0, "max_x": 748.0, "max_y": 408.0},
        "detail_level": "research",
        "metric_coloring": "Conformance bucket",
        "conformance_lens": "% of paths",
    }

    html = render_workflow_explorer_html(explorer)

    assert '<script>alert("node")</script>' not in html
    assert '<img src=x onerror=alert("edge")>' not in html
    assert "&lt;script&gt;alert(&quot;node&quot;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(&quot;edge&quot;)&gt;" in html


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
                    "business_label": "Invitation â†’ FIT mail",
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
                    "business_label": "FIT mail â†’ FIT return",
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
        assert float(top_text_box.get("max_y", top["y"] + top["height"])) + 4.0 <= float(bottom_text_box.get("min_y", bottom["y"]))


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
                {
                    "activity": "Invitation_mail",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "median_next_delay_days": 35.0,
                    "p90_next_delay_days": 40.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
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
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 1,
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
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 2,
                },
                {
                    "activity": "Lab_result",
                    "display_name": "Lab result",
                    "cases": 662,
                    "occurrences": 662,
                    "median_next_delay_days": 2.0,
                    "p90_next_delay_days": 4.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 3,
                },
                {
                    "activity": "PCC_observation",
                    "display_name": "PCC observation",
                    "cases": 28,
                    "occurrences": 28,
                    "median_next_delay_days": 45.0,
                    "p90_next_delay_days": 55.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 4,
                },
                {
                    "activity": "Colonoscopy",
                    "display_name": "Colonoscopy",
                    "cases": 28,
                    "occurrences": 28,
                    "median_next_delay_days": None,
                    "p90_next_delay_days": None,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                    "lane": "center",
                    "step_rank": 5,
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "source": "Invitation_mail",
                    "target": "FIT_mail",
                    "frequency": 1000,
                    "median_days": 35.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "FIT_mail",
                    "target": "FIT_return",
                    "frequency": 662,
                    "median_days": 15.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "FIT_return",
                    "target": "Lab_result",
                    "frequency": 662,
                    "median_days": 7.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "Lab_result",
                    "target": "PCC_observation",
                    "frequency": 28,
                    "median_days": 2.0,
                    "severity": "Moderate",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "source": "PCC_observation",
                    "target": "Colonoscopy",
                    "frequency": 28,
                    "median_days": 45.0,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
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
    assert all(not node.get("inline_detail") for node in mainline_nodes)
    assert all(
        float(node.get("timing_origin_y", 0.0)) > float(node.get("title_origin_y", 0.0))
        for node in mainline_nodes
        if node.get("timing_lines_render")
    )
    assert all(
        "path " in str(node.get("timing_lines_render", [""])[0]).lower() for node in mainline_nodes if node.get("timing_lines_render")
    )
    assert all(
        "activity " in str(node.get("timing_lines_render", [""])[0]).lower() for node in mainline_nodes if node.get("timing_lines_render")
    )


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
                    "business_label": "Invitation â†’ FIT mail",
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
    last_mainline_bottom = max(node["y"] + node["height"] for node in explorer["nodes"] if node.get("branch_role") == "mainline")
    end_anchor_y = last_mainline_bottom + 30.0

    assert explorer["height"] > max_node_bottom + 24.0
    if visible_labels:
        max_label_extent = max(edge["label_y"] + (float(edge.get("label_height", 18.0)) / 2.0) for edge in visible_labels)
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
                "caption": "Invitation â†’ FIT mail",
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

    assert re.search(r'markerWidth="11\.0"', html)
    assert re.search(r'markerHeight="10\.0"', html)
    assert 'id="workflow-explorer-arrow-mainline"' in html
    assert 'id="workflow-explorer-arrow-log"' in html
    assert 'id="workflow-explorer-arrow-model"' in html
    assert 'id="workflow-explorer-arrow-neutral"' in html
    assert 'marker-end="url(#workflow-explorer-arrow-mainline)"' in html
    assert 'markerUnits="userSpaceOnUse"' in html
    assert 'stroke="#c8d4d8" stroke-width="0.8"' not in html
    assert 'preserveAspectRatio="xMidYMin meet"' in html
    assert 'viewBox="0 0 900 420"' in html
    assert 'class="crpm-explorer-figure" style="width:100%;height:100%;"' in html
    assert 'style="display:block;width:100%;height:100%;overflow:visible;margin:0 auto;"' in html
    assert 'data-content-min-x="' in html
    assert 'data-drawable-min-x="' in html
    assert 'data-fit-pad-bottom="' in html
    assert "const computeBaselineFit = () => {" in html
    assert "const drawableMaxY = Number(svg.getAttribute('data-drawable-max-y') || String((viewBox.height || 0) - 12));" in html
    assert "const fitPadTop = Number(svg.getAttribute('data-fit-pad-top') || '0');" in html
    assert "baselineScale = Math.min(1.0, availableWidth / boundsWidth, availableHeight / boundsHeight);" in html
    assert "const scale = baselineScale * zoomFactor;" in html
    assert "translate(${tx} ${ty}) scale(${scale})" in html
    assert (
        ".crpm-explorer-canvas{position:relative;height:clamp(500px,68vh,720px);min-height:500px;border:1px solid #d9dfe6;border-radius:18px;background:#ffffff;overflow:hidden;"
        in html
    )
    assert "const panLimits = (scale) => {" in html
    assert "const setZoomFactor = (nextZoom, anchorPoint) =>" in html
    assert "const finishDrag = (event) => {" in html
    assert "streamlit:setFrameHeight" not in html
    assert "window.setTimeout(notifyFrameHeight" not in html
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


def test_workflow_primary_path_nodes_keeps_all_steps_when_only_side_nodes_are_visible():
    nodes = [
        {"id": "reminder", "step_rank": 0, "lane_position": "right", "cases": 57, "center_y": 44.0, "branch_role": "side"},
        {"id": "admin", "step_rank": 1, "lane_position": "right", "cases": 32, "center_y": 108.0, "branch_role": "side"},
        {"id": "reschedule", "step_rank": 2, "lane_position": "right", "cases": 18, "center_y": 172.0, "branch_role": "side"},
    ]

    primary = _workflow_primary_path_nodes(nodes)

    assert [node["id"] for node in primary] == ["reminder", "admin", "reschedule"]


def test_workflow_explorer_hides_variation_separator_without_reference_mainline():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "Reminder_mail",
                    "display_name": "Reminder mail",
                    "cases": 57,
                    "occurrences": 57,
                    "median_next_delay_days": 1.1,
                    "severity": "Low",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "lane": "right",
                    "step_rank": 0,
                },
                {
                    "activity": "Admin_review",
                    "display_name": "Admin review",
                    "cases": 32,
                    "occurrences": 32,
                    "median_next_delay_days": 1.0,
                    "severity": "Low",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                    "lane": "right",
                    "step_rank": 0,
                },
            ]
        ),
        "edges": pd.DataFrame(),
        "legend": pd.DataFrame(),
    }

    explorer = create_workflow_interactive_payload(payload)
    html = render_workflow_explorer_html(explorer)

    assert explorer["has_bottom_branches"] is True
    assert all(node.get("branch_role") != "mainline" for node in explorer["nodes"])
    last_node_bottom = max(float(node["y"]) + float(node["height"]) for node in explorer["nodes"])
    assert float(explorer["anchor_bounds"]["max_y"]) > last_node_bottom + 24.0
    assert "Lower variation" not in html
    end_anchor_match = re.search(
        r'<g id="crpm-workflow-end-anchor"[^>]*><rect x="[^"]+" y="([^"]+)"',
        html,
    )
    assert end_anchor_match is not None
    assert float(end_anchor_match.group(1)) > last_node_bottom


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
                {
                    "activity": "invitation",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "occurrences": 1000,
                    "severity": "Low",
                    "conformance_bucket": "Conformant",
                    "coverage_group": "dominant",
                    "branch_role": "mainline",
                },
                {
                    "activity": "admin_review",
                    "display_name": "Admin review",
                    "cases": 50,
                    "occurrences": 60,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                    "branch_role": "side",
                },
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
                },
                {
                    "edge_id": "fit_mail -> admin_review",
                    "source": "fit_mail",
                    "target": "admin_review",
                    "frequency": 50,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                    "branch_role": "side",
                },
            ]
        ),
        "trace_profiles": pd.DataFrame(
            [
                {
                    "case_id": "case-1",
                    "event_count": 4,
                    "throughput_days": 20.0,
                    "variant_signature": "Invitation â†’ FIT mail",
                    "has_deviation": False,
                    "node_ids": ["invitation", "fit_mail"],
                    "edge_ids": ["invitation -> fit_mail"],
                    "edge_uids": ["invitation -> fit_mail|Conformant|expected|mainline"],
                },
                {
                    "case_id": "case-2",
                    "event_count": 6,
                    "throughput_days": 42.0,
                    "variant_signature": "Invitation â†’ FIT mail â†’ Admin review",
                    "has_deviation": True,
                    "node_ids": ["invitation", "fit_mail", "admin_review"],
                    "edge_ids": ["invitation -> fit_mail", "fit_mail -> admin_review"],
                    "edge_uids": [
                        "invitation -> fit_mail|Conformant|expected|mainline",
                        "fit_mail -> admin_review|Model deviation|branch|admin_review",
                    ],
                },
            ]
        ),
        "summary": {
            "cases_covered": 2,
            "events_covered": 10,
            "visible_case_count": 2,
            "excluded_case_count": 0,
            "path_denominator": 2,
            "path_denominator_label": "cases in evaluation log",
            "activity_denominator": 10,
            "activity_denominator_label": "events in evaluation log",
            "transition_denominator": 2,
            "transition_denominator_label": "observed transitions in evaluation log",
            "dominant_path_share": 50.0,
            "deviation_share": 50.0,
            "median_throughput_days": 31.0,
        },
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="analyst")

    assert filtered["summary"]["cases_covered"] == 1
    assert filtered["summary"]["events_covered"] == 6
    assert filtered["summary"]["visible_case_count"] == 1
    assert filtered["summary"]["excluded_case_count"] == 1
    assert filtered["summary"]["path_denominator"] == 2
    assert filtered["summary"]["activity_denominator"] == 10
    assert filtered["summary"]["transition_denominator"] == 2
    assert filtered["visible_case_count"] == 1
    assert filtered["excluded_case_count"] == 1
    assert filtered["path_denominator"] == 2
    assert filtered["activity_denominator"] == 10
    assert filtered["process_map_payload"]["denominators"]["visible_case_count"] == 1
    assert filtered["summary"]["deviation_share"] == 100.0
    assert filtered["summary"]["median_throughput_days"] == 42.0


def test_filter_workflow_payload_matches_trace_profiles_by_edge_uid():
    edge_uid = "fit_mail -> admin_review|Model deviation|branch|admin_review"
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "fit_mail",
                    "display_name": "FIT mail",
                    "cases": 2,
                    "coverage_group": "dominant",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "activity": "admin_review",
                    "display_name": "Admin review",
                    "cases": 1,
                    "coverage_group": "rare",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "raw edge label",
                    "edge_uid": edge_uid,
                    "source": "fit_mail",
                    "target": "admin_review",
                    "frequency": 1,
                    "severity": "High",
                    "conformance_bucket": "Model deviation",
                    "coverage_group": "rare",
                    "branch_role": "side",
                }
            ]
        ),
        "trace_profiles": pd.DataFrame(
            [
                {
                    "case_id": "case-1",
                    "event_count": 3,
                    "throughput_days": 12.0,
                    "variant_signature": "FIT mail â†’ Admin review",
                    "has_deviation": True,
                    "has_model_deviation": True,
                    "node_ids": ["fit_mail", "admin_review"],
                    "edge_ids": ["does not match"],
                    "edge_uids": [edge_uid],
                }
            ]
        ),
        "summary": {
            "cases_covered": 2,
            "visible_case_count": 2,
            "path_denominator": 2,
            "activity_denominator": 5,
            "transition_denominator": 2,
        },
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="analyst")

    assert filtered["summary"]["cases_covered"] == 1
    assert filtered["summary"]["visible_case_count"] == 1
    assert filtered["summary"]["excluded_case_count"] == 1
    assert filtered["trace_profiles"].iloc[0]["case_id"] == "case-1"
    assert list(filtered["edges"]["edge_uid"]) == [edge_uid]


def test_filter_workflow_payload_keeps_node_only_deviations_visible():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "invitation",
                    "display_name": "Invitation",
                    "cases": 10,
                    "coverage_group": "dominant",
                    "conformance_bucket": "Conformant",
                    "branch_role": "mainline",
                },
                {
                    "activity": "unmapped_review",
                    "display_name": "Unmapped review",
                    "cases": 1,
                    "coverage_group": "rare",
                    "conformance_bucket": "Model deviation",
                    "branch_role": "side",
                },
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "invitation -> fit_mail",
                    "source": "invitation",
                    "target": "fit_mail",
                    "frequency": 10,
                    "coverage_group": "dominant",
                    "conformance_bucket": "Conformant",
                },
            ]
        ),
        "trace_profiles": pd.DataFrame(
            [
                {
                    "case_id": "case-1",
                    "event_count": 2,
                    "node_ids": ["unmapped_review"],
                    "edge_ids": [],
                    "edge_uids": [],
                    "has_deviation": True,
                },
            ]
        ),
        "summary": {"cases_covered": 1, "events_covered": 2, "deviation_share": 100.0},
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="rare", deviation_view="Model deviations", detail_level="analyst")

    assert list(filtered["nodes"]["activity"]) == ["unmapped_review"]
    assert filtered["edges"].empty
    assert filtered["summary"]["cases_covered"] == 1


def test_filter_workflow_payload_derives_nodes_when_edges_survive_filtering():
    payload = {
        "nodes": pd.DataFrame(
            [
                {
                    "activity": "invitation",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "coverage_group": "legacy",
                    "conformance_bucket": "Conformant",
                },
                {
                    "activity": "fit_mail",
                    "display_name": "FIT mail",
                    "cases": 900,
                    "coverage_group": "legacy",
                    "conformance_bucket": "Conformant",
                },
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
                {
                    "activity": "invitation",
                    "display_name": "Invitation",
                    "cases": 1000,
                    "coverage_group": "rare",
                    "conformance_bucket": "Conformant",
                },
                {
                    "activity": "fit_mail",
                    "display_name": "FIT mail",
                    "cases": 900,
                    "coverage_group": "rare",
                    "conformance_bucket": "Conformant",
                },
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


def test_filter_workflow_payload_analyst_view_prioritizes_deviating_edges_after_truncation():
    nodes = [
        {
            "activity": f"n{index}",
            "display_name": f"Node {index}",
            "cases": 1,
            "coverage_group": "dominant",
            "conformance_bucket": "Conformant",
            "branch_role": "side",
        }
        for index in range(23)
    ]
    edges = [
        {
            "edge_id": f"n{index} -> n{index + 1}",
            "source": f"n{index}",
            "target": f"n{index + 1}",
            "frequency": 100 - index,
            "coverage_group": "dominant",
            "conformance_bucket": "Conformant",
            "branch_role": "side",
            "severity": "Low",
        }
        for index in range(20)
    ]
    edges.append(
        {
            "edge_id": "n20 -> n21",
            "source": "n20",
            "target": "n21",
            "frequency": 1,
            "coverage_group": "dominant",
            "conformance_bucket": "Log deviation",
            "branch_role": "side",
            "severity": "High",
        }
    )
    payload = {"nodes": pd.DataFrame(nodes), "edges": pd.DataFrame(edges), "legend": pd.DataFrame()}

    filtered = filter_workflow_payload(payload, coverage_view="all", deviation_view="all", detail_level="analyst")

    assert len(filtered["edges"]) == 18
    assert "n20 -> n21" in set(filtered["edges"]["edge_id"])


def test_filter_workflow_payload_uses_semantic_edge_uid_fallback():
    payload = {
        "nodes": pd.DataFrame(
            [
                {"activity": "fit_mail", "display_name": "FIT mail", "cases": 1},
                {"activity": "admin_review", "display_name": "Admin review", "cases": 1},
            ]
        ),
        "edges": pd.DataFrame(
            [
                {
                    "edge_id": "fit_mail -> admin_review",
                    "source": "fit_mail",
                    "target": "admin_review",
                    "frequency": 1,
                    "conformance_bucket": "Model deviation",
                    "edge_type": "branch",
                    "branch_family": "admin_review",
                }
            ]
        ),
        "legend": pd.DataFrame(),
    }

    filtered = filter_workflow_payload(payload, coverage_view="all", deviation_view="all", detail_level="research")

    assert filtered["edges"].iloc[0]["edge_uid"] == workflow_edge_uid(
        "fit_mail -> admin_review",
        "Model deviation",
        "branch",
        "admin_review",
    )


def test_workflow_explorer_html_supports_keyboard_selection() -> None:
    explorer = create_workflow_interactive_payload(_bpmn_style_workflow_payload())

    html = render_workflow_explorer_html(explorer)

    assert 'role="button" tabindex="0" focusable="true"' in html
    assert 'aria-live="polite"' in html
    assert "const bindSelection" in html
    assert "event.key !== 'Enter' && event.key !== ' '" in html
