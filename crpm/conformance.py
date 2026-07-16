"""Utility functions for process discovery and conformance checking."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.algo.discovery.heuristics.algorithm import Variants
from pm4py.algo.evaluation.replay_fitness import algorithm as fitness_eval
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.obj import EventLog

from crpm.log_filters import filter_date_range

# ---------------------------------------------------------------------------
# Log utilities
# ---------------------------------------------------------------------------


def load_log(file_path: Path | str) -> EventLog:
    """Load a XES log from the given path."""
    return xes_importer.apply(str(file_path))


def load_petri_net_from_pnml(pnml_path: Path | str) -> Tuple[Any, Any, Any]:
    """Load a Petri net from a PNML file.

    Args:
        pnml_path: Path to the PNML file

    Returns:
        Tuple of (net, initial_marking, final_marking)

    Raises:
        Exception: If the file cannot be loaded or parsed
    """
    from pm4py.objects.petri_net.importer import importer as pnml_importer

    try:
        net, initial_marking, final_marking = pnml_importer.apply(str(pnml_path))
        return net, initial_marking, final_marking
    except Exception as e:
        raise Exception(f"Failed to load PNML file from {pnml_path}: {e}")


def inspect_pnml_model(pnml_path: Path | str) -> dict[str, Any]:
    """Load a PNML file and return a path-redacted interoperability report."""

    try:
        net, initial_marking, final_marking = load_petri_net_from_pnml(pnml_path)
    except Exception as exc:
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": "PNML model could not be loaded.",
        }
    return _petri_net_report(net, initial_marking, final_marking, status="ok")


def export_petri_net_to_pnml(net: Any, im: Any, fm: Any, output_path: Path | str) -> dict[str, Any]:
    """Export a Petri net to PNML and return a path-redacted shape report."""

    from pm4py.objects.petri_net.exporter import exporter as pnml_exporter

    pnml_exporter.apply(net, im, str(output_path), final_marking=fm)
    return _petri_net_report(net, im, fm, status="ok")


def _petri_net_report(net: Any, im: Any, fm: Any, *, status: str) -> dict[str, Any]:
    transitions = list(getattr(net, "transitions", []) or [])
    places = list(getattr(net, "places", []) or [])
    arcs = list(getattr(net, "arcs", []) or [])
    labeled_transition_count = sum(1 for transition in transitions if getattr(transition, "label", None))
    return {
        "status": status,
        "transition_count": len(transitions),
        "labeled_transition_count": labeled_transition_count,
        "silent_transition_count": max(len(transitions) - labeled_transition_count, 0),
        "place_count": len(places),
        "arc_count": len(arcs),
        "initial_marking_size": len(im or {}),
        "final_marking_size": len(fm or {}),
        "has_initial_marking": bool(im),
        "has_final_marking": bool(fm),
    }


def filter_start_event(log: EventLog, event_name: str | None) -> EventLog:
    """Return a copy of the log containing only traces starting with `event_name`."""
    if not event_name:
        return log
    filtered = EventLog()
    for trace in log:
        if not trace:
            continue
        first_name = None
        for event in trace:
            value = event.get("concept:name")
            if isinstance(value, str):
                first_name = value
                break
        if first_name == event_name:
            filtered.append(trace)
    return filtered


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def run_heuristics_miner(log: EventLog, variant: Variants = Variants.CLASSIC) -> Tuple[Any, Any, Any, Any]:
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
    fitness = fitness_eval.evaluate(aligned_traces, variant=fitness_eval.Variants.ALIGNMENT_BASED)
    return {"aligned_traces": aligned_traces, "fitness": fitness}


def compute_token_replay(log: EventLog, net, im, fm) -> Dict[str, Any]:
    """Return token replay results and fitness metrics."""
    token_results = token_replay.apply(log, net, im, fm)
    fitness = fitness_eval.evaluate(token_results, variant=fitness_eval.Variants.TOKEN_BASED)
    return {"token_results": token_results, "fitness": fitness}


# ---------------------------------------------------------------------------
# Metrics summary
# ---------------------------------------------------------------------------


def summarize_metrics(align_res: Dict[str, Any], token_res: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dictionary summarizing conformance metrics."""
    return {
        "alignment_fitness": align_res.get("fitness", {}),
        "token_fitness": token_res.get("fitness", {}),
    }


__all__ = [
    "load_log",
    "load_petri_net_from_pnml",
    "inspect_pnml_model",
    "export_petri_net_to_pnml",
    "filter_start_event",
    "filter_date_range",
    "run_heuristics_miner",
    "compute_alignments",
    "compute_token_replay",
    "summarize_metrics",
]
