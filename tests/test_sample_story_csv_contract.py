from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "examples" / "screening_conformance_demo.csv"


def _sample_frame() -> pd.DataFrame:
    frame = pd.read_csv(SAMPLE_CSV, parse_dates=["timestamp"])
    return frame.sort_values(["case_id", "timestamp"], kind="stable")


def test_sample_csv_contains_no_show_reschedule_story() -> None:
    frame = _sample_frame()
    matching_cases = 0

    for _, case_events in frame.groupby("case_id", sort=False):
        activities = case_events["activity"].tolist()
        if "Colonoscopy_no_show" not in activities:
            continue
        no_show_index = activities.index("Colonoscopy_no_show")
        if "Colonoscopy_center" in activities[no_show_index + 1 :]:
            matching_cases += 1

    assert matching_cases > 0


def test_sample_csv_contains_lab_rejection_resubmission_story() -> None:
    frame = _sample_frame()
    matching_cases = 0

    for _, case_events in frame.groupby("case_id", sort=False):
        activities = case_events["activity"].tolist()
        if "Lab_rejection" not in activities:
            continue
        rejection_index = activities.index("Lab_rejection")
        if {"Lab_return", "Lab_result"}.intersection(activities[rejection_index + 1 :]):
            matching_cases += 1

    assert matching_cases > 0


def test_sample_csv_keeps_pre_post_and_variant_richness() -> None:
    frame = _sample_frame()

    assert frame["case_id"].nunique() >= 900
    assert {"PRE", "POST"}.issubset(set(frame["phase"]))
    assert frame["variant_hint"].nunique() >= 10
