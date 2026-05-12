from datetime import date

import pytest

from crpm.config_schema import load_analysis_config, validate_analysis_config


def test_load_analysis_config_applies_safe_defaults(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
        {
          "source": {"type": "xes", "path": "examples/running-example.xes"},
          "analysis": {"selected_algorithms": ["Inductive (IMf)"]}
        }
        """,
        encoding="utf-8",
    )

    config = load_analysis_config(config_path)

    assert config.source.type == "xes"
    assert config.analysis.workflow_cohort_policy == "first_event_direct"
    assert config.analysis.start_filter == "All"
    assert config.analysis.date_filter_mode == "case"
    assert config.analysis.start_date is None
    assert config.analysis.selected_algorithms == ("Inductive (IMf)",)


def test_validate_analysis_config_rejects_invalid_policy() -> None:
    with pytest.raises(ValueError, match="workflow_cohort_policy"):
        validate_analysis_config(
            {
                "source": {"type": "xes", "path": "examples/running-example.xes"},
                "analysis": {"workflow_cohort_policy": "anchor_anything"},
            }
        )


def test_validate_analysis_config_parses_dates_and_csv_mapping() -> None:
    config = validate_analysis_config(
        {
            "source": {
                "type": "csv",
                "path": "examples/screening_conformance_demo.csv",
                "case_col": "case_id",
                "activity_col": "activity",
                "timestamp_col": "timestamp",
            },
            "analysis": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "selected_algorithms": ["Heuristics (Classic)"],
            },
        }
    )

    assert config.source.type == "csv"
    assert config.source.case_col == "case_id"
    assert config.analysis.start_date == date(2024, 1, 1)
    assert config.analysis.end_date == date(2024, 1, 31)
