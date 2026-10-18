#!/usr/bin/env python3
"""Merge three blind M5 recovery label exports using unanimous consensus only."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = ROOT / "eval" / "recovery"
DEFAULT_CANDIDATES = RECOVERY_ROOT / "candidates.jsonl"
DEFAULT_UNANIMOUS = RECOVERY_ROOT / "labeling" / "unanimous.jsonl"
DEFAULT_AMBIGUOUS = RECOVERY_ROOT / "labeling" / "ambiguity_audit.jsonl"
DEFAULT_REPORT = RECOVERY_ROOT / "labeling" / "agreement_report.json"
ALLOWED_LABELS = {"SILENT", "REACT", "REPLY"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def read_export(path: Path) -> dict[str, dict[str, str]]:
    """Read one complete evaluator export without accepting blank or invalid labels."""
    result: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not {"id", "label"}.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain id and label columns")
        for line_number, row in enumerate(reader, start=2):
            scenario_id = (row.get("id") or "").strip()
            label = (row.get("label") or "").strip().upper()
            note = (row.get("optional note") or "").strip()
            if not scenario_id:
                raise ValueError(f"{path}:{line_number} has no scenario id")
            if scenario_id in result:
                raise ValueError(f"{path} contains duplicate id {scenario_id}")
            if label not in ALLOWED_LABELS:
                raise ValueError(f"{path}:{line_number} has invalid or blank label")
            result[scenario_id] = {"label": label, "note": note}
    return result


def fleiss_kappa(label_sets: list[list[str]]) -> float | None:
    """Calculate Fleiss' kappa for three fixed raters and three categories."""
    if not label_sets:
        return None
    n_raters = 3
    item_agreement: list[float] = []
    totals = Counter[str]()
    for labels in label_sets:
        if len(labels) != n_raters:
            raise ValueError("Fleiss kappa requires exactly three labels per item")
        counts = Counter(labels)
        totals.update(labels)
        item_agreement.append(
            (sum(count * count for count in counts.values()) - n_raters)
            / (n_raters * (n_raters - 1))
        )
    observed = sum(item_agreement) / len(item_agreement)
    total_labels = len(label_sets) * n_raters
    expected = sum((totals[action] / total_labels) ** 2 for action in ALLOWED_LABELS)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def ensure_recovery_output(path: Path) -> None:
    recovery_root = RECOVERY_ROOT.resolve()
    resolved = path.resolve()
    if resolved != recovery_root and recovery_root not in resolved.parents:
        raise ValueError("recovery label outputs must stay under eval/recovery")


def merge_recovery_labels(
    candidates_path: Path,
    label_paths: list[Path],
    unanimous_path: Path,
    ambiguous_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Merge genuine exports and keep every disagreement in a separate audit pool."""
    if len(label_paths) != 3 or len({path.resolve() for path in label_paths}) != 3:
        raise ValueError("exactly three different evaluator files are required")
    for path in (unanimous_path, ambiguous_path, report_path):
        ensure_recovery_output(path)

    candidates = load_jsonl(candidates_path)
    ids = [row["id"] for row in candidates]
    expected = set(ids)
    if len(candidates) != 195 or len(expected) != 195:
        raise ValueError("recovery candidate pool must contain 195 unique rows")
    exports = [read_export(path) for path in label_paths]
    for path, export in zip(label_paths, exports, strict=True):
        missing = expected - set(export)
        extra = set(export) - expected
        if missing or extra:
            raise ValueError(
                f"{path} ids do not match candidates: missing={sorted(missing)} extra={sorted(extra)}"
            )

    unanimous: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    all_label_sets: list[list[str]] = []
    for candidate in candidates:
        scenario_id = candidate["id"]
        labels = [export[scenario_id]["label"] for export in exports]
        notes = {
            f"a{index + 1}": export[scenario_id]["note"]
            for index, export in enumerate(exports)
            if export[scenario_id]["note"]
        }
        all_label_sets.append(labels)
        merged = {
            **candidate,
            "labels": {"a1": labels[0], "a2": labels[1], "a3": labels[2]},
            "consensus": labels[0] if len(set(labels)) == 1 else "AMBIGUOUS",
            "notes": notes,
        }
        (unanimous if len(set(labels)) == 1 else ambiguous).append(merged)

    for path in (unanimous_path, ambiguous_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    unanimous_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in unanimous),
        encoding="utf-8",
    )
    ambiguous_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in ambiguous),
        encoding="utf-8",
    )
    consensus_counts = Counter(row["consensus"] for row in unanimous)
    report = {
        "artifact_version": "lurker-m5-recovery-agreement-v1",
        "candidate_count": len(candidates),
        "unanimous_count": len(unanimous),
        "ambiguous_count": len(ambiguous),
        "ambiguity_rate": len(ambiguous) / len(candidates),
        "fleiss_kappa": fleiss_kappa(all_label_sets),
        "unanimous_class_counts": {
            action: consensus_counts[action] for action in ("SILENT", "REACT", "REPLY")
        },
        "quality_targets": {
            "ambiguity_rate_max": 0.20,
            "fleiss_kappa_min": 0.60,
            "development_per_class": 30,
            "heldout_per_class": 20,
        },
        "ready_for_grouped_split": all(consensus_counts[action] >= 50 for action in ALLOWED_LABELS),
        "human_labels_are_ground_truth": True,
        "model_predictions_used": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a1", type=Path, required=True)
    parser.add_argument("--a2", type=Path, required=True)
    parser.add_argument("--a3", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--unanimous-output", type=Path, default=DEFAULT_UNANIMOUS)
    parser.add_argument("--ambiguous-output", type=Path, default=DEFAULT_AMBIGUOUS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = merge_recovery_labels(
        args.candidates,
        [args.a1, args.a2, args.a3],
        args.unanimous_output,
        args.ambiguous_output,
        args.report,
    )
    print(json.dumps(report, indent=2))
    print("heldout_evaluated=false model_calls=0 aws_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
