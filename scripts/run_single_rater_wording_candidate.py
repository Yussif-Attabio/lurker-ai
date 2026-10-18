#!/usr/bin/env python3
"""Evaluate one versioned wording candidate on the fixed 90-case development set."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import time
from pathlib import Path
from typing import Any

import yaml

from decision_pattern.lurker_gate import OPTIONS, QUESTION, apply_policy
from eval.metrics_def import compute_metrics
from eval.reporting import base_summary, build_report, create_run_directory, write_summary
from scripts.run_eval import validate_evaluation_rows
from scripts.run_single_rater_recovery import (
    BASELINE_THRESHOLDS,
    DEFAULT_CONFIG,
    DEFAULT_CRITERIA,
    DEVELOPMENT_PATH,
    ROOT,
    SPLIT_MANIFEST,
    load_single_rater_development,
    sha256,
    write_per_case,
)
from src.lurker.context import build_state

CANDIDATE_PATH = (
    ROOT / "config" / "wording_candidates" / "m5_recovery_social_value_v1.yaml"
)
FROZEN_CONFIG = ROOT / "config" / "m5_frozen_evaluation.yaml"
DEFAULT_RESULTS = ROOT / "results" / "m5_recovery" / "single_rater" / "wording_candidates"


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_candidate(path: Path = CANDIDATE_PATH) -> dict[str, Any]:
    if path.resolve() != CANDIDATE_PATH.resolve():
        raise ValueError("only the approved versioned wording candidate may be evaluated")
    candidate = yaml.safe_load(path.read_text(encoding="utf-8"))
    frozen = yaml.safe_load(FROZEN_CONFIG.read_text(encoding="utf-8"))
    baseline = candidate["baseline"]
    contract = candidate["decision_contract"]
    evaluation = candidate["evaluation"]
    model = candidate["model"]
    frozen_configuration = frozen["configuration"]

    if candidate["status"] != "development_only_not_production":
        raise ValueError("candidate is not marked development-only")
    if text_sha256(QUESTION) != baseline["question_sha256"]:
        raise ValueError("baseline decision wording changed after candidate creation")
    if contract["options"] != OPTIONS:
        raise ValueError("candidate options differ from the production options")
    if contract["policy_changed"] or contract["context_changed"]:
        raise ValueError("candidate may change wording only")
    if model["architecture_changed"]:
        raise ValueError("candidate may not change model architecture")
    if model["id"] != frozen_configuration["decider_model_id"]:
        raise ValueError("candidate model ID differs from the frozen model")
    if model["revision"] != frozen_configuration["decider_model_revision"]:
        raise ValueError("candidate model revision differs from the frozen revision")
    if evaluation["dataset"] != str(DEVELOPMENT_PATH.relative_to(ROOT)):
        raise ValueError("candidate points outside the fixed development dataset")
    if evaluation["expected_cases"] != 90 or evaluation["human_consensus"] is not False:
        raise ValueError("candidate has an invalid single-rater evaluation contract")
    if evaluation["reserve_allowed"] or evaluation["heldout_allowed"]:
        raise ValueError("candidate may not access reserve or held-out data")
    if evaluation["aws_or_bedrock_allowed"]:
        raise ValueError("candidate may not access AWS or Bedrock")
    if {
        "reply_threshold": float(baseline["reply_threshold"]),
        "react_threshold": float(baseline["react_threshold"]),
    } != BASELINE_THRESHOLDS:
        raise ValueError("candidate thresholds differ from the preserved baseline")
    return candidate


def evaluate_candidate_scenarios(
    adapter: Any,
    scenarios: list[Any],
    context_values: list[int],
    policy_config: dict[str, float],
    question: str,
) -> list[dict[str, Any]]:
    """Evaluate a development wording without modifying the frozen runner."""
    if bool(getattr(adapter, "mock", False)):
        raise ValueError("wording candidate runner refuses MockDecider")
    rows: list[dict[str, Any]] = []
    for context_k in context_values:
        for scenario in scenarios:
            state = build_state(
                [message.model_dump() for message in scenario.history],
                scenario.message.model_dump(),
                context_k,
            )
            result = adapter.decide(state, question, OPTIONS)
            final_action, downgraded, reason = apply_policy(result, policy_config)
            rows.append(
                {
                    "id": scenario.id,
                    "split": scenario.split,
                    "category": scenario.category,
                    "context_k": context_k,
                    "consensus": scenario.consensus,
                    "raw_choice": result.choice or "",
                    "confidence": result.confidence,
                    "final_action": final_action,
                    "downgraded": downgraded,
                    "reason": reason,
                    "decider_latency_ms": result.latency_ms,
                    "error": result.error or "",
                    "scores_json": json.dumps(result.scores or {}, sort_keys=True),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, nargs="+", default=[0, 3, 5], choices=(0, 3, 5))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()

    candidate = load_candidate()
    scenarios = load_single_rater_development()
    evaluator_ids = {scenario.evaluator_id for scenario in scenarios}
    if len(evaluator_ids) != 1:
        raise ValueError("single-rater development contains multiple evaluator ids")
    evaluator_id = evaluator_ids.pop()
    config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    criteria_payload = yaml.safe_load(DEFAULT_CRITERIA.read_text(encoding="utf-8"))
    thresholds = {
        "reply_threshold": float(config["reply_threshold"]),
        "react_threshold": float(config["react_threshold"]),
    }
    if thresholds != BASELINE_THRESHOLDS:
        raise ValueError("production thresholds no longer match the candidate baseline")
    if config["decider_model_id"] != candidate["model"]["id"]:
        raise ValueError("configured model ID differs from the candidate contract")
    criteria = {
        "accuracy_min": float(criteria_payload["accuracy_min"]),
        "unnecessary_interruption_rate_max": float(
            criteria_payload["unnecessary_interruption_rate_max"]
        ),
        "missed_help_rate_max": float(criteria_payload["missed_help_rate_max"]),
    }

    from src.lurker.decider_adapter import DeciderAdapter

    initialized = time.perf_counter()
    adapter = DeciderAdapter(
        config["decider_model_id"], config["decider_device"], int(config["decider_timeout_ms"])
    )
    initialization_ms = (time.perf_counter() - initialized) * 1000
    context_values = list(args.k)
    question = candidate["decision_contract"]["question"]
    rows = evaluate_candidate_scenarios(
        adapter,
        scenarios,
        context_values,
        thresholds,
        question,
    )
    validate_evaluation_rows(rows, scenarios, context_values)
    metrics = {
        str(context_k): compute_metrics(
            [row for row in rows if int(row["context_k"]) == context_k]
        )
        for context_k in context_values
    }
    summary = base_summary(
        split="tuning",
        model_id=config["decider_model_id"],
        device=config["decider_device"],
        policy_mode="configured_thresholds",
        thresholds=thresholds,
        criteria=criteria,
        context_metrics=metrics,
    )
    candidate_id = candidate["candidate_id"]
    summary.update(
        {
            "artifact_version": "lurker-m5-recovery-single-rater-wording-eval-v1",
            "status": "EXPLORATORY_ONLY",
            "variant": candidate_id,
            "wording_sha256": text_sha256(question),
            "label_basis": "single_evaluator",
            "evaluator_id": evaluator_id,
            "human_consensus": False,
            "final_m5_evidence": False,
            "production_candidate_applied": False,
            "react_criteria": {"precision_min": 0.70, "recall_min": 0.70},
        }
    )
    output_root = args.output_root / candidate_id
    run_dir = create_run_directory(output_root)
    write_per_case(run_dir / "per_case.csv", rows, evaluator_id)
    write_summary(run_dir / "results.json", summary)
    report_header = (
        f"# Single-evaluator wording candidate: {candidate_id}\n\n"
        "> Development-only comparison. This is not human consensus, held-out "
        "evidence, production configuration, or final M5 acceptance.\n\n"
    )
    report_body = build_report(summary).replace("# Lurker AI evaluation report\n\n", "", 1)
    (run_dir / "report.md").write_text(report_header + report_body, encoding="utf-8")
    (run_dir / "candidate_snapshot.yaml").write_text(
        yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "artifact_version": "lurker-m5-recovery-single-rater-wording-run-v1",
        "status": "EXPLORATORY_ONLY",
        "variant": candidate_id,
        "development_only": True,
        "label_basis": "single_evaluator",
        "human_consensus": False,
        "scenario_path": str(DEVELOPMENT_PATH.relative_to(ROOT)),
        "scenario_sha256": sha256(DEVELOPMENT_PATH),
        "split_manifest_sha256": sha256(SPLIT_MANIFEST),
        "candidate_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        "candidate_sha256": sha256(CANDIDATE_PATH),
        "baseline_question_sha256": text_sha256(QUESTION),
        "candidate_question_sha256": text_sha256(question),
        "model_id": config["decider_model_id"],
        "model_revision": candidate["model"]["revision"],
        "model_architecture_changed": False,
        "policy_changed": False,
        "thresholds": thresholds,
        "scenario_count": len(scenarios),
        "expected_predictions": len(scenarios) * len(context_values),
        "actual_predictions": len(rows),
        "context_values": context_values,
        "mock": False,
        "aws_or_bedrock_calls": 0,
        "original_heldout_opened_by_runner": False,
        "single_rater_reserve_opened_by_runner": False,
        "new_heldout_created": False,
        "production_configuration_changed": False,
        "error_count": sum(bool(row["error"]) for row in rows),
        "observability": {
            "adapter_initialization_ms": initialization_ms,
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"results={run_dir} development_cases=90 predictions={len(rows)}")
    print(
        "status=EXPLORATORY_ONLY production_candidate_applied=false "
        "heldout_opened_by_runner=false reserve_opened_by_runner=false "
        "aws_or_bedrock_calls=0"
    )
    return 3 if manifest["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
