"""Offline safeguards for the separate tuning-only REACT calibration."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.analyze_react_calibration import analyze, read_prediction_rows
from scripts.run_eval import PER_CASE_FIELDS

ROOT = Path(__file__).resolve().parents[1]


def write_predictions(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PER_CASE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "category": "casual",
                    "context_k": 3,
                    "confidence": 0.8,
                    "final_action": row["raw_choice"],
                    "downgraded": False,
                    "reason": "confident",
                    "decider_latency_ms": 10,
                    "error": "",
                    "scores_json": "{}",
                    **row,
                }
            )


def reviewed_scenarios(path: Path) -> None:
    rows = []
    for index in range(1, 16):
        if index <= 7:
            consensus = "REACT"
        elif index <= 12:
            consensus = "SILENT"
        else:
            consensus = "AMBIGUOUS"
        rows.append(
            {
                "id": f"r{index:03d}",
                "split": "tuning",
                "category": "casual",
                "history": [],
                "message": {"sender": "A", "text": "Synthetic test fixture"},
                "labels": {"a1": "REACT", "a2": "REACT", "a3": "REACT"},
                "consensus": consensus,
                "notes": "test fixture",
            }
        )
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_calibration_analysis_combines_tuning_without_changing_config(tmp_path: Path) -> None:
    original = tmp_path / "original.csv"
    calibration = tmp_path / "calibration.csv"
    scenarios = tmp_path / "reviewed.jsonl"
    output = tmp_path / "analysis"

    write_predictions(
        original,
        [
            {"id": "c001", "split": "tuning", "consensus": "SILENT", "raw_choice": "SILENT"},
            {"id": "c002", "split": "tuning", "consensus": "REPLY", "raw_choice": "REPLY"},
        ],
    )
    calibration_rows = []
    for index in range(1, 16):
        if index <= 7:
            consensus = raw_choice = "REACT"
        elif index <= 12:
            consensus = raw_choice = "SILENT"
        else:
            consensus, raw_choice = "AMBIGUOUS", "REACT"
        calibration_rows.append(
            {
                "id": f"r{index:03d}",
                "split": "tuning",
                "consensus": consensus,
                "raw_choice": raw_choice,
            }
        )
    write_predictions(calibration, calibration_rows)
    reviewed_scenarios(scenarios)

    config_path = ROOT / "config" / "default.yaml"
    config_before = config_path.read_bytes()
    payload = analyze(
        original,
        calibration,
        scenarios,
        ROOT / "eval" / "criteria.yaml",
        output,
    )

    assert payload["counts"] == {
        "original_scenarios": 2,
        "calibration_scenarios": 15,
        "combined_scenarios": 17,
    }
    assert payload["calibration_consensus_counts"]["REACT"] == 7
    assert "react_threshold" not in payload["threshold_evidence"]["unidentifiable_thresholds"]
    assert payload["production_config_modified"] is False
    assert payload["heldout_used"] is False
    assert config_path.read_bytes() == config_before
    assert (output / "combined_per_case.csv").is_file()
    assert (output / "threshold_sweep.csv").is_file()
    assert (output / "threshold_recommendation.json").is_file()
    assert (output / "calibration_report.md").is_file()


def test_calibration_analysis_refuses_heldout_prediction_rows(tmp_path: Path) -> None:
    path = tmp_path / "heldout.csv"
    write_predictions(
        path,
        [
            {
                "id": "r001",
                "split": "heldout",
                "consensus": "REACT",
                "raw_choice": "REACT",
            }
        ],
    )
    with pytest.raises(ValueError, match="tuning predictions only"):
        read_prediction_rows(path)
