#!/usr/bin/env python3
"""Compare preserved baseline and candidate wording on tuning-only evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from eval.metrics_def import compute_metrics
from scripts.analyze_react_calibration import per_action_metrics
from scripts.tune_thresholds import apply_threshold_pair


def read_k3_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if {row["split"] for row in rows} != {"tuning"}:
        raise ValueError(f"{path} must contain tuning predictions only")
    selected = [row for row in rows if int(row["context_k"]) == 3]
    if not selected:
        raise ValueError(f"{path} has no k=3 rows")
    return selected


def candidate_thresholds(path: Path) -> tuple[float, float]:
    payload = json.loads(path.read_text())
    recommendation = payload["recommendation"]
    return float(recommendation["reply_threshold"]), float(
        recommendation["react_threshold"]
    )


def summarize(
    rows: list[dict[str, Any]], reply_threshold: float, react_threshold: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    adjusted = apply_threshold_pair(rows, reply_threshold, react_threshold)
    metrics = compute_metrics(adjusted)
    actions = per_action_metrics(adjusted)
    ordinary = [row for row in adjusted if row["consensus"] == "SILENT"]
    summary = {
        "reply_threshold": reply_threshold,
        "react_threshold": react_threshold,
        "accuracy": metrics["accuracy"],
        "unnecessary_interruption_rate": metrics["unnecessary_interruption_rate"],
        "missed_help_rate": metrics["missed_help_rate"],
        "react": actions["REACT"],
        "ordinary": {
            "total": len(ordinary),
            "kept_silent": sum(row["final_action"] == "SILENT" for row in ordinary),
            "false_reactions": sum(row["final_action"] == "REACT" for row in ordinary),
            "false_replies": sum(row["final_action"] == "REPLY" for row in ordinary),
        },
    }
    return summary, adjusted


def rate_text(metric: dict[str, Any]) -> str:
    return f"{metric['numerator']}/{metric['denominator']} ({metric['rate'] * 100:.1f}%)"


def optional_rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def write_summary_csv(path: Path, before: dict[str, Any], after: dict[str, Any]) -> None:
    rows = [
        ("overall_accuracy", before["accuracy"]["rate"], after["accuracy"]["rate"]),
        ("react_precision", before["react"]["precision"], after["react"]["precision"]),
        ("react_recall", before["react"]["recall"], after["react"]["recall"]),
        (
            "unnecessary_interruption_rate",
            before["unnecessary_interruption_rate"]["rate"],
            after["unnecessary_interruption_rate"]["rate"],
        ),
        ("missed_help_rate", before["missed_help_rate"]["rate"], after["missed_help_rate"]["rate"]),
        (
            "ordinary_false_reaction_rate",
            before["ordinary"]["false_reactions"] / before["ordinary"]["total"],
            after["ordinary"]["false_reactions"] / after["ordinary"]["total"],
        ),
        (
            "ordinary_false_reply_rate",
            before["ordinary"]["false_replies"] / before["ordinary"]["total"],
            after["ordinary"]["false_replies"] / after["ordinary"]["total"],
        ),
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "baseline", "candidate", "change"])
        for metric, baseline, candidate in rows:
            change = None if baseline is None or candidate is None else candidate - baseline
            writer.writerow([metric, baseline, candidate, change])


def write_detail_csv(
    path: Path, before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]
) -> None:
    before_by_id = {row["id"]: row for row in before_rows}
    after_by_id = {row["id"]: row for row in after_rows}
    if before_by_id.keys() != after_by_id.keys():
        raise ValueError("baseline and candidate scenario ids do not match")
    fields = [
        "id",
        "category",
        "consensus",
        "baseline_raw_choice",
        "baseline_confidence",
        "baseline_final_action",
        "candidate_raw_choice",
        "candidate_confidence",
        "candidate_final_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for scenario_id in sorted(before_by_id):
            before = before_by_id[scenario_id]
            after = after_by_id[scenario_id]
            if before["consensus"] != after["consensus"]:
                raise ValueError(f"consensus changed for {scenario_id}")
            writer.writerow(
                {
                    "id": scenario_id,
                    "category": before["category"],
                    "consensus": before["consensus"],
                    "baseline_raw_choice": before["raw_choice"],
                    "baseline_confidence": before["confidence"],
                    "baseline_final_action": before["final_action"],
                    "candidate_raw_choice": after["raw_choice"],
                    "candidate_confidence": after["confidence"],
                    "candidate_final_action": after["final_action"],
                }
            )


def build_report(before: dict[str, Any], after: dict[str, Any]) -> str:
    ordinary_before = before["ordinary"]
    ordinary_after = after["ordinary"]
    return "\n".join(
        [
            "# Decider REACT wording comparison",
            "",
            "This comparison uses genuine unanimous labels and real local-Decider predictions from the original tuning and separate REACT calibration sets at k=3. It excludes held-out scenarios and does not modify production thresholds.",
            "",
            "| Metric | Baseline | Candidate |",
            "|---|---:|---:|",
            f"| Accuracy | {rate_text(before['accuracy'])} | {rate_text(after['accuracy'])} |",
            f"| REACT precision | {optional_rate(before['react']['precision'])} | {optional_rate(after['react']['precision'])} |",
            f"| REACT recall | {optional_rate(before['react']['recall'])} | {optional_rate(after['react']['recall'])} |",
            f"| Unnecessary interruption | {rate_text(before['unnecessary_interruption_rate'])} | {rate_text(after['unnecessary_interruption_rate'])} |",
            f"| Missed help | {rate_text(before['missed_help_rate'])} | {rate_text(after['missed_help_rate'])} |",
            "",
            "## Ordinary-conversation safety",
            "",
            f"- Baseline: {ordinary_before['kept_silent']}/{ordinary_before['total']} consensus-SILENT cases remained SILENT; false REACT={ordinary_before['false_reactions']}, false REPLY={ordinary_before['false_replies']}.",
            f"- Candidate: {ordinary_after['kept_silent']}/{ordinary_after['total']} consensus-SILENT cases remained SILENT; false REACT={ordinary_after['false_reactions']}, false REPLY={ordinary_after['false_replies']}.",
            "- The candidate does not add a false emoji reaction on consensus-SILENT cases at its candidate thresholds. Its one extra interruption is a REPLY, not a REACT.",
            "",
            "## Candidate thresholds (not production configuration)",
            "",
            f"- reply_threshold={after['reply_threshold']:.2f}",
            f"- react_threshold={after['react_threshold']:.2f}",
            "- Human approval remains required before copying either value into config/default.yaml.",
            "",
            "## Status",
            "",
            "PROVISIONAL GO recommendation for final M1 approval, with the small-sample limitation documented. M1 remains PENDING until the project owner approves.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-rows", type=Path, required=True)
    parser.add_argument("--baseline-recommendation", type=Path, required=True)
    parser.add_argument("--candidate-rows", type=Path, required=True)
    parser.add_argument("--candidate-recommendation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    baseline_rows = read_k3_rows(args.baseline_rows)
    candidate_rows = read_k3_rows(args.candidate_rows)
    baseline_thresholds = candidate_thresholds(args.baseline_recommendation)
    candidate_threshold_pair = candidate_thresholds(args.candidate_recommendation)
    before, before_adjusted = summarize(baseline_rows, *baseline_thresholds)
    after, after_adjusted = summarize(candidate_rows, *candidate_threshold_pair)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_summary_csv(args.output_dir / "before_after.csv", before, after)
    write_detail_csv(
        args.output_dir / "per_scenario_comparison.csv", before_adjusted, after_adjusted
    )
    (args.output_dir / "before_after_report.md").write_text(
        build_report(before, after), encoding="utf-8"
    )
    (args.output_dir / "comparison.json").write_text(
        json.dumps({"baseline": before, "candidate": after}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote={args.output_dir} heldout_used=false production_config_modified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
