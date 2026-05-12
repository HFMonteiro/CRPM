"""Serializable analysis configuration for headless CRPM runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from crpm.app_state import WORKFLOW_COHORT_FIRST_EVENT_DIRECT, WORKFLOW_COHORT_POLICIES
from crpm.discovery import AVAILABLE_ALGORITHMS
from crpm.governance import get_domain_template, get_privacy_mode


@dataclass(frozen=True)
class SourceConfig:
    type: str
    path: str
    case_col: str | None = None
    activity_col: str | None = None
    timestamp_col: str | None = None


@dataclass(frozen=True)
class AnalysisConfig:
    workflow_cohort_policy: str = WORKFLOW_COHORT_FIRST_EVENT_DIRECT
    start_filter: str = "All"
    date_filter_mode: str = "case"
    start_date: date | None = None
    end_date: date | None = None
    selected_algorithms: tuple[str, ...] = ("Heuristics (Classic)", "Inductive (IMf)")
    enable_train_test: bool = False
    random_seed: int = 42
    followup_days: int | None = None


@dataclass(frozen=True)
class OutputConfig:
    directory: str | None = None


@dataclass(frozen=True)
class GovernanceConfig:
    privacy_mode: str = "restricted_health_adjacent"
    domain_template: str = "ccr_screening"


@dataclass(frozen=True)
class CRPMAnalysisConfig:
    source: SourceConfig
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)


def load_analysis_config(path: str | Path) -> CRPMAnalysisConfig:
    """Load and validate a CRPM analysis config from JSON or YAML."""

    config_path = Path(path)
    payload = _load_mapping(config_path)
    return validate_analysis_config(payload)


def validate_analysis_config(payload: Mapping[str, Any]) -> CRPMAnalysisConfig:
    """Validate a JSON-safe configuration mapping."""

    source_payload = payload.get("source")
    if not isinstance(source_payload, Mapping):
        raise ValueError("Config requires a `source` object.")
    source_type = str(source_payload.get("type") or "").strip().lower()
    if source_type not in {"xes", "csv"}:
        raise ValueError("source.type must be `xes` or `csv`.")
    source_path = str(source_payload.get("path") or "").strip()
    if not source_path:
        raise ValueError("source.path is required.")
    source = SourceConfig(
        type=source_type,
        path=source_path,
        case_col=_optional_str(source_payload.get("case_col")),
        activity_col=_optional_str(source_payload.get("activity_col")),
        timestamp_col=_optional_str(source_payload.get("timestamp_col")),
    )
    if source.type == "csv" and not (source.case_col and source.activity_col and source.timestamp_col):
        raise ValueError("CSV source requires case_col, activity_col, and timestamp_col.")

    analysis_payload = payload.get("analysis", {})
    if analysis_payload is None:
        analysis_payload = {}
    if not isinstance(analysis_payload, Mapping):
        raise ValueError("analysis must be an object when provided.")
    workflow_policy = str(analysis_payload.get("workflow_cohort_policy") or WORKFLOW_COHORT_FIRST_EVENT_DIRECT)
    if workflow_policy not in WORKFLOW_COHORT_POLICIES:
        raise ValueError("workflow_cohort_policy is not supported.")
    date_filter_mode = str(analysis_payload.get("date_filter_mode") or "case")
    if date_filter_mode not in {"case", "event"}:
        raise ValueError("date_filter_mode must be `case` or `event`.")
    selected_algorithms = tuple(analysis_payload.get("selected_algorithms") or ("Heuristics (Classic)", "Inductive (IMf)"))
    unknown_algorithms = [name for name in selected_algorithms if name not in AVAILABLE_ALGORITHMS]
    if unknown_algorithms:
        raise ValueError(f"Unknown discovery algorithms: {', '.join(str(name) for name in unknown_algorithms)}")
    analysis = AnalysisConfig(
        workflow_cohort_policy=workflow_policy,
        start_filter=str(analysis_payload.get("start_filter") or "All"),
        date_filter_mode=date_filter_mode,
        start_date=_parse_date(analysis_payload.get("start_date")),
        end_date=_parse_date(analysis_payload.get("end_date")),
        selected_algorithms=tuple(str(name) for name in selected_algorithms),
        enable_train_test=bool(analysis_payload.get("enable_train_test", False)),
        random_seed=int(analysis_payload.get("random_seed", 42)),
        followup_days=_optional_int(analysis_payload.get("followup_days")),
    )

    output_payload = payload.get("output", {})
    if output_payload is None:
        output_payload = {}
    if not isinstance(output_payload, Mapping):
        raise ValueError("output must be an object when provided.")
    output = OutputConfig(directory=_optional_str(output_payload.get("directory")))

    governance_payload = payload.get("governance", {})
    if governance_payload is None:
        governance_payload = {}
    if not isinstance(governance_payload, Mapping):
        raise ValueError("governance must be an object when provided.")
    privacy_mode = str(governance_payload.get("privacy_mode") or "restricted_health_adjacent")
    domain_template = str(governance_payload.get("domain_template") or "ccr_screening")
    get_privacy_mode(privacy_mode)
    get_domain_template(domain_template)
    governance = GovernanceConfig(privacy_mode=privacy_mode, domain_template=domain_template)
    return CRPMAnalysisConfig(source=source, analysis=analysis, output=output, governance=governance)


def _load_mapping(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise ValueError("YAML config requires PyYAML; use JSON or install PyYAML.") from exc
        payload = yaml.safe_load(text)
    else:
        raise ValueError("Config file must be JSON, YAML, or YML.")
    if not isinstance(payload, Mapping):
        raise ValueError("Config root must be an object.")
    return payload


def _parse_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


__all__ = [
    "AnalysisConfig",
    "CRPMAnalysisConfig",
    "GovernanceConfig",
    "OutputConfig",
    "SourceConfig",
    "load_analysis_config",
    "validate_analysis_config",
]
