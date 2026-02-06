"""High level pipeline utilities for process mining.

These helpers wrap pm4py functions used in the full notebook so they can be
called programmatically or from a Streamlit interface.
"""

from __future__ import annotations

# ‑‑ standard library
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

# ‑‑ third‑party
from pm4py.objects.log.obj import EventLog
import pandas as pd
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.util import dataframe_utils
from pm4py.algo.filtering.log.timestamp import timestamp_filter
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.discovery.heuristics.algorithm import Variants as HeuristicsVariants
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.objects.petri_net.exporter import exporter as pnml_exporter
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.evaluation.precision import algorithm as precision_evaluator


# ---------------------------------------------------------------------------
# CSV utilities
# ---------------------------------------------------------------------------


def load_csv(path: Path | str) -> pd.DataFrame:
    """Load a CSV file."""
    return pd.read_csv(path)


def csv_to_event_log(
    df: pd.DataFrame,
    case_col: str,
    activity_col: str,
    timestamp_col: str,
) -> EventLog:
    """Convert a pandas DataFrame into a pm4py EventLog."""
    df = df.rename(
        columns={
            case_col: "case:concept:name",
            activity_col: "concept:name",
            timestamp_col: "time:timestamp",
        }
    )
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
    df = dataframe_utils.convert_timestamp_columns_in_df(df)
    parameters = {
        "case_id_key": "case:concept:name",
        "activity_key": "concept:name",
        "timestamp_key": "time:timestamp",
    }
    return log_converter.apply(df, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters)


# ---------------------------------------------------------------------------
# Log filtering and splitting
# ---------------------------------------------------------------------------


# Re-export from conformance to avoid duplication
from crpm.conformance import filter_date_range as filter_date_range  # noqa: E402


def split_by_date(log: EventLog, cutoff: date) -> Tuple[EventLog, EventLog]:
    """Split log into events strictly before the cutoff and on/after the cutoff."""
    cutoff_start = datetime.combine(cutoff, datetime.min.time())
    before_end = cutoff_start - timedelta(microseconds=1)
    before = timestamp_filter.apply_events(log, datetime.min, before_end)
    after = timestamp_filter.apply_events(log, cutoff_start, datetime.max)
    return before, after


def split_log_random(
    log: EventLog,
    train_ratio: float = 0.8,
    random_seed: int = 42
) -> Tuple[EventLog, EventLog, Dict[str, Any]]:
    """Split event log randomly into training and test sets by case.

    Args:
        log: Event log to split
        train_ratio: Ratio of cases for training (default 0.8 for 80/20 split)
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of (train_log, test_log, split_info)
        where split_info contains statistics about the split
    """
    import random
    from pm4py.objects.log.obj import EventLog as PM4PyEventLog

    # Set random seed for reproducibility
    random.seed(random_seed)

    # Get all case IDs
    case_ids = list(set(trace.attributes.get("concept:name", str(i)) for i, trace in enumerate(log)))
    total_cases = len(case_ids)

    # Shuffle case IDs
    shuffled_cases = case_ids.copy()
    random.shuffle(shuffled_cases)

    # Split into train and test
    train_size = int(total_cases * train_ratio)
    train_case_ids = set(shuffled_cases[:train_size])
    test_case_ids = set(shuffled_cases[train_size:])

    # Create train and test logs
    train_log = PM4PyEventLog()
    test_log = PM4PyEventLog()

    for trace in log:
        case_id = trace.attributes.get("concept:name", "unknown")
        if case_id in train_case_ids:
            train_log.append(trace)
        else:
            test_log.append(trace)

    # Compute statistics
    split_info = {
        "total_cases": total_cases,
        "train_cases": len(train_log),
        "test_cases": len(test_log),
        "train_ratio": len(train_log) / total_cases if total_cases > 0 else 0,
        "test_ratio": len(test_log) / total_cases if total_cases > 0 else 0,
        "train_events": sum(len(trace) for trace in train_log),
        "test_events": sum(len(trace) for trace in test_log),
        "random_seed": random_seed
    }

    return train_log, test_log, split_info


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


def discover_heuristics_net(
    log: EventLog,
    variant: HeuristicsVariants = HeuristicsVariants.CLASSIC,
) -> Tuple[Any, Any, Any, Any]:
    """Return heuristics net and corresponding Petri net."""
    heu_net = heuristics_miner.apply_heu(log, variant=variant)
    net, im, fm = heuristics_miner.apply(log, variant=variant)
    return heu_net, net, im, fm


def discover_petri_inductive(log: EventLog) -> Tuple[Any, Any, Any]:
    """Discover a Petri net using the inductive miner."""
    process_tree = inductive_miner.apply(log)
    net, im, fm = pt_converter.apply(process_tree)
    if not fm or not all(hasattr(p, "name") for p in fm):
        fm = petri_utils.get_final_marking(net)
    return net, im, fm


# ---------------------------------------------------------------------------
# Conformance metrics
# ---------------------------------------------------------------------------


def alignment_fitness(log: EventLog, net, im, fm) -> float:
    res = alignments.apply_log(log, net, im, fm)
    return sum(x.get("fitness", 0) for x in res) / max(len(res), 1)


def token_replay_fitness(log: EventLog, net, im, fm) -> float:
    res = token_replay.apply(log, net, im, fm)
    return sum(x.get("fitness", 0) for x in res) / max(len(res), 1)


def precision(log: EventLog, net, im, fm) -> float:
    return precision_evaluator.apply(
        log,
        net,
        im,
        fm,
        variant=precision_evaluator.Variants.ETCONFORMANCE_TOKEN,
    )


__all__ = [
    "load_csv",
    "csv_to_event_log",
    "filter_date_range",
    "split_by_date",
    "discover_heuristics_net",
    "discover_petri_inductive",
    "alignment_fitness",
    "token_replay_fitness",
    "precision",
]
