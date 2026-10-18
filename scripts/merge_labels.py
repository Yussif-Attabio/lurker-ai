#!/usr/bin/env python3
"""Merge three independent human CSV exports into evaluated scenarios."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "eval" / "scenario_candidates.jsonl"
DEFAULT_MANIFEST = ROOT / "eval" / "split_manifest.json"
DEFAULT_OUTPUT = ROOT / "eval" / "scenarios.jsonl"
ALLOWED_LABELS = {"SILENT", "REACT", "REPLY"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSON objects from a JSONL file."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_labels(path: Path) -> dict[str, str]:
    """Read and strictly validate one evaluator's `id,label` CSV export."""
    labels: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not {"id", "label"}.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain id and label columns")
        for line_number, row in enumerate(reader, start=2):
            scenario_id = (row.get("id") or "").strip()
            label = (row.get("label") or "").strip().upper()
            if not scenario_id:
                raise ValueError(f"{path}:{line_number} has no scenario id")
            if scenario_id in labels:
                raise ValueError(f"{path} contains duplicate id {scenario_id}")
            if label not in ALLOWED_LABELS:
                raise ValueError(
                    f"{path}:{line_number} label must be SILENT, REACT, or REPLY"
                )
            labels[scenario_id] = label
    return labels


def load_split_manifest(path: Path) -> dict[str, str]:
    """Return a validated scenario-id to split mapping."""
    payload = json.loads(path.read_text())
    tuning = payload.get("tuning", [])
    heldout = payload.get("heldout", [])
    if len(tuning) != 30 or len(heldout) != 15:
        raise ValueError("split manifest must contain exactly 30 tuning and 15 heldout ids")
    if set(tuning) & set(heldout):
        raise ValueError("split manifest contains overlapping ids")
    return {**{key: "tuning" for key in tuning}, **{key: "heldout" for key in heldout}}


def consensus_for(labels: list[str], min_agree: int) -> str:
    """Return the agreed label or AMBIGUOUS when agreement is insufficient."""
    label, count = Counter(labels).most_common(1)[0]
    return label if count >= min_agree else "AMBIGUOUS"


def merge_label_files(
    candidates_path: Path,
    manifest_path: Path,
    label_paths: list[Path],
    output_path: Path,
    min_agree: int = 3,
) -> dict[str, float | int]:
    """Validate and merge three evaluator exports into the canonical JSONL file."""
    if len(label_paths) != 3:
        raise ValueError("exactly three evaluator files are required")
    if len({path.resolve() for path in label_paths}) != 3:
        raise ValueError("each evaluator file must be a different file")
    if min_agree not in {2, 3}:
        raise ValueError("min_agree must be 2 or 3")

    candidates = load_jsonl(candidates_path)
    candidate_ids = [row["id"] for row in candidates]
    expected = set(candidate_ids)
    if len(candidate_ids) != len(expected):
        raise ValueError("candidate ids must be unique")

    split_by_id = load_split_manifest(manifest_path)
    if set(split_by_id) != expected:
        raise ValueError("split manifest ids must exactly match candidate ids")

    evaluator_labels = [read_labels(path) for path in label_paths]
    for path, labels in zip(label_paths, evaluator_labels, strict=True):
        missing = expected - set(labels)
        extra = set(labels) - expected
        if missing or extra:
            raise ValueError(
                f"{path} ids do not match candidates: missing={sorted(missing)} extra={sorted(extra)}"
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
                "split": split_by_id[scenario_id],
                "category": candidate["category"],
                "history": candidate["history"],
                "message": candidate["message"],
                "labels": {"a1": labels[0], "a2": labels[1], "a3": labels[2]},
                "consensus": consensus_for(labels, min_agree),
                "notes": "",
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in output_rows),
        encoding="utf-8",
    )
    total = len(output_rows)
    return {
        "rows": total,
        "unanimous": unanimous,
        "percent_agreement": (unanimous / total * 100) if total else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a1", type=Path, required=True)
    parser.add_argument("--a2", type=Path, required=True)
    parser.add_argument("--a3", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-agree", type=int, default=3, choices=(2, 3))
    args = parser.parse_args()

    summary = merge_label_files(
        args.candidates,
        args.manifest,
        [args.a1, args.a2, args.a3],
        args.output,
        args.min_agree,
    )
    print(
        f"wrote={args.output} rows={summary['rows']} unanimous={summary['unanimous']} "
        f"percent_agreement={summary['percent_agreement']:.2f}% min_agree={args.min_agree}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
