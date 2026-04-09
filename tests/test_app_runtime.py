from types import SimpleNamespace
from datetime import date

import pandas as pd
from pm4py.objects.log.obj import EventLog, Trace

from crpm.app_runtime import (
    LoadedLog,
    _delay_bucket,
    build_conformance_workspace_payload,
    build_model_comparison_dataframe,
    compute_filter_key,
    run_discovery_comparison_pipeline,
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
    assert comparison_df.iloc[0]["quadrant"]


def test_build_conformance_workspace_payload_creates_structured_tables() -> None:
    trace = Trace()
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
    assert not payload["workflow"]["nodes"].empty
    assert not payload["workflow"]["edges"].empty
    assert {
        "business_label",
        "branch_role",
        "lane",
        "coverage_group",
        "neighbor_ids",
        "node_type",
        "branch_family",
        "related_variant_ids",
        "selection_summary",
    }.issubset(payload["workflow"]["nodes"].columns)
    assert {
        "edge_id",
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
    assert {"deviation_share", "log_deviation_share", "model_deviation_share"}.issubset(payload["workflow"]["summary"].keys())


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


def test_run_discovery_pipeline_requires_explicit_followup_anchor(monkeypatch) -> None:
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
    assert "explicit screening anchor" in state.results.filter_error_message
    assert state.results.filter_key == compute_filter_key("sig", None, "case", None, None, 30)


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
