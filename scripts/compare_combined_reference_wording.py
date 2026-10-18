#!/usr/bin/env python3
"""Compare the original k=3 baseline with concise wording v2 on the same 90 labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = ROOT / "results" / "m5_recovery" / "single_rater" / "development"
CANDIDATE_ROOT = ROOT / "results" / "m5_recovery" / "combined_reference" / "wording_candidates"


def rate(metric: dict[str, Any]) -> float | None:
    value = metric.get("rate")
    return None if value is None else float(value)


def load_cases(path: Path, context_k: int = 3) -> dict[str, dict[str, str]]:
    with (path / "per_case.csv").open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if int(row["context_k"]) == context_k]
    if len(rows) != 90 or len({row["id"] for row in rows}) != 90:
        raise ValueError("comparison requires exactly 90 unique k=3 cases")
    return {row["id"]: row for row in rows}


def compact(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        key: metrics[key]
        for key in (
            "accuracy", "unnecessary_interruption_rate", "missed_help_rate",
            "react_precision", "react_recall", "latency_ms", "prediction_counts", "error_count",
        )
    }


def compare(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    if BASELINE_ROOT.resolve() not in baseline_path.resolve().parents:
        raise ValueError("baseline must be preserved recovery development evidence")
    if CANDIDATE_ROOT.resolve() not in candidate_path.resolve().parents:
        raise ValueError("candidate must be combined-reference wording evidence")
    baseline_summary = json.loads((baseline_path / "results.json").read_text(encoding="utf-8"))
    baseline_manifest = json.loads((baseline_path / "run_manifest.json").read_text(encoding="utf-8"))
    candidate_summary = json.loads((candidate_path / "results.json").read_text(encoding="utf-8"))
    candidate_manifest = json.loads((candidate_path / "run_manifest.json").read_text(encoding="utf-8"))
    if baseline_manifest.get("actual_predictions") != baseline_manifest.get("expected_predictions"):
        raise ValueError("baseline predictions are incomplete")
    if candidate_manifest.get("actual_predictions") != 90 or candidate_manifest.get("error_count") != 0:
        raise ValueError("candidate predictions are incomplete or contain errors")
    if candidate_manifest.get("label_basis") != "combined_three_contributor_reference":
        raise ValueError("candidate provenance is incorrect")
    if candidate_manifest.get("independent_decisions_available") is not False:
        raise ValueError("candidate incorrectly claims independent labels")
    if candidate_manifest.get("group_consensus_verified") is not False:
        raise ValueError("candidate incorrectly claims verified consensus")
    if candidate_manifest.get("mock") is not False or candidate_manifest.get("aws_or_bedrock_calls") != 0:
        raise ValueError("candidate is not real-local evidence")
    if candidate_manifest.get("reserve_opened_by_runner") is not False:
        raise ValueError("candidate reports reserve access")
    if candidate_manifest.get("original_m5_heldout_opened_by_runner") is not False:
        raise ValueError("candidate reports original held-out access")
    if candidate_manifest.get("production_configuration_changed") is not False:
        raise ValueError("candidate changed production configuration")
    if baseline_summary["thresholds"] != candidate_summary["thresholds"]:
        raise ValueError("thresholds differ")
    if baseline_summary["model_id"] != candidate_summary["model_id"]:
        raise ValueError("model IDs differ")

    baseline_rows = load_cases(baseline_path)
    candidate_rows = load_cases(candidate_path)
    if set(baseline_rows) != set(candidate_rows):
        raise ValueError("case IDs differ")
    if any(
        baseline_rows[item]["reference_label"] != candidate_rows[item]["reference_label"]
        for item in baseline_rows
    ):
        raise ValueError("reference labels differ")

    baseline_metrics = baseline_summary["context_metrics"]["3"]
    candidate_metrics = candidate_summary["context_metrics"]["3"]
    metric_names = (
        "accuracy", "unnecessary_interruption_rate", "missed_help_rate",
        "react_precision", "react_recall",
    )
    deltas = {
        name: (
            rate(candidate_metrics[name]) - rate(baseline_metrics[name])
            if rate(candidate_metrics[name]) is not None
            and rate(baseline_metrics[name]) is not None
            else None
        )
        for name in metric_names
    }

    def ids_where(predicate: Any) -> list[str]:
        return [
            item for item in sorted(baseline_rows)
            if predicate(baseline_rows[item], candidate_rows[item])
        ]

    regressions = {
        "new_unnecessary_interruptions": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] == "SILENT" and cand["final_action"] != "SILENT"
        ),
        "repaired_unnecessary_interruptions": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] != "SILENT" and cand["final_action"] == "SILENT"
        ),
        "new_unnecessary_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] != "REACT" and cand["final_action"] == "REACT"
        ),
        "repaired_unnecessary_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "SILENT"
            and base["final_action"] == "REACT" and cand["final_action"] != "REACT"
        ),
        "new_missed_requests": ids_where(
            lambda base, cand: base["reference_label"] == "REPLY"
            and base["final_action"] == "REPLY" and cand["final_action"] != "REPLY"
        ),
        "repaired_missed_requests": ids_where(
            lambda base, cand: base["reference_label"] == "REPLY"
            and base["final_action"] != "REPLY" and cand["final_action"] == "REPLY"
        ),
        "new_correct_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "REACT"
            and base["final_action"] != "REACT" and cand["final_action"] == "REACT"
        ),
        "lost_correct_reacts": ids_where(
            lambda base, cand: base["reference_label"] == "REACT"
            and base["final_action"] == "REACT" and cand["final_action"] != "REACT"
        ),
    }
    transitions = Counter(
        (
            baseline_rows[item]["reference_label"],
            baseline_rows[item]["final_action"],
            candidate_rows[item]["final_action"],
        )
        for item in sorted(baseline_rows)
    )
    gates = {
        "accuracy_not_worse": deltas["accuracy"] >= 0,
        "interruption_improved": deltas["unnecessary_interruption_rate"] < 0,
        "missed_help_not_worse": deltas["missed_help_rate"] <= 0,
        "react_recall_improved": deltas["react_recall"] > 0,
        "react_precision_at_least_70pct": (
            rate(candidate_metrics["react_precision"]) is not None
            and rate(candidate_metrics["react_precision"]) >= 0.70
        ),
        "zero_new_unnecessary_reactions": not regressions["new_unnecessary_reacts"],
        "zero_new_missed_requests": not regressions["new_missed_requests"],
        "zero_errors": candidate_metrics["error_count"] == 0,
    }
    return {
        "artifact_version": "lurker-m5-recovery-combined-reference-comparison-v1",
        "status": "EXPLORATORY_ONLY",
        "context_k": 3,
        "label_basis": "combined_three_contributor_reference",
        "contributor_count": 3,
        "independent_decisions_available": False,
        "group_consensus_verified": False,
        "inter_rater_agreement_calculable": False,
        "thresholds": baseline_summary["thresholds"],
        "model_id": baseline_summary["model_id"],
        "model_revision": candidate_manifest["model_revision"],
        "baseline": compact(baseline_metrics),
        "candidate": compact(candidate_metrics),
        "rate_deltas_candidate_minus_baseline": deltas,
        "decision_transitions": {
            f"{label}:{before}->{after}": count
            for (label, before, after), count in sorted(transitions.items())
        },
        "regression_checks": regressions,
        "review_gate": gates,
        "all_review_gates_met": all(gates.values()),
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
        "# Combined three-contributor reference: wording comparison",
        "",
        "> Development-only. The three contributors' individual decisions were not retained, so independence, consensus, and inter-rater agreement cannot be verified.",
        "",
        "| Metric | Original wording | Concise v2 | Delta |",
        "|---|---:|---:|---:|",
    ]
    for label, key in (
        ("Accuracy", "accuracy"),
        ("Unnecessary interruption", "unnecessary_interruption_rate"),
        ("Missed help", "missed_help_rate"),
        ("REACT precision", "react_precision"),
        ("REACT recall", "react_recall"),
    ):
        delta = result["rate_deltas_candidate_minus_baseline"][key]
        rendered_delta = "N/A" if delta is None else f"{delta * 100:+.1f} pp"
        lines.append(
            f"| {label} | {percentage(baseline[key])} | {percentage(candidate[key])} | {rendered_delta} |"
        )
    lines.extend(
        [
            f"| Latency p50 | {baseline['latency_ms']['p50']:.2f} ms | {candidate['latency_ms']['p50']:.2f} ms | {candidate['latency_ms']['p50'] - baseline['latency_ms']['p50']:+.2f} ms |",
            f"| Latency p95 | {baseline['latency_ms']['p95']:.2f} ms | {candidate['latency_ms']['p95']:.2f} ms | {candidate['latency_ms']['p95'] - baseline['latency_ms']['p95']:+.2f} ms |",
            "", "## Safety and regression checks", "",
        ]
    )
    for key, ids in result["regression_checks"].items():
        lines.append(f"- {key.replace('_', ' ')}: {len(ids)}")
    lines.extend(
        [
            "",
            f"All development review gates met: **{str(result['all_review_gates_met']).upper()}**",
            "",
            "Production wording, thresholds, model, and action policy remain unchanged.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate)
    output_json = args.candidate / "comparison_k3.json"
    output_md = args.candidate / "comparison_k3.md"
    if output_json.exists() or output_md.exists():
        raise FileExistsError("refusing to overwrite comparison evidence")
    output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_report(output_md, result)
    print(
        f"wrote={output_json} all_review_gates_met={str(result['all_review_gates_met']).lower()} "
        "heldout_opened=false reserve_opened=false aws_or_bedrock_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
