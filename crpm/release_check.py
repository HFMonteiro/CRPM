"""Local release checklist runner for CRPM."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from crpm import __version__
from crpm.preflight import format_preflight_messages, validate_runtime_environment


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def run_release_check(
    *,
    repo_root: Path | None = None,
    quick: bool = False,
    skip_tests: bool = False,
    skip_build: bool = False,
    skip_audit: bool = False,
) -> list[CheckResult]:
    """Run the public release checks that can execute locally."""

    root = repo_root or Path(__file__).resolve().parent.parent
    results: list[CheckResult] = []
    results.append(_check_versions(root))
    results.append(_check_preflight(root))

    if not quick and not skip_tests:
        results.append(_run_command("pytest", [sys.executable, "-m", "pytest", "-q"], root))
        results.append(_run_command("ruff", [sys.executable, "-m", "ruff", "check", "crpm", "tests", "app.py"], root))
        results.append(_run_command("black", [sys.executable, "-m", "black", "--check", "crpm", "tests", "app.py"], root))

    if not quick and not skip_build:
        results.append(_build_package(root))
        if results[-1].ok:
            results.append(_inspect_wheel(root))

    if not quick and not skip_audit:
        audit = _run_command("dependency-audit", [sys.executable, "-m", "pip_audit", "."], root)
        if "No module named pip_audit" in audit.detail:
            audit = CheckResult("dependency-audit", True, "pip-audit is not installed; audit skipped locally.")
        results.append(audit)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CRPM local release checks.")
    parser.add_argument("--quick", action="store_true", help="Run only version and runtime preflight checks.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest, Ruff, and Black checks.")
    parser.add_argument("--skip-build", action="store_true", help="Skip package build and artifact inspection.")
    parser.add_argument("--skip-audit", action="store_true", help="Skip dependency audit.")
    args = parser.parse_args(argv)

    results = run_release_check(
        quick=args.quick,
        skip_tests=args.skip_tests,
        skip_build=args.skip_build,
        skip_audit=args.skip_audit,
    )
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        if result.detail:
            print(result.detail.strip())
    return 0 if all(result.ok for result in results) else 1


def _check_versions(root: Path) -> CheckResult:
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8") if pyproject.exists() else ""
    expected = f'version = "{__version__}"'
    if expected not in text:
        return CheckResult("version-contract", False, "crpm.__version__ does not match pyproject.toml.")
    return CheckResult("version-contract", True, f"CRPM {__version__}")


def _check_preflight(root: Path) -> CheckResult:
    report = validate_runtime_environment(repo_root=root)
    if report.ok:
        return CheckResult("runtime-preflight", True, report.graphviz_version or "")
    return CheckResult("runtime-preflight", False, "\n".join(format_preflight_messages(report)))


def _run_command(name: str, command: list[str], cwd: Path) -> CheckResult:
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        return CheckResult(name, False, str(exc))
    detail = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return CheckResult(name, completed.returncode == 0, detail[-4000:])


def _build_package(root: Path) -> CheckResult:
    result = _run_command("package-build", [sys.executable, "-m", "build"], root)
    missing_build_module = "No module named build" in result.detail or "No module named build.__main__" in result.detail
    if result.ok or not missing_build_module:
        return result
    wheel_dir = root / "outputs" / "release_check_dist"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    fallback = _run_command(
        "package-build",
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheel_dir)],
        root,
    )
    if fallback.ok:
        return CheckResult("package-build", True, "Used pip wheel fallback because python -m build is unavailable.")
    return fallback


def _inspect_wheel(root: Path) -> CheckResult:
    wheels = sorted((root / "dist").glob("*.whl")) + sorted((root / "outputs" / "release_check_dist").glob("*.whl"))
    if not wheels:
        return CheckResult("package-artifact", False, "No wheel artifact found in dist/.")
    with zipfile.ZipFile(wheels[-1]) as wheel:
        names = set(wheel.namelist())
    if "crpm/assets/crpm_logo.png" not in names:
        return CheckResult("package-artifact", False, "Missing packaged CRPM logo asset.")
    if "crpm/py.typed" not in names:
        return CheckResult("package-artifact", False, "Missing packaged PEP 561 typing marker.")
    return CheckResult("package-artifact", True, wheels[-1].name)


if __name__ == "__main__":
    raise SystemExit(main())
