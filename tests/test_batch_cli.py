import json
from pathlib import Path

from crpm.batch_cli import main, run_headless_analysis


def test_headless_analysis_dry_run_redacts_source_and_does_not_execute(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    source_path = tmp_path / "private-inputs" / "running-example.xes"
    source_path.parent.mkdir()
    source_path.write_bytes(Path("examples/running-example.xes").read_bytes())
    config_path.write_text(
        json.dumps(
            {
                "source": {"type": "xes", "path": str(source_path)},
                "analysis": {"selected_algorithms": ["Inductive (IMf)"]},
            }
        ),
        encoding="utf-8",
    )

    result = run_headless_analysis(config_path, dry_run=True)

    assert result["status"] == "validated"
    assert result["source"]["display_name"] == "running-example.xes"
    assert str(tmp_path) not in json.dumps(result)


def test_headless_analysis_runs_xes_and_writes_manifest(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "out"
    config_path.write_text(
        json.dumps(
            {
                "source": {"type": "xes", "path": "examples/running-example.xes"},
                "analysis": {
                    "workflow_cohort_policy": "first_event_direct",
                    "start_filter": "register request",
                    "selected_algorithms": ["Inductive (IMf)"],
                },
                "output": {"directory": str(output_dir)},
            }
        ),
        encoding="utf-8",
    )

    result = run_headless_analysis(config_path)

    manifest_path = output_dir / "crpm_run_manifest.json"
    assert result["status"] == "completed"
    assert result["manifest_path"] == str(manifest_path)
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run"]["workflow_cohort_policy"] == "first_event_direct"
    assert manifest["algorithms"]["selected"] == ["Inductive (IMf)"]


def test_batch_cli_dry_run_returns_zero(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"source": {"type": "xes", "path": "examples/running-example.xes"}}),
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_path), "--dry-run"])

    assert exit_code == 0
    assert "validated" in capsys.readouterr().out
