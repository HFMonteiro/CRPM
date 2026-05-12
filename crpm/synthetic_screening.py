"""Synthetic CCR screening event-log generator for demos and tests."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import random

import pandas as pd
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.objects.log.util import dataframe_utils


DOMINANT_PATH = (
    "Invitation_mail",
    "FIT_mail",
    "FIT_return",
    "Lab_return",
    "Lab_result",
    "PCC_fwd",
    "PCC_observation",
    "Colonoscopy_center",
)


def generate_screening_demo(cases: int = 120, seed: int = 42) -> pd.DataFrame:
    """Generate a deterministic synthetic CCR screening event table."""

    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    boundary = max(cases // 2, 1)
    for index in range(cases):
        phase = "PRE" if index < boundary else "POST"
        start = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=index // 4, hours=(index % 4) * 6)
        variant, activities = _case_variant(index, rng)
        timestamp = start
        case_id = f"SYN-{index + 1:05d}"
        for event_index, activity in enumerate(activities, start=1):
            if event_index > 1:
                timestamp += timedelta(days=_delay_days(activity, phase, rng), hours=rng.randint(0, 8))
            rows.append(
                {
                    "case_id": case_id,
                    "activity": activity,
                    "timestamp": timestamp.isoformat(),
                    "phase": phase,
                    "variant_hint": variant,
                    "manual_review_flag": "Admin_review" in activities,
                    "no_show_flag": "Colonoscopy_no_show" in activities,
                    "followup_breach_days": max((timestamp - start).days - 60, 0),
                }
            )
    return pd.DataFrame(rows)


def write_screening_demo(
    *,
    output_csv: Path,
    output_xes: Path | None = None,
    cases: int = 120,
    seed: int = 42,
    force: bool = False,
) -> None:
    """Write a synthetic screening demo CSV and optional XES file."""

    if output_csv.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing CSV: {output_csv}")
    if output_xes is not None and output_xes.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing XES: {output_xes}")

    frame = generate_screening_demo(cases=cases, seed=seed)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    if output_xes is not None:
        output_xes.parent.mkdir(parents=True, exist_ok=True)
        event_df = frame.rename(
            columns={
                "case_id": "case:concept:name",
                "activity": "concept:name",
                "timestamp": "time:timestamp",
            }
        )
        event_df = dataframe_utils.convert_timestamp_columns_in_df(event_df)
        log = log_converter.apply(
            event_df,
            variant=log_converter.Variants.TO_EVENT_LOG,
            parameters={
                "case_id_key": "case:concept:name",
                "activity_key": "concept:name",
                "timestamp_key": "time:timestamp",
            },
        )
        xes_exporter.apply(log, str(output_xes))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic CRPM CCR screening event log.")
    parser.add_argument("--cases", type=int, default=120, help="Number of synthetic cases to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed.")
    parser.add_argument("--csv", type=Path, required=True, help="Output CSV path.")
    parser.add_argument("--xes", type=Path, help="Optional output XES path.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files.")
    args = parser.parse_args(argv)
    write_screening_demo(output_csv=args.csv, output_xes=args.xes, cases=args.cases, seed=args.seed, force=args.force)
    print(f"Wrote synthetic screening CSV: {args.csv}")
    if args.xes:
        print(f"Wrote synthetic screening XES: {args.xes}")
    return 0


def _case_variant(index: int, rng: random.Random) -> tuple[str, tuple[str, ...]]:
    bucket = index % 12
    if bucket in {0, 1, 2, 3, 4}:
        return "dominant", DOMINANT_PATH
    if bucket == 5:
        return "reminder_loop", (
            "Invitation_mail",
            "Reminder_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_return",
            "Lab_result",
            "PCC_observation",
        )
    if bucket == 6:
        return "lab_rejection", (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_rejection",
            "Lab_return",
            "Lab_result",
            "PCC_fwd",
            "PCC_observation",
        )
    if bucket == 7:
        return "admin_review", ("Invitation_mail", "FIT_mail", "FIT_return", "Admin_review", "Lab_return", "Lab_result", "PCC_observation")
    if bucket == 8:
        return "no_show_reschedule", (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_return",
            "Lab_result",
            "PCC_observation",
            "Colonoscopy_no_show",
            "Colonoscopy_center",
        )
    if bucket == 9:
        return "slow_path", DOMINANT_PATH
    if bucket == 10:
        return "direct_observation", ("Invitation_mail", "FIT_mail", "FIT_return", "Lab_result", "PCC_observation")
    extra_reminders = ("Reminder_mail",) * rng.randint(1, 2)
    return "rare_reminder", ("Invitation_mail", *extra_reminders, "FIT_mail", "FIT_return", "Lab_return", "Lab_result")


def _delay_days(activity: str, phase: str, rng: random.Random) -> int:
    base = {
        "FIT_mail": 2,
        "FIT_return": 4,
        "Lab_return": 2,
        "Lab_result": 2,
        "PCC_fwd": 1,
        "PCC_observation": 3,
        "Colonoscopy_center": 12,
        "Colonoscopy_no_show": 10,
        "Reminder_mail": 7,
        "Lab_rejection": 1,
        "Admin_review": 3,
    }.get(activity, 2)
    if phase == "POST" and activity in {"PCC_observation", "Colonoscopy_center", "Colonoscopy_no_show"}:
        base *= 2
    return max(base + rng.randint(-1, 3), 0)


if __name__ == "__main__":
    raise SystemExit(main())
