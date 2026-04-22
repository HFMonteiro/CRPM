"""Narrow runtime compatibility shims for third-party import quirks."""

from __future__ import annotations

import os
from typing import Any


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


__all__ = ["install_pm4py_import_guard"]
