"""High level pipeline utilities for process mining."""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Any, Dict

import pandas as pd
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.discovery.heuristics.algorithm import Variants as HeuristicsVariants
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.evaluation.precision import algorithm as precision_evaluator
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.utils import petri_utils

from crpm.log_filters import filter_date_range

# ---------------------------------------------------------------------------
# CSV utilities
# ---------------------------------------------------------------------------


def load_csv(path: Path | str) -> pd.DataFrame:
    """Load a CSV file without inferring away source identifiers."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def csv_to_event_log(
    df: pd.DataFrame,
    case_col: str,
    activity_col: str,
    timestamp_col: str,
) -> EventLog:
    """Convert a pandas DataFrame into a pm4py EventLog."""
    df = _prepare_event_dataframe(df, case_col, activity_col, timestamp_col)
    parameters = {
        "case_id_key": "case:concept:name",
        "activity_key": "concept:name",
        "timestamp_key": "time:timestamp",
    }
    return log_converter.apply(df, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters)


def _prepare_event_dataframe(
    df: pd.DataFrame,
    case_col: str,
    activity_col: str,
    timestamp_col: str,
) -> pd.DataFrame:
    """Validate and normalize a CSV event table before PM4Py conversion."""
    if df.empty:
        raise ValueError("CSV validation failed: file contains no event rows.")

    required = [case_col, activity_col, timestamp_col]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("CSV validation failed: required event columns are missing.")
    if len(set(required)) != 3:
        raise ValueError("CSV validation failed: case, activity, and timestamp columns must be distinct.")

    working = df.copy()
    case_values = working[case_col]
    activity_values = working[activity_col]
    timestamp_values = working[timestamp_col]

    if case_values.isna().any() or case_values.astype(str).str.strip().eq("").any():
        raise ValueError("CSV validation failed: case IDs cannot be null or blank.")
    if activity_values.isna().any() or activity_values.astype(str).str.strip().eq("").any():
        raise ValueError("CSV validation failed: activities cannot be null or blank.")
    if timestamp_values.isna().any() or timestamp_values.astype(str).str.strip().eq("").any():
        raise ValueError("CSV validation failed: timestamps cannot be null or blank.")

    timezone_kinds = {_timestamp_timezone_kind(value) for value in timestamp_values}
    timezone_kinds.discard("unknown")
    if len(timezone_kinds) > 1:
        raise ValueError("CSV validation failed: timestamps mix timezone-aware and timezone-naive values.")

    try:
        parsed_timestamps = pd.to_datetime(
            timestamp_values,
            errors="coerce",
            format="mixed",
            utc=timezone_kinds == {"aware"},
        )
    except TypeError:
        parsed_timestamps = pd.to_datetime(
            timestamp_values,
            errors="coerce",
            utc=timezone_kinds == {"aware"},
        )
    if parsed_timestamps.isna().any():
        raise ValueError("CSV validation failed: timestamp column contains invalid values.")

    working["case:concept:name"] = case_values.astype(str).str.strip()
    working["concept:name"] = activity_values.astype(str).str.strip()
    working["time:timestamp"] = parsed_timestamps
    working["_crpm_original_order"] = range(len(working.index))
    working = working.sort_values(
        by=["case:concept:name", "time:timestamp", "_crpm_original_order"],
        kind="mergesort",
    ).drop(columns=["_crpm_original_order"])
    # The mapped timestamp is already parsed explicitly above.  Running PM4Py's
    # heuristic converter over the full frame can reinterpret numeric-looking
    # case identifiers (for example "0001") as calendar years.
    return working


def _timestamp_timezone_kind(value: Any) -> str:
    if isinstance(value, datetime):
        return "aware" if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None else "naive"
    text = str(value).strip()
    if not text:
        return "unknown"
    if text.endswith("Z") or text.endswith("z"):
        return "aware"
    tail = text[-6:]
    if len(tail) == 6 and tail[0] in {"+", "-"} and tail[1:3].isdigit() and tail[3] == ":" and tail[4:6].isdigit():
        return "aware"
    compact_tail = text[-5:]
    if len(compact_tail) == 5 and compact_tail[0] in {"+", "-"} and compact_tail[1:].isdigit():
        return "aware"
    return "naive"


# ---------------------------------------------------------------------------
# Log filtering and splitting
# ---------------------------------------------------------------------------


def split_by_date(log: EventLog, cutoff: date) -> Tuple[EventLog, EventLog]:
    """Split into traces before cutoff day and from cutoff day onward."""
    before_end = date.fromordinal(cutoff.toordinal() - 1)
    before = filter_date_range(log, None, before_end)
    after = filter_date_range(log, cutoff, None)
    return before, after


def split_log_random(log: EventLog, train_ratio: float = 0.8, random_seed: int = 42) -> Tuple[EventLog, EventLog, Dict[str, Any]]:
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
        "random_seed": random_seed,
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
