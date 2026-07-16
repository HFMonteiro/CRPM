from collections import Counter

import pandas as pd
from pm4py.objects.log.importer.xes import importer as xes_importer

from crpm.pipeline import csv_to_event_log
from crpm.synthetic_screening import DOMINANT_PATH, VARIANT_PROFILES, generate_screening_demo, main


def test_generate_screening_demo_is_deterministic_and_story_rich() -> None:
    first = generate_screening_demo(cases=36, seed=7)
    second = generate_screening_demo(cases=36, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert {"case_id", "activity", "timestamp", "phase", "variant_hint"}.issubset(first.columns)
    assert set(first["phase"]) == {"PRE", "POST"}
    assert {"lab_rejection_resubmit", "no_show_reschedule", "dominant"}.issubset(set(first["variant_hint"]))
    variants = Counter(tuple(group["activity"]) for _, group in first.groupby("case_id", sort=False))
    assert DOMINANT_PATH in variants


def test_generate_screening_demo_has_a_controlled_long_tail() -> None:
    frame = generate_screening_demo(cases=1_200, seed=42)
    case_profiles = frame.groupby("case_id", sort=False)["variant_hint"].first()
    shares = case_profiles.value_counts(normalize=True).mul(100)

    assert case_profiles.nunique() == len(VARIANT_PROFILES) == 18
    assert 31 <= shares["dominant"] <= 33
    assert (shares < 3).sum() >= 6
    assert shares.min() < 1
    assert frame["case_id"].nunique() == 1_200
    assert frame["activity"].nunique() >= 13


def test_synthetic_screening_cli_writes_csv_and_xes(tmp_path) -> None:
    csv_path = tmp_path / "synthetic.csv"
    xes_path = tmp_path / "synthetic.xes"

    result = main(["--cases", "24", "--seed", "3", "--csv", str(csv_path), "--xes", str(xes_path)])

    assert result == 0
    assert csv_path.exists()
    assert xes_path.exists()
    frame = pd.read_csv(csv_path)
    log = csv_to_event_log(frame, "case_id", "activity", "timestamp")
    assert len(log) == 24

    xes_log = xes_importer.apply(str(xes_path))
    first_event = xes_log[0][0]
    assert len(xes_log) == 24
    assert {"phase", "variant_hint"}.issubset(xes_log[0].attributes)
    assert {"concept:name", "time:timestamp", "resource"}.issubset(first_event)
    assert "followup_breach_days" not in first_event
