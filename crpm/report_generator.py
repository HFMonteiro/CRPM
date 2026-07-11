"""PDF report generation for screening and process-mining analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from crpm.formatting import format_decimal


class ProcessMiningReport(FPDF):
    """Custom PDF report for process mining analysis."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Page header with title."""
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Process Mining Analysis Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

    def footer(self):
        """Page footer with page number."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, title: str):
        """Add a chapter title."""
        self.set_font("Helvetica", "B", 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

    def section_title(self, title: str):
        """Add a section title."""
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def body_text(self, text: str):
        """Add body text."""
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def add_metric(self, label: str, value: Any):
        """Add a metric row."""
        self.set_font("Helvetica", "B", 10)
        self.cell(70, 6, label + ":")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def generate_pdf_report(
    discovery_results: List[Dict[str, Any]],
    comparison_df: pd.DataFrame,
    case_stats: Dict[str, float],
    activity_stats: pd.DataFrame,
    bottleneck_df: pd.DataFrame,
    variant_stats: pd.DataFrame,
    log_summary: Dict[str, Any],
    filters_applied: Dict[str, Any],
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
        comparable_models = comparison_df.reset_index(drop=True).copy()
        # Find best model (highest average of fitness and precision)
        if "alignment_fitness" in comparable_models.columns and "precision" in comparable_models.columns:
            comparable_models["alignment_fitness"] = pd.to_numeric(comparable_models["alignment_fitness"], errors="coerce")
            comparable_models["precision"] = pd.to_numeric(comparable_models["precision"], errors="coerce")
            comparable_models["score"] = (comparable_models["alignment_fitness"] + comparable_models["precision"]) / 2
            valid_scores = comparable_models["score"].dropna()
            if valid_scores.empty:
                pdf.body_text("Conformance metrics not available for model recommendation.")
            else:
                best_idx = valid_scores.idxmax()
                best_model = comparable_models.loc[best_idx]
                pdf.body_text(
                    f"Based on conformance analysis, the recommended model is: " f"{best_model['algorithm']} - {best_model['variant']}"
                )
                pdf.ln(2)
                pdf.add_metric("Alignment Fitness", format_decimal(best_model["alignment_fitness"]))
                pdf.add_metric("Precision", format_decimal(best_model["precision"]))
                pdf.add_metric("Overall Score", format_decimal(best_model["score"]))
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
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            6,
            f"Model {i}: {result.get('algorithm', 'Unknown')} - {result.get('variant', 'Unknown')}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font("Helvetica", "", 9)
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
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [60, 25, 25, 25, 25]
        headers = ["Model", "Fitness", "Precision", "Simplicity", "Generalization"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, border=1, align="C", fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 8)
        for idx, row in comparison_df.head(10).iterrows():
            model_name = f"{row.get('algorithm', 'Unknown')} - {row.get('variant', 'Unknown')}"

            # Truncate long names
            if len(model_name) > 35:
                model_name = model_name[:32] + "..."

            pdf.cell(col_widths[0], 6, model_name, border=1)
            pdf.cell(col_widths[1], 6, format_decimal(row.get("alignment_fitness", 0)), border=1, align="C")
            pdf.cell(col_widths[2], 6, format_decimal(row.get("precision", 0)), border=1, align="C")
            pdf.cell(col_widths[3], 6, format_decimal(row.get("simplicity", 0)), border=1, align="C")
            pdf.cell(col_widths[4], 6, format_decimal(row.get("generalization", 0)), border=1, align="C")
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
        pdf.add_metric("Median Duration", f"{format_decimal(case_stats.get('median_duration_s', 0) / 86400)} days")
        pdf.add_metric("Average Duration", f"{format_decimal(case_stats.get('avg_duration_s', 0) / 86400)} days")
        pdf.add_metric("P90 Duration", f"{format_decimal(case_stats.get('p90_duration_s', 0) / 86400)} days")
        pdf.add_metric("Max Duration", f"{format_decimal(case_stats.get('max_duration_s', 0) / 86400)} days")
        pdf.add_metric("Std Deviation", f"{format_decimal(case_stats.get('std_duration_s', 0) / 86400)} days")
    else:
        pdf.body_text("No case duration statistics available.")

    pdf.ln(4)

    # Top activities by frequency
    pdf.section_title("3.2 Top Activities by Frequency")
    if not activity_stats.empty:
        pdf.ln(2)

        # Table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [80, 20, 30, 30]
        headers = ["Activity", "Frequency", "Median (days)", "P90 (days)"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, border=1, align="C", fill=True)
        pdf.ln()

        # Table rows (top 15)
        pdf.set_font("Helvetica", "", 8)
        for idx, row in activity_stats.head(15).iterrows():
            activity = str(row.get("activity", "Unknown"))
            if len(activity) > 45:
                activity = activity[:42] + "..."

            pdf.cell(col_widths[0], 6, activity, border=1)
            pdf.cell(col_widths[1], 6, str(row.get("frequency", 0)), border=1, align="C")

            median_days = row.get("median_duration_s", 0) / 86400 if pd.notna(row.get("median_duration_s")) else 0
            p90_days = row.get("p90_duration_s", 0) / 86400 if pd.notna(row.get("p90_duration_s")) else 0

            pdf.cell(col_widths[2], 6, format_decimal(median_days), border=1, align="C")
            pdf.cell(col_widths[3], 6, format_decimal(p90_days), border=1, align="C")
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
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(255, 220, 220)

        col_widths = [70, 20, 30, 30]
        headers = ["Transition", "Frequency", "Median (days)", "P90 (days)"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, border=1, align="C", fill=True)
        pdf.ln()

        # Table rows (top 10)
        pdf.set_font("Helvetica", "", 8)
        for idx, row in bottleneck_df.head(10).iterrows():
            transition = str(row.get("transition", "Unknown"))
            if len(transition) > 40:
                transition = transition[:37] + "..."

            pdf.cell(col_widths[0], 6, transition, border=1)
            pdf.cell(col_widths[1], 6, str(row.get("frequency", 0)), border=1, align="C")

            median_days = row.get("median_duration_s", 0) / 86400
            p90_days = row.get("p90_duration_s", 0) / 86400

            pdf.cell(col_widths[2], 6, format_decimal(median_days), border=1, align="C")
            pdf.cell(col_widths[3], 6, format_decimal(p90_days), border=1, align="C")
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
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)

        col_widths = [10, 90, 20, 20]
        headers = ["Rank", "Variant (truncated)", "Cases", "Percentage"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 6, header, border=1, align="C", fill=True)
        pdf.ln()

        # Table rows (top 15)
        pdf.set_font("Helvetica", "", 7)
        for rank, (_, row) in enumerate(variant_stats.head(15).iterrows(), start=1):
            variant_str = str(row.get("variant_str", "Unknown"))
            if len(variant_str) > 80:
                variant_str = variant_str[:77] + "..."

            pdf.cell(col_widths[0], 6, str(rank), border=1, align="C")
            pdf.cell(col_widths[1], 6, variant_str, border=1)
            pdf.cell(col_widths[2], 6, str(row.get("frequency", 0)), border=1, align="C")
            pdf.cell(col_widths[3], 6, f"{row.get('percentage', 0):.2f}%", border=1, align="C")
            pdf.ln()

        pdf.ln(4)
    else:
        pdf.body_text("No variant data available.")
        pdf.ln(4)

    # =========================================================================
    # FOOTER
    # =========================================================================
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0, 6, "This report was generated by the CRPM Process Mining Analysis Tool. For more information, refer to the tool documentation."
    )

    # Output PDF to bytes
    return bytes(pdf.output())


__all__ = ["generate_pdf_report"]
