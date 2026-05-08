"""Variant analysis for process mining.

This module provides functions for analyzing trace variants and computing
per-variant conformance metrics.
"""

from __future__ import annotations

from typing import Dict, Tuple, Optional
import logging

import pandas as pd

from pm4py.objects.log.obj import EventLog

logger = logging.getLogger(__name__)


VARIANT_STATS_COLUMNS = ["variant", "variant_str", "frequency", "percentage"]
VARIANT_CONFORMANCE_COLUMNS = [
    "variant",
    "frequency",
    "percentage",
    "token_fitness",
    "align_fitness",
    "align_cost",
    "moves_on_model",
    "moves_on_log",
    "perfect_fit_pct",
]


# ---------------------------------------------------------------------------
# Variant Statistics
# ---------------------------------------------------------------------------


def get_variant_statistics(
    log: EventLog,
    top_n: Optional[int] = None,
    variant_index: Optional[tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]] = None,
) -> pd.DataFrame:
    """Get frequency statistics for trace variants.

    Args:
        log: Event log
        top_n: If specified, return only top N most frequent variants

    Returns:
        DataFrame with columns: variant, variant_str, frequency, percentage
    """
    try:
        _, variant_counts = _get_variant_index(log, variant_index)
        return _variant_statistics_from_counts(variant_counts, top_n=top_n)
    except Exception as exc:
        # Fallback: manual variant extraction
        logger.debug("PM4Py variant statistics failed, using manual fallback: %s", exc)
        return _manual_variant_statistics(log, top_n)


def _manual_variant_statistics(log: EventLog, top_n: Optional[int] = None) -> pd.DataFrame:
    """Manually compute variant statistics (fallback if PM4Py fails).

    Args:
        log: Event log
        top_n: If specified, return only top N variants

    Returns:
        DataFrame with variant statistics
    """
    _, variant_counts = _build_variant_index(log)
    return _variant_statistics_from_counts(variant_counts, top_n=top_n)


def _build_variant_index(log: EventLog) -> tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]:
    """Build a grouped trace index and frequency map in one pass."""
    from pm4py.objects.log.obj import EventLog as PM4PyEventLog

    grouped: Dict[Tuple[str, ...], EventLog] = {}
    counts: Dict[Tuple[str, ...], int] = {}
    for trace in log:
        variant = tuple(event.get("concept:name", "Unknown") for event in trace)
        grouped.setdefault(variant, PM4PyEventLog()).append(trace)
        counts[variant] = counts.get(variant, 0) + 1
    return grouped, counts


def build_variant_index(log: EventLog) -> tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]:
    """Build a reusable grouped trace index for downstream variant operations."""
    return _build_variant_index(log)


def _get_variant_index(
    log: EventLog,
    variant_index: Optional[tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]] = None,
) -> tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]:
    if variant_index is not None:
        return variant_index
    return _build_variant_index(log)


def _sample_trace_indices(total: int, sample_size: int, seed_material: str) -> list[int]:
    import random

    if sample_size <= 0 or total <= 0:
        return []
    sample_size = min(sample_size, total)
    rng = random.Random(seed_material)
    return sorted(rng.sample(range(total), sample_size))


def _variant_statistics_from_counts(variant_counts: Dict[Tuple[str, ...], int], top_n: Optional[int] = None) -> pd.DataFrame:
    if not variant_counts:
        return pd.DataFrame(columns=VARIANT_STATS_COLUMNS)

    total_traces = sum(variant_counts.values())
    rows = [
        {
            "variant": variant,
            "variant_str": " → ".join(variant),
            "frequency": count,
            "percentage": (count / total_traces * 100) if total_traces > 0 else 0,
        }
        for variant, count in sorted(variant_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    df = pd.DataFrame(rows, columns=VARIANT_STATS_COLUMNS)
    if top_n is not None:
        df = df.head(top_n)
    return df.reset_index(drop=True)


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
    max_alignment_samples: int = 100,
    variant_index: Optional[tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]] = None,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """Compute conformance metrics for each variant.

    Args:
        log: Event log
        net: Petri net model
        im: Initial marking
        fm: Final marking
        top_n: Number of top variants to analyze
        sample_alignments: If True, sample traces deterministically for both metrics
        max_alignment_samples: Max traces per variant for alignment
        variant_index: Optional precomputed grouped variant index
        random_seed: Optional extra seed to make sampling reproducible across callers

    Returns:
        DataFrame with per-variant conformance metrics
    """
    try:
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog
    except Exception:
        logger.warning("Failed to import PM4Py conformance modules", exc_info=True)
        return pd.DataFrame()

    grouped_variants, variant_counts = _get_variant_index(log, variant_index)
    vdf = _variant_statistics_from_counts(variant_counts, top_n=top_n)

    if vdf.empty:
        return pd.DataFrame(columns=VARIANT_CONFORMANCE_COLUMNS)

    # Compute conformance for each variant
    rows = []
    for idx, row in vdf.iterrows():
        variant = row["variant"]
        frequency = int(row["frequency"])

        variant_log = grouped_variants.get(tuple(variant), PM4PyEventLog())

        # Sample if requested. Keep token replay and alignments on the same subset.
        if sample_alignments and len(variant_log) > max_alignment_samples:
            traces = list(variant_log)
            variant_log_sample = PM4PyEventLog()
            seed_material = repr(
                (
                    tuple(variant) if isinstance(variant, (list, tuple)) else str(variant),
                    random_seed,
                    max_alignment_samples,
                    len(traces),
                )
            )
            sample_indices = _sample_trace_indices(len(traces), max_alignment_samples, seed_material)
            for trace_index in sample_indices:
                variant_log_sample.append(traces[trace_index])
        else:
            variant_log_sample = variant_log

        # Token replay fitness
        try:
            tr = token_replay.apply(variant_log_sample, net, im, fm)
            if isinstance(tr, dict) and "log_fitness" in tr:
                token_fitness = float(tr["log_fitness"])
            elif isinstance(tr, list) and tr and isinstance(tr[0], dict) and "trace_fitness" in tr[0]:
                token_fitness = float(pd.DataFrame(tr)["trace_fitness"].mean())
            else:
                token_fitness = None
        except Exception:
            logger.debug("Token replay failed for variant %d", idx, exc_info=True)
            token_fitness = None

        # Alignments
        try:
            aln = alignments.apply_log(variant_log_sample, net, im, fm)
            if aln:
                adf = pd.DataFrame(aln)
                align_fitness = float(pd.to_numeric(adf.get("fitness", pd.Series([None] * len(adf))), errors="coerce").mean())
                align_cost = float(pd.to_numeric(adf.get("cost", pd.Series([None] * len(adf))), errors="coerce").mean())
                moves_on_model = float(pd.to_numeric(adf.get("bwc", pd.Series([0] * len(adf))), errors="coerce").mean())
                moves_on_log = float(pd.to_numeric(adf.get("bwt", pd.Series([0] * len(adf))), errors="coerce").mean())
                perfect_pct = float((pd.to_numeric(adf.get("fitness", pd.Series([0] * len(adf))), errors="coerce") == 1.0).mean() * 100)
            else:
                align_fitness = align_cost = moves_on_model = moves_on_log = perfect_pct = None
        except Exception:
            logger.debug("Alignment computation failed for variant %d", idx, exc_info=True)
            align_fitness = align_cost = moves_on_model = moves_on_log = perfect_pct = None

        # Variant string
        variant_str = " → ".join(variant) if isinstance(variant, (list, tuple)) else str(variant)

        rows.append(
            {
                "variant": variant_str,
                "frequency": frequency,
                "percentage": (frequency / len(log) * 100) if len(log) > 0 else 0,
                "token_fitness": token_fitness,
                "align_fitness": align_fitness,
                "align_cost": align_cost,
                "moves_on_model": moves_on_model,
                "moves_on_log": moves_on_log,
                "perfect_fit_pct": perfect_pct,
            }
        )

    return pd.DataFrame(rows, columns=VARIANT_CONFORMANCE_COLUMNS)


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
    min_percentage: Optional[float] = None,
    variant_index: Optional[tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]] = None,
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
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog

        grouped_variants, variant_counts = _get_variant_index(log, variant_index)
        total_traces = sum(variant_counts.values())
        if not variant_counts:
            return PM4PyEventLog()

        filtered_log = PM4PyEventLog()
        for variant, count in variant_counts.items():
            pct = (count / total_traces * 100) if total_traces > 0 else 0
            include = True
            if min_frequency and count < min_frequency:
                include = False
            if min_percentage and pct < min_percentage:
                include = False
            if include:
                for trace in grouped_variants.get(variant, PM4PyEventLog()):
                    filtered_log.append(trace)
        return filtered_log

    except Exception:
        logger.warning("Variant frequency filtering failed, returning original log", exc_info=True)
        return log


def filter_variants_by_conformance(
    log: EventLog,
    net,
    im,
    fm,
    min_fitness: float = 0.8,
    variant_index: Optional[tuple[Dict[Tuple[str, ...], EventLog], Dict[Tuple[str, ...], int]]] = None,
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
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.objects.log.obj import EventLog as PM4PyEventLog

        grouped_variants, variant_counts = _get_variant_index(log, variant_index)
        if not variant_counts:
            return PM4PyEventLog()

        conforming_variants = []
        for variant, variant_log in grouped_variants.items():
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
                logger.debug("Token replay failed for variant, skipping", exc_info=True)

        if not conforming_variants:
            return PM4PyEventLog()

        filtered_log = PM4PyEventLog()
        conforming_set = set(conforming_variants)
        for variant, variant_log in grouped_variants.items():
            if variant in conforming_set:
                for trace in variant_log:
                    filtered_log.append(trace)
        return filtered_log

    except Exception:
        logger.warning("Variant conformance filtering failed, returning original log", exc_info=True)
        return log


__all__ = [
    "build_variant_index",
    "get_variant_statistics",
    "compute_variant_conformance",
    "compute_variant_coverage",
    "filter_variants_by_frequency",
    "filter_variants_by_conformance",
]
