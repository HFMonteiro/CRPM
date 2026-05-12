from datetime import date, datetime

import pandas as pd

from crpm.run_manifest import build_run_manifest, manifest_to_json, sanitize_source_metadata


def test_run_manifest_is_json_safe_and_redacts_local_paths() -> None:
    manifest = build_run_manifest(
        input_name=r"C:\Analyst\Private\redacted_cohort.xes",
        log_signature=r"xes::C:\Analyst\Private\redacted_cohort.xes::123",
        source_metadata={
            "source_type": "XES",
            "source_kind": "local",
            "display_name": r"C:\Analyst\Private\redacted_cohort.xes",
            "size_bytes": 123,
            "validation_status": "validated:xes",
        },
        analysis_signature="analysis",
        filter_key=r"xes::C:\Analyst\Private\redacted_cohort.xes::filter",
        workflow_cohort_policy="first_event_direct",
        start_filter="Invitation",
        date_filter_mode="case",
        start_date=date(2024, 1, 1),
        end_date=None,
        selected_algorithms=["Inductive (IMf)"],
        enable_train_test=False,
        random_seed=42,
        followup_days=None,
        split_info={},
        analysis_summary={"period_start": datetime(2024, 1, 1), "cases": 1},
        denominator_registry={"case_count": 1},
        log_quality={"summary": {"quality_status": "ok"}, "issues": []},
        preprocessing_impact={"source_cases": 2, "filtered_cases": 1},
        analytics_depth={
            "loop_rework_summary": {"case_count": 1, "rework_cases_pct": 0.0},
            "model_quality_matrix_summary": {"best_quality_score": 0.9},
        },
        cache_telemetry={
            "summary": {"cache_count": 2, "total_entries": 1, "runtime_s": 0.1},
            "caches": [{"name": "filtered_cache", "entries": 1, "limit": 8}],
        },
        stage_timings={"filtering_s": 0.1},
        comparison_df=pd.DataFrame(
            [
                {
                    "model_name": "Inductive",
                    "precision": 0.9,
                    "parameter_profile_name": "inductive-noise-aware",
                    "pm4py_variant": "IMf",
                }
            ]
        ),
    )
    payload = manifest_to_json(manifest)

    assert manifest["input"]["display_name"] == "redacted_cohort.xes"
    assert "source_signature_sha1" in manifest["input"]
    assert r"C:\Analyst\Private" not in payload
    assert "filter_key_sha1" in payload
    assert "first_event_direct" in payload
    assert manifest["preprocessing_impact"]["source_cases"] == 2
    assert manifest["analytics_depth"]["model_quality_matrix_summary"]["best_quality_score"] == 0.9
    assert manifest["observability"]["cache_telemetry"]["summary"]["cache_count"] == 2
    assert manifest["observability"]["cache_telemetry"]["caches"][0]["name"] == "filtered_cache"
    assert manifest["algorithms"]["comparison"][0]["parameter_profile_name"] == "inductive-noise-aware"
    assert manifest["algorithms"]["comparison"][0]["pm4py_variant"] == "IMf"


def test_sanitize_source_metadata_drops_unexpected_fields() -> None:
    safe = sanitize_source_metadata({"display_name": "/tmp/cohort.xes", "secret": "raw-case-id", "validation_status": "ok"})

    assert safe["display_name"] == "cohort.xes"
    assert "secret" not in safe
