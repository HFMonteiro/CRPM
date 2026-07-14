"""Synthetic CCR screening event-log generator for demos and tests."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import floor
from pathlib import Path
import random

import pandas as pd
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.objects.log.util import dataframe_utils


DEFAULT_SAMPLE_CASES = 30_000
CASES_PER_DAY = 28
SAMPLE_START = datetime(2022, 1, 1, tzinfo=timezone.utc)
POST_START = datetime(2023, 7, 2, tzinfo=timezone.utc)

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


@dataclass(frozen=True)
class VariantProfile:
    """A named activity sequence and its intended share of the sample."""

    name: str
    activities: tuple[str, ...]
    weight: float
    delay_multiplier: float = 1.0


VARIANT_PROFILES = (
    VariantProfile("dominant", DOMINANT_PATH, 32.0),
    VariantProfile(
        "reminder_once",
        ("Invitation_mail", "Reminder_mail", *DOMINANT_PATH[1:]),
        12.0,
    ),
    VariantProfile(
        "reminder_twice",
        ("Invitation_mail", "Reminder_mail", "Reminder_mail", *DOMINANT_PATH[1:]),
        8.0,
    ),
    VariantProfile(
        "lab_rejection_resubmit",
        (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_return",
            "Lab_rejection",
            "Lab_return",
            "Lab_result",
            "PCC_fwd",
            "PCC_observation",
            "Colonoscopy_center",
        ),
        8.0,
    ),
    VariantProfile(
        "admin_review",
        (*DOMINANT_PATH[:5], "Admin_review", *DOMINANT_PATH[5:]),
        7.0,
    ),
    VariantProfile(
        "no_show_reschedule",
        (
            *DOMINANT_PATH[:-1],
            "Colonoscopy_no_show",
            "Reschedule_mail",
            "Colonoscopy_center",
        ),
        7.0,
        1.1,
    ),
    VariantProfile(
        "reminder_admin_review",
        ("Invitation_mail", "Reminder_mail", *DOMINANT_PATH[1:5], "Admin_review", *DOMINANT_PATH[5:]),
        5.0,
    ),
    VariantProfile(
        "pcc_fit_rejection",
        (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "PCC_FIT_rejection",
            "Admin_review",
            "Lab_return",
            "Lab_result",
            "PCC_fwd",
            "PCC_observation",
            "Colonoscopy_center",
        ),
        4.0,
        1.1,
    ),
    VariantProfile(
        "lab_rejection_admin_review",
        (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_return",
            "Lab_rejection",
            "Lab_return",
            "Lab_result",
            "Admin_review",
            "PCC_fwd",
            "PCC_observation",
            "Colonoscopy_center",
        ),
        3.5,
        1.1,
    ),
    VariantProfile(
        "direct_colonoscopy",
        ("Invitation_mail", "FIT_mail", "FIT_return", "Lab_return", "Lab_result", "Colonoscopy_center"),
        3.0,
    ),
    VariantProfile(
        "pcc_rework",
        (*DOMINANT_PATH[:-1], "Admin_review", "PCC_observation", "Colonoscopy_center"),
        2.5,
        1.2,
    ),
    VariantProfile(
        "fit_reissue",
        ("Invitation_mail", "FIT_mail", "Reminder_mail", *DOMINANT_PATH[1:]),
        2.0,
        1.1,
    ),
    VariantProfile(
        "lab_repeat",
        (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Lab_return",
            "Lab_result",
            "Lab_return",
            "Lab_result",
            "PCC_fwd",
            "PCC_observation",
            "Colonoscopy_center",
        ),
        1.5,
        1.2,
    ),
    VariantProfile(
        "repeated_no_show",
        (
            *DOMINANT_PATH[:-1],
            "Colonoscopy_no_show",
            "Reschedule_mail",
            "Colonoscopy_no_show",
            "Reschedule_mail",
            "Colonoscopy_center",
        ),
        1.2,
        1.35,
    ),
    VariantProfile(
        "admin_before_lab",
        (
            "Invitation_mail",
            "FIT_mail",
            "FIT_return",
            "Admin_review",
            "Lab_return",
            "Lab_result",
            "PCC_fwd",
            "PCC_observation",
            "Colonoscopy_center",
        ),
        1.0,
    ),
    VariantProfile(
        "direct_observation",
        ("Invitation_mail", "FIT_mail", "FIT_return", "Lab_return", "Lab_result", "PCC_observation", "Colonoscopy_center"),
        0.8,
    ),
    VariantProfile(
        "reminder_three_times",
        ("Invitation_mail", "Reminder_mail", "Reminder_mail", "Reminder_mail", *DOMINANT_PATH[1:]),
        0.7,
        1.15,
    ),
    VariantProfile("observation_followup_open", DOMINANT_PATH[:-1], 0.8, 1.1),
)


EVENT_METADATA = {
    "Invitation_mail": ("screening_office", "Community", "mail", "invited"),
    "Reminder_mail": ("screening_office", "Community", "mail", "reminded"),
    "FIT_mail": ("screening_office", "Community", "mail", "kit_sent"),
    "FIT_return": ("mailroom", "Community", "post", "kit_received"),
    "Lab_return": ("lab_team", "Laboratory", "lab", "sample_received"),
    "Lab_result": ("lab_team", "Laboratory", "lab", "processed"),
    "Lab_rejection": ("lab_team", "Laboratory", "lab", "rejected"),
    "Admin_review": ("clinical_admin", "Primary care", "manual", "reviewed"),
    "PCC_FIT_rejection": ("pcc_team", "Primary care", "manual", "fit_rejected"),
    "PCC_fwd": ("pcc_team", "Primary care", "internal", "forwarded"),
    "PCC_observation": ("pcc_team", "Primary care", "internal", "observed"),
    "Colonoscopy_no_show": ("endoscopy_unit", "Hospital", "hospital", "no_show"),
    "Reschedule_mail": ("endoscopy_unit", "Hospital", "mail", "rescheduled"),
    "Colonoscopy_center": ("endoscopy_unit", "Hospital", "hospital", "completed"),
}

# Keep the bundled XES lean for interactive use. The CSV remains the complete
# analytical fixture; the XES carries only fields consumed by CRPM at runtime.
XES_EVENT_COLUMNS = (
    "case:concept:name",
    "concept:name",
    "time:timestamp",
    "resource",
    "case:phase",
    "case:variant_hint",
)

BASE_DELAY_HOURS = {
    "Reminder_mail": 72,
    "FIT_mail": 24,
    "FIT_return": 40,
    "Lab_return": 18,
    "Lab_result": 34,
    "Lab_rejection": 12,
    "Admin_review": 20,
    "PCC_FIT_rejection": 14,
    "PCC_fwd": 18,
    "PCC_observation": 28,
    "Colonoscopy_no_show": 240,
    "Reschedule_mail": 168,
    "Colonoscopy_center": 52,
}


def generate_screening_demo(cases: int = DEFAULT_SAMPLE_CASES, seed: int = 42) -> pd.DataFrame:
    """Generate a deterministic, long-tail synthetic CCR screening event table."""

    if cases < 2:
        raise ValueError("At least two cases are required to preserve PRE and POST cohorts.")

    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    pre_cases = cases // 2
    phase_sizes = {"PRE": pre_cases, "POST": cases - pre_cases}
    global_case_index = 0

    for phase, phase_size in phase_sizes.items():
        profiles = _allocate_profiles(phase_size, rng)
        for phase_case_index, profile in enumerate(profiles):
            global_case_index += 1
            start = _case_start(phase, phase_case_index)
            case_id = f"{phase}-{phase_case_index + 1:04d}"
            lab_rejection_reason = rng.choice(("insufficient_sample", "labelling_issue", "transport_delay"))
            timestamp = start
            reminder_sequence = 0

            for event_index, activity in enumerate(profile.activities):
                delay_hours = 0.0
                if event_index:
                    delay_hours = _delay_hours(activity, phase, profile, rng)
                    timestamp += timedelta(hours=delay_hours)
                if activity == "Reminder_mail":
                    reminder_sequence += 1

                resource, site, channel, result_code = EVENT_METADATA[activity]
                rows.append(
                    {
                        "case_id": case_id,
                        "phase": phase,
                        "activity": activity,
                        "timestamp": timestamp.isoformat(),
                        "resource": resource,
                        "site": site,
                        "channel": channel,
                        "result_code": result_code,
                        "delay_bucket": _delay_bucket(delay_hours, event_index),
                        "variant_hint": profile.name,
                        "lab_rejection_reason": lab_rejection_reason if activity == "Lab_rejection" else "",
                        "reminder_sequence": reminder_sequence if activity == "Reminder_mail" else "",
                        "manual_review_flag": "Admin_review" in profile.activities,
                        "no_show_flag": "Colonoscopy_no_show" in profile.activities,
                        "followup_breach_days": max((timestamp - start).days - 60, 0),
                    }
                )

    frame = pd.DataFrame(rows)
    return frame.sort_values(["timestamp", "case_id"], kind="stable").reset_index(drop=True)


def write_screening_demo(
    *,
    output_csv: Path,
    output_xes: Path | None = None,
    cases: int = DEFAULT_SAMPLE_CASES,
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
        ).copy()
        event_df["case:phase"] = event_df["phase"]
        event_df["case:variant_hint"] = event_df["variant_hint"]
        event_df = event_df.loc[:, XES_EVENT_COLUMNS]
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
    parser.add_argument("--cases", type=int, default=DEFAULT_SAMPLE_CASES, help="Number of synthetic cases to generate.")
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


def _allocate_profiles(cases: int, rng: random.Random) -> list[VariantProfile]:
    raw_counts = [cases * profile.weight / 100 for profile in VARIANT_PROFILES]
    counts = [floor(value) for value in raw_counts]
    remaining = cases - sum(counts)
    ranked_remainders = sorted(
        range(len(VARIANT_PROFILES)),
        key=lambda index: (raw_counts[index] - counts[index], VARIANT_PROFILES[index].weight),
        reverse=True,
    )
    for profile_index in ranked_remainders[:remaining]:
        counts[profile_index] += 1

    allocated = [profile for profile, count in zip(VARIANT_PROFILES, counts) for _ in range(count)]
    rng.shuffle(allocated)
    return allocated


def _case_start(phase: str, phase_case_index: int) -> datetime:
    phase_start = SAMPLE_START if phase == "PRE" else POST_START
    minutes_between_cases = (24 * 60) // CASES_PER_DAY
    return phase_start + timedelta(
        days=phase_case_index // CASES_PER_DAY,
        minutes=(phase_case_index % CASES_PER_DAY) * minutes_between_cases,
    )


def _delay_hours(activity: str, phase: str, profile: VariantProfile, rng: random.Random) -> float:
    base = BASE_DELAY_HOURS.get(activity, 18)
    phase_multiplier = 1.0 if phase == "PRE" else 1.9
    if phase == "POST" and activity in {"PCC_observation", "Colonoscopy_no_show", "Reschedule_mail", "Colonoscopy_center"}:
        phase_multiplier *= 1.2
    jitter = rng.uniform(0.78, 1.22)
    return round(max(base * phase_multiplier * profile.delay_multiplier * jitter, 1), 2)


def _delay_bucket(delay_hours: float, event_index: int) -> str:
    if event_index == 0:
        return "start"
    if delay_hours < 24:
        return "same_day"
    if delay_hours < 72:
        return "standard"
    if delay_hours < 168:
        return "followup"
    return "breach"


if __name__ == "__main__":
    raise SystemExit(main())
