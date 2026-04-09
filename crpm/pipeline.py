"""High level pipeline utilities for process mining."""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

import pandas as pd
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.discovery.heuristics.algorithm import Variants as HeuristicsVariants
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.evaluation.precision import algorithm as precision_evaluator
from pm4py.algo.filtering.log.timestamp import timestamp_filter
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.petri_net.utils import petri_utils


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


def filter_date_range(
    log: EventLog,
    start: Optional[date],
    end: Optional[date],
    *,
    mode: str = "case",
) -> EventLog:
    """Filter traces by inclusive case-anchor date range or clip events explicitly."""
    if not start and not end:
        return log

    start_dt = datetime.combine(start, datetime.min.time()) if start else datetime.min
    end_dt = datetime.combine(end, datetime.max.time()) if end else datetime.max

    if mode == "event":
        return timestamp_filter.apply_events(log, start_dt, end_dt)

    if mode != "case":
        raise ValueError(f"Unknown date filter mode: {mode}")

    filtered = EventLog()
    for trace in log:
        anchor_ts = None
        for event in trace:
            timestamp = event.get("time:timestamp")
            if isinstance(timestamp, datetime):
                anchor_ts = timestamp
                break
        if anchor_ts is None:
            continue
        if start_dt <= anchor_ts <= end_dt:
            filtered.append(trace)
    return filtered


def split_by_date(log: EventLog, cutoff: date) -> Tuple[EventLog, EventLog]:
    """Split into traces before cutoff day and from cutoff day onward."""
    before_end = date.fromordinal(cutoff.toordinal() - 1)
    before = filter_date_range(log, None, before_end)
    after = filter_date_range(log, cutoff, None)
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

    # Preserve encounter order before shuffling so the split is reproducible across processes.
    case_ids = list(dict.fromkeys(trace.attributes.get("concept:name", str(i)) for i, trace in enumerate(log)))
    total_cases = len(case_ids)

    rng = random.Random(random_seed)
    shuffled_cases = case_ids.copy()
    rng.shuffle(shuffled_cases)

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
    return sum(x.get("trace_fitness", 0) for x in res) / max(len(res), 1)


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
    "split_log_random",
    "discover_heuristics_net",
    "discover_petri_inductive",
    "alignment_fitness",
    "token_replay_fitness",
    "precision",
]

