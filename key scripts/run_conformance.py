import os
import json
import sys
from pathlib import Path
from typing import List

# Ensure project root on sys.path when running as a script
BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_results.pipeline.io import load_year_eventlog_from_parquet, load_idealized_pnml
from agent_results.pipeline.discovery import (
    discover_inductive_petri,
    discover_heuristics_net,
    save_pnml,
    save_heuristics_png,
)
from agent_results.pipeline.conformance import run_conformance_yearly
from agent_results.pipeline.visuals import (
    alignment_transition_stats,
    transition_fitness_from_stats,
    save_transition_fitness_png,
)


def main():
    # Inputs
    parquet_path = os.path.abspath("agent_results/filtered_log_pre_2024.parquet")
    idealized_pnml = os.path.abspath("IDEALIZED DATASET/idealized_petri_net.pnml")

    # Years to process (2018 forward until 2023 as 'pre_2024')
    years: List[int] = [2018, 2019, 2020, 2021, 2022, 2023]

    # Output structure
    models_dir = os.path.abspath("agent_results/models/pre_2024")
    conf_dir = os.path.abspath("agent_results/conformance/pre_vs_idealized")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(conf_dir, exist_ok=True)

    # Discovery per year (inductive Petri + heuristics)
    discovered_index = []
    for y in years:
        log = load_year_eventlog_from_parquet(parquet_path, y)
        if len(log) == 0:
            continue
        print(f"[discovery] Year {y}: {len(log)} traces")
        # Inductive Miner Petri (fast variant + sampling)
        pnml_out = os.path.join(models_dir, f"inductive_{y}.pnml")
        try:
            net, im, fm = discover_inductive_petri(log, time_budget=25, max_traces=40000)
            save_pnml(net, im, fm, pnml_out)
        except TimeoutError:
            print(f"[discovery] Year {y}: inductive miner timed out; sampling more aggressively")
            net, im, fm = discover_inductive_petri(log, time_budget=None, max_traces=20000)
            save_pnml(net, im, fm, pnml_out)
        except Exception as e:
            print(f"[discovery] Year {y}: inductive miner failed: {e}")
            continue

        # Heuristics Net
        try:
            heu = discover_heuristics_net(log, max_traces=40000)
        except Exception as e:
            print(f"[discovery] Year {y}: heuristics miner failed: {e}")
            heu = None
        hpng_out = os.path.join(models_dir, f"heuristics_{y}.png")
        if heu is not None:
            save_heuristics_png(heu, hpng_out)

        discovered_index.append({"year": y, "inductive_pnml": pnml_out, "heuristics_png": hpng_out})

    with open(os.path.join(models_dir, "discovered_index.json"), "w", encoding="utf-8") as f:
        json.dump(discovered_index, f, indent=2)

    # Load idealized model
    idealized = load_idealized_pnml(idealized_pnml)

    # Conformance (pre vs idealized), batched per-year and time-aware
    def load_log_fn(year: int):
        return load_year_eventlog_from_parquet(parquet_path, year)

    _ = run_conformance_yearly(years, load_log_fn, idealized, conf_dir, max_seconds=25)

    # Visual conformance per year: per-transition fitness heatmap on the idealized net
    from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
    net, im, fm = idealized
    visuals_dir = os.path.abspath("agent_results/conformance_visuals/pre_vs_idealized")
    os.makedirs(visuals_dir, exist_ok=True)
    for y in years:
        log_y = load_log_fn(y)
        # Cap to avoid explosion; doubled cap
        if len(log_y) > 6000:
            from pm4py.objects.log.obj import EventLog
            head = EventLog()
            for i, tr in enumerate(log_y):
                if i >= 6000:
                    break
                head.append(tr)
            log_y = head
        al = alignments.apply_log(log_y, net, im, fm)
        stats = alignment_transition_stats(al)
        fitness_map = transition_fitness_from_stats(stats)
        out_png = os.path.join(visuals_dir, f"conformance_{y}.png")
        save_transition_fitness_png(net, im, fm, fitness_map, out_png)

    print("Done: models in", models_dir)
    print("Done: conformance in", conf_dir)
    print("Done: conformance visuals in", visuals_dir)


if __name__ == "__main__":
    main()
