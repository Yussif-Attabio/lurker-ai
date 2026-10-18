#!/usr/bin/env python3
"""Compare baseline and candidate wording on identical single-rater development rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results" / "m5_recovery" / "single_rater"


def rate(metric: dict[str, Any]) -> float | None:
    value = metric.get("rate")
    return None if value is None else float(value)


def load_run(path: Path, *, candidate: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if RESULTS_ROOT.resolve() not in path.resolve().parents:
        raise ValueError("comparison accepts single-rater development results only")
    summary = json.loads((path / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
    if summary.get("label_basis") != "single_evaluator":
        raise ValueError("run does not use the single-evaluator label basis")
    if summary.get("human_consensus") is not False:
        raise ValueError("run incorrectly claims human consensus")
    if manifest.get("mock") is not False or manifest.get("aws_or_bedrock_calls") != 0:
        raise ValueError("run is not valid real-local evidence")
    if manifest.get("actual_predictions") != manifest.get("expected_predictions"):
        raise ValueError("run has incomplete predictions")
    if manifest.get("error_count") != 0:
        raise ValueError("run contains model errors")
    if manifest.get("production_configuration_changed") is not False:
        raise ValueError("run changed production configuration")
    heldout_key = "original_heldout_opened_by_runner" if candidate else "original_heldout_opened"
    reserve_key = (
        "single_rater_reserve_opened_by_runner" if candidate else "single_rater_reserve_opened"
    )
    if manifest.get(heldout_key) is not False or manifest.get(reserve_key) is not False:
        raise ValueError("run reports prohibited dataset access")
    return summary, manifest


def load_cases(path: Path, context_k: int) -> dict[str, dict[str, str]]:
    with (path / "per_case.csv").open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if int(row["context_k"]) == context_k]
    if len(rows) != 90 or len({row["id"] for row in rows}) != 90:
        raise ValueError("comparison requires exactly 90 unique cases per run")
    return {row["id"]: row for row in rows}


def compact_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "accuracy": metrics["accuracy"],
        "unnecessary_interruption_rate": metrics["unnecessary_interruption_rate"],
        "missed_help_rate": metrics["missed_help_rate"],
        "react_precision": metrics["react_precision"],
        "react_recall": metrics["react_recall"],
        "latency_ms": metrics["latency_ms"],
        "prediction_counts": metrics["prediction_counts"],
        "error_count": metrics["error_count"],
    }


def compare(baseline_path: Path, candidate_path: Path, context_k: int = 3) -> dict[str, Any]:
    baseline_summary, baseline_manifest = load_run(baseline_path, candidate=False)
    candidate_summary, candidate_manifest = load_run(candidate_path, candidate=True)
    if baseline_manifest["scenario_sha256"] != candidate_manifest["scenario_sha256"]:
        raise ValueError("baseline and candidate use different scenario files")
    if baseline_summary["thresholds"] != candidate_summary["thresholds"]:
        raise ValueError("baseline and candidate use different thresholds")
    if baseline_summary["model_id"] != candidate_summary["model_id"]:
        raise ValueError("baseline and candidate use different model IDs")
    baseline_rows = load_cases(baseline_path, context_k)
    candidate_rows = load_cases(candidate_path, context_k)
    if set(baseline_rows) != set(candidate_rows):
        raise ValueError("baseline and candidate case IDs differ")
    if any(
        baseline_rows[item]["reference_label"] != candidate_rows[item]["reference_label"]
        for item in baseline_rows
    ):
        raise ValueError("baseline and candidate reference labels differ")

    transitions = Counter(
        (
            baseline_rows[item]["reference_label"],
            baseline_rows[item]["final_action"],
            candidate_rows[item]["final_action"],
        )
        for item in sorted(baseline_rows)
    )
    baseline_metrics = baseline_summary["context_metrics"][str(context_k)]
    candidate_metrics = candidate_summary["context_metrics"][str(context_k)]
    rate_names = (
        "accuracy",
        "unnecessary_interruption_rate",
        "missed_help_rate",
        "react_precision",
        "react_recall",
    )
    deltas = {
        name: rate(candidate_metrics[name]) - rate(baseline_metrics[name])
        for name in rate_names
        if rate(candidate_metrics[name]) is not None and rate(baseline_metrics[name]) is not None
    }

    def ids_where(predicate: Any) -> list[str]:
        return [
            item
            for item in sorted(baseline_rows)
            if predicate(baseline_rows[item], candidate_rows[item])
        ]

    regression = {
        "new_unnecessary_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] != "REACT"
            and cand["final_action"] == "REACT"
        ),
        "repaired_unnecessary_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] == "REACT"
            and cand["final_action"] != "REACT"
        ),
        "new_missed_requests": ids_where(
            lambda base, cand: base["reference_label"] == "REPLY"
            and base["final_action"] == "REPLY"
            and cand["final_action"] != "REPLY"
        ),
        "repaired_missed_requests": ids_where(
            lambda base, cand: base["reference_label"] == "REPLY"
            and base["final_action"] != "REPLY"
            and cand["final_action"] == "REPLY"
        ),
        "new_correct_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "REACT"
            and base["final_action"] != "REACT"
            and cand["final_action"] == "REACT"
        ),
        "lost_correct_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "REACT"
            and base["final_action"] == "REACT"
            and cand["final_action"] != "REACT"
        ),
    }
    review_gate = {
        "accuracy_not_worse": deltas["accuracy"] >= 0,
        "interruption_not_worse": deltas["unnecessary_interruption_rate"] <= 0,
        "missed_help_not_worse": deltas["missed_help_rate"] <= 0,
        "react_precision_at_least_70pct": rate(candidate_metrics["react_precision"]) >= 0.70,
        "react_recall_at_least_70pct": rate(candidate_metrics["react_recall"]) >= 0.70,
        "zero_errors": candidate_metrics["error_count"] == 0,
    }
    return {
        "artifact_version": "lurker-m5-recovery-single-rater-wording-comparison-v1",
        "status": "EXPLORATORY_ONLY",
        "context_k": context_k,
        "scenario_sha256": baseline_manifest["scenario_sha256"],
        "thresholds": baseline_summary["thresholds"],
        "model_id": baseline_summary["model_id"],
        "model_revision": candidate_manifest["model_revision"],
        "label_basis": "single_evaluator",
        "human_consensus": False,
        "baseline": compact_metrics(baseline_metrics),
        "candidate": compact_metrics(candidate_metrics),
        "rate_deltas_candidate_minus_baseline": deltas,
        "decision_transitions": {
            f"{label}:{before}->{after}": count
            for (label, before, after), count in sorted(transitions.items())
        },
        "regression_checks": regression,
        "owner_review_gate": review_gate,
        "all_review_gates_met": all(review_gate.values()),
        "production_candidate_applied": False,
        "production_thresholds_changed": False,
        "policy_changed": False,
        "reserve_opened": False,
        "heldout_opened": False,
        "aws_or_bedrock_calls": 0,
    }


def percentage(metric: dict[str, Any]) -> str:
    value = rate(metric)
    return "N/A" if value is None else f"{value * 100:.1f}%"


def write_report(path: Path, result: dict[str, Any]) -> None:
    baseline = result["baseline"]
    candidate = result["candidate"]
    lines = [
        "# Single-evaluator wording comparison",
        "",
        "> Development-only evidence. Not human consensus, held-out evidence, or production approval.",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
    ]
    names = (
        ("Accuracy", "accuracy"),
        ("Unnecessary interruption", "unnecessary_interruption_rate"),
        ("Missed help", "missed_help_rate"),
        ("REACT precision", "react_precision"),
        ("REACT recall", "react_recall"),
    )
    for label, key in names:
        delta = result["rate_deltas_candidate_minus_baseline"][key]
        lines.append(
            f"| {label} | {percentage(baseline[key])} | {percentage(candidate[key])} | {delta * 100:+.1f} pp |"
        )
    lines.extend(
        [
            f"| Latency p50 | {baseline['latency_ms']['p50']:.2f} ms | {candidate['latency_ms']['p50']:.2f} ms | {candidate['latency_ms']['p50'] - baseline['latency_ms']['p50']:+.2f} ms |",
            f"| Latency p95 | {baseline['latency_ms']['p95']:.2f} ms | {candidate['latency_ms']['p95']:.2f} ms | {candidate['latency_ms']['p95'] - baseline['latency_ms']['p95']:+.2f} ms |",
            "",
            "## Regression checks",
            "",
        ]
    )
    for key, ids in result["regression_checks"].items():
        lines.append(f"- {key.replace('_', ' ')}: {len(ids)}")
    lines.extend(
        [
            "",
            f"All development review gates met: **{str(result['all_review_gates_met']).upper()}**",
            "",
            "Production wording, thresholds, and policy remain unchanged.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--context-k", type=int, default=3, choices=(0, 3, 5))
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate, args.context_k)
    output_json = args.candidate / f"comparison_k{args.context_k}.json"
    output_md = args.candidate / f"comparison_k{args.context_k}.md"
    if output_json.exists() or output_md.exists():
        raise FileExistsError("refusing to overwrite wording comparison evidence")
    output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_report(output_md, result)
    print(
        f"wrote={output_json} all_review_gates_met={str(result['all_review_gates_met']).lower()} "
        "heldout_opened=false reserve_opened=false aws_or_bedrock_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
