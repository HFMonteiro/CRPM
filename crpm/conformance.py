"""Utility functions for process discovery and conformance checking."""

from __future__ import annotations

# ‑‑ standard library
from pathlib import Path
from typing import Any, Dict, Tuple

# ‑‑ third‑party
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.discovery.heuristics.algorithm import Variants
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.evaluation.replay_fitness import algorithm as fitness_eval


# ---------------------------------------------------------------------------
# Log utilities
# ---------------------------------------------------------------------------


def load_log(file_path: Path | str) -> EventLog:
    """Load a XES log from the given path."""
    return xes_importer.apply(str(file_path))


def filter_start_event(log: EventLog, event_name: str | None) -> EventLog:
    """Return a copy of the log containing only traces starting with `event_name`."""
    if not event_name:
        return log
    filtered = EventLog()
    for trace in log:
        if trace and trace[0]["concept:name"] == event_name:
            filtered.append(trace)
    return filtered


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def run_heuristics_miner(
    log: EventLog, variant: Variants = Variants.CLASSIC
) -> Tuple[Any, Any, Any, Any]:
    """Discover both a Heuristics Net and a Petri net from the event log."""
    heu_net = heuristics_miner.apply_heu(log, variant=variant)
    net, im, fm = heuristics_miner.apply(log, variant=variant)
    return heu_net, net, im, fm


# ---------------------------------------------------------------------------
# Conformance checking
# ---------------------------------------------------------------------------


def compute_alignments(log: EventLog, net, im, fm) -> Dict[str, Any]:
    """Return alignments and their fitness metrics."""
    aligned_traces = alignments.apply_log(log, net, im, fm)
    fitness = fitness_eval.evaluate(
        aligned_traces, variant=fitness_eval.Variants.ALIGNMENT_BASED
    )
    return {"aligned_traces": aligned_traces, "fitness": fitness}


def compute_token_replay(log: EventLog, net, im, fm) -> Dict[str, Any]:
    """Return token replay results and fitness metrics."""
    token_results = token_replay.apply(log, net, im, fm)
    fitness = fitness_eval.evaluate(
        token_results, variant=fitness_eval.Variants.TOKEN_BASED
    )
    return {"token_results": token_results, "fitness": fitness}


# ---------------------------------------------------------------------------
# Metrics summary
# ---------------------------------------------------------------------------


def summarize_metrics(
    align_res: Dict[str, Any], token_res: Dict[str, Any]
) -> Dict[str, Any]:
    """Return a dictionary summarizing conformance metrics."""
    return {
        "alignment_fitness": align_res.get("fitness", {}),
        "token_fitness": token_res.get("fitness", {}),
    }


__all__ = [
    "load_log",
    "filter_start_event",
    "run_heuristics_miner",
    "compute_alignments",
    "compute_token_replay",
    "summarize_metrics",
]
