import argparse
from pathlib import Path
import sys
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Simple builder: reads conformance_analytics.md and builds a PDF with text pages and embeds existing visuals.
# It looks for visuals in OUTPUT_ROOT (from config) and agent_results standard locations.

def parse_md(md_path: Path) -> dict:
    sections = {}
    current = None
    lines = md_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    for ln in lines:
        if ln.startswith('# '):
            current = ln[2:].strip()
            sections[current] = []
        elif ln.startswith('## '):
            current = ln[3:].strip()
            sections[current] = []
        elif ln.startswith('### '):
            current = ln[4:].strip()
            sections[current] = []
        else:
            if current is not None:
                sections[current].append(ln)
    return {k: '\n'.join(v).strip() for k,v in sections.items()}


def add_text_page(pdf: PdfPages, title: str, body: str):
    fig = plt.figure(figsize=(11.69, 8.27), dpi=300)
    ax = fig.add_subplot(111)
    ax.axis('off')
    fig.suptitle(title, fontsize=16, weight='bold')
    ax.text(0.05, 0.95, body, va='top', ha='left', fontsize=10, wrap=True)
    fig.tight_layout(); pdf.savefig(fig); plt.close(fig)


def add_image_if_exists(pdf: PdfPages, title: str, path: Path):
    if path and path.exists():
        fig = plt.figure(figsize=(11.69, 8.27), dpi=300)
        ax = fig.add_subplot(111)
        ax.axis('off')
        fig.suptitle(title, fontsize=16, weight='bold')
        img = plt.imread(str(path))
        ax.imshow(img)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--md', default=None, help='Path to conformance_analytics.md')
    p.add_argument('--config', default=None, help='Path to config_FULLdata.json to resolve OUTPUT_ROOT')
    p.add_argument('--out', default=None, help='Output PDF path')
    args = p.parse_args()

    artigo3_root = Path(__file__).resolve().parents[2]
    md_path = Path(args.md) if args.md else (artigo3_root / 'conformance_analytics.md')
    if not md_path.exists():
        print(f"MD not found: {md_path}")
        sys.exit(2)

    if args.config and Path(args.config).exists():
        import json
        cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
        output_root = Path(cfg.get('OUTPUT_ROOT')) if cfg.get('OUTPUT_ROOT') else None
    else:
        output_root = None

    out_pdf = Path(args.out) if args.out else (artigo3_root / 'conformance analytics.pdf')
    tmp_pdf = out_pdf.with_name(out_pdf.stem + '.tmp.pdf')

    sections = parse_md(md_path)

    with PdfPages(str(tmp_pdf)) as pdf:
        # Cohorts & coverage
        for title_key in ['Conformance analytics — key stats', 'Cohorts', 'Conformance (alignments/token replay)', 'Replay fitness (log-level)', 'Precision', 'POST vs IDEALIZED PRE', 'PRE per-year sizes', 'POST per-year sizes']:
            for k,v in sections.items():
                if k.lower().startswith(title_key.lower()):
                    add_text_page(pdf, k, v)
        # Try to embed visuals if present
        ar = artigo3_root / 'agent_results'
        visuals = []
        # Common snapshots
        if output_root:
            visuals += [
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / f'dfg_pre_2024_cohort_incident_unbounded_FULLdata.png',
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / f'heuristics_pre_2024_cohort_incident_unbounded_FULLdata.png',
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / f'inductive_pre_2024_cohort_incident_unbounded_FULLdata.png',
                output_root / 'post_2024' / 'cohort_FULLdata' / 'visuals' / f'dfg_post_2024_cohort_incident_unbounded_FULLdata.png',
                output_root / 'post_2024' / 'cohort_FULLdata' / 'visuals' / f'heuristics_post_2024_cohort_incident_unbounded_FULLdata.png',
                output_root / 'post_2024' / 'cohort_FULLdata' / 'visuals' / f'inductive_post_2024_cohort_incident_unbounded_FULLdata.png',
            ]
        visuals += [
            ar / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'dfg_pre_2024_cohort_incident_365d_FULLdata.png',
            ar / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'heuristics_pre_2024_cohort_incident_365d_FULLdata.png',
            ar / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'inductive_pre_2024_cohort_incident_365d_FULLdata.png',
            ar / 'post_2024' / 'cohort_FULLdata' / 'visuals' / 'dfg_post_2024_cohort_incident_365d_FULLdata.png',
            ar / 'post_2024' / 'cohort_FULLdata' / 'visuals' / 'heuristics_post_2024_cohort_incident_365d_FULLdata.png',
            ar / 'post_2024' / 'cohort_FULLdata' / 'visuals' / 'inductive_post_2024_cohort_incident_365d_FULLdata.png',
        ]
        # Idealized visuals
        if output_root:
            visuals += [
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'dfg_idealized_pre_2022_2023_unbounded.png',
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'heuristics_idealized_pre_2022_2023_unbounded.png',
                output_root / 'pre_2024' / 'cohort_FULLdata' / 'visuals' / 'inductive_idealized_pre_2022_2023_unbounded.png',
            ]
        for v in visuals:
            add_image_if_exists(pdf, v.stem.replace('_', ' '), v)

    try:
        tmp_pdf.replace(out_pdf)
    except Exception:
        import shutil
        shutil.copyfile(tmp_pdf, out_pdf)
        try:
            tmp_pdf.unlink(missing_ok=True)
        except Exception:
            pass
    print(f"Wrote rebuilt PDF to {out_pdf}")

if __name__ == '__main__':
    main()
