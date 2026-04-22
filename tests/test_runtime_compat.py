from __future__ import annotations

import os
from types import SimpleNamespace

from crpm.runtime_compat import install_pm4py_import_guard


def test_install_pm4py_import_guard_masks_dead_parent_pid(monkeypatch) -> None:
    parent_pid = os.getppid()

    class _NoSuchProcess(Exception):
        pass

    class _OriginalProcess:
        def __init__(self, pid=None, *args, **kwargs) -> None:
            if pid == parent_pid:
                raise _NoSuchProcess()
            self.pid = pid

        def name(self) -> str:
            return "python"

    fake_psutil = SimpleNamespace(
        Process=_OriginalProcess,
        NoSuchProcess=_NoSuchProcess,
    )

    monkeypatch.setitem(__import__("sys").modules, "psutil", fake_psutil)

    install_pm4py_import_guard()

    guarded_parent = fake_psutil.Process(parent_pid)
    assert guarded_parent.name() == ""

    guarded_current = fake_psutil.Process(1234)
    assert guarded_current.name() == "python"


def test_install_pm4py_import_guard_is_idempotent(monkeypatch) -> None:
    class _OriginalProcess:
        def __init__(self, pid=None, *args, **kwargs) -> None:
            self.pid = pid

        def name(self) -> str:
            return "python"

    fake_psutil = SimpleNamespace(
        Process=_OriginalProcess,
        NoSuchProcess=RuntimeError,
    )

    monkeypatch.setitem(__import__("sys").modules, "psutil", fake_psutil)

    install_pm4py_import_guard()
    first_wrapper = fake_psutil.Process
    install_pm4py_import_guard()

    assert fake_psutil.Process is first_wrapper
