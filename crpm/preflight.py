"""Runtime preflight checks for the CRPM Streamlit entrypoint."""

from __future__ import annotations

import importlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PYTHON_MODULES = (
    "streamlit",
    "streamlit_cytoscape",
    "pandas",
    "pm4py",
    "plotly",
    "fpdf",
)

REQUIRED_SAMPLE_FILES = (
    Path("examples/running-example.xes"),
    Path("examples/screening_conformance_demo.xes"),
    Path("examples/screening_conformance_demo.csv"),
    Path("examples/idealized_petri_net.pnml"),
)


@dataclass(frozen=True)
class PreflightReport:
    """Collected runtime readiness information."""

    missing_python_modules: tuple[str, ...]
    graphviz_executable: str | None
    graphviz_version: str | None
    graphviz_error: str | None
    missing_sample_files: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not (
            self.missing_python_modules or self.graphviz_executable is None or self.graphviz_error is not None or self.missing_sample_files
        )


def validate_runtime_environment(*, repo_root: Path | None = None) -> PreflightReport:
    """Validate Python modules, Graphviz, and bundled sample data."""
    root = repo_root or Path(__file__).resolve().parent.parent
    missing_python_modules = tuple(module_name for module_name in REQUIRED_PYTHON_MODULES if not _module_exists(module_name))
    graphviz_executable, graphviz_version, graphviz_error = _check_graphviz_binary()
    missing_sample_files = tuple(str(path) for path in REQUIRED_SAMPLE_FILES if not (root / path).exists())
    return PreflightReport(
        missing_python_modules=missing_python_modules,
        graphviz_executable=graphviz_executable,
        graphviz_version=graphviz_version,
        graphviz_error=graphviz_error,
        missing_sample_files=missing_sample_files,
    )


def format_preflight_messages(report: PreflightReport) -> list[str]:
    """Return a compact human-readable summary of preflight issues."""
    lines: list[str] = []
    if report.missing_python_modules:
        lines.append("Missing Python modules:")
        lines.extend(f"- `{module_name}`" for module_name in report.missing_python_modules)
        lines.append('Install the package with `pip install -e ".[dev]"` for development or `pip install .` for runtime.')
    if report.graphviz_executable is None:
        lines.append("Graphviz `dot` was not found on `PATH`.")
        lines.append("Install Graphviz from https://graphviz.org/download/ and ensure `dot` is available before launching CRPM.")
    elif report.graphviz_error is not None:
        lines.append("Graphviz binary validation failed.")
        lines.append(f"`dot -V` returned: {report.graphviz_error}")
    if report.missing_sample_files:
        lines.append("Missing bundled sample data:")
        lines.extend(f"- `{path}`" for path in report.missing_sample_files)
    return lines


def _module_exists(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except Exception:
        return False
    return True


def _check_graphviz_binary() -> tuple[str | None, str | None, str | None]:
    executable = shutil.which("dot")
    if executable is None:
        return None, None, None

    try:
        completed = subprocess.run(
            [executable, "-V"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return executable, None, str(exc)

    output = (completed.stderr or completed.stdout or "").strip()
    if completed.returncode != 0:
        return executable, None, output or f"exit code {completed.returncode}"
    return executable, output or None, None


__all__ = [
    "PreflightReport",
    "format_preflight_messages",
    "validate_runtime_environment",
]


def main() -> int:
    """CLI entrypoint for `python -m crpm.preflight`."""
    report = validate_runtime_environment()
    if report.ok:
        print("CRPM runtime preflight passed.")
        if report.graphviz_version:
            print(report.graphviz_version)
        return 0

    print("CRPM runtime preflight failed.")
    for line in format_preflight_messages(report):
        print(line)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
