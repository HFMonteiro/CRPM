"""Headless CRPM batch-analysis entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

from crpm.app_runtime import LoadedLog, resolve_csv_log, resolve_xes_log, run_discovery_comparison_pipeline
from crpm.app_state import CRPMState, get_crpm_state
from crpm.config_schema import CRPMAnalysisConfig, load_analysis_config
from crpm.governance import build_governance_context
from crpm.run_manifest import manifest_to_json


def run_headless_analysis(config_path: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Run or validate a CRPM analysis config without launching Streamlit."""

    config = load_analysis_config(config_path)
    source_path = Path(config.source.path)
    if not source_path.exists():
        raise ValueError("Configured source path does not exist.")
    if dry_run:
        return {
            "status": "validated",
            "source": {
                "type": config.source.type,
                "display_name": _redact_path(source_path),
            },
            "analysis": _analysis_summary(config),
            "governance": _governance_summary(config),
        }

    state = get_crpm_state({})
    state.config.workflow_cohort_policy = config.analysis.workflow_cohort_policy
    loaded_log = _load_configured_log(state, config)
    analysis = config.analysis
    run_discovery_comparison_pipeline(
        state,
        loaded_log=loaded_log,
        start_filter=analysis.start_filter,
        date_filter_mode=analysis.date_filter_mode,
        start_date=analysis.start_date,
        end_date=analysis.end_date,
        selected_algorithms=list(analysis.selected_algorithms),
        enable_train_test=analysis.enable_train_test,
        random_seed=analysis.random_seed,
        followup_days=analysis.followup_days,
    )
    if not state.results.analysis_complete:
        message = state.results.filter_error_message or "Analysis did not complete for the configured filters."
        raise ValueError(message)

    state.results.run_manifest["governance"] = _governance_summary(config)
    manifest_path = None
    if config.output.directory:
        output_dir = Path(config.output.directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "crpm_run_manifest.json"
        manifest_path.write_text(manifest_to_json(state.results.run_manifest), encoding="utf-8")
    return {
        "status": "completed",
        "source": {
            "type": loaded_log.source_type.lower(),
            "display_name": _redact_path(source_path),
        },
        "analysis": _analysis_summary(config),
        "governance": _governance_summary(config),
        "manifest_path": str(manifest_path) if manifest_path else None,
        "case_count": state.results.case_count if hasattr(state.results, "case_count") else len(state.results.filtered_log or []),
        "event_count": sum(len(trace) for trace in state.results.filtered_log or []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CRPM analysis from a JSON/YAML config.")
    parser.add_argument("--config", required=True, help="Path to a CRPM analysis config file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and source without running process mining.")
    args = parser.parse_args(argv)
    result = run_headless_analysis(args.config, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _load_configured_log(state: CRPMState, config: CRPMAnalysisConfig) -> LoadedLog:
    source_path = Path(config.source.path)
    if config.source.type == "xes":
        return resolve_xes_log(
            state,
            selected_path=str(source_path),
            uploaded_bytes=None,
            uploaded_name=None,
        )
    loaded_log, _ = resolve_csv_log(
        state,
        uploaded_bytes=source_path.read_bytes(),
        uploaded_name=source_path.name,
        case_col=config.source.case_col,
        activity_col=config.source.activity_col,
        timestamp_col=config.source.timestamp_col,
    )
    return loaded_log


def _analysis_summary(config: CRPMAnalysisConfig) -> dict[str, Any]:
    analysis = config.analysis
    return {
        "workflow_cohort_policy": analysis.workflow_cohort_policy,
        "start_filter": analysis.start_filter,
        "date_filter_mode": analysis.date_filter_mode,
        "selected_algorithms": list(analysis.selected_algorithms),
        "enable_train_test": analysis.enable_train_test,
        "random_seed": analysis.random_seed,
        "followup_days": analysis.followup_days,
    }


def _governance_summary(config: CRPMAnalysisConfig) -> dict[str, Any]:
    return build_governance_context(
        privacy_mode=config.governance.privacy_mode,
        domain_template=config.governance.domain_template,
    )


def _redact_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/").rstrip("/")
    return PurePosixPath(normalized).name or "redacted"


if __name__ == "__main__":
    raise SystemExit(main())
