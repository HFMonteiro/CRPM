from collections import Counter

import pandas as pd

from crpm.pipeline import csv_to_event_log
from crpm.synthetic_screening import DOMINANT_PATH, generate_screening_demo, main


def test_generate_screening_demo_is_deterministic_and_story_rich() -> None:
    first = generate_screening_demo(cases=36, seed=7)
    second = generate_screening_demo(cases=36, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert {"case_id", "activity", "timestamp", "phase", "variant_hint"}.issubset(first.columns)
    assert set(first["phase"]) == {"PRE", "POST"}
    assert {"lab_rejection", "no_show_reschedule", "dominant"}.issubset(set(first["variant_hint"]))
    variants = Counter(tuple(group["activity"]) for _, group in first.groupby("case_id", sort=False))
    assert DOMINANT_PATH in variants


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
