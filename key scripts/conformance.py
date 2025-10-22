from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.algo.evaluation.generalization import algorithm as generalization
from pm4py.algo.evaluation.precision import algorithm as precision


def token_replay_fitness(log, net, im, fm) -> float:
    """Compute token-based replay fitness."""
    results = token_replay.apply(log, net, im, fm)
    return sum(r["trace_fitness"] for r in results) / len(results)


def alignment_fitness(log, net, im, fm) -> float:
    """Compute alignment-based fitness."""
    results = alignments.apply_log(log, net, im, fm)
    return sum(r["fitness"] for r in results) / len(results)


def precision_metric(log, net, im, fm) -> float:
    """Compute model precision."""
    return precision.evaluate(log, net, im, fm)


def generalization_metric(log, net, im, fm) -> float:
    """Compute model generalization."""
    return generalization.evaluate(log, net, im, fm)


CONFORMANCE_METRICS = {
    "token-replay": token_replay_fitness,
    "alignment": alignment_fitness,
    "precision": precision_metric,
    "generalization": generalization_metric,
}
