from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(r"C:\Users\hugof\CRPM4Screening\agents_results_1\config_FULLdata.json")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def validate_pdf(path: Path) -> None:
    with path.open("rb") as fh:
        header = fh.read(5)
    if header != b"%PDF-":
        raise ValueError(f"Invalid PDF header for {path}")
    if path.stat().st_size < 1024:
        raise ValueError(f"PDF {path} appears too small ({path.stat().st_size} bytes)")


def add_summary_page(pdf: PdfPages, matrix_df: pd.DataFrame, variant_target: float) -> None:
    post_pre = matrix_df[(matrix_df["log_key"] == "post") & (matrix_df["model_key"] == "pre_ind")].iloc[0]
    post_post = matrix_df[(matrix_df["log_key"] == "post") & (matrix_df["model_key"] == "post_ind")].iloc[0]
    ideal_post = matrix_df[(matrix_df["log_key"] == "post") & (matrix_df["model_key"] == "ideal_ind")].iloc[0]

    text_lines = [
        "FULLdata Conformance Analytics",
        "",
        "Key Metrics (Post Cohort):",
        f"• Post vs Post-Inductive – token={post_post['token_fitness']:.4f}, alignment={post_post['alignment_fitness']:.4f}, precision={post_post['precision_et']:.4f}",
        f"• Post vs Pre-Inductive – token={post_pre['token_fitness']:.4f}, alignment={post_pre['alignment_fitness']:.4f}, precision={post_pre['precision_et']:.4f}",
        f"• Post vs Idealized-Inductive – token={ideal_post['token_fitness']:.4f}, alignment={ideal_post['alignment_fitness']:.4f}, precision={ideal_post['precision_et']:.4f}",
        "",
        "Observations:",
        "• Token replay remains ~1.0 across scenarios; drift surfaces in precision when Post runs on Pre models.",
        "• Alignment penalties concentrate on invitation path variants; idealized model achieves perfect precision by design.",
        f"• Variant coverage target: {variant_target:.2f} (see next page).",
    ]
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 portrait
    ax.axis("off")
    y = 0.95
    for line in text_lines:
        ax.text(0.02, y, line, fontsize=12, family="DejaVu Sans")
        y -= 0.04 if line else 0.02
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_heatmaps(pdf: PdfPages, matrix_df: pd.DataFrame) -> None:
    metrics = [
        ("token_fitness", 0.0, 1.0, "Token Replay Fitness"),
        ("alignment_fitness", 0.0, 1.0, "Alignment Fitness"),
        ("precision_et", 0.0, 1.0, "ET Precision"),
    ]
    for metric, vmin, vmax, title in metrics:
        pivot = matrix_df.pivot_table(
            index="log_label",
            columns="model_label",
            values=metric,
            aggfunc="mean",
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(pivot.values, cmap="viridis", vmin=vmin, vmax=vmax)
        ax.set_xticks(range(pivot.shape[1]), pivot.columns, rotation=45, ha="right")
        ax.set_yticks(range(pivot.shape[0]), pivot.index)
        ax.set_title(title)
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                val = pivot.values[i, j]
                if math.isnan(val):
                    display_val = "n/a"
                else:
                    display_val = f"{val:.3f}"
                ax.text(j, i, display_val, ha="center", va="center", color="white", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)


def add_variant_curve(pdf: PdfPages, variant_path: Path, target: float) -> None:
    df = pd.read_csv(variant_path)
    fig, ax = plt.subplots(figsize=(8, 5))
    ranks = np.arange(1, len(df) + 1)
    coverage = df["cum_coverage"]
    ax.plot(ranks, coverage, marker="o", linewidth=2)
    ax.axhline(target, color="red", linestyle="--", label=f"Target {target:.2f}")
    try:
        idx = coverage.searchsorted(target, side="left")
        if idx < len(df):
            ax.scatter([ranks[idx]], [coverage.iloc[idx]], color="red")
            ax.annotate(
                f"Rank {idx+1}\n{coverage.iloc[idx]:.3f}",
                (ranks[idx], coverage.iloc[idx]),
                textcoords="offset points",
                xytext=(10, -10),
                ha="left",
            )
    except Exception:
        pass
    ax.set_xlabel("Variant Rank")
    ax.set_ylabel("Cumulative Coverage")
    ax.set_title("Post Cohort Variant Coverage")
    ax.set_ylim(0, 1.05)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower right")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_dfg_compare(pdf: PdfPages, pre_img: Path, post_img: Path) -> None:
    if not pre_img.exists() or not post_img.exists():
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    for ax, img_path, title in zip(axes, [pre_img, post_img], ["Pre (2022-2023)", "Post (2024-2025)"]):
        img = mpimg.imread(str(img_path))
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(title)
    fig.suptitle("DFG Compare – Invitation Path")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    pdf.savefig(fig)
    plt.close(fig)


def add_alignment_diagnostics(pdf: PdfPages, matrix_df: pd.DataFrame) -> None:
    subset = matrix_df[matrix_df["log_key"] == "post"].copy()
    if subset.empty:
        return
    melted = subset[["model_label", "alignment_moves_log", "alignment_moves_model"]]
    melted = melted.set_index("model_label")
    fig, ax = plt.subplots(figsize=(8, 5))
    width = 0.35
    x = np.arange(len(melted))
    ax.bar(x - width / 2, melted["alignment_moves_log"], width, label="Moves on Log")
    ax.bar(x + width / 2, melted["alignment_moves_model"], width, label="Moves on Model")
    ax.set_xticks(x, melted.index, rotation=30, ha="right")
    ax.set_ylabel("Count")
    ax.set_title("Alignment Diagnostics – Post Cohort")
    ax.legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_transition_performance(pdf: PdfPages, runs_root: Path) -> None:
    run_dirs = sorted(
        (p for p in runs_root.glob("*_phase4_FULLdata") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    pre_df = post_df = None
    for run_dir in run_dirs:
        candidate_pre = run_dir / "bottlenecks_transition_FULLdata_pre.csv"
        candidate_post = run_dir / "bottlenecks_transition_FULLdata_post.csv"
        if candidate_pre.exists() and candidate_post.exists():
            pre_df = pd.read_csv(candidate_pre)
            post_df = pd.read_csv(candidate_post)
            break
    if pre_df is None or post_df is None:
        return
    metrics = [
        (pre_df, "Pre (2022-2023)"),
        (post_df, "Post (2024-2025)"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (df, title) in zip(axes, metrics):
        df_sorted = df.sort_values("mean_h", ascending=False).head(10)
        labels = df_sorted["act"].astype(str) + " → " + df_sorted["next_act"].astype(str)
        ax.barh(labels, df_sorted["mean_h"], color="#4C72B0")
        ax.set_xlabel("Mean Hours")
        ax.set_title(title)
        ax.invert_yaxis()
    fig.suptitle("Transition Performance (Mean Hours)")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    output_root = Path(cfg["OUTPUT_ROOT"]).resolve()
    cohort_name = cfg.get("COHORT_NAME", "FULLdata")

    matrix_path = output_root / "curated" / "conformance" / "conformance_matrix_FULLdata.csv"
    matrix_df = pd.read_csv(matrix_path)
    variant_path = output_root / "results" / cohort_name / "variants_rank_FULLdata.csv"
    variant_target = float(cfg.get("VARIANT_COVERAGE", 0.95))

    pdf_dir = output_root / "pdf" / cohort_name
    ensure_dir(pdf_dir)
    pdf_path = pdf_dir / "conformance_analytics.pdf"

    with PdfPages(pdf_path) as pdf:
        add_summary_page(pdf, matrix_df, variant_target)
        add_heatmaps(pdf, matrix_df)
        add_variant_curve(pdf, variant_path, variant_target)
        discovery_root = output_root / "discovery" / cohort_name
        pre_img = discovery_root / "pre" / "dfg_pre_FULLdata_365d.png"
        post_img = discovery_root / "post" / "dfg_post_FULLdata_365d.png"
        add_dfg_compare(pdf, pre_img, post_img)
        add_alignment_diagnostics(pdf, matrix_df)
        runs_root = output_root / "runs"
        add_transition_performance(pdf, runs_root)

    validate_pdf(pdf_path)
    print(f"Conformance analytics report generated -> {pdf_path}")


if __name__ == "__main__":
    main()
