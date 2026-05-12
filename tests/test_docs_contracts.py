from __future__ import annotations

import re
from pathlib import Path

from crpm.pages import PAGE_REGISTRY

ROOT = Path(__file__).resolve().parents[1]


def test_readme_screenshot_paths_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    screenshot_paths = re.findall(r"\]\((docs/screenshots/[^)]+)\)", readme)

    assert screenshot_paths
    for relative_path in screenshot_paths:
        assert (ROOT / relative_path).is_file(), relative_path


def test_readme_mentions_canonical_page_names() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for page_name in PAGE_REGISTRY:
        assert page_name in readme


def test_readme_documents_data_quality_and_synthetic_cli() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Data Quality and Timestamp Policy" in readme
    assert "semantic profile" in readme
    assert "timezone" in readme
    assert "CSV" in readme
    assert "crpm-generate-screening-demo" in readme
    assert "docs/governance.md" in readme


def test_governance_doc_records_non_clinical_scope_and_privacy_modes() -> None:
    governance = (ROOT / "docs" / "governance.md").read_text(encoding="utf-8")

    assert "not a clinical decision-support system" in governance
    assert "restricted_health_adjacent" in governance
    assert "ccr_screening" in governance


def test_readme_documents_future_readiness_without_new_required_dependencies() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "DuckDB/Parquet" in readme
    assert "optional future staging track" in readme
    assert "OCEL 2.0" in readme
    assert "experimental future track" in readme
    assert '"duckdb' not in pyproject.lower()
    assert '"pyarrow' not in pyproject.lower()


def test_agents_md_stays_local_only() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert re.search(r"(?m)^AGENTS\.md$", gitignore)
