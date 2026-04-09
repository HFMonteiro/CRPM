from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

pm4py = pytest.importorskip("pm4py")
from pm4py.objects.log.obj import EventLog, Trace

from crpm.queue_flow import (
    aggregate_weekly_step_counts,
    build_case_state_frame,
    build_operational_view,
    compute_queue_stock_levels,
    compute_stage_aging_metrics,
    derive_operational_periods,
    smooth_series,
    split_operational_periods,
)


def make_trace(case_id: str, events: list[tuple[str, datetime]]) -> Trace:
    trace = Trace(attributes={"concept:name": case_id})
    for activity, timestamp in events:
        trace.append({"concept:name": activity, "time:timestamp": timestamp})
    return trace


def _step_map() -> dict[str, str]:
    return {
        "invitation": "Invitation_mail",
        "fit_mail": "FIT_mail",
        "fit_return": "FIT_return",
        "lab_result": "Lab_result",
        "pcc_observation": "PCC_observation",
        "colonoscopy": "Colonoscopy_center",
    }


def test_smooth_series_preserves_edges() -> None:
    values = smooth_series(arr=np.array([10.0, 0.0, 0.0, 10.0]), window=3)
    assert values[0] == 10.0
    assert values[-1] == 10.0


def test_smooth_series_handles_short_arrays() -> None:
    values = smooth_series(arr=np.array([4.0, 1.0]), window=13)
    assert len(values) == 2
    assert np.isfinite(values).all()


def test_build_case_state_frame_derives_highest_stage() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("Invitation_mail", datetime(2024, 1, 1)),
                    ("FIT_mail", datetime(2024, 1, 2)),
                    ("FIT_return", datetime(2024, 1, 15)),
                    ("Lab_result", datetime(2024, 1, 20)),
                ],
            )
        ]
    )

    frame = build_case_state_frame(log, _step_map())

    assert len(frame) == 1
    assert frame.iloc[0]["highest_stage"] == "Lab result"
    assert bool(frame.iloc[0]["has_colonoscopy"]) is False


def test_weekly_counts_and_stock_levels_are_computed() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("Invitation_mail", datetime(2024, 1, 1)),
                    ("FIT_mail", datetime(2024, 1, 2)),
                    ("FIT_return", datetime(2024, 1, 10)),
                    ("Lab_result", datetime(2024, 1, 15)),
                    ("PCC_observation", datetime(2024, 1, 20)),
                ],
            ),
            make_trace(
                "case-2",
                [
                    ("Invitation_mail", datetime(2024, 1, 8)),
                    ("FIT_mail", datetime(2024, 1, 9)),
                ],
            ),
        ]
    )

    case_frame = build_case_state_frame(log, _step_map())
    weekly_counts = aggregate_weekly_step_counts(case_frame)
    stock = compute_queue_stock_levels(weekly_counts)

    assert "Invitation" in weekly_counts.columns
    assert "Pending FIT return" in stock.columns
    assert stock["Pending FIT return"].max() >= 0


def test_stage_aging_metrics_use_canonical_transitions() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("Invitation_mail", datetime(2024, 1, 1)),
                    ("FIT_mail", datetime(2024, 1, 3)),
                    ("FIT_return", datetime(2024, 1, 8)),
                ],
            ),
            make_trace(
                "case-2",
                [
                    ("Invitation_mail", datetime(2024, 1, 2)),
                    ("FIT_mail", datetime(2024, 1, 4)),
                    ("FIT_return", datetime(2024, 1, 9)),
                ],
            ),
        ]
    )

    aging = compute_stage_aging_metrics(log, _step_map())

    assert not aging.empty
    assert "median_days" in aging.columns
    assert aging.iloc[0]["frequency"] >= 1


def test_build_operational_view_includes_kpis() -> None:
    log = EventLog(
        [
            make_trace(
                "case-1",
                [
                    ("Invitation_mail", datetime(2024, 1, 1)),
                    ("FIT_mail", datetime(2024, 1, 2)),
                    ("FIT_return", datetime(2024, 1, 12)),
                    ("Lab_result", datetime(2024, 1, 18)),
                    ("PCC_observation", datetime(2024, 1, 25)),
                    ("Colonoscopy_center", datetime(2024, 2, 10)),
                ],
            )
        ]
    )

    result = build_operational_view(log, _step_map(), smooth_window=3)

    assert "weekly_counts" in result
    assert "stock_levels" in result
    assert result["kpis"]["colonoscopy_completion_rate"] == pytest.approx(1.0)


def test_derive_operational_periods_uses_log_span() -> None:
    log = EventLog(
        [
            make_trace("case-1", [("Invitation_mail", datetime(2010, 12, 30)), ("FIT_mail", datetime(2010, 12, 31))]),
            make_trace("case-2", [("Invitation_mail", datetime(2011, 1, 12)), ("FIT_mail", datetime(2011, 1, 24))]),
        ]
    )

    pre_period, post_period = derive_operational_periods(log, anchor_activity="Invitation_mail")

    assert pre_period.start == datetime(2010, 12, 30).date()
    assert post_period.end == datetime(2011, 1, 12).date()
    assert pre_period.end < post_period.start


def test_split_operational_periods_defaults_to_derived_windows() -> None:
    log = EventLog(
        [
            make_trace("case-1", [("Invitation_mail", datetime(2010, 12, 30)), ("FIT_mail", datetime(2010, 12, 31))]),
            make_trace("case-2", [("Invitation_mail", datetime(2011, 1, 12)), ("FIT_mail", datetime(2011, 1, 24))]),
        ]
    )

    periods = split_operational_periods(log, anchor_activity="Invitation_mail")

    assert len(periods["PRE"]) == 1
    assert len(periods["POST"]) == 1


def test_build_operational_view_handles_empty_log() -> None:
    result = build_operational_view(EventLog(), _step_map(), smooth_window=13)

    assert result["case_state_frame"].empty
    assert result["weekly_counts"].empty
    assert result["stock_levels"].empty
    assert result["aging_metrics"].empty
    assert result["kpis"]["total_cases"] == 0
