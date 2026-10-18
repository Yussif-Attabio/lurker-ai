#!/usr/bin/env python3
"""Evaluate concise wording v2 on only the fixed combined-reference development set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import resource
import time
from collections import Counter
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

from decision_pattern.lurker_gate import OPTIONS, QUESTION, apply_policy
from eval.metrics_def import compute_metrics
from eval.reporting import base_summary, build_report, create_run_directory, write_summary
from scripts.run_eval import validate_evaluation_rows
from src.lurker.context import build_state
from src.lurker.schemas import Action, ScenarioMessage

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_PATH = (
    ROOT / "eval" / "recovery" / "combined_reference" / "development" / "development.jsonl"
)
PROVENANCE_MANIFEST = (
    ROOT / "eval" / "recovery" / "combined_reference" / "provenance_manifest.json"
)
CANDIDATE_PATH = (
    ROOT / "config" / "wording_candidates" / "m5_recovery_concise_boundaries_v2.yaml"
)
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"
FROZEN_CONFIG = ROOT / "config" / "m5_frozen_evaluation.yaml"
DEFAULT_RESULTS = (
    ROOT / "results" / "m5_recovery" / "combined_reference" / "wording_candidates"
)
BASELINE_THRESHOLDS = {"reply_threshold": 0.20, "react_threshold": 0.04}
PER_CASE_FIELDS = [
    "id", "split", "category", "context_k", "reference_label", "label_basis",
    "contributor_count", "independent_decisions_available", "group_consensus_verified",
    "raw_choice", "confidence", "final_action", "downgraded", "reason",
    "decider_latency_ms", "error", "scores_json",
]


class CombinedReferenceScenario(BaseModel):
    id: str
    split: Literal["tuning"]
    category: str
    family_id: str
    history: list[ScenarioMessage]
    message: ScenarioMessage
    reference_label: Action
    label_basis: Literal["combined_three_contributor_reference"]
    contributor_count: Literal[3]
    independent_decisions_available: Literal[False]
    group_consensus_verified: Literal[False]
    aggregation_method: Literal["combined_document_process_not_reconstructable"]
    notes: str = ""

    @property
    def consensus(self) -> Action:
        """Compatibility view; this is a reference label, not verified consensus."""
        return self.reference_label


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_development(path: Path = DEVELOPMENT_PATH) -> list[CombinedReferenceScenario]:
    if path.resolve() != DEVELOPMENT_PATH.resolve():
        raise ValueError("runner accepts only the fixed combined-reference development file")
    manifest = json.loads(PROVENANCE_MANIFEST.read_text(encoding="utf-8"))
    required_false = (
        "independent_decisions_available", "group_consensus_verified",
        "inter_rater_agreement_calculable", "reserve_opened", "original_m5_heldout_opened",
    )
    if any(manifest.get(key) is not False for key in required_false):
        raise ValueError("combined-reference provenance is not safely constrained")
    if manifest.get("contributor_count") != 3:
        raise ValueError("combined-reference contributor count must be three")
    scenarios = [
        CombinedReferenceScenario.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(scenarios) != 90 or len({item.id for item in scenarios}) != 90:
        raise ValueError("combined-reference development must contain 90 unique cases")
    if Counter(item.reference_label for item in scenarios) != Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    ):
        raise ValueError("combined-reference development must contain 30 cases per class")
    if len({item.family_id for item in scenarios}) != 18:
        raise ValueError("combined-reference development must contain 18 complete families")
    return scenarios


def load_candidate() -> dict[str, Any]:
    candidate = yaml.safe_load(CANDIDATE_PATH.read_text(encoding="utf-8"))
    frozen = yaml.safe_load(FROZEN_CONFIG.read_text(encoding="utf-8"))["configuration"]
    baseline = candidate["baseline"]
    contract = candidate["decision_contract"]
    evaluation = candidate["evaluation"]
    model = candidate["model"]
    if candidate["status"] != "development_only_not_production":
        raise ValueError("candidate is not development-only")
    if text_sha256(QUESTION) != baseline["question_sha256"]:
        raise ValueError("original production wording changed")
    if contract["options"] != OPTIONS or contract["policy_changed"] or contract["context_changed"]:
        raise ValueError("candidate may change decision wording only")
    if model["architecture_changed"]:
        raise ValueError("candidate may not change model architecture")
    if model["id"] != frozen["decider_model_id"] or model["revision"] != frozen["decider_model_revision"]:
        raise ValueError("candidate model differs from the frozen model")
    if evaluation["dataset"] != str(DEVELOPMENT_PATH.relative_to(ROOT)):
        raise ValueError("candidate points outside fixed development data")
    if evaluation["expected_cases"] != 90 or evaluation["context_values"] != [3]:
        raise ValueError("candidate evaluation must be exactly 90 k=3 predictions")
    if evaluation["contributor_count"] != 3:
        raise ValueError("candidate provenance contributor count is invalid")
    if evaluation["independent_decisions_available"] or evaluation["group_consensus_verified"]:
        raise ValueError("candidate overstates human-label provenance")
    if evaluation["reserve_allowed"] or evaluation["heldout_allowed"] or evaluation["aws_or_bedrock_allowed"]:
        raise ValueError("candidate permits prohibited resources")
    thresholds = {
        "reply_threshold": float(baseline["reply_threshold"]),
        "react_threshold": float(baseline["react_threshold"]),
    }
    if thresholds != BASELINE_THRESHOLDS:
        raise ValueError("candidate thresholds differ from baseline")
    if len(contract["question"]) >= len(QUESTION):
        raise ValueError("candidate is not a concise wording revision")
    return candidate


def evaluate(
    adapter: Any,
    scenarios: list[CombinedReferenceScenario],
    thresholds: dict[str, float],
    question: str,
) -> list[dict[str, Any]]:
    if bool(getattr(adapter, "mock", False)):
        raise ValueError("runner refuses MockDecider")
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        state = build_state(
            [message.model_dump() for message in scenario.history],
            scenario.message.model_dump(),
            3,
        )
        result = adapter.decide(state, question, OPTIONS)
        final_action, downgraded, reason = apply_policy(result, thresholds)
        rows.append(
            {
                "id": scenario.id,
                "split": scenario.split,
                "category": scenario.category,
                "context_k": 3,
                "consensus": scenario.reference_label,
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


def write_per_case(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PER_CASE_FIELDS)
        writer.writeheader()
        for row in rows:
            output = dict(row)
            output["reference_label"] = output.pop("consensus")
            output.update(
                {
                    "label_basis": "combined_three_contributor_reference",
                    "contributor_count": 3,
                    "independent_decisions_available": False,
                    "group_consensus_verified": False,
                }
            )
            writer.writerow(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    candidate = load_candidate()
    scenarios = load_development()
    config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    criteria_payload = yaml.safe_load(DEFAULT_CRITERIA.read_text(encoding="utf-8"))
    thresholds = {
        "reply_threshold": float(config["reply_threshold"]),
        "react_threshold": float(config["react_threshold"]),
    }
    if thresholds != BASELINE_THRESHOLDS:
        raise ValueError("production thresholds no longer match preserved baseline")
    if config["decider_model_id"] != candidate["model"]["id"]:
        raise ValueError("configured model ID differs from frozen candidate contract")
    criteria = {
        "accuracy_min": float(criteria_payload["accuracy_min"]),
        "unnecessary_interruption_rate_max": float(criteria_payload["unnecessary_interruption_rate_max"]),
        "missed_help_rate_max": float(criteria_payload["missed_help_rate_max"]),
    }

    from src.lurker.decider_adapter import DeciderAdapter

    initialized = time.perf_counter()
    adapter = DeciderAdapter(
        config["decider_model_id"], config["decider_device"], int(config["decider_timeout_ms"])
    )
    initialization_ms = (time.perf_counter() - initialized) * 1000
    question = candidate["decision_contract"]["question"]
    rows = evaluate(adapter, scenarios, thresholds, question)
    validate_evaluation_rows(rows, scenarios, [3])
    metrics = compute_metrics(rows)
    summary = base_summary(
        split="tuning",
        model_id=config["decider_model_id"],
        device=config["decider_device"],
        policy_mode="configured_thresholds",
        thresholds=thresholds,
        criteria=criteria,
        context_metrics={"3": metrics},
    )
    candidate_id = candidate["candidate_id"]
    summary.update(
        {
            "artifact_version": "lurker-m5-recovery-combined-reference-wording-eval-v1",
            "status": "EXPLORATORY_ONLY",
            "variant": candidate_id,
            "wording_sha256": text_sha256(question),
            "label_basis": "combined_three_contributor_reference",
            "contributor_count": 3,
            "independent_decisions_available": False,
            "group_consensus_verified": False,
            "human_consensus": False,
            "final_m5_evidence": False,
            "production_candidate_applied": False,
            "react_criteria": {"precision_min": 0.70, "recall_min": 0.70},
        }
    )
    run_dir = create_run_directory(args.output_root / candidate_id)
    write_per_case(run_dir / "per_case.csv", rows)
    write_summary(run_dir / "results.json", summary)
    header = (
        f"# Combined-reference wording candidate: {candidate_id}\n\n"
        "> Development-only. Three people contributed to one final-label document, "
        "but independence, consensus, and inter-rater agreement cannot be verified. "
        "This is not held-out evidence or production approval.\n\n"
    )
    body = build_report(summary).replace("# Lurker AI evaluation report\n\n", "", 1)
    (run_dir / "report.md").write_text(header + body, encoding="utf-8")
    (run_dir / "candidate_snapshot.yaml").write_text(
        yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "artifact_version": "lurker-m5-recovery-combined-reference-wording-run-v1",
        "status": "EXPLORATORY_ONLY",
        "variant": candidate_id,
        "development_only": True,
        "label_basis": "combined_three_contributor_reference",
        "contributor_count": 3,
        "independent_decisions_available": False,
        "group_consensus_verified": False,
        "inter_rater_agreement_calculable": False,
        "scenario_path": str(DEVELOPMENT_PATH.relative_to(ROOT)),
        "scenario_sha256": sha256(DEVELOPMENT_PATH),
        "provenance_manifest_sha256": sha256(PROVENANCE_MANIFEST),
        "candidate_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        "candidate_sha256": sha256(CANDIDATE_PATH),
        "baseline_question_sha256": text_sha256(QUESTION),
        "candidate_question_sha256": text_sha256(question),
        "model_id": config["decider_model_id"],
        "model_revision": candidate["model"]["revision"],
        "model_architecture_changed": False,
        "policy_changed": False,
        "thresholds": thresholds,
        "scenario_count": 90,
        "expected_predictions": 90,
        "actual_predictions": len(rows),
        "context_values": [3],
        "mock": False,
        "aws_or_bedrock_calls": 0,
        "original_m5_heldout_opened_by_runner": False,
        "reserve_opened_by_runner": False,
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
        "heldout_opened=false reserve_opened=false aws_or_bedrock_calls=0"
    )
    return 3 if manifest["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
