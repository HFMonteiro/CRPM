import json, csv
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

import pandas as pd
import math

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "1200k"
CURATED = ROOT / "curated" / "metrics"
RUNS = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}_phase4_1200k"

RESULTS.mkdir(parents=True, exist_ok=True)
CURATED.mkdir(parents=True, exist_ok=True)
RUNS.mkdir(parents=True, exist_ok=True)


@dataclass
class Params:
    incident_split_date: str = "2024-01-01"
    followup_days: int = 365
    cap_events: int = 1_200_000
    rng_seed: int = 42


@dataclass
class Inputs:
    baseline_pre_pnml: Path
    idealized_pnml: Optional[Path]
    pre_xes: Path
    post_xes: Path
    post_2024_xes: Optional[Path] = None
    post_2025_xes: Optional[Path] = None


@dataclass
class ConformanceRow:
    scenario: str
    token_fitness: float
    align_fitness: float
    align_avg_cost: float
    precision_et: float
    perfect_pct: float
    moves_on_model: float
    moves_on_log: float


def load_log(xes_path: Path):
    from pm4py.objects.log.importer.xes import importer as xes_importer
    return xes_importer.apply(str(xes_path))


def load_pnml(p: Path):
    from pm4py.objects.petri_net.importer import importer as pnml_importer
    return pnml_importer.apply(str(p))


def token_fit(log, net, im, fm) -> float:
    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
    res = token_replay.apply(log, net, im, fm)
    if isinstance(res, dict) and "log_fitness" in res:
        return float(res["log_fitness"])
    if isinstance(res, list) and res and isinstance(res[0], dict) and "trace_fitness" in res[0]:
        return float(pd.DataFrame(res)["trace_fitness"].mean())
    return float("nan")


def align_summary(log, net, im, fm, sample: int = 5000, seed: int = 42) -> Tuple[float, float, float, float, float]:
    import random
    from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
    traces = list(log)
    if len(traces) > sample:
        random.seed(seed)
        traces = random.sample(traces, sample)
    res = alignments.apply_log(traces, net, im, fm)
    if not res:
        return float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
    df = pd.DataFrame(res)
    fit = float(pd.to_numeric(df.get("fitness", pd.Series([float("nan")]*len(df)))).mean())
    cost = float(pd.to_numeric(df.get("cost", pd.Series([float("nan")]*len(df)))).mean())
    mom = float(pd.to_numeric(df.get("moves_on_model", pd.Series([0]*len(df)))).mean())
    mol = float(pd.to_numeric(df.get("moves_on_log", pd.Series([0]*len(df)))).mean())
    perf = float((df.get("fitness", pd.Series([0]*len(df))) == 1.0).mean())
    return fit, cost, mom, mol, perf


def precision_et(log, net, im, fm) -> float:
    try:
        from pm4py.algo.evaluation.precision import algorithm as et_precision
        return float(et_precision.apply(log, net, im, fm))
    except Exception:
        return float("nan")


def variant_stats(log, net, im, fm, top_n: int = 20, seed: int = 42) -> pd.DataFrame:
    """Compute per-variant token fitness and alignment summary for top-N variants by frequency."""
    try:
        from pm4py.statistics.traces.generic.log import case_statistics
        from pm4py.objects.log.util import sampling
        from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
        from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
    except Exception:
        return pd.DataFrame()

    # get variants and frequencies
    variants = case_statistics.get_variant_statistics(log)
    vdf = pd.DataFrame(variants)
    if vdf.empty:
        return vdf
    vdf = vdf.sort_values("count", ascending=False).head(top_n).reset_index(drop=True)

    rows = []
    for _, row in vdf.iterrows():
        var = row["variant"]
        freq = int(row["count"])
        v_log = sampling.filter_log_by_variants(log, [var])
        # token replay fitness for this variant
        try:
            tr = token_replay.apply(v_log, net, im, fm)
            if isinstance(tr, dict) and "log_fitness" in tr:
                tf = float(tr["log_fitness"])
            elif isinstance(tr, list) and tr and isinstance(tr[0], dict) and "trace_fitness" in tr[0]:
                tf = float(pd.DataFrame(tr)["trace_fitness"].mean())
            else:
                tf = float("nan")
        except Exception:
            tf = float("nan")
        # alignments summary for this variant
        try:
            aln = alignments.apply_log(v_log, net, im, fm)
            adf = pd.DataFrame(aln)
            afit = float(pd.to_numeric(adf.get("fitness", pd.Series([float("nan")]*len(adf)))).mean())
            acost = float(pd.to_numeric(adf.get("cost", pd.Series([float("nan")]*len(adf)))).mean())
            amom = float(pd.to_numeric(adf.get("moves_on_model", pd.Series([0]*len(adf)))).mean())
            amol = float(pd.to_numeric(adf.get("moves_on_log", pd.Series([0]*len(adf)))).mean())
            aperf = float((adf.get("fitness", pd.Series([0]*len(adf))) == 1.0).mean())
        except Exception:
            afit = acost = amom = amol = aperf = float("nan")
        rows.append({
            "variant": var,
            "frequency": freq,
            "token_fitness": tf,
            "align_fitness": afit,
            "align_avg_cost": acost,
            "moves_on_model": amom,
            "moves_on_log": amol,
            "perfect_pct": aperf,
        })
    return pd.DataFrame(rows)


def variant_trace_alignments(
    log,
    net,
    im,
    fm,
    top_n: int = 20,
    max_traces_per_variant: int = 200,
    seed: int = 42,
):
    """Return per-trace alignment metrics for sampled traces of the top-N variants.

    Columns: variant, trace_index, fitness, cost, moves_on_model, moves_on_log, is_perfect
    """
    try:
        from pm4py.statistics.traces.generic.log import case_statistics
        from pm4py.objects.log.util import sampling
        from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
    except Exception:
        return pd.DataFrame()

    variants = case_statistics.get_variant_statistics(log)
    vdf = pd.DataFrame(variants)
    if vdf.empty:
        return vdf
    vdf = vdf.sort_values("count", ascending=False).head(top_n).reset_index(drop=True)

    recs = []
    for _, row in vdf.iterrows():
        var = row["variant"]
        v_log = sampling.filter_log_by_variants(log, [var])
        # sample up to max_traces_per_variant traces
        traces = list(v_log)
        if len(traces) > max_traces_per_variant:
            import random
            random.seed(seed)
            traces = random.sample(traces, max_traces_per_variant)
        try:
            aln = alignments.apply_log(traces, net, im, fm)
        except Exception:
            aln = []
        if not aln:
            continue
        adf = pd.DataFrame(aln)
        # Compose a safe row per trace
        for i in range(len(adf)):
            recs.append({
                "variant": var,
                "trace_index": i,
                "fitness": float(pd.to_numeric(adf.get("fitness").iloc[i]) if "fitness" in adf else float("nan")),
                "cost": float(pd.to_numeric(adf.get("cost").iloc[i]) if "cost" in adf else float("nan")),
                "moves_on_model": float(pd.to_numeric(adf.get("moves_on_model").iloc[i]) if "moves_on_model" in adf else float("nan")),
                "moves_on_log": float(pd.to_numeric(adf.get("moves_on_log").iloc[i]) if "moves_on_log" in adf else float("nan")),
                "is_perfect": 1.0 if ("fitness" in adf and adf.get("fitness").iloc[i] == 1.0) else 0.0,
            })
    return pd.DataFrame(recs)


def write_curated(suffix: str, rows: List[ConformanceRow]):
    with open(CURATED / f"metrics_token_replay_{suffix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["scenario","token_fitness"]) 
        for r in rows: w.writerow([r.scenario, f"{r.token_fitness:.6f}"])
    with open(CURATED / f"metrics_precision_et_{suffix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["scenario","precision_et"]) 
        for r in rows: w.writerow([r.scenario, f"{r.precision_et:.6f}"])
    with open(CURATED / f"metrics_alignment_{suffix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["scenario","align_fitness","align_avg_cost","moves_on_model","moves_on_log","perfect_pct"]) 
        for r in rows: w.writerow([r.scenario, f"{r.align_fitness:.6f}", f"{r.align_avg_cost:.6f}", f"{r.moves_on_model:.6f}", f"{r.moves_on_log:.6f}", f"{r.perfect_pct:.6f}"])


def write_results(name: str, rows: List[ConformanceRow]):
    recs = [asdict(r) for r in rows]
    (RESULTS / f"{name}.json").write_text(json.dumps(recs, indent=2), encoding="utf-8")
    pd.DataFrame(recs).to_csv(RESULTS / f"{name}.csv", index=False)


def _first_existing(paths):
    for p in paths:
        if p and p.exists():
            return p
    return None


def _save_pn_png(net, im, fm, out_path: Path):
    try:
        from pm4py.visualization.petri_net import visualizer as pn_viz
        g = pn_viz.apply(net, im, fm); pn_viz.save(g, str(out_path)); return True
    except Exception:
        return False


def main():
    params = Params()
    (RUNS / "params.json").write_text(json.dumps(asdict(params), indent=2), encoding="utf-8")

    baseline_candidates = [
        ROOT / "pre_2024" / "cohort_1200k" / "models" / "pre_2024_cohort_incident_365d_1200k.pnml",
        ROOT / "agent_results" / "pre_2024" / "cohort_1200k" / "models" / "pre_2024_cohort_incident_365d_1200k.pnml",
    ]
    ideal_candidates = [
        ROOT / "idealized" / "idealized_petri_net.pnml",
        ROOT / "CONFORMANCE BASIS" / "petri_ideal.pnml",
    ]
    pre_xes_candidates = [
        ROOT / "pre_2024" / "cohort_1200k" / "events" / "pre_2024_incident_365d_1200k.xes",
        ROOT / "agent_results" / "pre_2024" / "cohort_1200k" / "events" / "pre_2024_incident_365d_1200k.xes",
    ]
    post_xes_candidates = [
        ROOT / "post_2024" / "cohort_1200k" / "events" / "post_2024_incident_365d_1200k.xes",
        ROOT / "agent_results" / "post_2024" / "cohort_1200k" / "events" / "post_2024_incident_365d_1200k.xes",
    ]
    post_2024_candidates = [
        ROOT / "post_2024" / "per_year_1200k" / "2024" / "events" / "post_2024_1200k.xes",
        ROOT / "agent_results" / "post_2024" / "per_year_1200k" / "2024" / "events" / "post_2024_1200k.xes",
    ]
    post_2025_candidates = [
        ROOT / "post_2024" / "per_year_1200k" / "2025" / "events" / "post_2025_1200k.xes",
        ROOT / "agent_results" / "post_2024" / "per_year_1200k" / "2025" / "events" / "post_2025_1200k.xes",
    ]

    inputs = Inputs(
        baseline_pre_pnml=_first_existing(baseline_candidates) or baseline_candidates[0],
        idealized_pnml=_first_existing(ideal_candidates),
        pre_xes=_first_existing(pre_xes_candidates) or pre_xes_candidates[0],
        post_xes=_first_existing(post_xes_candidates) or post_xes_candidates[0],
        post_2024_xes=_first_existing(post_2024_candidates),
        post_2025_xes=_first_existing(post_2025_candidates),
    )

    inv = []
    for p in [inputs.baseline_pre_pnml, inputs.pre_xes, inputs.post_xes]:
        inv.append((str(p), p.exists()))
    for p in [inputs.idealized_pnml, inputs.post_2024_xes, inputs.post_2025_xes]:
        if p is not None:
            inv.append((str(p), p.exists()))
    (RUNS / "inventory_paths.txt").write_text("\n".join([f"{ok}\t{path}" for path, ok in inv]), encoding="utf-8")

    missing = [path for path, ok in inv if not ok]
    if missing:
        (RUNS / "checks_report.csv").write_text("status,message\nFAIL,missing inputs; run Phases 2/3 1200k\n", encoding="utf-8")
        raise SystemExit("Missing inputs:\n - " + "\n - ".join(missing))
    (RUNS / "checks_report.csv").write_text("status,message\nOK,inputs present\n", encoding="utf-8")

    net_pre, im_pre, fm_pre = load_pnml(inputs.baseline_pre_pnml)
    ideal_net = ideal_im = ideal_fm = None
    if inputs.idealized_pnml and inputs.idealized_pnml.exists():
        ideal_net, ideal_im, ideal_fm = load_pnml(inputs.idealized_pnml)
    pre_log = load_log(inputs.pre_xes)
    post_log = load_log(inputs.post_xes)

    rows: List[ConformanceRow] = []
    tf = token_fit(post_log, net_pre, im_pre, fm_pre)
    af, cost, mom, mol, perf = align_summary(post_log, net_pre, im_pre, fm_pre)
    pt = precision_et(post_log, net_pre, im_pre, fm_pre)
    rows.append(ConformanceRow(
        scenario="Post log on Pre-incident model (incident, 365d, 1200k)",
        token_fitness=tf, align_fitness=af, align_avg_cost=cost,
        precision_et=pt, perfect_pct=perf, moves_on_model=mom, moves_on_log=mol
    ))
    tf = token_fit(pre_log, net_pre, im_pre, fm_pre)
    af, cost, mom, mol, perf = align_summary(pre_log, net_pre, im_pre, fm_pre)
    pt = precision_et(pre_log, net_pre, im_pre, fm_pre)
    rows.append(ConformanceRow(
        scenario="Pre log on Pre-incident model (incident, 365d, 1200k)",
        token_fitness=tf, align_fitness=af, align_avg_cost=cost,
        precision_et=pt, perfect_pct=perf, moves_on_model=mom, moves_on_log=mol
    ))
    write_results("pre_vs_post_incident_365d_1200k", rows)

    rows_b: List[ConformanceRow] = []
    if ideal_net is None:
        ideal_net, ideal_im, ideal_fm = net_pre, im_pre, fm_pre
    tf = token_fit(post_log, ideal_net, ideal_im, ideal_fm)
    af, cost, mom, mol, perf = align_summary(post_log, ideal_net, ideal_im, ideal_fm)
    pt = precision_et(post_log, ideal_net, ideal_im, ideal_fm)
    row_b = ConformanceRow(
        scenario="Idealized model on Post log (incident, 365d, 1200k)",
        token_fitness=tf, align_fitness=af, align_avg_cost=cost,
        precision_et=pt, perfect_pct=perf, moves_on_model=mom, moves_on_log=mol
    )
    rows_b.append(row_b)
    (RESULTS / "alignment_stats_incident_365d_1200k.json").write_text(json.dumps(asdict(row_b), indent=2), encoding="utf-8")
    _save_pn_png(ideal_net, ideal_im, ideal_fm, RESULTS / "transition_fitness_1200k.png")
    write_results("idealized_vs_post_incident_365d_1200k", rows_b)

    # variant-level statistics for key scenarios (top-N variants)
    try:
        vpost = variant_stats(post_log, ideal_net, ideal_im, ideal_fm, top_n=20)
        if not vpost.empty:
            vpost.to_csv(RESULTS/"variants_post_on_ideal_1200k.csv", index=False)
        vpre = variant_stats(pre_log, net_pre, im_pre, fm_pre, top_n=20)
        if not vpre.empty:
            vpre.to_csv(RESULTS/"variants_pre_on_preModel_1200k.csv", index=False)
        tpost = variant_trace_alignments(post_log, ideal_net, ideal_im, ideal_fm, top_n=20, max_traces_per_variant=200)
        if not tpost.empty:
            tpost.to_csv(RESULTS/"trace_alignments_post_on_ideal_1200k.csv", index=False)
        tpre = variant_trace_alignments(pre_log, net_pre, im_pre, fm_pre, top_n=20, max_traces_per_variant=200)
        if not tpre.empty:
            tpre.to_csv(RESULTS/"trace_alignments_pre_on_preModel_1200k.csv", index=False)
    except Exception:
        pass

    rows_c: List[ConformanceRow] = []
    for year, xes in [(2024, inputs.post_2024_xes), (2025, inputs.post_2025_xes)]:
        if xes and xes.exists():
            ylog = load_log(xes)
            tf = token_fit(ylog, ideal_net, ideal_im, ideal_fm)
            af, cost, mom, mol, perf = align_summary(ylog, ideal_net, ideal_im, ideal_fm)
            pt = precision_et(ylog, ideal_net, ideal_im, ideal_fm)
            rows_c.append(ConformanceRow(
                scenario=f"Idealized on Post {year} (incident, 365d, 1200k)",
                token_fitness=tf, align_fitness=af, align_avg_cost=cost,
                precision_et=pt, perfect_pct=perf, moves_on_model=mom, moves_on_log=mol
            ))
    if rows_c:
        write_results("post_per_year_conformance_1200k", rows_c)

    write_curated("1200k", rows + rows_b + rows_c)
    print("[OK] Phase 4 (1200k) conformance metrics written to curated and results/1200k.")


if __name__ == "__main__":
    main()
