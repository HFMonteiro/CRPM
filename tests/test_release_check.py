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


def test_build_package_falls_back_when_build_module_is_missing(monkeypatch, tmp_path) -> None:
    calls: list[list[str]] = []

    def fake_run_command(name: str, command: list[str], cwd):
        calls.append(command)
        if command == ["python", "-m", "build"]:
            return release_check.CheckResult("package-build", False, "python: No module named build")
        return release_check.CheckResult("package-build", True, "fallback ok")

    monkeypatch.setattr(release_check.sys, "executable", "python")
    monkeypatch.setattr(release_check, "_run_command", fake_run_command)

    result = release_check._build_package(tmp_path)

    assert result.ok
    assert "pip" in calls[1]
    assert "wheel" in calls[1]
