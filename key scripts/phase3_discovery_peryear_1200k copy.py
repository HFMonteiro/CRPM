from pathlib import Path
import pandas as pd
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.petri_net.exporter import exporter as pnml_exporter
from pm4py.visualization.petri_net import visualizer as pn_viz
from pm4py.algo.discovery.dfg import algorithm as dfg_disc
from pm4py.visualization.dfg import visualizer as dfg_viz
from pm4py.algo.discovery.inductive import algorithm as inductive
from pm4py.objects.conversion.process_tree import converter as pt_converter

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "pre_2024" / "cohort_1200k"
POST = ROOT / "post_2024"

for p in [PRE/"discovery", PRE/"visuals", POST/"per_year_1200k"]:
    p.mkdir(parents=True, exist_ok=True)


def to_event_log(df: pd.DataFrame):
    parms = {"case_id_key": "case:concept:name", "activity_key": "concept:name", "timestamp_key": "time:timestamp"}
    return log_converter.apply(df, parameters=parms)


def activity_visuals(df: pd.DataFrame, out_dir: Path):
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = df["concept:name"].value_counts().sort_values(ascending=False)
    plt.figure(figsize=(10,4)); counts.head(25).plot(kind="bar"); plt.title("Activity frequency (top 25)")
    plt.tight_layout(); plt.savefig(out_dir/"activity_bar_1200k.png"); plt.close()
    work = df[["case:concept:name","concept:name","time:timestamp"]].sort_values(["case:concept:name","time:timestamp"]).copy()
    work["event_idx"] = work.groupby("case:concept:name").cumcount()+1
    acts = {a:i for i,a in enumerate(sorted(work["concept:name"].unique()))}
    work["act_i"] = work["concept:name"].map(acts)
    plt.figure(figsize=(10,5)); plt.scatter(work["event_idx"], work["act_i"], s=3, alpha=0.3)
    plt.title("Activity dot plot"); plt.tight_layout(); plt.savefig(out_dir/"activity_dot_1200k.png"); plt.close()


def discover_pn(log):
    tree_or_tuple = inductive.apply(log)
    if isinstance(tree_or_tuple, tuple) and len(tree_or_tuple) == 3:
        return tree_or_tuple
    net, im, fm = pt_converter.apply(tree_or_tuple)
    return net, im, fm


def export_year(log, base_dir: Path, year: int, name_prefix: str):
    ydir = base_dir / "per_year_1200k" / str(year)
    (ydir/"events").mkdir(parents=True, exist_ok=True)
    (ydir/"discovery").mkdir(parents=True, exist_ok=True)
    (ydir/"visuals").mkdir(parents=True, exist_ok=True)
    from pm4py.objects.log.exporter.xes import exporter as xes_exporter
    xes = ydir/"events"/f"{name_prefix}_{year}_1200k.xes"
    xes_exporter.apply(log, str(xes))
    try:
        dfg = dfg_disc.apply(log)
        gviz = dfg_viz.apply(dfg, log=log, variant=dfg_viz.Variants.FREQUENCY)
        dfg_viz.save(gviz, str(ydir/"discovery"/"dfg_1200k.png"))
    except Exception as e:
        (ydir/"discovery"/"dfg_error.txt").write_text(str(e), encoding="utf-8")
    net, im, fm = discover_pn(log)
    try:
        g = pn_viz.apply(net, im, fm)
        pn_viz.save(g, str(ydir/"discovery"/"inductive_1200k.png"))
    except Exception as e:
        (ydir/"discovery"/"petrinet_viz_error.txt").write_text(str(e), encoding="utf-8")
    pnml_exporter.apply(net, im, str(ydir/"discovery"/"inductive_1200k.pnml"), final_marking=fm)
    try:
        import pm4py
        df = pm4py.convert_to_dataframe(log)
        activity_visuals(df, ydir/"visuals")
    except Exception as e:
        (ydir/"visuals"/"activity_viz_error.txt").write_text(str(e), encoding="utf-8")


def main():
    pre_parquet = PRE/"events"/"pre_2024_incident_365d_1200k.parquet"
    if not pre_parquet.exists():
        raise SystemExit(f"Missing {pre_parquet} (run Phase 2 1200k)")
    pre_df = pd.read_parquet(pre_parquet)
    pre_log = to_event_log(pre_df)
    net, im, fm = discover_pn(pre_log)
    (PRE/"models").mkdir(exist_ok=True)
    pnml = PRE/"models"/"pre_2024_cohort_incident_365d_1200k.pnml"
    pnml_exporter.apply(net, im, str(pnml), final_marking=fm)
    try:
        g = pn_viz.apply(net, im, fm)
        pn_viz.save(g, str(PRE/"discovery"/"inductive_1200k.png"))
    except Exception as e:
        (PRE/"discovery"/"petrinet_viz_error.txt").write_text(str(e), encoding="utf-8")
    try:
        dfg = dfg_disc.apply(pre_log)
        gviz = dfg_viz.apply(dfg, log=pre_log, variant=dfg_viz.Variants.FREQUENCY)
        dfg_viz.save(gviz, str(PRE/"discovery"/"dfg_1200k.png"))
    except Exception as e:
        (PRE/"discovery"/"dfg_error.txt").write_text(str(e), encoding="utf-8")
    try:
        activity_visuals(pre_df, PRE/"visuals")
    except Exception as e:
        (PRE/"visuals"/"activity_viz_error.txt").write_text(str(e), encoding="utf-8")

    post_parquet = ROOT/"post_2024"/"cohort_1200k"/"events"/"post_2024_incident_365d_1200k.parquet"
    if not post_parquet.exists():
        raise SystemExit(f"Missing {post_parquet} (run Phase 2 1200k)")
    post_df = pd.read_parquet(post_parquet)
    post_df["year"] = pd.to_datetime(post_df["time:timestamp"]).dt.year
    for year in [2024, 2025]:
        ydf = post_df[post_df["year"] == year].copy()
        if ydf.empty:
            continue
        ylog = to_event_log(ydf)
        export_year(ylog, ROOT/"post_2024", year, "post")
    print("Phase 3 (1200k) discovery/per-year complete")

if __name__ == "__main__":
    main()
