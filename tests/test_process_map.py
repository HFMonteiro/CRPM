from crpm.process_map import build_process_map_kpis, build_selection_context


def test_process_map_kpis_uses_explicit_denominators() -> None:
    rows = build_process_map_kpis(
        {
            "visible_case_count": 10,
            "excluded_case_count": 2,
            "activity_denominator": 40,
            "transition_denominator": 30,
        }
    )

    assert [row["key"] for row in rows] == [
        "visible_case_count",
        "excluded_case_count",
        "activity_denominator",
        "transition_denominator",
    ]
    assert rows[0]["label"] == "Visible cases"
    assert rows[0]["value"] == 10


def test_selection_context_is_json_safe_and_redacts_unknown_fields() -> None:
    context = build_selection_context(
        source_page="DFG Visualizations",
        renderer_role="dfg",
        selected_node_id="<FIT>",
        selected_edge_uid="A->B",
        local_focus_hint="Local focus only",
        extra={"case_id": "raw-secret", "allowed": "ignored"},
    )

    assert context == {
        "source_page": "DFG Visualizations",
        "renderer_role": "dfg",
        "selected_node_id": "<FIT>",
        "selected_edge_uid": "A->B",
        "local_focus_hint": "Local focus only",
    }


def test_process_map_kpis_handles_empty_payload() -> None:
    assert build_process_map_kpis({}) == []
