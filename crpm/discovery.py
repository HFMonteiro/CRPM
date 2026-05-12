"""Multi-algorithm process discovery for model comparison and sensitivity analysis.

This module provides wrappers for multiple discovery algorithms:
- Heuristics Miner (Classic, PLUS variants)
- Inductive Miner (IM, IMf, IMd variants)
- Alpha Miner (Classic, Alpha+ variants)
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging
import time

from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import PetriNet, Marking

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Discovery Result Data Structure
# ---------------------------------------------------------------------------


@dataclass
class DiscoveryResult:
    """Result from a process discovery algorithm."""

    algorithm: str
    variant: str
    net: PetriNet
    initial_marking: Marking
    final_marking: Marking
    discovery_time_s: float
    num_transitions: int
    num_places: int
    num_arcs: int
    heuristics_net: Optional[Any] = None  # For heuristics miner only
    parameter_profile: dict[str, Any] = field(default_factory=dict)


DISCOVERY_PARAMETER_PROFILES: dict[str, dict[str, Any]] = {
    "Heuristics (Classic)": {
        "profile_name": "heuristics-classic-default",
        "algorithm_family": "Heuristics Miner",
        "intended_use": "Dependency-aware discovery for operational logs where noise and loops are expected.",
        "parameters": {
            "dependency_threshold": "pm4py default",
            "and_measure_threshold": "pm4py default",
            "min_activity_count": "pm4py default",
        },
    },
    "Heuristics (PLUS)": {
        "profile_name": "heuristics-plus-default",
        "algorithm_family": "Heuristics Miner",
        "intended_use": "Sensitivity comparison when the installed PM4Py build exposes the PLUS variant.",
        "parameters": {
            "variant": "PLUS when available; Classic fallback otherwise",
            "dependency_threshold": "pm4py default",
        },
    },
    "Inductive (IM)": {
        "profile_name": "inductive-structured",
        "algorithm_family": "Inductive Miner",
        "intended_use": "Structured baseline model discovery with a sound Petri net target.",
        "parameters": {"noise_threshold": "pm4py default", "variant": "IM when available"},
    },
    "Inductive (IMf)": {
        "profile_name": "inductive-noise-aware",
        "algorithm_family": "Inductive Miner",
        "intended_use": "Preferred robust baseline when screening logs contain rare deviations and local noise.",
        "parameters": {"noise_threshold": "pm4py default", "variant": "IMf when available"},
    },
    "Inductive (IMd)": {
        "profile_name": "inductive-dfg-driven",
        "algorithm_family": "Inductive Miner",
        "intended_use": "Directly-follows sensitivity path for comparing with DFG-first readings.",
        "parameters": {"noise_threshold": "pm4py default", "variant": "IMd when available"},
    },
    "Alpha (Classic)": {
        "profile_name": "alpha-classic-baseline",
        "algorithm_family": "Alpha Miner",
        "intended_use": "Didactic baseline and sensitivity check on clean, simple logs.",
        "parameters": {"variant": "Classic"},
    },
    "Alpha+": {
        "profile_name": "alpha-plus-sensitivity",
        "algorithm_family": "Alpha Miner",
        "intended_use": "Sensitivity check when Alpha+ is available in the installed PM4Py build.",
        "parameters": {"variant": "Alpha+ when available; Classic fallback otherwise"},
    },
}


# ---------------------------------------------------------------------------
# Heuristics Miner
# ---------------------------------------------------------------------------


def discover_heuristics_classic(log: EventLog) -> DiscoveryResult:
    """Discover process model using Heuristics Miner (Classic variant).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    from pm4py.algo.discovery.heuristics.algorithm import Variants

    start_time = time.time()

    # Discover heuristics net
    heu_net = heuristics_miner.apply_heu(log, variant=Variants.CLASSIC)

    # Convert to Petri net
    net, im, fm = heuristics_miner.apply(log, variant=Variants.CLASSIC)

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Heuristics Miner",
        variant="Classic",
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
        heuristics_net=heu_net,
    )


def discover_heuristics_plus(log: EventLog) -> DiscoveryResult:
    """Discover process model using Heuristics Miner (PLUS variant).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    from pm4py.algo.discovery.heuristics.algorithm import Variants

    start_time = time.time()

    # Try PLUS variant if available, fallback to CLASSIC
    try:
        variant = Variants.PLUS if hasattr(Variants, "PLUS") else Variants.CLASSIC
        heu_net = heuristics_miner.apply_heu(log, variant=variant)
        net, im, fm = heuristics_miner.apply(log, variant=variant)
        variant_name = "PLUS" if hasattr(Variants, "PLUS") else "Classic"
    except Exception:
        # Fallback to classic variant
        logger.debug("PLUS variant unavailable, falling back to Classic", exc_info=True)
        heu_net = heuristics_miner.apply_heu(log, variant=Variants.CLASSIC)
        net, im, fm = heuristics_miner.apply(log, variant=Variants.CLASSIC)
        variant_name = "Classic (fallback)"

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Heuristics Miner",
        variant=variant_name,
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
        heuristics_net=heu_net,
    )


# ---------------------------------------------------------------------------
# Inductive Miner
# ---------------------------------------------------------------------------


def discover_inductive_im(log: EventLog) -> DiscoveryResult:
    """Discover process model using Inductive Miner (IM variant).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.objects.conversion.process_tree import converter as pt_converter
    from pm4py.objects.petri_net.utils import petri_utils

    start_time = time.time()

    # Discover process tree
    try:
        from pm4py.algo.discovery.inductive.algorithm import Variants

        tree = inductive_miner.apply(log, variant=Variants.IM if hasattr(Variants, "IM") else None)
    except Exception:
        logger.debug("IM variant unavailable, using default", exc_info=True)
        tree = inductive_miner.apply(log)

    # Convert to Petri net
    net, im, fm = pt_converter.apply(tree)

    # Ensure final marking is valid
    if not fm or not all(hasattr(p, "name") for p in fm):
        fm = petri_utils.get_final_marking(net)

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Inductive Miner",
        variant="IM",
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
    )


def discover_inductive_imf(log: EventLog) -> DiscoveryResult:
    """Discover process model using Inductive Miner (IMf variant - handles noise).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.objects.conversion.process_tree import converter as pt_converter
    from pm4py.objects.petri_net.utils import petri_utils

    start_time = time.time()

    # Discover process tree with IMf variant
    try:
        from pm4py.algo.discovery.inductive.algorithm import Variants

        tree = inductive_miner.apply(log, variant=Variants.IMf if hasattr(Variants, "IMf") else Variants.IMF)
        variant_name = "IMf"
    except Exception:
        logger.debug("IMf variant unavailable, using default", exc_info=True)
        tree = inductive_miner.apply(log)
        variant_name = "IM (fallback from IMf)"

    # Convert to Petri net
    net, im, fm = pt_converter.apply(tree)

    # Ensure final marking is valid
    if not fm or not all(hasattr(p, "name") for p in fm):
        fm = petri_utils.get_final_marking(net)

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Inductive Miner",
        variant=variant_name,
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
    )


def discover_inductive_imd(log: EventLog) -> DiscoveryResult:
    """Discover process model using Inductive Miner (IMd variant - directly-follows).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.objects.conversion.process_tree import converter as pt_converter
    from pm4py.objects.petri_net.utils import petri_utils

    start_time = time.time()

    # Discover process tree with IMd variant
    try:
        from pm4py.algo.discovery.inductive.algorithm import Variants

        tree = inductive_miner.apply(log, variant=Variants.IMd if hasattr(Variants, "IMd") else Variants.IMD)
        variant_name = "IMd"
    except Exception:
        logger.debug("IMd variant unavailable, using default", exc_info=True)
        tree = inductive_miner.apply(log)
        variant_name = "IM (fallback from IMd)"

    # Convert to Petri net
    net, im, fm = pt_converter.apply(tree)

    # Ensure final marking is valid
    if not fm or not all(hasattr(p, "name") for p in fm):
        fm = petri_utils.get_final_marking(net)

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Inductive Miner",
        variant=variant_name,
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
    )


# ---------------------------------------------------------------------------
# Alpha Miner
# ---------------------------------------------------------------------------


def discover_alpha_classic(log: EventLog) -> DiscoveryResult:
    """Discover process model using Alpha Miner (Classic variant).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.alpha import algorithm as alpha_miner

    start_time = time.time()

    # Discover using alpha algorithm
    net, im, fm = alpha_miner.apply(log)

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Alpha Miner",
        variant="Classic",
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
    )


def discover_alpha_plus(log: EventLog) -> DiscoveryResult:
    """Discover process model using Alpha+ Miner (enhanced variant).

    Args:
        log: Event log

    Returns:
        DiscoveryResult with discovered model
    """
    from pm4py.algo.discovery.alpha import algorithm as alpha_miner

    start_time = time.time()

    # Try Alpha+ variant if available
    try:
        from pm4py.algo.discovery.alpha.algorithm import Variants

        variant = Variants.ALPHA_PLUS if hasattr(Variants, "ALPHA_PLUS") else None
        if variant:
            net, im, fm = alpha_miner.apply(log, variant=variant)
            variant_name = "Alpha+"
        else:
            net, im, fm = alpha_miner.apply(log)
            variant_name = "Classic"
    except Exception:
        # Fallback to classic
        logger.debug("Alpha+ variant unavailable, falling back to Classic", exc_info=True)
        net, im, fm = alpha_miner.apply(log)
        variant_name = "Classic (fallback)"

    discovery_time = time.time() - start_time

    return DiscoveryResult(
        algorithm="Alpha Miner",
        variant=variant_name,
        net=net,
        initial_marking=im,
        final_marking=fm,
        discovery_time_s=discovery_time,
        num_transitions=len(net.transitions),
        num_places=len(net.places),
        num_arcs=len(net.arcs),
    )


# ---------------------------------------------------------------------------
# Multi-Algorithm Discovery
# ---------------------------------------------------------------------------


AVAILABLE_ALGORITHMS = {
    "Heuristics (Classic)": discover_heuristics_classic,
    "Heuristics (PLUS)": discover_heuristics_plus,
    "Inductive (IM)": discover_inductive_im,
    "Inductive (IMf)": discover_inductive_imf,
    "Inductive (IMd)": discover_inductive_imd,
    "Alpha (Classic)": discover_alpha_classic,
    "Alpha+": discover_alpha_plus,
}


def discover_with_algorithm(log: EventLog, algorithm_name: str) -> Optional[DiscoveryResult]:
    """Discover process model using specified algorithm.

    Args:
        log: Event log
        algorithm_name: Name of algorithm (key from AVAILABLE_ALGORITHMS)

    Returns:
        DiscoveryResult or None if algorithm fails
    """
    if algorithm_name not in AVAILABLE_ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm_name}. Available: {list(AVAILABLE_ALGORITHMS.keys())}")

    try:
        discover_func = AVAILABLE_ALGORITHMS[algorithm_name]
        result = discover_func(log)
        result.parameter_profile = get_algorithm_parameter_profile(
            algorithm_name,
            pm4py_variant=result.variant,
        )
        return result
    except Exception:
        logger.exception("Error discovering with %s", algorithm_name)
        return None


def discover_all_algorithms(log: EventLog, selected_algorithms: Optional[List[str]] = None) -> Dict[str, DiscoveryResult]:
    """Discover process models using multiple algorithms.

    Args:
        log: Event log
        selected_algorithms: List of algorithm names to run. If None, runs all.

    Returns:
        Dictionary mapping algorithm name to DiscoveryResult
    """
    algorithms_to_run = selected_algorithms if selected_algorithms else list(AVAILABLE_ALGORITHMS.keys())

    results = {}
    for algo_name in algorithms_to_run:
        result = discover_with_algorithm(log, algo_name)
        if result:
            results[algo_name] = result

    return results


def list_algorithm_parameter_profiles() -> dict[str, dict[str, Any]]:
    """Return documented PM4Py discovery parameter profiles by UI algorithm key."""

    return {key: dict(value) for key, value in DISCOVERY_PARAMETER_PROFILES.items()}


def get_algorithm_parameter_profile(algorithm_name: str, *, pm4py_variant: str | None = None) -> dict[str, Any]:
    """Return the documented discovery profile for one algorithm key."""

    if algorithm_name not in DISCOVERY_PARAMETER_PROFILES:
        raise ValueError(f"Unknown algorithm profile: {algorithm_name}")
    profile = dict(DISCOVERY_PARAMETER_PROFILES[algorithm_name])
    profile["parameters"] = dict(profile.get("parameters", {}))
    profile["algorithm_key"] = algorithm_name
    profile["pm4py_variant"] = pm4py_variant or str(profile["parameters"].get("variant") or "pm4py default")
    return profile


# ---------------------------------------------------------------------------
# Model Quality Metrics
# ---------------------------------------------------------------------------


def compute_model_complexity(result: DiscoveryResult) -> Dict[str, float]:
    """Compute complexity metrics for a discovered model.

    Args:
        result: DiscoveryResult from discovery

    Returns:
        Dictionary with complexity metrics
    """
    net = result.net

    # Basic counts
    num_transitions = len(net.transitions)
    num_places = len(net.places)
    num_arcs = len(net.arcs)

    # Arc degree (average connections per node)
    total_nodes = num_transitions + num_places
    arc_degree = num_arcs / total_nodes if total_nodes > 0 else 0

    # Control-flow complexity (simplified CFC)
    # CFC approximation: number of decision points (places with multiple outgoing arcs)
    decision_points = sum(1 for p in net.places if len(p.out_arcs) > 1)

    # Connector heterogeneity (mix of split/join types)
    splits = sum(1 for p in net.places if len(p.out_arcs) > 1)
    joins = sum(1 for p in net.places if len(p.in_arcs) > 1)

    return {
        "num_transitions": num_transitions,
        "num_places": num_places,
        "num_arcs": num_arcs,
        "arc_degree": arc_degree,
        "decision_points": decision_points,
        "splits": splits,
        "joins": joins,
        "complexity_score": arc_degree + decision_points,  # Simple complexity metric
    }


__all__ = [
    "DiscoveryResult",
    "AVAILABLE_ALGORITHMS",
    "DISCOVERY_PARAMETER_PROFILES",
    "discover_with_algorithm",
    "discover_all_algorithms",
    "discover_heuristics_classic",
    "discover_heuristics_plus",
    "discover_inductive_im",
    "discover_inductive_imf",
    "discover_inductive_imd",
    "discover_alpha_classic",
    "discover_alpha_plus",
    "get_algorithm_parameter_profile",
    "list_algorithm_parameter_profiles",
    "compute_model_complexity",
]
