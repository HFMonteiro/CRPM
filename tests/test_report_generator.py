from __future__ import annotations

import pandas as pd

from crpm.report_generator import generate_pdf_report


def test_pdf_report_handles_models_without_comparable_metrics() -> None:
    comparison = pd.DataFrame(
        [
            {
                "algorithm": "Inductive Miner",
                "variant": "IMf",
                "alignment_fitness": None,
                "precision": None,
            }
        ]
    )

    payload = generate_pdf_report(
        discovery_results=[
            {
                "algorithm": "Inductive Miner",
                "variant": "IMf",
                "num_transitions": 3,
                "num_places": 4,
                "num_arcs": 6,
                "discovery_time_s": 0.25,
            }
        ],
        comparison_df=comparison,
        case_stats={
            "total_cases": 1,
            "median_duration_s": 86_400,
            "avg_duration_s": 86_400,
            "p90_duration_s": 86_400,
            "max_duration_s": 86_400,
            "std_duration_s": 0,
        },
        activity_stats=pd.DataFrame([{"activity": "FIT", "frequency": 1, "median_duration_s": 86_400, "p90_duration_s": 86_400}]),
        bottleneck_df=pd.DataFrame(
            [{"transition": "FIT -> Colonoscopy", "frequency": 1, "median_duration_s": 86_400, "p90_duration_s": 86_400}]
        ),
        variant_stats=pd.DataFrame(
            [{"variant_str": "FIT -> Colonoscopy", "frequency": 1, "percentage": 100.0}],
            index=["variant-a"],
        ),
        log_summary={"num_cases": 1, "num_events": 2, "num_activities": 2, "num_variants": 1},
        filters_applied={"start_activity": "FIT"},
    )

    assert payload.startswith(b"%PDF")
    assert len(payload) > 1_000
