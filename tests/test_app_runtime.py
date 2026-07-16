from types import SimpleNamespace
from datetime import date

import pandas as pd
import pytest
from pm4py.objects.log.obj import EventLog, Trace

import crpm.app_runtime as app_runtime
from crpm.app_runtime import (
    LoadedLog,
    _delay_bucket,
    build_conformance_workspace_payload,
    build_model_comparison_dataframe,
    compute_log_stats,
    compute_filter_key,
    get_log_profile,
    list_safe_local_xes_files,
    preview_csv_dataframe,
    resolve_csv_log,
    resolve_xes_log,
    run_discovery_comparison_pipeline,
    compute_full_conformance,
)
from crpm.app_state import get_crpm_state


def _fake_place(in_arcs: int, out_arcs: int) -> SimpleNamespace:
    return SimpleNamespace(in_arcs=[object()] * in_arcs, out_arcs=[object()] * out_arcs)


def test_build_model_comparison_dataframe_adds_quality_columns() -> None:
    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=3,
            num_places=2,
            num_arcs=4,
            discovery_time_s=0.42,
            parameter_profile={
                "profile_name": "inductive-noise-aware",
                "pm4py_variant": "IMf",
                "intended_use": "Preferred robust baseline",
            },
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
        }
    }

    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    assert list(comparison_df["model_name"]) == ["Inductive"]
    assert comparison_df.iloc[0]["fitness_quality"] == "Good"
    assert comparison_df.iloc[0]["precision_quality"] in {"Good", "Excellent"}
    assert comparison_df.iloc[0]["num_arcs"] == 4
    assert comparison_df.iloc[0]["parameter_profile_name"] == "inductive-noise-aware"
    assert comparison_df.iloc[0]["pm4py_variant"] == "IMf"
    assert comparison_df.iloc[0]["quality_band"] in {"Good", "Excellent"}
    assert 0.0 <= comparison_df.iloc[0]["quality_score"] <= 1.0
    assert comparison_df.iloc[0]["quadrant"]


def test_compute_full_conformance_declares_method_profile(monkeypatch) -> None:
    monkeypatch.setattr(
        "crpm.app_runtime.compute_alignments",
        lambda *args, **kwargs: {"fitness": {"log_fitness": 0.91}, "aligned_traces": []},
    )
    monkeypatch.setattr(
        "crpm.app_runtime.compute_token_replay",
        lambda *args, **kwargs: {"fitness": {"log_fitness": 0.89}, "token_results": []},
    )

    result = compute_full_conformance(EventLog(), object(), object(), object(), "Inductive")

    assert result["conformance_profile"]["profile_name"] == "alignment-first-diagnostics"
    assert result["conformance_profile"]["primary_diagnostic"] == "alignments"
    assert result["summary"]["conformance_profile"]["token_replay_role"] == "fast screening"


def test_build_conformance_workspace_payload_creates_structured_tables() -> None:
    trace = Trace()
    trace.attributes["concept:name"] = "raw-case-identifier-001"
    trace.append(
        {
            "concept:name": "Invitation_mail",
            "org:resource": "Nurse Maria",
            "time:timestamp": pd.Timestamp("2024-01-01"),
        }
    )
    trace.append(
        {
            "concept:name": "FIT_mail",
            "org:resource": "Screening Team",
            "time:timestamp": pd.Timestamp("2024-01-02"),
        }
    )
    trace.append(
        {
            "concept:name": "FIT_return",
            "org:resource": "Screening Team",
            "time:timestamp": pd.Timestamp("2024-01-05"),
        }
    )
    log = EventLog([trace])

    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=3,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": [{"fitness": 0.75, "cost": 2.0}]},
            "token": {"token_results": [{"trace_fitness": 0.70, "missing_tokens": 1, "remaining_tokens": 0}]},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    assert not payload["model_summary_df"].empty
    assert not payload["deviation_summary_df"].empty
    assert not payload["trace_deviation_df"].empty
    assert payload["model_summary_df"].iloc[0]["summary"] == "Alignment log fit 0.91 · Token log fit 0.89"
    assert payload["deviation_summary_df"].iloc[0]["alignment_summary"] == "log fit 0.91"
    assert payload["deviation_summary_df"].iloc[0]["token_summary"] == "log fit 0.89"
    assert not payload["workflow"]["nodes"].empty
    assert not payload["workflow"]["edges"].empty
    assert payload["resource_perspective"]["summary"]["resource_count"] == 2
    assert payload["resource_perspective"]["summary"]["handoff_count"] == 1
    assert payload["conformance_root_causes"]["summary"]["deviating_trace_count"] == 1
    assert "Nurse Maria" not in str(payload["resource_perspective"])
    assert "raw-case-identifier-001" not in str(payload["conformance_root_causes"])
    assert {
        "business_label",
        "branch_role",
        "lane",
        "coverage_group",
        "activity_pct",
        "sync_cases",
        "log_move_cases",
        "model_move_cases",
        "sync_pct",
        "log_move_pct",
        "model_move_pct",
        "neighbor_ids",
        "node_type",
        "branch_family",
        "related_variant_ids",
        "selection_summary",
    }.issubset(payload["workflow"]["nodes"].columns)
    assert {
        "edge_id",
        "edge_uid",
        "business_label",
        "branch_role",
        "coverage_group",
        "coverage_rank",
        "edge_type",
        "branch_family",
        "related_variant_ids",
        "selection_summary",
    }.issubset(payload["workflow"]["edges"].columns)
    assert payload["has_workflow"] is True
    assert {
        "deviation_share",
        "log_deviation_share",
        "model_deviation_share",
        "visible_case_count",
        "excluded_case_count",
        "path_denominator",
        "activity_denominator",
        "transition_denominator",
    }.issubset(payload["workflow"]["summary"].keys())
    workflow = payload["workflow"]
    assert workflow["summary"]["visible_case_count"] == 1
    assert workflow["summary"]["excluded_case_count"] == 0
    assert workflow["summary"]["path_denominator"] == 1
    assert workflow["summary"]["activity_denominator"] == 3
    assert workflow["summary"]["transition_denominator"] == 2
    assert workflow["summary"]["path_denominator_label"] == "cases in evaluation log"
    assert workflow["visible_case_count"] == 1
    assert workflow["excluded_case_count"] == 0
    assert workflow["path_denominator"] == 1
    assert workflow["activity_denominator"] == 3
    assert workflow["renderer_role"] == "conformance_explorer"
    assert workflow["process_map_payload"]["renderer_role"] == "conformance_explorer"
    assert workflow["process_map_payload"]["schema_version"] == 1
    assert workflow["process_map_payload"]["map_kind"] == "workflow_conformance"
    assert workflow["process_map_payload"]["selection_context"]["renderer_role"] == "conformance_explorer"
    assert workflow["process_map_payload"]["kpi_rows"][0]["key"] == "visible_case_count"
    assert workflow["process_map_payload"]["denominators"] == {
        "visible_case_count": 1,
        "excluded_case_count": 0,
        "path_denominator": 1,
        "activity_denominator": 3,
        "transition_denominator": 2,
    }
    assert set(workflow["nodes"]["path_denominator"]) == {1}
    assert set(workflow["nodes"]["activity_denominator"]) == {3}
    assert set(workflow["nodes"]["coverage_pct"]) == {100.0}
    assert set(workflow["nodes"]["activity_pct"].round(1)) == {33.3}
    assert set(workflow["edges"]["share_pct"]) == {50.0}
    assert workflow["trace_profiles"].iloc[0]["case_id"] == "case-001"
    assert set(workflow["edges"]["edge_uid"]).issubset(set(workflow["trace_profiles"].iloc[0]["edge_uids"]))
    assert "raw-case-identifier-001" not in workflow["trace_profiles"].to_string()
    assert "raw-case-identifier-001" not in workflow["nodes"].to_string()
    assert "raw-case-identifier-001" not in workflow["edges"].to_string()


def test_build_conformance_workspace_payload_derives_node_level_alignment_mix() -> None:
    trace = Trace()
    trace.attributes["concept:name"] = "case-1"
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace.append({"concept:name": "FIT_return", "time:timestamp": pd.Timestamp("2024-01-05")})
    log = EventLog([trace])

    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Heuristics (Classic)": SimpleNamespace(
            algorithm="Heuristics Miner",
            variant="Classic",
            net=fake_net,
            num_transitions=3,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Heuristics (Classic)": {
            "precision": 1.0,
            "summary": {
                "alignment_fitness": {"log_fitness": 1.0},
                "token_fitness": {"log_fitness": 1.0},
            },
            "alignments": {
                "aligned_traces": [
                    {
                        "fitness": 0.75,
                        "cost": 2.0,
                        "alignment": [
                            ("Invitation_mail", "Invitation_mail"),
                            ("FIT_mail", "FIT_mail"),
                            ("FIT_return", ">>"),
                            (">>", "PCC_observation"),
                        ],
                    }
                ]
            },
            "token": {"token_results": [{"trace_fitness": 0.75, "missing_tokens": 1, "remaining_tokens": 1}]},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    nodes = payload["workflow"]["nodes"].set_index("activity")
    invitation = nodes.loc["invitation"]
    fit_mail = nodes.loc["fit_mail"]
    fit_return = nodes.loc["fit_return"]
    pcc_observation = nodes.loc["pcc_observation"]

    assert invitation["sync_cases"] == 1
    assert invitation["sync_pct"] == 100.0
    assert fit_mail["sync_cases"] == 1
    assert fit_mail["sync_pct"] == 100.0
    assert fit_return["log_move_cases"] == 1
    assert fit_return["log_move_pct"] == 100.0
    assert fit_return["branch_role"] == "mainline"
    assert pcc_observation["model_move_cases"] == 1
    assert pcc_observation["model_move_pct"] == 100.0


def test_build_conformance_workspace_payload_humanizes_unmapped_activity_labels() -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "Admin_review", "time:timestamp": pd.Timestamp("2024-01-02")})
    log = EventLog([trace])

    fake_net = SimpleNamespace(
        transitions=[object(), object()],
        places=[_fake_place(1, 1), _fake_place(1, 1)],
        arcs=[object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=2,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": []},
            "token": {"token_results": []},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    nodes = payload["workflow"]["nodes"]
    edges = payload["workflow"]["edges"]
    assert "Admin review" in set(nodes["display_name"].tolist())
    assert "Invitation → Admin review" in set(edges["business_label"].tolist())


def test_build_conformance_workspace_payload_uses_processed_case_denominators() -> None:
    skipped_trace = Trace()
    skipped_trace.append({"time:timestamp": pd.Timestamp("2024-01-01")})

    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})

    payload = build_conformance_workspace_payload(
        log=EventLog([skipped_trace, trace]),
        discovery_results={},
        conformance_results={},
        comparison_df=pd.DataFrame(),
    )

    workflow = payload["workflow"]
    assert workflow["summary"]["visible_case_count"] == 1
    assert workflow["summary"]["excluded_case_count"] == 1
    assert workflow["summary"]["path_denominator"] == 1
    assert workflow["summary"]["events_covered"] == 2
    assert workflow["summary"]["dominant_path_share"] == 100.0
    assert set(workflow["nodes"]["path_denominator"]) == {1}


def test_build_conformance_workspace_payload_sorts_trace_events_for_timing() -> None:
    trace = Trace()
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})

    payload = build_conformance_workspace_payload(
        log=EventLog([trace]),
        discovery_results={},
        conformance_results={},
        comparison_df=pd.DataFrame(),
    )

    workflow = payload["workflow"]
    assert workflow["summary"]["median_throughput_days"] == 1.0
    assert workflow["edges"].iloc[0]["business_label"] == "Invitation → FIT mail"


def test_build_conformance_workspace_payload_fallback_mix_uses_cases_not_occurrences() -> None:
    trace = Trace()
    trace.append({"concept:name": "Custom_activity", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "Custom_activity", "time:timestamp": pd.Timestamp("2024-01-02")})

    payload = build_conformance_workspace_payload(
        log=EventLog([trace]),
        discovery_results={},
        conformance_results={},
        comparison_df=pd.DataFrame(),
    )

    node = payload["workflow"]["nodes"].iloc[0]
    assert node["cases"] == 1
    assert node["occurrences"] == 2
    assert node["conformance_mix_total_cases"] == 1


def test_build_conformance_workspace_payload_merges_canonical_activity_labels() -> None:
    trace_a = Trace()
    trace_a.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace_a.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace_a.append({"concept:name": "Lab_result", "time:timestamp": pd.Timestamp("2024-01-05")})

    trace_b = Trace()
    trace_b.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace_b.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace_b.append({"concept:name": "Lab_return", "time:timestamp": pd.Timestamp("2024-01-04")})
    trace_b.append({"concept:name": "PCC_observation", "time:timestamp": pd.Timestamp("2024-01-06")})

    log = EventLog([trace_a, trace_b])

    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=3,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": [{"fitness": 0.75, "cost": 2.0}]},
            "token": {"token_results": [{"trace_fitness": 0.70, "missing_tokens": 1, "remaining_tokens": 0}]},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    nodes = payload["workflow"]["nodes"]
    lab_result_row = nodes.loc[nodes["activity"] == "lab_result"].iloc[0]
    pcc_row = nodes.loc[nodes["activity"] == "pcc_observation"].iloc[0]

    assert lab_result_row["display_name"] == "Lab result"
    assert lab_result_row["business_label"] == "Lab result"
    assert {"Lab_result", "Lab_return"}.issubset(set(lab_result_row["raw_activities"]))
    assert pcc_row["display_name"] == "PCC observation"


def test_build_conformance_workspace_payload_humanizes_extra_branch_labels() -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace.append({"concept:name": "FIT_return", "time:timestamp": pd.Timestamp("2024-01-03")})
    trace.append({"concept:name": "Lab_result", "time:timestamp": pd.Timestamp("2024-01-04")})
    trace.append({"concept:name": "Lab_return", "time:timestamp": pd.Timestamp("2024-01-05")})
    trace.append({"concept:name": "PCC_fwd", "time:timestamp": pd.Timestamp("2024-01-06")})
    trace.append({"concept:name": "PCC_observation", "time:timestamp": pd.Timestamp("2024-01-07")})
    log = EventLog([trace])

    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=3,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": []},
            "token": {"token_results": []},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    node_labels = set(payload["workflow"]["nodes"]["display_name"].astype(str))
    edge_labels = set(payload["workflow"]["edges"]["business_label"].astype(str))
    assert "Lab result" in node_labels
    assert "PCC observation" in node_labels
    assert "Lab return" not in node_labels
    assert "Lab result → PCC observation" in edge_labels


def test_build_conformance_workspace_payload_humanizes_unmapped_and_transition_labels() -> None:
    trace = Trace()
    trace.attributes["concept:name"] = "case-1"
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "Lab_return", "time:timestamp": pd.Timestamp("2024-01-02")})
    trace.append({"concept:name": "PCC_observation", "time:timestamp": pd.Timestamp("2024-01-03")})
    log = EventLog([trace])

    payload = build_conformance_workspace_payload(
        log=log,
        discovery_results={},
        conformance_results={},
        comparison_df=pd.DataFrame(),
    )

    nodes_df = payload["workflow"]["nodes"]
    edges_df = payload["workflow"]["edges"]

    assert "Lab result" in nodes_df["display_name"].tolist()
    assert "PCC observation" in nodes_df["display_name"].tolist()
    assert "Lab result → PCC observation" in edges_df["business_label"].tolist()


def test_build_conformance_workspace_payload_handles_empty_log() -> None:
    fake_net = SimpleNamespace(
        transitions=[object(), object(), object()],
        places=[_fake_place(1, 2), _fake_place(2, 1)],
        arcs=[object(), object(), object(), object()],
    )
    discovery_results = {
        "Inductive": SimpleNamespace(
            algorithm="Inductive Miner",
            variant="IMf",
            net=fake_net,
            num_transitions=3,
            discovery_time_s=0.42,
        )
    }
    conformance_results = {
        "Inductive": {
            "precision": None,
            "summary": {
                "alignment_fitness": {"log_fitness": None},
                "token_fitness": {"log_fitness": None},
            },
            "alignments": {"aligned_traces": []},
            "token": {"token_results": []},
        }
    }
    comparison_df = build_model_comparison_dataframe(discovery_results, conformance_results)

    payload = build_conformance_workspace_payload(
        log=None,
        discovery_results=discovery_results,
        conformance_results=conformance_results,
        comparison_df=comparison_df,
    )

    assert payload["workflow"]["nodes"].empty
    assert payload["workflow"]["edges"].empty
    assert not payload["workflow"]["legend"].empty
    assert payload["has_workflow"] is False


def test_compute_filter_key_distinguishes_date_filter_modes() -> None:
    case_key = compute_filter_key("sig", "Invitation_mail", "case", date(2024, 1, 1), date(2024, 1, 31), 30)
    event_key = compute_filter_key("sig", "Invitation_mail", "event", date(2024, 1, 1), date(2024, 1, 31), 30)

    assert case_key != event_key
    assert "::case::" in case_key
    assert "::event::" in event_key


def test_run_discovery_pipeline_requires_first_event_workflow_gate(monkeypatch) -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    log = EventLog([trace])
    loaded_log = LoadedLog(log=log, input_name="demo.xes", log_signature="sig")
    state = get_crpm_state({})

    monkeypatch.setattr("crpm.app_runtime.filter_start_event", lambda value, selected_first: value)
    monkeypatch.setattr("crpm.app_runtime.filter_date_range", lambda value, start_dt, end_dt, mode: value)

    run_discovery_comparison_pipeline(
        state,
        loaded_log=loaded_log,
        start_filter="All",
        date_filter_mode="case",
        start_date=None,
        end_date=None,
        selected_algorithms=["Inductive (IMf)"],
        enable_train_test=False,
        random_seed=42,
        followup_days=30,
    )

    assert not state.results.analysis_complete
    assert state.results.discovery_results == {}
    assert state.results.filter_error_message is not None
    assert "First-event workflow gate" in state.results.filter_error_message
    assert state.results.filter_key == compute_filter_key("sig", None, "case", None, None, 30)
    assert state.results.workflow_cohort_policy == "first_event_direct"


def test_run_discovery_pipeline_reports_reversed_date_range() -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    loaded_log = LoadedLog(log=EventLog([trace]), input_name="demo.xes", log_signature="sig")
    state = get_crpm_state({})

    run_discovery_comparison_pipeline(
        state,
        loaded_log=loaded_log,
        start_filter="Invitation_mail",
        date_filter_mode="case",
        start_date=date(2024, 2, 1),
        end_date=date(2024, 1, 1),
        selected_algorithms=["Inductive (IMf)"],
        enable_train_test=False,
        random_seed=42,
    )

    assert not state.results.analysis_complete
    assert state.results.filter_error_message == "Start date must be on or before end date."
    assert state.results.filter_key == compute_filter_key(
        "sig",
        "Invitation_mail",
        "case",
        date(2024, 2, 1),
        date(2024, 1, 1),
        None,
    )


def test_resolve_xes_log_rejects_unsafe_xml_without_filename_leak() -> None:
    state = get_crpm_state({})
    unsafe_payload = b'<!DOCTYPE log [ <!ENTITY secret SYSTEM "file:///secret"> ]><log></log>'

    with pytest.raises(ValueError) as exc_info:
        resolve_xes_log(
            state,
            selected_path=None,
            uploaded_bytes=unsafe_payload,
            uploaded_name="sensitive_cohort_upload.xes",
        )

    message = str(exc_info.value)
    assert "XES validation failed" in message
    assert "sensitive_cohort_upload" not in message


def test_resolve_xes_log_rejects_unsafe_xml_after_large_prefix(tmp_path) -> None:
    state = get_crpm_state({})
    unsafe_file = tmp_path / "cohort.xes"
    unsafe_file.write_bytes(b" " * 70000 + b'<!DOCTYPE log [ <!ENTITY secret SYSTEM "file:///secret"> ]><log></log>')

    with pytest.raises(ValueError) as exc_info:
        resolve_xes_log(
            state,
            selected_path=str(unsafe_file),
            uploaded_bytes=None,
            uploaded_name=None,
        )

    message = str(exc_info.value)
    assert "unsafe XML declaration" in message
    assert str(unsafe_file) not in message


def test_resolve_xes_log_skips_full_xml_validation_for_unchanged_cached_file(tmp_path, monkeypatch) -> None:
    state = get_crpm_state({})
    xes_file = tmp_path / "cohort.xes"
    xes_file.write_text("<log></log>", encoding="utf-8")
    validation_calls = []

    monkeypatch.setattr(app_runtime, "_validate_xes_file", lambda path: validation_calls.append(path) or path.stat().st_size)
    monkeypatch.setattr(app_runtime, "load_log", lambda _path: EventLog())

    first = resolve_xes_log(state, selected_path=str(xes_file), uploaded_bytes=None, uploaded_name=None)
    second = resolve_xes_log(state, selected_path=str(xes_file), uploaded_bytes=None, uploaded_name=None)

    assert first.log is second.log
    assert validation_calls == [xes_file]


def test_resolve_xes_upload_skips_revalidation_after_cache_hit(monkeypatch) -> None:
    state = get_crpm_state({})
    raw = b"<log></log>"
    log = EventLog()
    validation_calls = []
    load_calls = []

    monkeypatch.setattr(app_runtime, "_validate_xes_bytes", lambda payload: validation_calls.append(payload))
    monkeypatch.setattr(app_runtime, "load_log", lambda path: load_calls.append(path) or log)

    first = resolve_xes_log(state, selected_path=None, uploaded_bytes=raw, uploaded_name="demo.xes")
    second = resolve_xes_log(state, selected_path=None, uploaded_bytes=raw, uploaded_name="demo.xes")

    assert first.log is second.log is log
    assert validation_calls == [raw]
    assert len(load_calls) == 1


def test_csv_preview_is_bounded_and_full_resolution_preserves_text_identifiers() -> None:
    state = get_crpm_state({})
    rows = ["case_id,activity,timestamp"]
    rows.extend(f"{index:04d},A,2024-01-01T00:00:00Z" for index in range(1, 206))
    raw = ("\n".join(rows) + "\n").encode("utf-8")

    preview = preview_csv_dataframe(state, raw)
    first, returned_preview = resolve_csv_log(
        state,
        uploaded_bytes=raw,
        uploaded_name="demo.csv",
        case_col="case_id",
        activity_col="activity",
        timestamp_col="timestamp",
    )
    second, _ = resolve_csv_log(
        state,
        uploaded_bytes=raw,
        uploaded_name="demo.csv",
        case_col="case_id",
        activity_col="activity",
        timestamp_col="timestamp",
    )

    assert len(preview.index) == app_runtime.CSV_PREVIEW_ROWS
    assert returned_preview is preview
    assert preview.iloc[0]["case_id"] == "0001"
    assert len(first.log) == 205
    assert first.log[0].attributes["concept:name"] == "0001"
    assert second.log is first.log
    assert all(len(frame.index) <= app_runtime.CSV_PREVIEW_ROWS for frame in state.caches["dataframe_cache"].values())


def test_csv_preview_reports_empty_input_as_validation_error() -> None:
    state = get_crpm_state({})

    with pytest.raises(ValueError, match="CSV validation failed"):
        preview_csv_dataframe(state, b"")


def test_compute_log_stats_normalizes_mixed_timezone_kinds() -> None:
    trace = Trace()
    trace.append({"concept:name": "A", "time:timestamp": pd.Timestamp("2024-01-01T10:00:00")})
    trace.append({"concept:name": "B", "time:timestamp": pd.Timestamp("2024-01-01T12:00:00+01:00")})

    stats = compute_log_stats(EventLog([trace]))

    assert stats["start"] == pd.Timestamp("2024-01-01T10:00:00")
    assert stats["end"] == pd.Timestamp("2024-01-01T11:00:00")


def test_get_log_profile_reuses_stats_and_first_events(monkeypatch) -> None:
    state = get_crpm_state({})
    loaded_log = LoadedLog(log=EventLog(), input_name="Local XES log", log_signature="xes::stable")
    calls = {"stats": 0, "first_events": 0}

    def fake_stats(_log):
        calls["stats"] += 1
        return {"traces": 12, "events": 44, "start": None, "end": None}

    def fake_first_events(_log):
        calls["first_events"] += 1
        return ["Invitation_mail"]

    monkeypatch.setattr(app_runtime, "compute_log_stats", fake_stats)
    monkeypatch.setattr(app_runtime, "first_event_names", fake_first_events)

    first = get_log_profile(state, loaded_log)
    second = get_log_profile(state, loaded_log)

    assert first == second
    assert calls == {"stats": 1, "first_events": 1}


def test_resolve_xes_log_rejects_unc_network_paths_without_touching_share() -> None:
    state = get_crpm_state({})

    with pytest.raises(ValueError) as exc_info:
        resolve_xes_log(
            state,
            selected_path=r"\\attacker.example\share\cohort.xes",
            uploaded_bytes=None,
            uploaded_name=None,
        )

    message = str(exc_info.value)
    assert "network paths are not allowed" in message
    assert "attacker" not in message


def test_list_safe_local_xes_files_rejects_unc_directory() -> None:
    assert list_safe_local_xes_files(r"\\attacker.example\share") == []


def test_delay_bucket_uses_p90_tail_for_severity() -> None:
    assert _delay_bucket([1.0, 1.0, 1.0, 1.2], overall_median=1.0) == "Low"
    assert _delay_bucket([1.0, 1.0, 1.0, 12.0], overall_median=1.0) == "High"


def test_run_discovery_pipeline_reuses_cached_conformance_workspace(monkeypatch) -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    log = EventLog([trace])
    loaded_log = LoadedLog(log=log, input_name="demo.xes", log_signature="sig")
    state = get_crpm_state({})
    call_counter = {"workspace": 0}

    monkeypatch.setattr("crpm.app_runtime.filter_start_event", lambda value, selected_first: value)
    monkeypatch.setattr("crpm.app_runtime.filter_date_range", lambda value, start_dt, end_dt, mode: value)
    monkeypatch.setattr(
        "crpm.app_runtime.discover_all_algorithms",
        lambda current_log, selected_algorithms: {
            "Inductive (IMf)": SimpleNamespace(
                algorithm="Inductive Miner",
                variant="IMf",
                net=SimpleNamespace(transitions=[object()], places=[_fake_place(1, 1)], arcs=[object()]),
                initial_marking=SimpleNamespace(),
                final_marking=SimpleNamespace(),
                num_transitions=1,
                num_places=1,
                num_arcs=1,
                discovery_time_s=0.1,
            )
        },
    )
    monkeypatch.setattr(
        "crpm.app_runtime.compute_full_conformance",
        lambda *args, **kwargs: {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": []},
            "token": {"token_results": []},
        },
    )

    def _build_workspace(**kwargs):
        call_counter["workspace"] += 1
        return {
            "model_summary_df": pd.DataFrame([{"model": "Inductive (IMf)"}]),
            "deviation_summary_df": pd.DataFrame(),
            "trace_deviation_df": pd.DataFrame(),
            "workflow": {"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()},
            "has_workflow": False,
        }

    monkeypatch.setattr("crpm.app_runtime.build_conformance_workspace_payload", _build_workspace)

    for _ in range(2):
        run_discovery_comparison_pipeline(
            state,
            loaded_log=loaded_log,
            start_filter="Invitation_mail",
            date_filter_mode="case",
            start_date=None,
            end_date=None,
            selected_algorithms=["Inductive (IMf)"],
            enable_train_test=False,
            random_seed=42,
            followup_days=None,
        )

    assert state.results.analysis_complete
    assert call_counter["workspace"] == 1
    assert state.results.analysis_summary["cases"] == 1
    assert state.results.analysis_summary["events"] == 2
    assert state.results.analysis_summary["model_count"] == 1
    assert state.results.denominator_registry["case_count"] == 1
    assert state.results.log_quality["summary"]["quality_status"] == "critical"
    assert state.results.run_manifest["run"]["workflow_cohort_policy"] == "first_event_direct"
    assert "source_signature_sha1" in state.results.run_manifest["input"]
    assert state.results.analysis_summary["preprocessing_impact"]["source_cases"] == 1
    assert state.results.run_manifest["preprocessing_impact"]["evaluation_cases"] == 1
    assert "loop_rework_metrics" in state.results.analysis_summary
    assert "model_quality_matrix_summary" in state.results.analysis_summary
    assert "cohort_lenses" in state.results.analysis_summary
    assert "time_series_monitoring" in state.results.analysis_summary
    assert "analytics_depth" in state.results.run_manifest
    assert "cohort_lenses_summary" in state.results.run_manifest["analytics_depth"]
    assert "cache_telemetry" in state.results.analysis_summary
    assert state.results.analysis_summary["cache_telemetry"]["summary"]["total_entries"] >= 1
    assert state.results.run_manifest["observability"]["cache_telemetry"]["summary"]["cache_count"] >= 1


def test_run_discovery_pipeline_uses_semantic_profile_in_quality_cache(monkeypatch) -> None:
    trace = Trace()
    trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
    trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
    log = EventLog([trace])
    loaded_log = LoadedLog(log=log, input_name="screening_conformance_demo.xes", log_signature="sig")
    state = get_crpm_state({})
    profiles = []

    monkeypatch.setattr("crpm.app_runtime.filter_start_event", lambda value, selected_first: value)
    monkeypatch.setattr("crpm.app_runtime.filter_date_range", lambda value, start_dt, end_dt, mode: value)
    monkeypatch.setattr(
        "crpm.app_runtime.discover_all_algorithms",
        lambda current_log, selected_algorithms: {
            "Inductive (IMf)": SimpleNamespace(
                algorithm="Inductive Miner",
                variant="IMf",
                net=SimpleNamespace(transitions=[object()], places=[_fake_place(1, 1)], arcs=[object()]),
                initial_marking=SimpleNamespace(),
                final_marking=SimpleNamespace(),
                num_transitions=1,
                num_places=1,
                num_arcs=1,
                discovery_time_s=0.1,
            )
        },
    )
    monkeypatch.setattr(
        "crpm.app_runtime.compute_full_conformance",
        lambda *args, **kwargs: {
            "precision": 0.88,
            "summary": {"alignment_fitness": {"log_fitness": 0.91}, "token_fitness": {"log_fitness": 0.89}},
            "alignments": {"aligned_traces": []},
        },
    )
    monkeypatch.setattr(
        "crpm.app_runtime.build_conformance_workspace_payload",
        lambda **kwargs: {
            "model_summary_df": pd.DataFrame(),
            "deviation_summary_df": pd.DataFrame(),
            "trace_deviation_df": pd.DataFrame(),
            "workflow": {"nodes": pd.DataFrame(), "edges": pd.DataFrame(), "legend": pd.DataFrame()},
            "has_workflow": False,
        },
    )

    def _quality(current_log, *, semantic_profile):
        profiles.append(semantic_profile)
        return {"summary": {"quality_status": "ok", "semantic_profile": semantic_profile}, "issues": []}

    monkeypatch.setattr("crpm.app_runtime.compute_event_log_quality", _quality)

    run_discovery_comparison_pipeline(
        state,
        loaded_log=loaded_log,
        start_filter="Invitation_mail",
        date_filter_mode="case",
        start_date=None,
        end_date=None,
        selected_algorithms=["Inductive (IMf)"],
        enable_train_test=False,
        random_seed=42,
        followup_days=None,
    )

    assert profiles == ["ccr_screening"]
    assert any("ccr_screening::quality-v1" in key for key in state.caches["log_quality_cache"])


def test_train_test_workspace_uses_evaluation_log_and_seeded_cache(monkeypatch) -> None:
    traces = []
    for case_id in ["case-a", "case-b", "case-c", "case-d"]:
        trace = Trace(attributes={"concept:name": case_id})
        trace.append({"concept:name": "Invitation_mail", "time:timestamp": pd.Timestamp("2024-01-01")})
        trace.append({"concept:name": "FIT_mail", "time:timestamp": pd.Timestamp("2024-01-02")})
        traces.append(trace)
    log = EventLog(traces)
    loaded_log = LoadedLog(log=log, input_name="demo.xes", log_signature="sig")
    state = get_crpm_state({})
    conformance_calls = {"count": 0}
    workspace_cases = []

    def _split(current_log, train_ratio, random_seed):
        train_log = EventLog([current_log[0], current_log[1]])
        test_index = 2 if random_seed == 1 else 3
        test_log = EventLog([current_log[test_index]])
        return train_log, test_log, {"random_seed": random_seed}

    monkeypatch.setattr("crpm.app_runtime.filter_start_event", lambda value, selected_first: value)
    monkeypatch.setattr("crpm.app_runtime.filter_date_range", lambda value, start_dt, end_dt, mode: value)
    monkeypatch.setattr("crpm.app_runtime.split_log_random", _split)
    monkeypatch.setattr(
        "crpm.app_runtime.discover_all_algorithms",
        lambda current_log, selected_algorithms: {
            "Inductive (IMf)": SimpleNamespace(
                algorithm="Inductive Miner",
                variant="IMf",
                net=SimpleNamespace(transitions=[object()], places=[_fake_place(1, 1)], arcs=[object()]),
                initial_marking=SimpleNamespace(),
                final_marking=SimpleNamespace(),
                num_transitions=1,
                num_places=1,
                num_arcs=1,
                discovery_time_s=0.1,
            )
        },
    )

    def _compute_conformance(*args, **kwargs):
        conformance_calls["count"] += 1
        return {
            "precision": 0.88,
            "summary": {
                "alignment_fitness": {"log_fitness": 0.91},
                "token_fitness": {"log_fitness": 0.89},
            },
            "alignments": {"aligned_traces": []},
            "token": {"token_results": []},
        }

    def _build_workspace(**kwargs):
        workspace_cases.append([trace.attributes["concept:name"] for trace in kwargs["log"]])
        return {
            "model_summary_df": pd.DataFrame([{"model": "Inductive (IMf)"}]),
            "deviation_summary_df": pd.DataFrame(),
            "trace_deviation_df": pd.DataFrame(),
            "workflow": {
                "nodes": pd.DataFrame(),
                "edges": pd.DataFrame(),
                "legend": pd.DataFrame(),
                "summary": {"cases_covered": len(kwargs["log"])},
            },
            "has_workflow": False,
        }

    monkeypatch.setattr("crpm.app_runtime.compute_full_conformance", _compute_conformance)
    monkeypatch.setattr("crpm.app_runtime.build_conformance_workspace_payload", _build_workspace)

    for seed in [1, 2]:
        run_discovery_comparison_pipeline(
            state,
            loaded_log=loaded_log,
            start_filter="Invitation_mail",
            date_filter_mode="case",
            start_date=None,
            end_date=None,
            selected_algorithms=["Inductive (IMf)"],
            enable_train_test=True,
            random_seed=seed,
            followup_days=None,
        )

    assert conformance_calls["count"] == 2
    assert workspace_cases == [["case-c"], ["case-d"]]
    assert state.results.analysis_summary["evaluation_cases"] == 1
