"""Interpretation and assessment helpers for process mining metrics.

This module provides functions to assess metric quality and provide
user-friendly interpretations for process mining analysis results.
"""

from __future__ import annotations

from typing import Tuple, Dict, Any
import pandas as pd


# ---------------------------------------------------------------------------
# Conformance Metric Assessments
# ---------------------------------------------------------------------------


def assess_fitness(value: float) -> Tuple[str, str, str]:
    """Assess fitness metric quality.

    Args:
        value: Fitness value (0-1)

    Returns:
        Tuple of (quality_level, color, message)
    """
    if pd.isna(value):
        return ("Unknown", "gray", "N/A")

    if value >= 0.95:
        return ("Excellent", "green", "Model fits the log very well")
    elif value >= 0.85:
        return ("Good", "orange", "Model fits the log adequately")
    elif value >= 0.70:
        return ("Fair", "orange", "Model has notable deviations")
    else:
        return ("Poor", "red", "Model poorly represents the log")


def assess_precision(value: float) -> Tuple[str, str, str]:
    """Assess precision metric quality.

    Args:
        value: Precision value (0-1)

    Returns:
        Tuple of (quality_level, color, message)
    """
    if pd.isna(value):
        return ("Unknown", "gray", "N/A")

    if value >= 0.90:
        return ("Excellent", "green", "Model is very precise")
    elif value >= 0.75:
        return ("Good", "orange", "Model has acceptable precision")
    elif value >= 0.60:
        return ("Fair", "orange", "Model allows too much behavior")
    else:
        return ("Poor", "red", "Model is too general")


def assess_model_complexity(num_transitions: int, num_places: int) -> Tuple[str, str, str]:
    """Assess model complexity.

    Args:
        num_transitions: Number of transitions in the model
        num_places: Number of places in the model

    Returns:
        Tuple of (complexity_level, color, message)
    """
    if num_transitions < 30:
        return ("Simple", "green", "Easy to understand and maintain")
    elif num_transitions < 50:
        return ("Moderate", "orange", "Reasonably manageable complexity")
    else:
        return ("Complex", "red", "High complexity - consider simplification")


def assess_balanced_quality(fitness: float, precision: float) -> Tuple[str, str, str]:
    """Assess overall model quality based on fitness and precision balance.

    Args:
        fitness: Fitness value (0-1)
        precision: Precision value (0-1)

    Returns:
        Tuple of (quality_level, color, message)
    """
    if pd.isna(fitness) or pd.isna(precision):
        return ("Unknown", "gray", "Incomplete metrics")

    avg_score = (fitness + precision) / 2

    # Check balance (both should be reasonably high)
    is_balanced = abs(fitness - precision) < 0.20

    if avg_score >= 0.85 and is_balanced:
        return ("Excellent", "green", "Well-balanced, high-quality model")
    elif avg_score >= 0.75 and is_balanced:
        return ("Good", "green", "Good balance between fitness and precision")
    elif avg_score >= 0.75 and not is_balanced:
        return ("Fair", "orange", "Good average but imbalanced metrics")
    elif avg_score >= 0.60:
        return ("Fair", "orange", "Acceptable but room for improvement")
    else:
        return ("Poor", "red", "Low quality - consider alternative algorithm")


def get_model_quadrant(fitness: float, precision: float) -> str:
    """Determine which quality quadrant a model falls into.

    Args:
        fitness: Fitness value (0-1)
        precision: Precision value (0-1)

    Returns:
        Quadrant name with emoji
    """
    if pd.isna(fitness) or pd.isna(precision):
        return "❓ Unknown"

    fitness_threshold = 0.85
    precision_threshold = 0.75

    if fitness >= fitness_threshold and precision >= precision_threshold:
        return "🟢 Ideal Zone"
    elif fitness >= fitness_threshold and precision < precision_threshold:
        return "🟡 Overfitting"
    elif fitness < fitness_threshold and precision >= precision_threshold:
        return "🟡 Underfitting"
    else:
        return "🔴 Poor Quality"


# ---------------------------------------------------------------------------
# Performance Metric Assessments
# ---------------------------------------------------------------------------


def assess_process_variance(std_dev: float, median: float) -> Tuple[str, str, str]:
    """Assess process duration variance/consistency.

    Args:
        std_dev: Standard deviation of durations (in same units as median)
        median: Median duration

    Returns:
        Tuple of (variance_level, color, message)
    """
    if pd.isna(std_dev) or pd.isna(median) or median == 0:
        return ("Unknown", "gray", "Insufficient data")

    coefficient_of_variation = std_dev / median

    if coefficient_of_variation < 0.20:
        return ("Low", "green", "Consistent process execution")
    elif coefficient_of_variation < 0.50:
        return ("Medium", "orange", "Some process variability")
    else:
        return ("High", "red", "High variability - investigate outliers")


def assess_bottleneck_severity(
    median_duration_s: float,
    p90_duration_s: float,
    frequency: int,
    overall_median_s: float
) -> Tuple[str, str, str]:
    """Assess bottleneck severity.

    Args:
        median_duration_s: Median duration of this transition
        p90_duration_s: P90 duration of this transition
        frequency: Frequency of this transition
        overall_median_s: Overall median across all transitions

    Returns:
        Tuple of (severity_level, color, message)
    """
    if pd.isna(median_duration_s) or overall_median_s == 0:
        return ("Unknown", "gray", "Insufficient data")

    # Calculate relative duration compared to overall median
    relative_duration = median_duration_s / overall_median_s

    # High frequency and long duration = critical
    if relative_duration > 3.0 and frequency > 10:
        return ("Critical", "red", "Immediate attention needed")
    elif relative_duration > 2.0:
        return ("High", "orange", "Should be optimized")
    elif relative_duration > 1.5:
        return ("Moderate", "orange", "Monitor closely")
    else:
        return ("Low", "green", "Within acceptable range")


def assess_case_duration_outliers(p90: float, median: float) -> Tuple[str, str, str]:
    """Assess whether there are significant duration outliers.

    Args:
        p90: 90th percentile duration
        median: Median duration

    Returns:
        Tuple of (outlier_level, color, message)
    """
    if pd.isna(p90) or pd.isna(median) or median == 0:
        return ("Unknown", "gray", "Insufficient data")

    p90_to_median_ratio = p90 / median

    if p90_to_median_ratio < 1.5:
        return ("Few", "green", "Minimal outliers - consistent process")
    elif p90_to_median_ratio < 2.5:
        return ("Some", "orange", "Some outliers present")
    else:
        return ("Many", "red", "Significant outliers - investigate delays")


# ---------------------------------------------------------------------------
# Variant Analysis Assessments
# ---------------------------------------------------------------------------


def assess_variant_coverage(top_n_percentage: float, top_n: int = 10) -> Tuple[str, str, str]:
    """Assess variant coverage - process standardization level.

    Args:
        top_n_percentage: Percentage of cases covered by top N variants
        top_n: Number of top variants (default 10)

    Returns:
        Tuple of (standardization_level, color, message)
    """
    if pd.isna(top_n_percentage):
        return ("Unknown", "gray", "Insufficient data")

    if top_n_percentage >= 80:
        return (
            "Excellent",
            "green",
            f"Process is highly standardized (top {top_n} variants cover {top_n_percentage:.1f}%)"
        )
    elif top_n_percentage >= 60:
        return (
            "Good",
            "orange",
            f"Moderate standardization (top {top_n} variants cover {top_n_percentage:.1f}%)"
        )
    else:
        return (
            "Poor",
            "red",
            f"High process variability (top {top_n} variants only cover {top_n_percentage:.1f}%) - review compliance"
        )


def assess_variant_count(num_variants: int, num_cases: int) -> Tuple[str, str, str]:
    """Assess whether the number of variants is appropriate.

    Args:
        num_variants: Total number of unique variants
        num_cases: Total number of cases

    Returns:
        Tuple of (variety_level, color, message)
    """
    if num_cases == 0:
        return ("Unknown", "gray", "No cases")

    variants_per_case = num_variants / num_cases

    if variants_per_case < 0.1:
        return ("Low", "green", "Good process standardization")
    elif variants_per_case < 0.3:
        return ("Moderate", "orange", "Acceptable variant diversity")
    else:
        return ("High", "red", "Too many variants - process may lack control")


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def get_quality_badge_html(quality_level: str, color: str) -> str:
    """Generate HTML for a colored quality badge.

    Args:
        quality_level: Quality level text
        color: Color name (green, orange, red, gray)

    Returns:
        HTML string for badge
    """
    color_map = {
        "green": "#28a745",
        "orange": "#fd7e14",
        "red": "#dc3545",
        "gray": "#6c757d"
    }

    bg_color = color_map.get(color, "#6c757d")

    return f'''<span style="
        background-color: {bg_color};
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        font-weight: bold;
        margin-left: 5px;
    ">{quality_level}</span>'''


def format_metric_with_assessment(
    metric_name: str,
    value: float,
    assessment: Tuple[str, str, str]
) -> str:
    """Format a metric value with its quality assessment.

    Args:
        metric_name: Name of the metric
        value: Metric value
        assessment: Tuple from assessment function (quality, color, message)

    Returns:
        Formatted string with HTML badge
    """
    quality, color, message = assessment

    if pd.isna(value):
        return f"{metric_name}: N/A {get_quality_badge_html('Unknown', 'gray')}"

    badge = get_quality_badge_html(quality, color)
    return f"{metric_name}: {value:.4f} {badge} - {message}"


def get_executive_summary(
    fitness: float,
    precision: float,
    num_transitions: int,
    discovery_algorithm: str
) -> Dict[str, Any]:
    """Generate an executive summary for a discovered model.

    Args:
        fitness: Fitness value
        precision: Precision value
        num_transitions: Number of transitions
        discovery_algorithm: Algorithm name

    Returns:
        Dictionary with summary information
    """
    fitness_assessment = assess_fitness(fitness)
    precision_assessment = assess_precision(precision)
    balanced_assessment = assess_balanced_quality(fitness, precision)
    quadrant = get_model_quadrant(fitness, precision)

    return {
        "algorithm": discovery_algorithm,
        "overall_quality": balanced_assessment[0],
        "overall_color": balanced_assessment[1],
        "overall_message": balanced_assessment[2],
        "quadrant": quadrant,
        "fitness_quality": fitness_assessment[0],
        "precision_quality": precision_assessment[0],
        "complexity": assess_model_complexity(num_transitions, 0)[0],
        "recommendation": _get_recommendation(fitness, precision, num_transitions)
    }


def _get_recommendation(fitness: float, precision: float, num_transitions: int) -> str:
    """Generate a recommendation based on metrics.

    Args:
        fitness: Fitness value
        precision: Precision value
        num_transitions: Number of transitions

    Returns:
        Recommendation string
    """
    if pd.isna(fitness) or pd.isna(precision):
        return "Incomplete metrics - run full conformance analysis"

    if fitness >= 0.85 and precision >= 0.75:
        return "✅ This model is recommended for production use"
    elif fitness < 0.70:
        return "⚠️ Low fitness - try Inductive Miner for guaranteed fitness"
    elif precision < 0.60:
        return "⚠️ Low precision - model is too general, try Heuristics Miner"
    elif num_transitions > 50:
        return "⚠️ Complex model - consider filtering or using IMf for simplification"
    else:
        return "✓ Acceptable model quality with room for optimization"


__all__ = [
    "assess_fitness",
    "assess_precision",
    "assess_model_complexity",
    "assess_balanced_quality",
    "get_model_quadrant",
    "assess_process_variance",
    "assess_bottleneck_severity",
    "assess_case_duration_outliers",
    "assess_variant_coverage",
    "assess_variant_count",
    "get_quality_badge_html",
    "format_metric_with_assessment",
    "get_executive_summary",
]
