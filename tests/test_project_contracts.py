from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_research_contract_records_first_event_direct_workflow_rule() -> None:
    contract = (REPO_ROOT / "docs" / "research_contract.md").read_text(encoding="utf-8")

    assert "first-event direct workflow gate" in contract.lower()
    assert "`workflow_cohort_policy` defaults to `first_event_direct`" in contract
    assert "Explicit anchor semantics are allowed only as secondary analysis" in contract


def test_ci_runs_on_push_and_pull_request_with_security_gates() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert '_CRPM_v3"' in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "ruff check crpm tests app.py" in workflow
    assert "black --check crpm tests app.py" in workflow
    assert "python -m build" in workflow
    assert "build==1.5.0" in workflow
    assert "pip-audit" in workflow
    assert "pip-audit==2.10.0" in workflow
    assert "crpm/py.typed" in workflow
    assert "__pycache__/" in workflow


def test_package_declares_pep561_typing_marker() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (REPO_ROOT / "crpm" / "py.typed").is_file()
    assert 'crpm = ["assets/*", "py.typed"]' in pyproject
