"""Variant analysis for process mining.

This module provides functions for analyzing trace variants and computing
per-variant conformance metrics.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional
import pandas as pd

from pm4py.objects.log.obj import EventLog


# ---------------------------------------------------------------------------
# Variant Statistics
# ---------------------------------------------------------------------------


def get_variant_statistics(log: EventLog, top_n: Optional[int] = None) -> pd.DataFrame:
    """Get frequency statistics for trace variants.

    Args:
        log: Event log
        top_n: If specified, return only top N most frequent variants

    Returns:
        DataFrame with columns: variant, variant_str, frequency, percentage
    """
    try:
        from pm4py.statistics.traces.generic.log import case_statistics

        # Get variant statistics from PM4Py
        variants = case_statistics.get_variant_statistics(log)

        # Convert to DataFrame
        df = pd.DataFrame(variants)

        if df.empty:
            return df

        # Add percentage
        total_traces = df["count"].sum()
        df["percentage"] = (df["count"] / total_traces * 100) if total_traces > 0 else 0

        # Rename columns for clarity
        df = df.rename(columns={"count": "frequency"})

        # Convert variant tuple to readable string
        if "variant" in df.columns:
            df["variant_str"] = df["variant"].apply(lambda v: " → ".join(v) if isinstance(v, (list, tuple)) else str(v))

        # Sort by frequency
        df = df.sort_values("frequency", ascending=False).reset_index(drop=True)

        # Limit to top N if specified
        if top_n:
            df = df.head(top_n)

        return df

    except Exception as e:
        # Fallback: manual variant extraction
        return _manual_variant_statistics(log, top_n)


def _manual_variant_statistics(log: EventLog, top_n: Optional[int] = None) -> pd.DataFrame:
    """Manually compute variant statistics (fallback if PM4Py fails).

    Args:
        log: Event log
        top_n: If specified, return only top N variants

    Returns:
        DataFrame with variant statistics
    """
    variant_counts: Dict[Tuple[str, ...], int] = {}

    for trace in log:
        # Extract activity sequence
        activities = tuple(event.get("concept:name", "Unknown") for event in trace)

        # Count variant
        if activities in variant_counts:
            variant_counts[activities] += 1
        else:
            variant_counts[activities] = 1

    # Convert to DataFrame
    data = []
    total_traces = sum(variant_counts.values())

    for variant, count in variant_counts.items():
        data.append({
            "variant": variant,
            "variant_str": " → ".join(variant),
            "frequency": count,
            "percentage": (count / total_traces * 100) if total_traces > 0 else 0
        })

    df = pd.DataFrame(data)
    df = df.sort_values("frequency", ascending=False).reset_index(drop=True)

    if top_n:
        df = df.head(top_n)

    return df


# ---------------------------------------------------------------------------
# Per-Variant Conformance
# ---------------------------------------------------------------------------


def compute_variant_conformance(
    log: EventLog,
    net,
    im,
    fm,
    top_n: int = 20,
    sample_alignments: bool = False,
    max_alignment_samples: int = 100
) -> pd.DataFrame:
    """Compute conformance metrics for each variant.

    Args:
        log: Event log
        net: Petri net model
        im: Initial marking
        fm: Final marking
        top_n: Number of top variants to analyze
        sample_alignments: If True, sample traces for alignment computation
        max_alignment_samples: Max traces per variant for alignment

    Returns:
        DataFrame with per-variant conformance metrics
    """
    try:
        from pm4py.statistics.traces.generic.log import case_statistics
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog
    except Exception:
        return pd.DataFrame()

    # Get variants
    variants = case_statistics.get_variant_statistics(log)
    vdf = pd.DataFrame(variants)

    if vdf.empty:
        return vdf

    # Sort and limit to top N
    vdf = vdf.sort_values("count", ascending=False).head(top_n).reset_index(drop=True)

    # Compute conformance for each variant
    rows = []
    for idx, row in vdf.iterrows():
        variant = row["variant"]
        frequency = int(row["count"])

        # Filter log to this variant manually
        variant_log = PM4PyEventLog()
        for trace in log:
            trace_variant = tuple(event.get("concept:name", "Unknown") for event in trace)
            if trace_variant == variant:
                variant_log.append(trace)

        # Sample if requested
        if sample_alignments and len(variant_log) > max_alignment_samples:
            import random
            traces = list(variant_log)
            variant_log_sample = EventLog()
            for trace in random.sample(traces, max_alignment_samples):
                variant_log_sample.append(trace)
        else:
            variant_log_sample = variant_log

        # Token replay fitness
        try:
            tr = token_replay.apply(variant_log, net, im, fm)
            if isinstance(tr, dict) and "log_fitness" in tr:
                token_fitness = float(tr["log_fitness"])
            elif isinstance(tr, list) and tr and isinstance(tr[0], dict) and "trace_fitness" in tr[0]:
                token_fitness = float(pd.DataFrame(tr)["trace_fitness"].mean())
            else:
                token_fitness = None
        except Exception:
            token_fitness = None

        # Alignments
        try:
            aln = alignments.apply_log(variant_log_sample, net, im, fm)
            if aln:
                adf = pd.DataFrame(aln)
                align_fitness = float(pd.to_numeric(adf.get("fitness", pd.Series([None]*len(adf))), errors="coerce").mean())
                align_cost = float(pd.to_numeric(adf.get("cost", pd.Series([None]*len(adf))), errors="coerce").mean())
                moves_on_model = float(pd.to_numeric(adf.get("bwc", pd.Series([0]*len(adf))), errors="coerce").mean())
                moves_on_log = float(pd.to_numeric(adf.get("bwt", pd.Series([0]*len(adf))), errors="coerce").mean())
                perfect_pct = float((pd.to_numeric(adf.get("fitness", pd.Series([0]*len(adf))), errors="coerce") == 1.0).mean() * 100)
            else:
                align_fitness = align_cost = moves_on_model = moves_on_log = perfect_pct = None
        except Exception:
            align_fitness = align_cost = moves_on_model = moves_on_log = perfect_pct = None

        # Variant string
        variant_str = " → ".join(variant) if isinstance(variant, (list, tuple)) else str(variant)

        rows.append({
            "variant": variant_str,
            "frequency": frequency,
            "percentage": (frequency / len(log) * 100) if len(log) > 0 else 0,
            "token_fitness": token_fitness,
            "align_fitness": align_fitness,
            "align_cost": align_cost,
            "moves_on_model": moves_on_model,
            "moves_on_log": moves_on_log,
            "perfect_fit_pct": perfect_pct
        })

    return pd.DataFrame(rows)


def compute_variant_coverage(variant_stats: pd.DataFrame) -> pd.DataFrame:
    """Compute cumulative coverage of variants.

    Args:
        variant_stats: DataFrame from get_variant_statistics

    Returns:
        DataFrame with cumulative frequency and percentage
    """
    if variant_stats.empty or "frequency" not in variant_stats.columns:
        return variant_stats

    df = variant_stats.copy()
    df["cumulative_frequency"] = df["frequency"].cumsum()

    total = df["frequency"].sum()
    df["cumulative_percentage"] = (df["cumulative_frequency"] / total * 100) if total > 0 else 0

    return df


# ---------------------------------------------------------------------------
# Variant Filtering
# ---------------------------------------------------------------------------


def filter_variants_by_frequency(
    log: EventLog,
    min_frequency: Optional[int] = None,
    min_percentage: Optional[float] = None
) -> EventLog:
    """Filter log to keep only variants meeting frequency threshold.

    Args:
        log: Event log
        min_frequency: Minimum absolute frequency
        min_percentage: Minimum percentage (0-100)

    Returns:
        Filtered event log
    """
    try:
        from pm4py.statistics.traces.generic.log import case_statistics
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog

        # Get variant statistics
        variants = case_statistics.get_variant_statistics(log)
        vdf = pd.DataFrame(variants)

        if vdf.empty:
            return log

        # Calculate thresholds
        total_traces = vdf["count"].sum()

        # Filter variants
        filtered_variants = []
        for _, row in vdf.iterrows():
            variant = row["variant"]
            count = row["count"]
            pct = (count / total_traces * 100) if total_traces > 0 else 0

            include = True
            if min_frequency and count < min_frequency:
                include = False
            if min_percentage and pct < min_percentage:
                include = False

            if include:
                filtered_variants.append(variant)

        # Filter log manually
        if filtered_variants:
            filtered_log = PM4PyEventLog()
            for trace in log:
                trace_variant = tuple(event.get("concept:name", "Unknown") for event in trace)
                if trace_variant in filtered_variants:
                    filtered_log.append(trace)
            return filtered_log
        else:
            return PM4PyEventLog()

    except Exception:
        return log


def filter_variants_by_conformance(
    log: EventLog,
    net,
    im,
    fm,
    min_fitness: float = 0.8
) -> EventLog:
    """Filter log to keep only variants with fitness >= threshold.

    Args:
        log: Event log
        net: Petri net model
        im: Initial marking
        fm: Final marking
        min_fitness: Minimum fitness threshold (0-1)

    Returns:
        Filtered event log
    """
    try:
        from pm4py.statistics.traces.generic.log import case_statistics
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog

        # Get variants
        variants = case_statistics.get_variant_statistics(log)

        # Test fitness for each variant
        conforming_variants = []
        for variant_info in variants:
            variant = variant_info["variant"]

            # Filter log to this variant manually
            variant_log = PM4PyEventLog()
            for trace in log:
                trace_variant = tuple(event.get("concept:name", "Unknown") for event in trace)
                if trace_variant == variant:
                    variant_log.append(trace)

            # Check fitness
            try:
                tr = token_replay.apply(variant_log, net, im, fm)
                if isinstance(tr, dict) and "log_fitness" in tr:
                    fitness = tr["log_fitness"]
                elif isinstance(tr, list) and tr:
                    fitness = pd.DataFrame(tr)["trace_fitness"].mean()
                else:
                    fitness = 0

                if fitness >= min_fitness:
                    conforming_variants.append(variant)
            except Exception:
                pass

        # Filter log manually
        if conforming_variants:
            filtered_log = PM4PyEventLog()
            for trace in log:
                trace_variant = tuple(event.get("concept:name", "Unknown") for event in trace)
                if trace_variant in conforming_variants:
                    filtered_log.append(trace)
            return filtered_log
        else:
            return PM4PyEventLog()

    except Exception:
        return log


__all__ = [
    "get_variant_statistics",
    "compute_variant_conformance",
    "compute_variant_coverage",
    "filter_variants_by_frequency",
    "filter_variants_by_conformance",
]
