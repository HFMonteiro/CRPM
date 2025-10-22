import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer

# Add project root to path to import pipeline helpers
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_results.pipeline.discovery import (
    discover_inductive_petri,
    discover_heuristics_net,
    save_pnml,
    save_heuristics_png,
    save_petri_png,
)


def dataframe_to_event_log(df: pd.DataFrame):
    data = df[["case_id", "activity", "event_timestamp"]].copy()
    data = data.rename(columns={
        "case_id": "case:concept:name",
        "activity": "concept:name",
        "event_timestamp": "time:timestamp",
    })
    data["time:timestamp"] = pd.to_datetime(data["time:timestamp"], utc=True, errors="coerce")
    data = data.dropna(subset=["case:concept:name", "concept:name", "time:timestamp"]).sort_values([
        "case:concept:name", "time:timestamp"
    ])
    return log_converter.apply(data, parameters={log_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: "case:concept:name"})


def normalize_events_df(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {c.lower(): c for c in df.columns}
    case = colmap.get("case_id") or colmap.get("case:concept:name") or colmap.get("case")
    act = colmap.get("activity") or colmap.get("concept:name")
    ts = colmap.get("event_timestamp") or colmap.get("timestamp") or colmap.get("time:timestamp")
    if not case or not act or not ts:
        raise RuntimeError("Parquet missing required columns: case_id/activity/event_timestamp")
    df = df.rename(columns={case: "case_id", act: "activity", ts: "event_timestamp"})
    return df


def find_first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def render_activity_plots(events_df: pd.DataFrame, out_dir: Path, tag: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = events_df["activity"].value_counts()
    top = counts.head(40)
    # Bar
    fig, ax = plt.subplots(figsize=(12, 6))
    top.plot(kind="bar", ax=ax, color="#0C5DA5")
    ax.set_title(f"Activity frequency (top 40) [{tag}]")
    ax.set_ylabel("Events")
    ax.set_xlabel("Activity")
    fig.tight_layout()
    fig.savefig(out_dir / f"activity_bar_{tag}.png", dpi=300)
    plt.close(fig)
    # Dot
    ranks = np.arange(1, len(top) + 1)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(ranks, top.values, color="#F37B1D")
    ax.set_title(f"Activity frequency distribution (top 40) [{tag}]")
    ax.set_xlabel("Rank")
    ax.set_ylabel("Events")
    ax.set_xticks(ranks)
    fig.tight_layout()
    fig.savefig(out_dir / f"activity_dot_{tag}.png", dpi=300)
    plt.close(fig)


def discover_for_log(events_df: pd.DataFrame, out_models_dir: Path, out_visuals_dir: Path, tag: str,
                     heur_max_traces: int = 40000, ind_max_traces: int = 60000, ind_time_budget: int = 90) -> Tuple[Path, Path]:
    out_models_dir.mkdir(parents=True, exist_ok=True)
    out_visuals_dir.mkdir(parents=True, exist_ok=True)

    log = dataframe_to_event_log(events_df)

    # DFG
    try:
        dfg_obj = dfg_discovery.apply(log)
        gviz = dfg_visualizer.apply(dfg_obj, log=log)
        dfg_visualizer.save(gviz, str(out_visuals_dir / f"dfg_{tag}.png"))
    except Exception:
        pass

    # Heuristics Miner
    try:
        heu_net = discover_heuristics_net(log, max_traces=heur_max_traces)
        save_heuristics_png(heu_net, str(out_visuals_dir / f"heuristics_{tag}.png"))
    except Exception:
        pass

    # Inductive Miner -> Petri Net PNML + PNG
    net, im, fm = discover_inductive_petri(log, time_budget=ind_time_budget, max_traces=ind_max_traces)
    pnml_path = out_models_dir / f"{tag}.pnml"
    png_path = out_visuals_dir / f"inductive_{tag}.png"
    save_pnml(net, im, fm, str(pnml_path))
    save_petri_png(net, im, fm, str(png_path))

    # Activity plots
    render_activity_plots(events_df, out_visuals_dir, tag)

    return pnml_path, png_path


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Discover models (Inductive + Heuristics) for PRE and POST using existing Parquet cohorts.")
    parser.add_argument("--config", default=None, help="Path to config_FULLdata.json (used for defaults and OUTPUT_ROOT)")
    parser.add_argument("--pre-parquet", default=None, help="Optional override for PRE parquet path")
    parser.add_argument("--post-parquet", default=None, help="Optional override for POST parquet path")
    args = parser.parse_args()

    artigo3_root = ROOT
    agent_results_root = artigo3_root / "agent_results"

    # Load config for potential limits (optional)
    cfg = {}
    if args.config and Path(args.config).exists():
        with open(args.config, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))

    heur_max = int(cfg.get("HEURISTICS_MAX_TRACES", 40000))
    ind_max = int(cfg.get("INDUCTIVE_MAX_TRACES", 60000))
    ind_budget = int(cfg.get("INDUCTIVE_TIME_BUDGET", 90))

    # Locate input Parquet files
    output_root = Path(cfg.get("OUTPUT_ROOT")) if cfg.get("OUTPUT_ROOT") else None
    pre_parquet = Path(args.pre_parquet) if args.pre_parquet else find_first_existing([
        (output_root / "pre_2024" / "cohort_FULLdata" / "events" / f"pre_2024_incident_{cfg.get('FOLLOWUP_DAYS', 365)}d_FULLdata.parquet") if output_root else Path("/__missing__"),
        (output_root / "pre_2024" / "cohort_FULLdata" / "events" / "pre_2024_incident_unbounded_FULLdata.parquet") if output_root else Path("/__missing__"),
        agent_results_root / "pre_2024" / "cohort_FULLdata" / "events" / "pre_2024_incident_365d_FULLdata.parquet",
        agent_results_root / "pre_2024" / "cohort_800k" / "events" / "pre_2024_incident_365d_800k.parquet",
        agent_results_root / "pre_2024" / "events" / "year_2023.parquet",
    ])
    post_parquet = Path(args.post_parquet) if args.post_parquet else find_first_existing([
        (output_root / "post_2024" / "cohort_FULLdata" / "events" / f"post_2024_incident_{cfg.get('FOLLOWUP_DAYS', 365)}d_FULLdata.parquet") if output_root else Path("/__missing__"),
        (output_root / "post_2024" / "cohort_FULLdata" / "events" / "post_2024_incident_unbounded_FULLdata.parquet") if output_root else Path("/__missing__"),
        agent_results_root / "post_2024" / "cohort_FULLdata" / "events" / "post_2024_incident_365d_FULLdata.parquet",
        agent_results_root / "post_2024" / "cohort_800k" / "events" / "post_2024_incident_365d_800k.parquet",
        agent_results_root / "post_2024" / "events" / "year_2024.parquet",
    ])

    if not pre_parquet or not Path(pre_parquet).exists():
        raise SystemExit("PRE parquet not found. Ensure Phase 2/inputs exist.")
    if not post_parquet or not Path(post_parquet).exists():
        raise SystemExit("POST parquet not found. Ensure Phase 2/inputs exist.")

    # Load and normalize event data
    pre_df = normalize_events_df(pd.read_parquet(pre_parquet))
    post_df = normalize_events_df(pd.read_parquet(post_parquet))

    # Output locations (FULLdata cohort-first if present)
    pre_models_dir = (output_root / "pre_2024" / "cohort_FULLdata" / "models") if output_root else (agent_results_root / "pre_2024" / "cohort_FULLdata" / "models")
    post_models_dir = (output_root / "post_2024" / "cohort_FULLdata" / "models") if output_root else (agent_results_root / "post_2024" / "cohort_FULLdata" / "models")
    pre_visuals_dir = (output_root / "pre_2024" / "cohort_FULLdata" / "visuals") if output_root else (agent_results_root / "pre_2024" / "cohort_FULLdata" / "visuals")
    post_visuals_dir = (output_root / "post_2024" / "cohort_FULLdata" / "visuals") if output_root else (agent_results_root / "post_2024" / "cohort_FULLdata" / "visuals")

    # Tags for filenames aligned with analytics expectations
    followup_label = (f"{cfg.get('FOLLOWUP_DAYS', 365)}d" if not cfg.get('FULLDATA_FORWARD_UNLIMITED', False) else "unbounded")
    pre_tag = f"pre_2024_cohort_incident_{followup_label}_FULLdata"
    post_tag = f"post_2024_cohort_incident_{followup_label}_FULLdata"

    # Discover and save
    print(f"Discovering PRE model from {pre_parquet} ...")
    pre_pnml, _ = discover_for_log(pre_df, pre_models_dir, pre_visuals_dir, pre_tag,
                                   heur_max_traces=heur_max, ind_max_traces=ind_max, ind_time_budget=ind_budget)
    print(f"Saved PRE PNML to {pre_pnml}")

    print(f"Discovering POST model from {post_parquet} ...")
    post_pnml, _ = discover_for_log(post_df, post_models_dir, post_visuals_dir, post_tag,
                                    heur_max_traces=heur_max, ind_max_traces=ind_max, ind_time_budget=ind_budget)
    print(f"Saved POST PNML to {post_pnml}")

    print("Phase 3 discovery completed.")


if __name__ == "__main__":
    main()
