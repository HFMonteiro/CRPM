"""Reproducibility manifest helpers for CRPM runs."""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import UTC, date, datetime
from importlib import metadata
from pathlib import PurePosixPath
from typing import Any, Mapping

import pandas as pd

from crpm import __version__
from crpm.governance import build_governance_context


def build_run_manifest(
    *,
    input_name: str | None,
    log_signature: str | None,
    source_metadata: Mapping[str, Any],
    analysis_signature: str,
    filter_key: str,
    workflow_cohort_policy: str,
    start_filter: str,
    date_filter_mode: str,
    start_date: date | None,
    end_date: date | None,
    selected_algorithms: list[str],
    enable_train_test: bool,
    random_seed: int,
    followup_days: int | None,
    split_info: Mapping[str, Any],
    analysis_summary: Mapping[str, Any],
    denominator_registry: Mapping[str, Any],
    log_quality: Mapping[str, Any],
    stage_timings: Mapping[str, float],
    comparison_df: pd.DataFrame,
    preprocessing_impact: Mapping[str, Any] | None = None,
    analytics_depth: Mapping[str, Any] | None = None,
    governance_context: Mapping[str, Any] | None = None,
    cache_telemetry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe, privacy-preserving run manifest."""

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "versions": _versions(),
        "input": {
            "display_name": _redact_label(input_name),
            "source_metadata": sanitize_source_metadata(source_metadata),
            "source_signature_sha1": _digest(log_signature),
        },
        "run": {
            "analysis_signature": analysis_signature,
            "filter_key_sha1": _digest(filter_key),
            "workflow_cohort_policy": workflow_cohort_policy,
            "first_event_direct": workflow_cohort_policy == "first_event_direct",
        },
        "filters": {
            "start_filter": start_filter,
            "date_filter_mode": date_filter_mode,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "followup_days": followup_days,
        },
        "algorithms": {
            "selected": list(selected_algorithms),
            "comparison": _comparison_rows(comparison_df),
        },
        "split": {
            "enabled": bool(enable_train_test),
            "random_seed": int(random_seed),
            "details": _json_safe(dict(split_info)),
        },
        "governance": _json_safe(dict(governance_context or build_governance_context())),
        "denominators": _json_safe(dict(denominator_registry)),
        "preprocessing_impact": _json_safe(dict(preprocessing_impact or {})),
        "analytics_depth": _json_safe(dict(analytics_depth or {})),
        "observability": {
            "cache_telemetry": _json_safe(dict(cache_telemetry or {})),
        },
        "log_quality": _json_safe(_quality_summary(log_quality)),
        "summary": _json_safe(dict(analysis_summary)),
        "stage_timings_s": _json_safe(dict(stage_timings)),
    }
    return _json_safe(manifest)


def manifest_to_json(manifest: Mapping[str, Any]) -> str:
    """Serialize a run manifest with stable key ordering."""

    return json.dumps(_json_safe(dict(manifest)), indent=2, sort_keys=True)


def sanitize_source_metadata(source_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return safe source metadata without local paths or uploaded names."""

    safe = {
        "source_type": source_metadata.get("source_type"),
        "source_kind": source_metadata.get("source_kind"),
        "display_name": _redact_label(source_metadata.get("display_name")),
        "size_bytes": source_metadata.get("size_bytes"),
        "validation_status": source_metadata.get("validation_status"),
    }
    return {key: _json_safe(value) for key, value in safe.items() if value is not None}


def _versions() -> dict[str, str | None]:
    return {
        "crpm": __version__,
        "python": platform.python_version(),
        "pm4py": _package_version("pm4py"),
        "pandas": _package_version("pandas"),
        "numpy": _package_version("numpy"),
    }


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _comparison_rows(comparison_df: pd.DataFrame) -> list[dict[str, Any]]:
    if not isinstance(comparison_df, pd.DataFrame) or comparison_df.empty:
        return []
    allowed = (
        "model_name",
        "algorithm",
        "variant",
        "parameter_profile_name",
        "pm4py_variant",
        "alignment_fitness",
        "precision",
        "num_transitions",
        "num_places",
        "num_arcs",
        "quality_score",
        "quality_band",
        "simplicity_proxy",
        "generalization_proxy",
        "discovery_time_s",
    )
    existing = [column for column in allowed if column in comparison_df.columns]
    return [_json_safe(row) for row in comparison_df[existing].to_dict(orient="records")]


def _quality_summary(log_quality: Mapping[str, Any]) -> dict[str, Any]:
    summary = log_quality.get("summary", {}) if isinstance(log_quality, Mapping) else {}
    issues = log_quality.get("issues", []) if isinstance(log_quality, Mapping) else []
    return {
        "summary": dict(summary) if isinstance(summary, Mapping) else {},
        "issues": list(issues)[:10] if isinstance(issues, list) else [],
    }


def _digest(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()


def _redact_label(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("\\", "/").rstrip("/")
    looks_like_path = "\\" in text or (len(text) > 2 and text[1] == ":" and text[2] in {"/", "\\"}) or normalized.startswith("/")
    if looks_like_path:
        return PurePosixPath(normalized).name or "redacted"
    return text[:120]


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return [_json_safe(row) for row in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, int | float | str | bool) or value is None:
        return value
    return str(value)
