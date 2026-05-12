from types import SimpleNamespace

from crpm import release_check


def test_release_check_quick_composes_version_and_preflight(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text('version = "0.3.0"\n', encoding="utf-8")
    monkeypatch.setattr(
        release_check,
        "validate_runtime_environment",
        lambda repo_root: SimpleNamespace(ok=True, graphviz_version="dot - graphviz", missing_python_modules=()),
    )

    results = release_check.run_release_check(repo_root=tmp_path, quick=True)

    assert [result.name for result in results] == ["version-contract", "runtime-preflight"]
    assert all(result.ok for result in results)
