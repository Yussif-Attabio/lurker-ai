#!/usr/bin/env python3
"""Sweep confidence thresholds using tuning predictions only."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from decision_pattern.lurker_gate import apply_policy
from eval.metrics_def import compute_metrics, meets_criteria
from src.lurker.schemas import DeciderResult

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"


def load_tuning_rows(path: Path, context_k: int) -> list[dict[str, Any]]:
    """Load one context slice and refuse any file containing held-out predictions."""
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("prediction file is empty")
    observed_splits = {row["split"] for row in rows}
    if observed_splits != {"tuning"}:
        raise ValueError("threshold tuning accepts tuning predictions only")
    selected = [row for row in rows if int(row["context_k"]) == context_k]
    if not selected:
        raise ValueError(f"no tuning predictions found for k={context_k}")
    return selected


def apply_threshold_pair(
    rows: list[dict[str, Any]], reply_threshold: float, react_threshold: float
) -> list[dict[str, Any]]:
    """Reapply policy to saved real predictions without another model call."""
    adjusted: list[dict[str, Any]] = []
    config = {
        "reply_threshold": reply_threshold,
        "react_threshold": react_threshold,
    }
    for source in rows:
        result = DeciderResult(
            choice=source["raw_choice"] or None,
            confidence=float(source["confidence"]),
            latency_ms=float(source["decider_latency_ms"]),
            error=source.get("error") or None,
        )
        action, downgraded, reason = apply_policy(result, config)
        adjusted.append(
            {
                **source,
                "confidence": float(source["confidence"]),
                "decider_latency_ms": float(source["decider_latency_ms"]),
                "final_action": action,
                "downgraded": downgraded,
                "reason": reason,
            }
        )
    return adjusted


def sweep_thresholds(
    rows: list[dict[str, Any]], criteria: dict[str, float], step: float
) -> list[dict[str, Any]]:
    """Return every threshold pair and its exact tuning metrics."""
    if step <= 0 or step > 1:
        raise ValueError("step must be greater than 0 and at most 1")
    count = round(1 / step)
    values = sorted({round(index * step, 6) for index in range(count + 1)} | {1.0})
    results: list[dict[str, Any]] = []
    for reply_threshold in values:
        for react_threshold in values:
            metrics = compute_metrics(
                apply_threshold_pair(rows, reply_threshold, react_threshold)
            )
            results.append(
                {
                    "reply_threshold": reply_threshold,
                    "react_threshold": react_threshold,
                    "accuracy": metrics["accuracy"]["rate"],
                    "accuracy_n": metrics["accuracy"]["numerator"],
                    "accuracy_d": metrics["accuracy"]["denominator"],
                    "unnecessary_interruption_rate": metrics[
                        "unnecessary_interruption_rate"
                    ]["rate"],
                    "unnecessary_interruption_n": metrics[
                        "unnecessary_interruption_rate"
                    ]["numerator"],
                    "unnecessary_interruption_d": metrics[
                        "unnecessary_interruption_rate"
                    ]["denominator"],
                    "missed_help_rate": metrics["missed_help_rate"]["rate"],
                    "missed_help_n": metrics["missed_help_rate"]["numerator"],
                    "missed_help_d": metrics["missed_help_rate"]["denominator"],
                    "downgraded_count": metrics["low_confidence"]["downgraded_count"],
                    "meets_all_criteria": meets_criteria(metrics, criteria),
                }
            )
    return results


def recommendation_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """Rank feasible rows, then favor accuracy, safety, and quieter tied thresholds."""
    return (
        bool(row["meets_all_criteria"]),
        -1.0 if row["accuracy"] is None else float(row["accuracy"]),
        1.0
        - (
            1.0
            if row["missed_help_rate"] is None
            else float(row["missed_help_rate"])
        ),
        1.0
        - (
            1.0
            if row["unnecessary_interruption_rate"] is None
            else float(row["unnecessary_interruption_rate"])
        ),
        -int(row["downgraded_count"]),
        float(row["reply_threshold"]),
        float(row["react_threshold"]),
    )


def threshold_evidence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe which action thresholds the unanimous tuning labels can identify."""
    scored = [row for row in rows if row["consensus"] != "AMBIGUOUS"]
    consensus_counts = {
        action: sum(row["consensus"] == action for row in scored)
        for action in ("SILENT", "REACT", "REPLY")
    }
    raw_choice_counts = {
        action: sum(row["raw_choice"] == action for row in scored)
        for action in ("SILENT", "REACT", "REPLY")
    }
    unidentifiable: list[str] = []
    if consensus_counts["REPLY"] == 0 or raw_choice_counts["REPLY"] == 0:
        unidentifiable.append("reply_threshold")
    if consensus_counts["REACT"] == 0 or raw_choice_counts["REACT"] == 0:
        unidentifiable.append("react_threshold")
    return {
        "scored_consensus_counts": consensus_counts,
        "scored_raw_choice_counts": raw_choice_counts,
        "unidentifiable_thresholds": unidentifiable,
    }


def conservative_recommendation_pool(
    sweep: list[dict[str, Any]], evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    """Use threshold 1.0 when the tuning data cannot identify an action threshold."""
    pool = sweep
    if "reply_threshold" in evidence["unidentifiable_thresholds"]:
        pool = [row for row in pool if float(row["reply_threshold"]) == 1.0]
    if "react_threshold" in evidence["unidentifiable_thresholds"]:
        pool = [row for row in pool if float(row["react_threshold"]) == 1.0]
    return pool


def write_sweep(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write all threshold pairs and raw counts to CSV."""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="tuning run per_case.csv")
    parser.add_argument("--k", type=int, default=3, choices=(0, 3, 5))
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    try:
        rows = load_tuning_rows(args.predictions, args.k)
        raw_criteria = yaml.safe_load(args.criteria.read_text())
        criteria = {
            "accuracy_min": float(raw_criteria["accuracy_min"]),
            "unnecessary_interruption_rate_max": float(
                raw_criteria["unnecessary_interruption_rate_max"]
            ),
            "missed_help_rate_max": float(raw_criteria["missed_help_rate_max"]),
        }
        sweep = sweep_thresholds(rows, criteria, args.step)
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"threshold tuning refused: {exc}") from exc

    evidence = threshold_evidence(rows)
    ranked = sorted(
        conservative_recommendation_pool(sweep, evidence),
        key=recommendation_key,
        reverse=True,
    )
    recommendation = ranked[0]
    output_dir = args.output_dir or args.predictions.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    write_sweep(output_dir / "threshold_sweep.csv", sweep)
    (output_dir / "threshold_recommendation.json").write_text(
        json.dumps(
            {
                "context_k": args.k,
                "criteria": criteria,
                "threshold_evidence": evidence,
                "recommendation": recommendation,
                "human_approval_required": True,
                "instructions": (
                    "Review the sweep and evidence limitations, then copy approved thresholds "
                    "into config/default.yaml. A 1.0 value for an unidentifiable threshold is a "
                    "conservative fallback, not an empirically tuned result."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Top threshold candidates (human approval required):")
    if evidence["unidentifiable_thresholds"]:
        print(
            "Evidence limitation: "
            + ", ".join(evidence["unidentifiable_thresholds"])
            + " cannot be identified; candidate output uses conservative threshold 1.0."
        )
    for row in ranked[:10]:
        print(
            f"reply={row['reply_threshold']:.2f} react={row['react_threshold']:.2f} "
            f"accuracy={row['accuracy']} interruption={row['unnecessary_interruption_rate']} "
            f"missed_help={row['missed_help_rate']} meets_all={row['meets_all_criteria']}"
        )
    print(f"wrote={output_dir / 'threshold_sweep.csv'}")
    print(f"wrote={output_dir / 'threshold_recommendation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
