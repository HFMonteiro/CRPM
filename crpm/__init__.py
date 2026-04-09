"""CRPM - Process mining workbench for colorectal cancer screening programs."""

__version__ = "0.3.0"

from . import analytics
from . import conformance
from . import dfg_utils
from . import discovery
from . import interpretations
from . import pipeline
from . import queue_flow
from . import screening
from . import variants
from . import visualization

__all__ = [
    "analytics",
    "conformance",
    "dfg_utils",
    "discovery",
    "interpretations",
    "pipeline",
    "queue_flow",
    "screening",
    "variants",
    "visualization",
]
