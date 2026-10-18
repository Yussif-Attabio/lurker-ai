#!/usr/bin/env python3
"""Merge three independent calibration exports without touching the M1 dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.merge_labels import consensus_for, load_jsonl, read_labels

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "eval" / "react_calibration_candidates.jsonl"
DEFAULT_MANIFEST = ROOT / "eval" / "react_calibration_manifest.json"
DEFAULT_OUTPUT = ROOT / "eval" / "react_calibration_scenarios.jsonl"
PROTECTED_ORIGINAL_PATHS = {
    (ROOT / "eval" / "scenario_candidates.jsonl").resolve(),
    (ROOT / "eval" / "split_manifest.json").resolve(),
    (ROOT / "eval" / "scenarios.jsonl").resolve(),
}


def load_calibration_manifest(path: Path, candidate_ids: set[str]) -> None:
    """Validate that every calibration item is tuning-only and none is held out."""
    payload = json.loads(path.read_text())
    tuning = payload.get("tuning", [])
    heldout = payload.get("heldout", [])
    if heldout:
        raise ValueError("calibration manifest must not contain held-out scenarios")
    if len(tuning) != 15 or len(set(tuning)) != 15:
        raise ValueError("calibration manifest must contain 15 unique tuning ids")
    if set(tuning) != candidate_ids:
        raise ValueError("calibration manifest ids must exactly match candidate ids")


def validate_design(rows: list[dict[str, Any]]) -> None:
    """Check the owner-only design balance without treating it as ground truth."""
    expected = {"clear_react": 7, "clear_silent": 5, "borderline": 3}
    observed = Counter(row.get("design_group") for row in rows)
    if dict(observed) != expected:
        raise ValueError(f"calibration design must be {expected}; found {dict(observed)}")


def merge_calibration_label_files(
    candidates_path: Path,
    manifest_path: Path,
    label_paths: list[Path],
    output_path: Path,
    min_agree: int = 3,
) -> dict[str, float | int]:
    """Validate genuine labels and write a separate tuning-only reviewed dataset."""
    if output_path.resolve() in PROTECTED_ORIGINAL_PATHS:
        raise ValueError("calibration output may not overwrite an original M1 dataset file")
    if len(label_paths) != 3:
        raise ValueError("exactly three evaluator files are required")
    if len({path.resolve() for path in label_paths}) != 3:
        raise ValueError("each evaluator file must be a different file")
    if min_agree != 3:
        raise ValueError("calibration merge requires unanimous consensus (min_agree=3)")

    candidates = load_jsonl(candidates_path)
    candidate_ids = [row["id"] for row in candidates]
    expected = set(candidate_ids)
    if len(candidates) != 15 or len(expected) != 15:
        raise ValueError("calibration candidates must contain 15 unique ids")
    validate_design(candidates)
    load_calibration_manifest(manifest_path, expected)

    evaluator_labels = [read_labels(path) for path in label_paths]
    for path, labels in zip(label_paths, evaluator_labels, strict=True):
        missing = expected - set(labels)
        extra = set(labels) - expected
        if missing or extra:
            raise ValueError(
                f"{path} ids do not match calibration candidates: "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )

    output_rows: list[dict[str, Any]] = []
    unanimous = 0
    for candidate in candidates:
        scenario_id = candidate["id"]
        labels = [mapping[scenario_id] for mapping in evaluator_labels]
        if len(set(labels)) == 1:
            unanimous += 1
        output_rows.append(
            {
                "id": scenario_id,
                "split": "tuning",
                "category": candidate["category"],
                "history": candidate["history"],
                "message": candidate["message"],
                "labels": {"a1": labels[0], "a2": labels[1], "a3": labels[2]},
                "consensus": consensus_for(labels, min_agree),
                "notes": "Separate M1 REACT calibration; not part of the held-out set.",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in output_rows),
        encoding="utf-8",
    )
    return {
        "rows": len(output_rows),
        "unanimous": unanimous,
        "ambiguous": len(output_rows) - unanimous,
        "percent_agreement": unanimous / len(output_rows) * 100,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a1", type=Path, required=True)
    parser.add_argument("--a2", type=Path, required=True)
    parser.add_argument("--a3", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = merge_calibration_label_files(
        args.candidates,
        args.manifest,
        [args.a1, args.a2, args.a3],
        args.output,
    )
    print(
        f"wrote={args.output} rows={summary['rows']} unanimous={summary['unanimous']} "
        f"ambiguous={summary['ambiguous']} "
        f"percent_agreement={summary['percent_agreement']:.2f}% min_agree=3"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
