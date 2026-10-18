#!/usr/bin/env python3
"""Create a family-grouped M5 recovery split after genuine unanimous labeling."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = ROOT / "eval" / "recovery"
DEFAULT_UNANIMOUS = RECOVERY_ROOT / "labeling" / "unanimous.jsonl"
DEFAULT_DEVELOPMENT = RECOVERY_ROOT / "development" / "development.jsonl"
DEFAULT_HELDOUT = RECOVERY_ROOT / "heldout" / "new_heldout_locked.jsonl"
DEFAULT_RESERVE = RECOVERY_ROOT / "labeling" / "family_locked_reserve.jsonl"
DEFAULT_MANIFEST = RECOVERY_ROOT / "split_manifest.json"
SEED = 20261017
ACTIONS = ("SILENT", "REACT", "REPLY")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts_for(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(row["consensus"] for row in rows)


def choose_partition(
    rows: list[dict[str, Any]],
    seed: int = SEED,
    max_attempts: int = 100_000,
) -> tuple[set[str], set[str]]:
    """Find disjoint family allocations with enough rows for exact class quotas."""
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[row["family_id"]].append(row)
    families = sorted(by_family)
    if len(families) != 39:
        raise ValueError("expected all 39 scenario families before grouped splitting")

    rng = random.Random(seed)
    for _ in range(max_attempts):
        shuffled = list(families)
        rng.shuffle(shuffled)
        heldout_families = set(shuffled[:15])
        development_families = set(shuffled[15:36])
        heldout_counts = counts_for(
            [row for family in heldout_families for row in by_family[family]]
        )
        development_counts = counts_for(
            [row for family in development_families for row in by_family[family]]
        )
        if all(heldout_counts[action] >= 20 for action in ACTIONS) and all(
            development_counts[action] >= 30 for action in ACTIONS
        ):
            return development_families, heldout_families
    raise ValueError(
        "could not satisfy 30/30/30 development and 20/20/20 held-out quotas "
        "without family leakage; label additional candidates"
    )


def deterministic_pick(
    rows: list[dict[str, Any]],
    families: set[str],
    per_class: int,
    split_name: str,
    seed: int,
) -> list[dict[str, Any]]:
    """Choose exact per-class quotas without moving a family to another split."""
    eligible = [row for row in rows if row["family_id"] in families]
    selected: list[dict[str, Any]] = []
    for action in ACTIONS:
        action_rows = [row for row in eligible if row["consensus"] == action]
        action_rows.sort(
            key=lambda row: hashlib.sha256(
                f"{seed}:{split_name}:{row['id']}".encode()
            ).hexdigest()
        )
        if len(action_rows) < per_class:
            raise ValueError(f"{split_name} has fewer than {per_class} {action} candidates")
        selected.extend(action_rows[:per_class])
    return sorted(selected, key=lambda row: row["id"])


def reviewed_row(row: dict[str, Any], split: str) -> dict[str, Any]:
    """Convert a merged recovery row into the existing Scenario contract."""
    return {
        "id": row["id"],
        "split": split,
        "category": row["category"],
        "history": row["history"],
        "message": row["message"],
        "labels": row["labels"],
        "consensus": row["consensus"],
        "notes": "M5 recovery dataset; family-grouped before any model prediction.",
    }


def ensure_new(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen recovery artifact: {path}")
    recovery_root = RECOVERY_ROOT.resolve()
    resolved = path.resolve()
    if resolved != recovery_root and recovery_root not in resolved.parents:
        raise ValueError("recovery split outputs must stay under eval/recovery")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def create_grouped_split(
    unanimous_path: Path,
    development_path: Path,
    heldout_path: Path,
    reserve_path: Path,
    manifest_path: Path,
    seed: int = SEED,
) -> dict[str, Any]:
    """Freeze exact balanced splits without opening any prior held-out dataset."""
    for path in (development_path, heldout_path, reserve_path, manifest_path):
        ensure_new(path)
    rows = load_jsonl(unanimous_path)
    if any(row.get("consensus") not in ACTIONS for row in rows):
        raise ValueError("split input must contain unanimous labels only")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("unanimous input contains duplicate ids")

    development_families, heldout_families = choose_partition(rows, seed)
    development_selected = deterministic_pick(
        rows, development_families, 30, "development", seed
    )
    heldout_selected = deterministic_pick(rows, heldout_families, 20, "heldout", seed)
    selected_ids = {row["id"] for row in development_selected + heldout_selected}
    reserve = [row for row in rows if row["id"] not in selected_ids]

    development = [reviewed_row(row, "tuning") for row in development_selected]
    heldout = [reviewed_row(row, "heldout") for row in heldout_selected]
    write_jsonl(development_path, development)
    write_jsonl(heldout_path, heldout)
    write_jsonl(reserve_path, reserve)

    development_family_set = {row["family_id"] for row in development_selected}
    heldout_family_set = {row["family_id"] for row in heldout_selected}
    if development_family_set & heldout_family_set:
        raise AssertionError("scenario family leaked across development and held-out")
    manifest = {
        "artifact_version": "lurker-m5-recovery-split-v1",
        "seed": seed,
        "method": "family-grouped, human-consensus-stratified, deterministic selection",
        "development": {
            "path": str(development_path.relative_to(ROOT)),
            "ids": [row["id"] for row in development_selected],
            "family_ids": sorted(development_family_set),
            "class_counts": dict(counts_for(development_selected)),
            "sha256": sha256(development_path),
        },
        "heldout": {
            "path": str(heldout_path.relative_to(ROOT)),
            "ids": [row["id"] for row in heldout_selected],
            "family_ids": sorted(heldout_family_set),
            "class_counts": dict(counts_for(heldout_selected)),
            "sha256": sha256(heldout_path),
            "evaluated": False,
        },
        "reserve": {
            "path": str(reserve_path.relative_to(ROOT)),
            "count": len(reserve),
            "sha256": sha256(reserve_path),
        },
        "family_leakage_count": 0,
        "model_predictions_seen_before_split": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unanimous", type=Path, default=DEFAULT_UNANIMOUS)
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--heldout", type=Path, default=DEFAULT_HELDOUT)
    parser.add_argument("--reserve", type=Path, default=DEFAULT_RESERVE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = create_grouped_split(
        args.unanimous,
        args.development,
        args.heldout,
        args.reserve,
        args.manifest,
        args.seed,
    )
    print(json.dumps(manifest, indent=2))
    print("heldout_evaluated=false model_calls=0 aws_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
