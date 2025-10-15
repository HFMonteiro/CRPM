"""High level pipeline utilities for process mining.

These helpers wrap pm4py functions used in the full notebook so they can be
called programmatically or from a Streamlit interface.
"""

from __future__ import annotations

# ‑‑ standard library
from datetime import datetime, date
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


from datetime import datetime, timedelta  # já deve lá estar, só confirma

def filter_date_range(log: EventLog,
                      start: Optional[date],
                      end:   Optional[date]) -> EventLog:
    # 1) Se não há limite, devolve o log tal‑qual‑é
    if not start and not end:
        return log

    # 2) Constrói os datetimes limite
    start_dt = datetime.combine(start, datetime.min.time()) if start else datetime.min
    end_dt   = datetime.combine(end,   datetime.max.time()) if end   else datetime.max

    # 3) Usa a função correcta da PM4Py para EventLog
    return timestamp_filter.apply_events(log, start_dt, end_dt)


def split_by_date(log: EventLog, cutoff: date) -> Tuple[EventLog, EventLog]:
    before = filter_date_range(log, None, cutoff)
    after = filter_date_range(log, cutoff, None)
    return before, after


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

