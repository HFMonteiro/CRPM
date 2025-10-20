"""PDF Report Generation for Process Mining Analysis.

This module generates comprehensive PDF reports from analysis results.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import pandas as pd
from fpdf import FPDF
import plotly.graph_objects as go


class ProcessMiningReport(FPDF):
    """Custom PDF report for process mining analysis."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header with title."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Process Mining Analysis Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        """Page footer with page number."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title: str):
        """Add a chapter title."""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def section_title(self, title: str):
        """Add a section title."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(2)

    def body_text(self, text: str):
        """Add body text."""
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def add_metric(self, label: str, value: str):
        """Add a metric row."""
        self.set_font('Arial', 'B', 10)
        self.cell(70, 6, label + ':', 0, 0, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 6, str(value), 0, 1, 'L')


def generate_pdf_report(
    discovery_results: List[Dict[str, Any]],
    comparison_df: pd.DataFrame,
    case_stats: Dict[str, float],
    activity_stats: pd.DataFrame,
    bottleneck_df: pd.DataFrame,
    variant_stats: pd.DataFrame,
    log_summary: Dict[str, Any],
    filters_applied: Dict[str, Any]
) -> bytes:
    """Generate comprehensive PDF report from analysis results.

    Args:
        discovery_results: List of discovery results with conformance metrics
        comparison_df: Model comparison DataFrame
        case_stats: Case duration statistics
        activity_stats: Activity statistics DataFrame
        bottleneck_df: Bottleneck analysis DataFrame
        variant_stats: Variant statistics DataFrame
        log_summary: Log summary statistics
        filters_applied: Dictionary of applied filters

    Returns:
        PDF file as bytes
    """
    pdf = ProcessMiningReport()
    pdf.add_page()

    # =========================================================================
    # 1. EXECUTIVE SUMMARY
    # =========================================================================
    pdf.chapter_title("1. Executive Summary")

    # Report metadata
    pdf.body_text(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.ln(2)

    # Log summary
    pdf.section_title("1.1 Event Log Summary")
    pdf.add_metric("Total Cases", log_summary.get("num_cases", "N/A"))
    pdf.add_metric("Total Events", log_summary.get("num_events", "N/A"))
    pdf.add_metric("Unique Activities", log_summary.get("num_activities", "N/A"))
    pdf.add_metric("Unique Variants", log_summary.get("num_variants", "N/A"))

    if log_summary.get("start_date"):
        pdf.add_metric("Start Date", str(log_summary.get("start_date")))
    if log_summary.get("end_date"):
        pdf.add_metric("End Date", str(log_summary.get("end_date")))

    pdf.ln(4)

    # Filters applied
    if filters_applied:
        pdf.section_title("1.2 Filters Applied")
        if filters_applied.get("start_activity") and filters_applied["start_activity"] != "All":
            pdf.add_metric("Start Activity Filter", filters_applied["start_activity"])
        if filters_applied.get("date_range"):
            pdf.add_metric("Date Range", filters_applied["date_range"])
        pdf.ln(4)

    # Best model recommendation
    pdf.section_title("1.3 Recommended Model")
    if not comparison_df.empty:
        # Find best model (highest average of fitness and precision)
        if "alignment_fitness" in comparison_df.columns and "precision" in comparison_df.columns:
            comparison_df["score"] = (
                comparison_df["alignment_fitness"] + comparison_df["precision"]
            ) / 2
            best_idx = comparison_df["score"].idxmax()
            best_model = comparison_df.loc[best_idx]

            pdf.body_text(
                f"Based on conformance analysis, the recommended model is: "
                f"{best_model['algorithm']} - {best_model['variant']}"
            )
            pdf.ln(2)
            pdf.add_metric("Alignment Fitness", f"{best_model['alignment_fitness']:.4f}")
            pdf.add_metric("Precision", f"{best_model['precision']:.4f}")
            pdf.add_metric("Overall Score", f"{best_model['score']:.4f}")
        else:
            pdf.body_text("Conformance metrics not available for model recommendation.")
    else:
        pdf.body_text("No models available for comparison.")

    pdf.ln(6)

    # =========================================================================
    # 2. MODEL DISCOVERY & COMPARISON
    # =========================================================================
    pdf.chapter_title("2. Model Discovery & Comparison")

    pdf.section_title("2.1 Models Discovered")
    pdf.body_text(f"Total models discovered: {len(discovery_results)}")
    pdf.ln(2)

    for i, result in enumerate(discovery_results, 1):
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, f"Model {i}: {result.get('algorithm', 'Unknown')} - {result.get('variant', 'Unknown')}", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.add_metric("  Transitions", result.get("num_transitions", "N/A"))
        pdf.add_metric("  Places", result.get("num_places", "N/A"))
        pdf.add_metric("  Arcs", result.get("num_arcs", "N/A"))
        pdf.add_metric("  Discovery Time", f"{result.get('discovery_time_s', 0):.2f}s")
        pdf.ln(2)

    pdf.ln(4)

    # Conformance comparison table
    if not comparison_df.empty:
        pdf.section_title("2.2 Conformance Metrics Comparison")
        pdf.ln(2)

        # Table header
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [60, 25, 25, 25, 25]
        headers = ["Model", "Fitness", "Precision", "Simplicity", "Generalization"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, 1, 0, 'C', 1)
        pdf.ln()

        # Table rows
        pdf.set_font('Arial', '', 8)
        for idx, row in comparison_df.head(10).iterrows():
            model_name = f"{row.get('algorithm', 'Unknown')} - {row.get('variant', 'Unknown')}"

            # Truncate long names
            if len(model_name) > 35:
                model_name = model_name[:32] + "..."

            pdf.cell(col_widths[0], 6, model_name, 1, 0, 'L')
            pdf.cell(col_widths[1], 6, f"{row.get('alignment_fitness', 0):.4f}", 1, 0, 'C')
            pdf.cell(col_widths[2], 6, f"{row.get('precision', 0):.4f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"{row.get('simplicity', 0):.4f}", 1, 0, 'C')
            pdf.cell(col_widths[4], 6, f"{row.get('generalization', 0):.4f}", 1, 0, 'C')
            pdf.ln()

        pdf.ln(4)

    # =========================================================================
    # 3. PERFORMANCE ANALYTICS
    # =========================================================================
    pdf.add_page()
    pdf.chapter_title("3. Performance Analytics")

    # Case duration statistics
    pdf.section_title("3.1 Case Duration Statistics")
    if case_stats:
        pdf.add_metric("Total Cases", case_stats.get("total_cases", "N/A"))
        pdf.add_metric("Median Duration", f"{case_stats.get('median_duration_s', 0) / 86400:.4f} days")
        pdf.add_metric("Average Duration", f"{case_stats.get('avg_duration_s', 0) / 86400:.4f} days")
        pdf.add_metric("P90 Duration", f"{case_stats.get('p90_duration_s', 0) / 86400:.4f} days")
        pdf.add_metric("Max Duration", f"{case_stats.get('max_duration_s', 0) / 86400:.4f} days")
        pdf.add_metric("Std Deviation", f"{case_stats.get('std_duration_s', 0) / 86400:.4f} days")
    else:
        pdf.body_text("No case duration statistics available.")

    pdf.ln(4)

    # Top activities by frequency
    pdf.section_title("3.2 Top Activities by Frequency")
    if not activity_stats.empty:
        pdf.ln(2)

        # Table header
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [80, 20, 30, 30]
        headers = ["Activity", "Frequency", "Median (days)", "P90 (days)"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, 1, 0, 'C', 1)
        pdf.ln()

        # Table rows (top 15)
        pdf.set_font('Arial', '', 8)
        for idx, row in activity_stats.head(15).iterrows():
            activity = str(row.get("activity", "Unknown"))
            if len(activity) > 45:
                activity = activity[:42] + "..."

            pdf.cell(col_widths[0], 6, activity, 1, 0, 'L')
            pdf.cell(col_widths[1], 6, str(row.get("frequency", 0)), 1, 0, 'C')

            median_days = row.get("median_duration_s", 0) / 86400 if pd.notna(row.get("median_duration_s")) else 0
            p90_days = row.get("p90_duration_s", 0) / 86400 if pd.notna(row.get("p90_duration_s")) else 0

            pdf.cell(col_widths[2], 6, f"{median_days:.4f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"{p90_days:.4f}", 1, 0, 'C')
            pdf.ln()

        pdf.ln(4)
    else:
        pdf.body_text("No activity statistics available.")
        pdf.ln(4)

    # =========================================================================
    # 4. BOTTLENECK ANALYSIS
    # =========================================================================
    pdf.section_title("4. Bottleneck Analysis")
    if not bottleneck_df.empty:
        pdf.body_text(
            "Bottlenecks are identified using weighted scoring: 70% duration + 30% frequency. "
            "Higher scores indicate more critical bottlenecks."
        )
        pdf.ln(2)

        # Table header
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(255, 220, 220)

        col_widths = [70, 20, 30, 30]
        headers = ["Transition", "Frequency", "Median (days)", "P90 (days)"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, 1, 0, 'C', 1)
        pdf.ln()

        # Table rows (top 10)
        pdf.set_font('Arial', '', 8)
        for idx, row in bottleneck_df.head(10).iterrows():
            transition = str(row.get("transition", "Unknown"))
            if len(transition) > 40:
                transition = transition[:37] + "..."

            pdf.cell(col_widths[0], 6, transition, 1, 0, 'L')
            pdf.cell(col_widths[1], 6, str(row.get("frequency", 0)), 1, 0, 'C')

            median_days = row.get("median_duration_s", 0) / 86400
            p90_days = row.get("p90_duration_s", 0) / 86400

            pdf.cell(col_widths[2], 6, f"{median_days:.4f}", 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"{p90_days:.4f}", 1, 0, 'C')
            pdf.ln()

        pdf.ln(4)
    else:
        pdf.body_text("No bottleneck data available.")
        pdf.ln(4)

    # =========================================================================
    # 5. VARIANT ANALYSIS
    # =========================================================================
    pdf.add_page()
    pdf.chapter_title("5. Variant Analysis")

    if not variant_stats.empty:
        pdf.body_text(f"Total unique variants: {len(variant_stats)}")
        pdf.ln(2)

        # Coverage summary
        top_10_coverage = variant_stats.head(10)["percentage"].sum() if "percentage" in variant_stats.columns else 0
        pdf.add_metric("Top 10 Variants Coverage", f"{top_10_coverage:.2f}%")
        pdf.ln(4)

        # Table header
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [10, 90, 20, 20]
        headers = ["Rank", "Variant (truncated)", "Cases", "Percentage"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, 1, 0, 'C', 1)
        pdf.ln()

        # Table rows (top 15)
        pdf.set_font('Arial', '', 7)
        for idx, row in variant_stats.head(15).iterrows():
            variant_str = str(row.get("variant_str", "Unknown"))
            if len(variant_str) > 80:
                variant_str = variant_str[:77] + "..."

            pdf.cell(col_widths[0], 6, str(idx + 1), 1, 0, 'C')
            pdf.cell(col_widths[1], 6, variant_str, 1, 0, 'L')
            pdf.cell(col_widths[2], 6, str(row.get("case_count", 0)), 1, 0, 'C')
            pdf.cell(col_widths[3], 6, f"{row.get('percentage', 0):.2f}%", 1, 0, 'C')
            pdf.ln()

        pdf.ln(4)
    else:
        pdf.body_text("No variant data available.")
        pdf.ln(4)

    # =========================================================================
    # FOOTER
    # =========================================================================
    pdf.ln(6)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(
        0, 6,
        "This report was generated by the CRPM Process Mining Analysis Tool. "
        "For more information, refer to the tool documentation."
    )

    # Output PDF to bytes
    return pdf.output(dest='S').encode('latin-1')


__all__ = ["generate_pdf_report"]
