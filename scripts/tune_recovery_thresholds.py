#!/usr/bin/env python3
"""Sweep thresholds on M5 recovery development predictions only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval.metrics_def import compute_metrics
from scripts.tune_thresholds import (
    apply_threshold_pair,
    load_tuning_rows,
    recommendation_key,
    sweep_thresholds,
    write_sweep,
)

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_RESULTS = ROOT / "results" / "m5_recovery" / "development"
BASELINE = {"reply_threshold": 0.20, "react_threshold": 0.04}
PROPOSED_CRITERIA = {
    "accuracy_min": 0.75,
    "unnecessary_interruption_rate_max": 0.20,
    "missed_help_rate_max": 0.25,
    "react_precision_min": 0.70,
    "react_recall_min": 0.70,
}


def validate_prediction_path(path: Path) -> None:
    resolved = path.resolve()
    root = RECOVERY_RESULTS.resolve()
    if root not in resolved.parents or path.name != "per_case.csv":
        raise ValueError("threshold tuning accepts recovery development per_case.csv files only")


def augment_react_metrics(
    sweep: list[dict[str, Any]], source_rows: list[dict[str, Any]]
) -> None:
    for row in sweep:
        metrics = compute_metrics(
            apply_threshold_pair(
                source_rows,
                float(row["reply_threshold"]),
                float(row["react_threshold"]),
            )
        )
        row["react_precision"] = metrics["react_precision"]["rate"]
        row["react_precision_n"] = metrics["react_precision"]["numerator"]
        row["react_precision_d"] = metrics["react_precision"]["denominator"]
        row["react_recall"] = metrics["react_recall"]["rate"]
        row["react_recall_n"] = metrics["react_recall"]["numerator"]
        row["react_recall_d"] = metrics["react_recall"]["denominator"]
        row["meets_recovery_criteria"] = bool(
            row["accuracy"] is not None
            and row["accuracy"] >= PROPOSED_CRITERIA["accuracy_min"]
            and row["unnecessary_interruption_rate"] is not None
            and row["unnecessary_interruption_rate"]
            <= PROPOSED_CRITERIA["unnecessary_interruption_rate_max"]
            and row["missed_help_rate"] is not None
            and row["missed_help_rate"] <= PROPOSED_CRITERIA["missed_help_rate_max"]
            and row["react_precision"] is not None
            and row["react_precision"] >= PROPOSED_CRITERIA["react_precision_min"]
            and row["react_recall"] is not None
            and row["react_recall"] >= PROPOSED_CRITERIA["react_recall_min"]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--k", type=int, default=3, choices=(0, 3, 5))
    parser.add_argument("--step", type=float, default=0.02)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    validate_prediction_path(args.predictions)
    rows = load_tuning_rows(args.predictions, args.k)
    if len(rows) != 90 or any(not row["id"].startswith("rc") for row in rows):
        raise SystemExit("recovery threshold tuning requires exactly 90 rc-prefixed development rows")
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
    output_dir = args.output_dir or args.predictions.parent / f"threshold_k{args.k}"
    if RECOVERY_RESULTS.resolve() not in output_dir.resolve().parents:
        raise SystemExit("recovery threshold outputs must stay under results/m5_recovery/development")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_sweep(output_dir / "threshold_sweep.csv", sweep)
    (output_dir / "threshold_recommendation.json").write_text(
        json.dumps(
            {
                "artifact_version": "lurker-m5-recovery-threshold-review-v1",
                "development_only": True,
                "context_k": args.k,
                "starting_baseline": BASELINE,
                "proposed_criteria_not_heldout_frozen": PROPOSED_CRITERIA,
                "recommendation": ranked[0],
                "human_approval_required": True,
                "production_configuration_changed": False,
                "heldout_opened": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote={output_dir} candidates={len(sweep)} heldout_opened=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
