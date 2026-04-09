"""Page registry for the staged CRPM Streamlit refactor."""

from .comparison import render_comparison_page
from .conformance import render_conformance_page
from .dfg import render_dfg_page
from .discovery import render_discovery_page
from .overview import render_overview_page
from .operational_flow import render_operational_flow_page
from .performance import render_performance_page
from .variants import render_variant_page

PAGE_REGISTRY = {
    "Overview": render_overview_page,
    "Discovery": render_discovery_page,
    "Model Comparison": render_comparison_page,
    "Operational Flow": render_operational_flow_page,
    "DFG Visualizations": render_dfg_page,
    "Variant Analysis": render_variant_page,
    "Conformance Analytics": render_conformance_page,
    "Process Performance": render_performance_page,
}

__all__ = ["PAGE_REGISTRY"]
