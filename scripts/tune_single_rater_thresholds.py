#!/usr/bin/env python3
"""Explore thresholds on single-rater development predictions only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from eval.metrics_def import compute_metrics
from scripts.tune_recovery_thresholds import (
    BASELINE,
    PROPOSED_CRITERIA,
    augment_react_metrics,
)
from scripts.tune_thresholds import (
    apply_threshold_pair,
    recommendation_key,
    sweep_thresholds,
    write_sweep,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results" / "m5_recovery" / "single_rater" / "development"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path, context_k: int) -> list[dict[str, Any]]:
    resolved = path.resolve()
    if RESULTS_ROOT.resolve() not in resolved.parents or path.name != "per_case.csv":
        raise ValueError("single-rater tuning accepts only its development per_case.csv")
    with path.open(newline="", encoding="utf-8") as stream:
        source = list(csv.DictReader(stream))
    if not source or {row["split"] for row in source} != {"tuning"}:
        raise ValueError("single-rater threshold input must contain tuning rows only")
    if {row["label_basis"] for row in source} != {"single_evaluator"}:
        raise ValueError("single-rater threshold input has an invalid label basis")
    selected = []
    for row in source:
        if int(row["context_k"]) != context_k:
            continue
        selected.append({**row, "consensus": row["reference_label"]})
    if len(selected) != 90:
        raise ValueError("single-rater threshold tuning requires exactly 90 rows")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--k", type=int, default=3, choices=(0, 3, 5))
    parser.add_argument("--step", type=float, default=0.02)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    rows = load_rows(args.predictions, args.k)
    base_criteria = {
        key: PROPOSED_CRITERIA[key]
        for key in (
            "accuracy_min",
            "unnecessary_interruption_rate_max",
            "missed_help_rate_max",
        )
    }
    sweep = sweep_thresholds(rows, base_criteria, args.step)
    augment_react_metrics(sweep, rows)
    ranked = sorted(
        sweep,
        key=lambda row: (bool(row["meets_recovery_criteria"]), *recommendation_key(row)),
        reverse=True,
    )
    meeting = [row for row in ranked if row["meets_recovery_criteria"]]
    baseline_metrics = compute_metrics(
        apply_threshold_pair(rows, BASELINE["reply_threshold"], BASELINE["react_threshold"])
    )
    output_dir = args.output_dir or args.predictions.parent / f"threshold_k{args.k}"
    if RESULTS_ROOT.resolve() not in output_dir.resolve().parents:
        raise ValueError("single-rater threshold outputs must stay under their result root")
    output_dir.mkdir(parents=True, exist_ok=False)
    write_sweep(output_dir / "threshold_sweep.csv", sweep)
    result = {
        "artifact_version": "lurker-m5-recovery-single-rater-threshold-review-v1",
        "status": "EXPLORATORY_ONLY",
        "development_only": True,
        "label_basis": "single_evaluator",
        "human_consensus": False,
        "context_k": args.k,
        "source_predictions_sha256": sha256(args.predictions),
        "starting_baseline": BASELINE,
        "proposed_recovery_criteria_not_frozen": PROPOSED_CRITERIA,
        "baseline_metrics": baseline_metrics,
        "threshold_pair_count": len(sweep),
        "pairs_meeting_all_recovery_criteria": len(meeting),
        "best_observed_tradeoff": ranked[0],
        "recommendation": (
            meeting[0]
            if meeting
            else "Keep production thresholds unchanged; no tested pair meets all recovery criteria."
        ),
        "production_configuration_changed": False,
        "heldout_opened": False,
        "reserve_opened": False,
        "model_calls": 0,
        "aws_or_bedrock_calls": 0,
    }
    (output_dir / "threshold_review.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"wrote={output_dir} candidates={len(sweep)} meeting_all={len(meeting)} "
        "production_config_changed=false heldout_opened=false model_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
