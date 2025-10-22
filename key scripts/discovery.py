import os
from typing import Tuple
import time
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.petri_net.exporter import exporter as pnml_exporter
from pm4py.visualization.heuristics_net import visualizer as hn_visualizer
from pm4py.visualization.petri_net import visualizer as pn_visualizer
import shutil
import subprocess


def _sample_log(event_log, max_traces: int):
    if max_traces is None or len(event_log) <= max_traces:
        return event_log
    # Deterministic head sample to avoid heavy random costs
    from pm4py.objects.log.obj import EventLog
    sampled = EventLog()
    for i, trace in enumerate(event_log):
        if i >= max_traces:
            break
        sampled.append(trace)
    return sampled


def discover_inductive_petri(event_log, time_budget: int | None = None, max_traces: int | None = None, start_activity: str | None = None) -> Tuple[object, object, object]:
    start = time.time()
    log_in = _sample_log(event_log, max_traces)
    try:
        variant = getattr(inductive_miner, 'Variants', None)
        if variant and hasattr(variant, 'IMf'):
            process_tree = inductive_miner.apply(log_in, variant=variant.IMf)
        else:
            process_tree = inductive_miner.apply(log_in)
    except Exception:
        # Fallback to default
        process_tree = inductive_miner.apply(log_in)
    net, im, fm = pt_converter.apply(process_tree)
    if time_budget is not None and (time.time() - start) > time_budget:
        # Budget exceeded, caller can decide to skip further work
        raise TimeoutError("Inductive discovery exceeded time budget")
    return net, im, fm


def save_pnml(net, im, fm, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pnml_exporter.apply(net, im, out_path, final_marking=fm)


def discover_heuristics_net(event_log, max_traces: int | None = None, start_activity: str | None = None):
    log_in = _sample_log(event_log, max_traces)
    parameters = None
    if start_activity:
        try:
            parameters = {
                heuristics_miner.Variants.CLASSIC.value.Parameters.START_ACTIVITIES: {start_activity: 1.0}
            }
        except Exception:
            parameters = None
    if parameters:
        return heuristics_miner.apply_heu(log_in, parameters=parameters)
    return heuristics_miner.apply_heu(log_in)


def save_heuristics_png(heu_net, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        gviz = hn_visualizer.apply(heu_net)
        hn_visualizer.save(gviz, out_path)
    except Exception as e:
        # Fallback: write a minimal dot file if Graphviz is unavailable
        dot_path = os.path.splitext(out_path)[0] + ".dot"
        with open(dot_path, "w", encoding="utf-8") as f:
            f.write("digraph G { label=\"Heuristics Net (render failed)\" }")
        # Try to convert DOT to PNG if graphviz 'dot' is available
        try:
            if shutil.which("dot"):
                subprocess.run(["dot", "-Tpng", dot_path, "-o", out_path], check=True)
        except Exception:
            pass


def save_petri_png(net, im, fm, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        gviz = pn_visualizer.apply(net, im, fm)
        pn_visualizer.save(gviz, out_path)
    except Exception:
        # try DOT conversion
        dot_path = os.path.splitext(out_path)[0] + ".dot"
        try:
            gviz = pn_visualizer.apply(net, im, fm)
            with open(dot_path, "w", encoding="utf-8") as f:
                if hasattr(gviz, 'source'):
                    f.write(gviz.source)
                else:
                    f.write("digraph G { label=\"Petri Net (render failed)\" }")
            import shutil, subprocess
            if shutil.which("dot"):
                subprocess.run(["dot", "-Tpng", dot_path, "-o", out_path], check=True)
        except Exception:
            pass
