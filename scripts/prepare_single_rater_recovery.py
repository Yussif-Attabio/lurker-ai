#!/usr/bin/env python3
"""Prepare a balanced, family-isolated recovery set from one evaluator.

This is an explicitly exploratory workflow. It does not create human consensus,
does not create a held-out set, and does not weaken the three-rater recovery
pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.merge_recovery_labels import ALLOWED_LABELS, load_jsonl, read_export

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = ROOT / "eval" / "recovery"
DEFAULT_CANDIDATES = RECOVERY_ROOT / "candidates.jsonl"
DEFAULT_ROOT = RECOVERY_ROOT / "single_rater"
DEFAULT_SOURCE = DEFAULT_ROOT / "source" / "recovery_labels_a1.csv"
DEFAULT_DEVELOPMENT = DEFAULT_ROOT / "development" / "development.jsonl"
DEFAULT_RESERVE = DEFAULT_ROOT / "reserve" / "locked_reserve.jsonl"
DEFAULT_MANIFEST = DEFAULT_ROOT / "split_manifest.json"
ACTIONS = ("SILENT", "REACT", "REPLY")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_balanced_development_families(
    candidates: list[dict[str, Any]], labels: dict[str, dict[str, str]]
) -> tuple[set[str], Counter[str]]:
    """Choose whole families that total exactly 30 examples per action."""
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    for row in candidates:
        by_family[row["family_id"]][labels[row["id"]]["label"]] += 1
    if len(by_family) != 39:
        raise ValueError("expected all 39 recovery scenario families")

    # Dynamic programming keeps family membership deterministic and never
    # exceeds the exact 30/30/30 target.
    states: dict[tuple[int, int, int], tuple[str, ...]] = {(0, 0, 0): ()}
    for family_id in sorted(by_family):
        family_counts = by_family[family_id]
        next_states = dict(states)
        for counts, selected in states.items():
            candidate_counts = tuple(
                counts[index] + family_counts[action]
                for index, action in enumerate(ACTIONS)
            )
            if any(count > 30 for count in candidate_counts):
                continue
            candidate_selection = selected + (family_id,)
            previous = next_states.get(candidate_counts)
            if previous is None or (len(candidate_selection), candidate_selection) < (
                len(previous),
                previous,
            ):
                next_states[candidate_counts] = candidate_selection
        states = next_states

    target = (30, 30, 30)
    if target not in states:
        raise ValueError(
            "single-rater labels cannot produce an exact family-isolated 30/30/30 development set"
        )
    selected_families = set(states[target])
    return selected_families, Counter(dict(zip(ACTIONS, target, strict=True)))


def reviewed_row(
    row: dict[str, Any], label: str, evaluator_id: str
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "split": "tuning",
        "category": row["category"],
        "family_id": row["family_id"],
        "history": row["history"],
        "message": row["message"],
        "reference_label": label,
        "label_basis": "single_evaluator",
        "evaluator_id": evaluator_id,
        "notes": "Exploratory M5 recovery development label; not human consensus.",
    }


def build_single_rater_split(
    candidates: list[dict[str, Any]],
    labels: dict[str, dict[str, str]],
    evaluator_id: str = "a1",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    ids = [row["id"] for row in candidates]
    expected = set(ids)
    if len(candidates) != 195 or len(expected) != 195:
        raise ValueError("recovery candidate pool must contain 195 unique rows")
    if set(labels) != expected:
        missing = sorted(expected - set(labels))
        extra = sorted(set(labels) - expected)
        raise ValueError(f"label ids do not match candidates: missing={missing} extra={extra}")
    if any(item["label"] not in ALLOWED_LABELS for item in labels.values()):
        raise ValueError("single-rater export contains an invalid label")

    development_families, expected_counts = choose_balanced_development_families(
        candidates, labels
    )
    development = [
        reviewed_row(row, labels[row["id"]]["label"], evaluator_id)
        for row in candidates
        if row["family_id"] in development_families
    ]
    reserve = [
        reviewed_row(row, labels[row["id"]]["label"], evaluator_id)
        for row in candidates
        if row["family_id"] not in development_families
    ]
    development_counts = Counter(row["reference_label"] for row in development)
    if len(development) != 90 or development_counts != expected_counts:
        raise AssertionError("single-rater development split is not exactly balanced")
    development_family_ids = {row["family_id"] for row in development}
    reserve_family_ids = {row["family_id"] for row in reserve}
    if development_family_ids & reserve_family_ids:
        raise AssertionError("scenario family leaked between development and reserve")

    manifest = {
        "artifact_version": "lurker-m5-recovery-single-rater-split-v1",
        "status": "EXPLORATORY_ONLY",
        "label_basis": "single_evaluator",
        "evaluator_id": evaluator_id,
        "human_consensus": False,
        "development": {
            "count": len(development),
            "class_counts": {action: development_counts[action] for action in ACTIONS},
            "family_ids": sorted(development_family_ids),
        },
        "locked_reserve": {
            "count": len(reserve),
            "family_ids": sorted(reserve_family_ids),
            "model_predictions_allowed": False,
        },
        "family_leakage_count": 0,
        "new_heldout_created": False,
        "heldout_opened": False,
        "model_predictions_seen_before_split": False,
        "aws_or_bedrock_calls": 0,
        "limitations": [
            "One evaluator cannot establish agreement or ambiguity.",
            "Results cannot support final M5 acceptance or a held-out GO decision.",
            "The locked reserve is not a validated held-out dataset.",
        ],
    }
    return development, reserve, manifest


def ensure_new(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite single-rater artifact: {path}")
    root = DEFAULT_ROOT.resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("single-rater outputs must stay under eval/recovery/single_rater")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def prepare(
    label_path: Path,
    candidates_path: Path = DEFAULT_CANDIDATES,
    source_path: Path = DEFAULT_SOURCE,
    development_path: Path = DEFAULT_DEVELOPMENT,
    reserve_path: Path = DEFAULT_RESERVE,
    manifest_path: Path = DEFAULT_MANIFEST,
    evaluator_id: str = "a1",
) -> dict[str, Any]:
    for path in (source_path, development_path, reserve_path, manifest_path):
        ensure_new(path)
    candidates = load_jsonl(candidates_path)
    labels = read_export(label_path)
    development, reserve, manifest = build_single_rater_split(
        candidates, labels, evaluator_id
    )

    source_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(label_path, source_path)
    write_jsonl(development_path, development)
    write_jsonl(reserve_path, reserve)
    manifest.update(
        {
            "source_export": str(source_path.relative_to(ROOT)),
            "source_export_sha256": sha256(source_path),
            "candidates": str(candidates_path.relative_to(ROOT)),
            "candidates_sha256": sha256(candidates_path),
            "development_path": str(development_path.relative_to(ROOT)),
            "development_sha256": sha256(development_path),
            "reserve_path": str(reserve_path.relative_to(ROOT)),
            "reserve_sha256": sha256(reserve_path),
        }
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--evaluator-id", default="a1")
    args = parser.parse_args()
    manifest = prepare(args.labels, evaluator_id=args.evaluator_id)
    print(json.dumps(manifest, indent=2))
    print("heldout_opened=false model_calls=0 aws_or_bedrock_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
