from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from crpm import preflight


def _workspace_root() -> Path:
    root = Path("outputs") / f"preflight-test-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_validate_runtime_environment_reports_ok_when_everything_is_present(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_module_exists", lambda _name: True)
    monkeypatch.setattr(preflight, "_check_graphviz_binary", lambda: ("dot", "Graphviz version 1.0", None))

    repo_root = _workspace_root()
    try:
        for relative_path in preflight.REQUIRED_SAMPLE_FILES:
            path = repo_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample", encoding="utf-8")

        report = preflight.validate_runtime_environment(repo_root=repo_root)
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)

    assert report.ok is True
    assert report.missing_python_modules == ()
    assert report.graphviz_executable == "dot"
    assert report.missing_sample_files == ()


def test_validate_runtime_environment_flags_missing_workflow_dependency(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_module_exists", lambda name: name != "streamlit_cytoscape")
    monkeypatch.setattr(preflight, "_check_graphviz_binary", lambda: ("dot", "Graphviz version 1.0", None))

    repo_root = _workspace_root()
    try:
        for relative_path in preflight.REQUIRED_SAMPLE_FILES:
            path = repo_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample", encoding="utf-8")

        report = preflight.validate_runtime_environment(repo_root=repo_root)
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)

    assert report.ok is False
    assert "streamlit_cytoscape" in report.missing_python_modules


def test_validate_runtime_environment_flags_missing_graphviz(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_module_exists", lambda _name: True)
    monkeypatch.setattr(preflight, "_check_graphviz_binary", lambda: (None, None, None))

    repo_root = _workspace_root()
    try:
        for relative_path in preflight.REQUIRED_SAMPLE_FILES:
            path = repo_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample", encoding="utf-8")

        report = preflight.validate_runtime_environment(repo_root=repo_root)
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)

    messages = preflight.format_preflight_messages(report)

    assert report.ok is False
    assert any("Graphviz `dot` was not found" in line for line in messages)


def test_validate_runtime_environment_flags_missing_sample_data(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_module_exists", lambda _name: True)
    monkeypatch.setattr(preflight, "_check_graphviz_binary", lambda: ("dot", "Graphviz version 1.0", None))

    repo_root = _workspace_root()
    try:
        report = preflight.validate_runtime_environment(repo_root=repo_root)
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)

    assert report.ok is False
    assert set(report.missing_sample_files) == {str(path) for path in preflight.REQUIRED_SAMPLE_FILES}
