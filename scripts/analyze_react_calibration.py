#!/usr/bin/env python3
"""Combine original tuning evidence with calibration evidence and tune safely."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from eval.metrics_def import compute_metrics
from scripts.run_eval import PER_CASE_FIELDS
from scripts.tune_thresholds import (
    apply_threshold_pair,
    conservative_recommendation_pool,
    recommendation_key,
    sweep_thresholds,
    threshold_evidence,
    write_sweep,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALIBRATION_SCENARIOS = ROOT / "eval" / "react_calibration_scenarios.jsonl"
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"


def read_prediction_rows(path: Path) -> list[dict[str, Any]]:
    """Read one run and reject anything other than tuning evidence."""
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"{path} is empty")
    if set(rows[0]) != set(PER_CASE_FIELDS):
        raise ValueError(f"{path} does not match the evaluation prediction schema")
    observed_splits = {row["split"] for row in rows}
    if observed_splits != {"tuning"}:
        raise ValueError(f"{path} must contain tuning predictions only")
    keys = [(row["id"], int(row["context_k"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{path} contains duplicate scenario/context rows")
    return rows


def reviewed_calibration_ids(path: Path) -> set[str]:
    """Require the separate merged dataset before accepting model evidence."""
    scenarios = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(scenarios) != 15:
        raise ValueError("reviewed calibration dataset must contain exactly 15 scenarios")
    if any(row.get("split") != "tuning" for row in scenarios):
        raise ValueError("reviewed calibration scenarios must all be tuning-only")
    if any(row.get("consensus") not in {"SILENT", "REACT", "REPLY", "AMBIGUOUS"} for row in scenarios):
        raise ValueError("reviewed calibration scenarios contain an invalid consensus")
    ids = {row["id"] for row in scenarios}
    if len(ids) != 15:
        raise ValueError("reviewed calibration scenario ids must be unique")
    return ids


def combine_prediction_rows(
    original_rows: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
    calibration_ids: set[str],
) -> list[dict[str, Any]]:
    """Return disjoint tuning rows after verifying calibration coverage."""
    original_ids = {row["id"] for row in original_rows}
    observed_calibration_ids = {row["id"] for row in calibration_rows}
    if observed_calibration_ids != calibration_ids:
        raise ValueError("calibration predictions do not exactly match reviewed calibration ids")
    if original_ids & calibration_ids:
        raise ValueError("original and calibration scenario ids must be disjoint")
    original_contexts = {int(row["context_k"]) for row in original_rows}
    calibration_contexts = {int(row["context_k"]) for row in calibration_rows}
    if original_contexts != calibration_contexts:
        raise ValueError("original and calibration runs must use the same context values")
    expected_calibration_rows = len(calibration_ids) * len(calibration_contexts)
    if len(calibration_rows) != expected_calibration_rows:
        raise ValueError("calibration run is missing scenario/context predictions")
    return original_rows + calibration_rows


def write_prediction_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a new combined evidence file without modifying either source run."""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PER_CASE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def action_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Return stable action counts for evidence summaries."""
    counts = Counter(row[field] for row in rows)
    return {action: counts.get(action, 0) for action in ("SILENT", "REACT", "REPLY", "AMBIGUOUS")}


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate unthresholded metrics from raw choices, not saved policy output."""
    return compute_metrics(apply_threshold_pair(rows, 0.0, 0.0))


def per_action_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    """Report precision and recall for each scored action after policy application."""
    scored = [row for row in rows if row["consensus"] != "AMBIGUOUS"]
    output: dict[str, dict[str, float | int | None]] = {}
    for action in ("SILENT", "REACT", "REPLY"):
        actual = sum(row["consensus"] == action for row in scored)
        predicted = sum(row["final_action"] == action for row in scored)
        true_positive = sum(
            row["consensus"] == action and row["final_action"] == action
            for row in scored
        )
        output[action] = {
            "actual": actual,
            "predicted": predicted,
            "true_positive": true_positive,
            "precision": true_positive / predicted if predicted else None,
            "recall": true_positive / actual if actual else None,
        }
    return output


def percent(metric: dict[str, Any]) -> str:
    rate = metric["rate"]
    return "N/A" if rate is None else f"{rate * 100:.1f}%"


def build_report(payload: dict[str, Any]) -> str:
    """Create a compact human-approval report for the calibration recommendation."""
    rec = payload["recommendation"]
    evidence = payload["threshold_evidence"]
    react = payload["candidate_action_metrics"]["REACT"]
    react_precision = "N/A" if react["precision"] is None else f"{react['precision'] * 100:.1f}%"
    react_recall = "N/A" if react["recall"] is None else f"{react['recall'] * 100:.1f}%"
    sections = [
        "# M1 REACT calibration analysis",
        "",
        "This report combines the preserved original tuning predictions with the separate calibration run. It does not use held-out scenarios or modify production thresholds.",
        "",
        "## Evidence",
        "",
        f"- Original tuning scenarios at k={payload['context_k']}: {payload['counts']['original_scenarios']}",
        f"- Calibration scenarios at k={payload['context_k']}: {payload['counts']['calibration_scenarios']}",
        f"- Combined scenarios at k={payload['context_k']}: {payload['counts']['combined_scenarios']}",
        f"- Calibration consensus: {payload['calibration_consensus_counts']}",
        f"- Combined raw choices: {payload['combined_raw_choice_counts']}",
        "",
        "## Unthresholded combined metrics",
        "",
        f"- Accuracy: {percent(payload['combined_unthresholded_metrics']['accuracy'])}",
        f"- Unnecessary-interruption rate: {percent(payload['combined_unthresholded_metrics']['unnecessary_interruption_rate'])}",
        f"- Missed-help rate: {percent(payload['combined_unthresholded_metrics']['missed_help_rate'])}",
        "",
        "## Candidate thresholds",
        "",
        f"- Reply threshold: {rec['reply_threshold']}",
        f"- REACT threshold: {rec['react_threshold']}",
        f"- Accuracy: {rec['accuracy_n']}/{rec['accuracy_d']} ({rec['accuracy'] * 100:.1f}%)",
        f"- Unnecessary interruption: {rec['unnecessary_interruption_n']}/{rec['unnecessary_interruption_d']} ({rec['unnecessary_interruption_rate'] * 100:.1f}%)",
        f"- Missed help: {rec['missed_help_n']}/{rec['missed_help_d']} ({rec['missed_help_rate'] * 100:.1f}%)",
        f"- Meets all criteria: {rec['meets_all_criteria']}",
        f"- Unidentifiable thresholds: {evidence['unidentifiable_thresholds']}",
        "",
        "## REACT-class check",
        "",
        f"- Human-consensus REACT cases: {react['actual']}",
        f"- Scored REACT predictions after thresholds: {react['predicted']}",
        f"- Correct REACT predictions: {react['true_positive']}",
        f"- REACT precision: {react_precision}",
        f"- REACT recall: {react_recall}",
        "",
        "The overall success criteria do not contain a class-specific REACT recall gate. A passing overall result therefore does not by itself establish strong REACT coverage.",
        "",
        "## Decision status",
        "",
        "PENDING. The project owner must review this evidence before changing `config/default.yaml` or approving final M1 GO.",
        "",
    ]
    return "\n".join(sections)


def analyze(
    original_predictions: Path,
    calibration_predictions: Path,
    calibration_scenarios: Path,
    criteria_path: Path,
    output_dir: Path,
    context_k: int = 3,
    step: float = 0.05,
) -> dict[str, Any]:
    """Validate, combine, calculate metrics, and write an approval-only recommendation."""
    if output_dir.resolve() == original_predictions.parent.resolve():
        raise ValueError("calibration analysis may not write into the original result directory")

    original_rows = read_prediction_rows(original_predictions)
    calibration_rows = read_prediction_rows(calibration_predictions)
    calibration_ids = reviewed_calibration_ids(calibration_scenarios)
    combined_rows = combine_prediction_rows(original_rows, calibration_rows, calibration_ids)

    original_k = [row for row in original_rows if int(row["context_k"]) == context_k]
    calibration_k = [row for row in calibration_rows if int(row["context_k"]) == context_k]
    combined_k = [row for row in combined_rows if int(row["context_k"]) == context_k]
    if not original_k or len(calibration_k) != 15:
        raise ValueError(f"both runs must contain complete k={context_k} evidence")

    raw_criteria = yaml.safe_load(criteria_path.read_text())
    criteria = {
        "accuracy_min": float(raw_criteria["accuracy_min"]),
        "unnecessary_interruption_rate_max": float(raw_criteria["unnecessary_interruption_rate_max"]),
        "missed_help_rate_max": float(raw_criteria["missed_help_rate_max"]),
    }
    sweep = sweep_thresholds(combined_k, criteria, step)
    evidence = threshold_evidence(combined_k)
    ranked = sorted(
        conservative_recommendation_pool(sweep, evidence),
        key=recommendation_key,
        reverse=True,
    )
    recommendation = ranked[0]
    candidate_rows = apply_threshold_pair(
        combined_k,
        float(recommendation["reply_threshold"]),
        float(recommendation["react_threshold"]),
    )
    calibration_candidate_rows = apply_threshold_pair(
        calibration_k,
        float(recommendation["reply_threshold"]),
        float(recommendation["react_threshold"]),
    )

    payload = {
        "context_k": context_k,
        "criteria": criteria,
        "counts": {
            "original_scenarios": len(original_k),
            "calibration_scenarios": len(calibration_k),
            "combined_scenarios": len(combined_k),
        },
        "calibration_consensus_counts": action_counts(calibration_k, "consensus"),
        "combined_raw_choice_counts": action_counts(combined_k, "raw_choice"),
        "original_unthresholded_metrics": metric_summary(original_k),
        "calibration_unthresholded_metrics": metric_summary(calibration_k),
        "combined_unthresholded_metrics": metric_summary(combined_k),
        "threshold_evidence": evidence,
        "recommendation": recommendation,
        "candidate_action_metrics": per_action_metrics(candidate_rows),
        "calibration_candidate_action_metrics": per_action_metrics(
            calibration_candidate_rows
        ),
        "human_approval_required": True,
        "production_config_modified": False,
        "heldout_used": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_prediction_rows(output_dir / "combined_per_case.csv", combined_rows)
    write_sweep(output_dir / "threshold_sweep.csv", sweep)
    (output_dir / "threshold_recommendation.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "calibration_report.md").write_text(
        build_report(payload), encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-predictions", type=Path, required=True)
    parser.add_argument("--calibration-predictions", type=Path, required=True)
    parser.add_argument("--calibration-scenarios", type=Path, default=DEFAULT_CALIBRATION_SCENARIOS)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--k", type=int, choices=(0, 3, 5), default=3)
    parser.add_argument("--step", type=float, default=0.05)
    args = parser.parse_args()
    output_dir = args.output_dir or args.calibration_predictions.parent

    try:
        payload = analyze(
            args.original_predictions,
            args.calibration_predictions,
            args.calibration_scenarios,
            args.criteria,
            output_dir,
            args.k,
            args.step,
        )
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"calibration analysis refused: {exc}") from exc

    recommendation = payload["recommendation"]
    print(
        f"wrote={output_dir} combined={payload['counts']['combined_scenarios']} "
        f"react_labels={payload['calibration_consensus_counts']['REACT']} "
        f"candidate_reply={recommendation['reply_threshold']:.2f} "
        f"candidate_react={recommendation['react_threshold']:.2f} "
        "production_config_modified=false human_approval_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
