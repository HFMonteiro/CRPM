#!/usr/bin/env python3
"""
Generate missing figures for article3_v05
- Figure 3: Precision heatmap (cross-evaluation)
- Figure 5: Bottleneck comparison heatmap
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set paths
BASE_PATH = Path(r"C:\Users\hugof\CRPM4Screening\agents_results_1")
OUTPUT_PATH = Path(r"C:\Users\hugof\OneDrive - SPMS - Serviços Partilhados do Ministério da Saúde, EPE\DEP\Rastreios\RCCR\PM_mining\run_R_pm_phd\ARTIGO 3\ARTIGO 3\agent_results\figures")

# Read data
conf_matrix = pd.read_csv(BASE_PATH / "curated" / "conformance" / "conformance_matrix_FULLdata.csv")
bottlenecks_pre = pd.read_csv(BASE_PATH / "curated" / "bottlenecks" / "bottleneck_edges_pre.csv")
bottlenecks_post = pd.read_csv(BASE_PATH / "curated" / "bottlenecks" / "bottleneck_edges_post.csv")

print("Loaded data successfully")
print(f"Conformance matrix: {len(conf_matrix)} rows")
print(f"Bottlenecks PRE: {len(bottlenecks_pre)} rows")
print(f"Bottlenecks POST: {len(bottlenecks_post)} rows")

# ============================================
# FIGURE 3: Precision Heatmap (S1 scenarios)
# ============================================

# Extract S1 scenarios with Inductive Miner only
s1_data = conf_matrix[
    (conf_matrix['scenario'] == 'S1') &
    (conf_matrix['miner'] == 'inductive')
].copy()

# Create pivot table for heatmap
# Rows: Log (PRE, POST), Cols: Model (PRE, POST, Ideal)
# Filter for key scenarios
precision_data = []

for idx, row in s1_data.iterrows():
    log_label = row['log_label'].split()[0]  # 'Pre' or 'Post'
    model_label = row['model_label'].split()[0] + " " + row['model_label'].split()[1] if len(row['model_label'].split()) > 1 else row['model_label'].split()[0]
    prec_value = row['precision_et']

    precision_data.append({
        'Log': log_label,
        'Model': model_label,
        'Precision_ET': prec_value
    })

df_prec = pd.DataFrame(precision_data)
pivot_prec = df_prec.pivot(index='Log', columns='Model', values='Precision_ET')

# Plot heatmap
fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
sns.heatmap(pivot_prec, annot=True, fmt='.3f', cmap='RdYlGn',
            vmin=0.4, vmax=0.7, cbar_kws={'label': 'ETConformance Precision'},
            linewidths=1, linecolor='black', ax=ax)
ax.set_title('Precision Cross-Evaluation (S1 Scenarios - Inductive Miner)', fontsize=14, fontweight='bold')
ax.set_xlabel('Model', fontsize=12)
ax.set_ylabel('Log', fontsize=12)
plt.tight_layout()
plt.savefig(OUTPUT_PATH / "fig3_precision_heatmap.png", dpi=150, bbox_inches='tight')
print("[OK] Generated fig3_precision_heatmap.png")
plt.close()

# ============================================
# FIGURE 5: Bottleneck Comparison
# ============================================

# Merge PRE and POST bottlenecks
bottlenecks_pre['transition'] = bottlenecks_pre['activity'] + ' → ' + bottlenecks_pre['next_activity']
bottlenecks_post['transition'] = bottlenecks_post['activity'] + ' → ' + bottlenecks_post['next_activity']

# Get top 10 transitions by POST median (or combined frequency)
top_transitions = bottlenecks_post.nlargest(10, 'median_s')['transition'].tolist()

# Filter both datasets for these transitions
pre_subset = bottlenecks_pre[bottlenecks_pre['transition'].isin(top_transitions)].copy()
post_subset = bottlenecks_post[bottlenecks_post['transition'].isin(top_transitions)].copy()

# Merge for comparison
pre_subset['period'] = 'PRE (2022-2023)'
post_subset['period'] = 'POST (2024-2025)'
combined = pd.concat([pre_subset, post_subset])

# Convert seconds to hours for readability
combined['median_hours'] = combined['median_s'] / 3600
combined['p90_hours'] = combined['p90_s'] / 3600

# Plot grouped bar chart
fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
transitions_sorted = combined.groupby('transition')['median_hours'].max().nlargest(10).index.tolist()
combined_sorted = combined[combined['transition'].isin(transitions_sorted)]

pivot_bottleneck = combined_sorted.pivot(index='transition', columns='period', values='median_hours')
pivot_bottleneck = pivot_bottleneck.reindex(transitions_sorted)

pivot_bottleneck.plot(kind='barh', ax=ax, color=['#1f77b4', '#ff7f0e'], edgecolor='black')
ax.set_xlabel('Median Dwell Time (hours)', fontsize=12)
ax.set_ylabel('Transition', fontsize=12)
ax.set_title('Top 10 Bottleneck Transitions: PRE vs POST', fontsize=14, fontweight='bold')
ax.legend(title='Period', loc='best')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_PATH / "fig5_bottleneck_comparison.png", dpi=150, bbox_inches='tight')
print("[OK] Generated fig5_bottleneck_comparison.png")
plt.close()

print("\n[SUCCESS] All figures generated successfully!")
print(f"Output location: {OUTPUT_PATH}")
