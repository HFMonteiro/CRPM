"""CRPM - Process mining workbench for colorectal cancer screening programs."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.3.0"

__all__ = [
    "analytics",
    "conformance",
    "dfg_utils",
    "discovery",
    "interpretations",
    "pipeline",
    "preflight",
    "queue_flow",
    "runtime_compat",
    "screening",
    "variants",
    "visualization",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f".{name}", __name__)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
