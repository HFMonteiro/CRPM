"""Narrow runtime compatibility shims for third-party import quirks."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


def ensure_graphviz_on_path() -> str | None:
    """Return Graphviz `dot`, adding common Windows install paths when needed."""
    executable = shutil.which("dot")
    if executable:
        return executable

    for candidate in _graphviz_dot_candidates():
        if not candidate.exists():
            continue
        bin_dir = str(candidate.parent)
        path_parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
        if not any(os.path.normcase(part) == os.path.normcase(bin_dir) for part in path_parts):
            os.environ["PATH"] = os.pathsep.join([bin_dir, *path_parts])
        return str(candidate)

    return None


def _graphviz_dot_candidates() -> tuple[Path, ...]:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Graphviz" / "bin" / "dot.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Graphviz" / "bin" / "dot.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Graphviz" / "bin" / "dot.exe",
    ]
    return tuple(candidate for candidate in candidates if str(candidate))


def install_pm4py_import_guard() -> None:
    """Guard PM4Py against dead-parent psutil lookups at import time."""
    try:
        import psutil  # type: ignore
    except Exception:
        return

    if bool(getattr(psutil.Process, "_crpm_wrapped", False)):
        return

    original_process = psutil.Process
    no_such_process = psutil.NoSuchProcess

    class _DeadParentProcess:
        def __init__(self, pid: int | None) -> None:
            self.pid = pid

        def name(self) -> str:
            return ""

    def _safe_process(pid: int | None = None, *args: Any, **kwargs: Any) -> Any:
        try:
            return original_process(pid, *args, **kwargs)
        except no_such_process:
            target_pid = pid if pid is not None else os.getpid()
            if target_pid == os.getppid():
                return _DeadParentProcess(target_pid)
            raise

    setattr(_safe_process, "_crpm_wrapped", True)
    setattr(_safe_process, "_crpm_original", original_process)
    psutil.Process = _safe_process  # type: ignore[assignment]


__all__ = ["ensure_graphviz_on_path", "install_pm4py_import_guard"]
