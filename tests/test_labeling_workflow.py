"""Offline tests for split locking and independent human-label merging."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.labeling_server import public_dataset, public_scenarios
from scripts.make_label_sheet import FIELDNAMES, write_blank_sheet
from scripts.merge_labels import merge_label_files
from scripts.merge_react_calibration_labels import (
    PROTECTED_ORIGINAL_PATHS,
    merge_calibration_label_files,
)

ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_CANDIDATES = ROOT / "eval" / "react_calibration_candidates.jsonl"
CALIBRATION_MANIFEST = ROOT / "eval" / "react_calibration_manifest.json"


def candidate_files(tmp_path: Path) -> tuple[Path, Path]:
    categories = ("direct_request", "joke", "technical_question")
    rows = [
        {
            "id": f"c{index:03d}",
            "category": categories[(index - 1) % len(categories)],
            "history": [],
            "message": {"sender": "Sam", "text": f"Synthetic candidate {index}"},
        }
        for index in range(1, 46)
    ]
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = tmp_path / "split_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "tuning": [row["id"] for row in rows[:30]],
                "heldout": [row["id"] for row in rows[30:]],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return candidates, manifest


def candidate_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def write_labels(path: Path, labels: dict[str, str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "label"])
        writer.writeheader()
        for scenario_id, label in labels.items():
            writer.writerow({"id": scenario_id, "label": label})


def test_split_is_stratified_and_locked_30_15(tmp_path: Path) -> None:
    candidates, manifest_path = candidate_files(tmp_path)
    rows = candidate_rows(candidates)
    by_id = {row["id"]: row["category"] for row in rows}
    manifest = json.loads(manifest_path.read_text())

    assert len(manifest["tuning"]) == 30
    assert len(manifest["heldout"]) == 15
    assert not (set(manifest["tuning"]) & set(manifest["heldout"]))
    assert set(manifest["tuning"] + manifest["heldout"]) == set(by_id)
    assert set(Counter(by_id[item] for item in manifest["tuning"])) == set(
        Counter(by_id[item] for item in manifest["heldout"])
    )


def test_public_labeling_payload_hides_split_labels_and_predictions(tmp_path: Path) -> None:
    candidates, _ = candidate_files(tmp_path)
    rows = public_scenarios(candidates)
    assert len(rows) == 45
    for row in rows:
        assert set(row) == {"id", "history", "message"}
        assert "split" not in row
        assert "labels" not in row
        assert "consensus" not in row
        assert "prediction" not in row


def test_calibration_design_and_public_payload_are_separate() -> None:
    candidates = [
        json.loads(line)
        for line in CALIBRATION_CANDIDATES.read_text().splitlines()
        if line
    ]
    assert len(candidates) == 15
    assert Counter(row["design_group"] for row in candidates) == {
        "clear_react": 7,
        "clear_silent": 5,
        "borderline": 3,
    }

    payload = public_dataset("calibration")
    assert payload["dataset"]["scenario_count"] == 15
    assert "react" not in json.dumps(payload["dataset"]).lower()
    for row in payload["scenarios"]:
        assert set(row) == {"id", "history", "message"}
        assert "design_group" not in row
        assert "category" not in row


def test_blank_sheet_has_spec_columns_and_no_labels(tmp_path: Path) -> None:
    candidates, _ = candidate_files(tmp_path)
    output = tmp_path / "labels_blank.csv"
    assert write_blank_sheet(candidates, output) == 45
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 45
    assert list(rows[0]) == FIELDNAMES
    assert all(not row[slot] for row in rows for slot in ("a1", "a2", "a3"))


def test_merge_requires_three_complete_independent_exports(tmp_path: Path) -> None:
    candidates, manifest = candidate_files(tmp_path)
    ids = [row["id"] for row in candidate_rows(candidates)]
    files = [tmp_path / f"a{index}.csv" for index in range(1, 4)]
    labels = [{scenario_id: "SILENT" for scenario_id in ids} for _ in range(3)]
    labels[2]["c001"] = "REPLY"
    for path, values in zip(files, labels, strict=True):
        write_labels(path, values)

    output = tmp_path / "scenarios.jsonl"
    summary = merge_label_files(candidates, manifest, files, output)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    c001 = next(row for row in rows if row["id"] == "c001")

    assert summary == {"rows": 45, "unanimous": 44, "percent_agreement": pytest.approx(44 / 45 * 100)}
    assert c001["labels"] == {"a1": "SILENT", "a2": "SILENT", "a3": "REPLY"}
    assert c001["consensus"] == "AMBIGUOUS"
    assert sum(row["split"] == "tuning" for row in rows) == 30
    assert sum(row["split"] == "heldout" for row in rows) == 15

    majority_output = tmp_path / "majority.jsonl"
    merge_label_files(candidates, manifest, files, majority_output, min_agree=2)
    majority_rows = [json.loads(line) for line in majority_output.read_text().splitlines()]
    assert next(row for row in majority_rows if row["id"] == "c001")["consensus"] == "SILENT"


def test_merge_rejects_incomplete_or_reused_exports(tmp_path: Path) -> None:
    candidates, manifest = candidate_files(tmp_path)
    ids = [row["id"] for row in candidate_rows(candidates)]
    complete = tmp_path / "complete.csv"
    incomplete = tmp_path / "incomplete.csv"
    third = tmp_path / "third.csv"
    write_labels(complete, {scenario_id: "SILENT" for scenario_id in ids})
    write_labels(incomplete, {scenario_id: "SILENT" for scenario_id in ids[:-1]})
    write_labels(third, {scenario_id: "SILENT" for scenario_id in ids})

    with pytest.raises(ValueError, match="different file"):
        merge_label_files(candidates, manifest, [complete, complete, third], tmp_path / "x.jsonl")
    with pytest.raises(ValueError, match="ids do not match"):
        merge_label_files(candidates, manifest, [complete, incomplete, third], tmp_path / "y.jsonl")


def test_calibration_merge_is_unanimous_tuning_only_and_separate(tmp_path: Path) -> None:
    ids = [
        json.loads(line)["id"]
        for line in CALIBRATION_CANDIDATES.read_text().splitlines()
        if line
    ]
    files = [tmp_path / f"calibration_a{index}.csv" for index in range(1, 4)]
    labels = [{scenario_id: "SILENT" for scenario_id in ids} for _ in range(3)]
    labels[2][ids[0]] = "REACT"
    for path, values in zip(files, labels, strict=True):
        write_labels(path, values)

    output = tmp_path / "react_calibration_scenarios.jsonl"
    summary = merge_calibration_label_files(
        CALIBRATION_CANDIDATES,
        CALIBRATION_MANIFEST,
        files,
        output,
    )
    rows = [json.loads(line) for line in output.read_text().splitlines()]

    assert summary["rows"] == 15
    assert summary["unanimous"] == 14
    assert summary["ambiguous"] == 1
    assert {row["split"] for row in rows} == {"tuning"}
    assert rows[0]["consensus"] == "AMBIGUOUS"
    assert not any(row["id"].startswith("c") for row in rows)

    protected_output = next(iter(PROTECTED_ORIGINAL_PATHS))
    with pytest.raises(ValueError, match="may not overwrite"):
        merge_calibration_label_files(
            CALIBRATION_CANDIDATES,
            CALIBRATION_MANIFEST,
            files,
            protected_output,
        )
