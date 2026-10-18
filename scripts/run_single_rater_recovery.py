#!/usr/bin/env python3
"""Run the real local Decider on the single-rater recovery development set."""

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
from typing import Literal

import yaml
from pydantic import BaseModel

from eval.metrics_def import compute_metrics
from eval.reporting import base_summary, build_report, create_run_directory, write_summary
from scripts.run_eval import evaluate_scenarios, validate_evaluation_rows
from src.lurker.schemas import Action, ScenarioMessage

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_PATH = (
    ROOT / "eval" / "recovery" / "single_rater" / "development" / "development.jsonl"
)
SPLIT_MANIFEST = ROOT / "eval" / "recovery" / "single_rater" / "split_manifest.json"
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"
DEFAULT_RESULTS = ROOT / "results" / "m5_recovery" / "single_rater" / "development"
BASELINE_THRESHOLDS = {"reply_threshold": 0.20, "react_threshold": 0.04}

PER_CASE_FIELDS = [
    "id",
    "split",
    "category",
    "context_k",
    "reference_label",
    "label_basis",
    "evaluator_id",
    "raw_choice",
    "confidence",
    "final_action",
    "downgraded",
    "reason",
    "decider_latency_ms",
    "error",
    "scores_json",
]


class SingleRaterScenario(BaseModel):
    """A validated development scenario with one human reference label."""

    id: str
    split: Literal["tuning"]
    category: str
    family_id: str
    history: list[ScenarioMessage]
    message: ScenarioMessage
    reference_label: Action
    label_basis: Literal["single_evaluator"]
    evaluator_id: str
    notes: str = ""

    @property
    def consensus(self) -> Action:
        """Compatibility view for shared evaluation logic; not human consensus."""
        return self.reference_label


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_single_rater_development(
    path: Path = DEVELOPMENT_PATH,
) -> list[SingleRaterScenario]:
    if path.resolve() != DEVELOPMENT_PATH.resolve():
        raise ValueError("single-rater evaluation accepts only the fixed development file")
    manifest = json.loads(SPLIT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("human_consensus") is not False:
        raise ValueError("single-rater manifest must explicitly deny human consensus")
    if manifest.get("heldout_opened") is not False:
        raise ValueError("single-rater manifest indicates held-out access")
    scenarios = [
        SingleRaterScenario.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(scenarios) != 90:
        raise ValueError("single-rater development file must contain exactly 90 rows")
    counts = Counter(scenario.reference_label for scenario in scenarios)
    if counts != Counter({"SILENT": 30, "REACT": 30, "REPLY": 30}):
        raise ValueError("single-rater development must contain 30 rows per class")
    if len({scenario.family_id for scenario in scenarios}) != 18:
        raise ValueError("single-rater development must contain 18 complete families")
    return scenarios


def write_per_case(path: Path, rows: list[dict[str, object]], evaluator_id: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PER_CASE_FIELDS)
        writer.writeheader()
        for row in rows:
            output = dict(row)
            output["reference_label"] = output.pop("consensus")
            output["label_basis"] = "single_evaluator"
            output["evaluator_id"] = evaluator_id
            writer.writerow(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, nargs="+", default=[0, 3, 5], choices=(0, 3, 5))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()

    scenarios = load_single_rater_development()
    evaluator_ids = {scenario.evaluator_id for scenario in scenarios}
    if len(evaluator_ids) != 1:
        raise ValueError("single-rater development contains multiple evaluator ids")
    evaluator_id = evaluator_ids.pop()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    criteria_payload = yaml.safe_load(args.criteria.read_text(encoding="utf-8"))
    thresholds = {
        "reply_threshold": float(config["reply_threshold"]),
        "react_threshold": float(config["react_threshold"]),
    }
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
    rows = evaluate_scenarios(adapter, scenarios, context_values, thresholds)
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
    summary.update(
        {
            "artifact_version": "lurker-m5-recovery-single-rater-eval-v1",
            "status": "EXPLORATORY_ONLY",
            "label_basis": "single_evaluator",
            "evaluator_id": evaluator_id,
            "human_consensus": False,
            "final_m5_evidence": False,
            "react_criteria": {"precision_min": 0.70, "recall_min": 0.70},
        }
    )
    run_dir = create_run_directory(args.output_root)
    write_per_case(run_dir / "per_case.csv", rows, evaluator_id)
    write_summary(run_dir / "results.json", summary)
    report_header = (
        "# Single-evaluator exploratory recovery evaluation\n\n"
        "> These metrics compare model predictions with one evaluator's labels. "
        "They are not human consensus, held-out evidence, or final M5 acceptance evidence.\n\n"
    )
    report_body = build_report(summary).replace("# Lurker AI evaluation report\n\n", "", 1)
    (run_dir / "report.md").write_text(report_header + report_body, encoding="utf-8")
    (run_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "artifact_version": "lurker-m5-recovery-single-rater-run-v1",
        "status": "EXPLORATORY_ONLY",
        "development_only": True,
        "label_basis": "single_evaluator",
        "evaluator_id": evaluator_id,
        "human_consensus": False,
        "scenario_path": str(DEVELOPMENT_PATH.relative_to(ROOT)),
        "scenario_sha256": sha256(DEVELOPMENT_PATH),
        "split_manifest_sha256": sha256(SPLIT_MANIFEST),
        "scenario_count": len(scenarios),
        "expected_predictions": len(scenarios) * len(context_values),
        "actual_predictions": len(rows),
        "context_values": context_values,
        "mock": False,
        "aws_or_bedrock_calls": 0,
        "original_heldout_opened": False,
        "single_rater_reserve_opened": False,
        "new_heldout_created": False,
        "production_configuration_changed": False,
        "config_sha256": sha256(args.config),
        "starting_baseline_thresholds": BASELINE_THRESHOLDS,
        "uses_starting_baseline_thresholds": thresholds == BASELINE_THRESHOLDS,
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
        "status=EXPLORATORY_ONLY human_consensus=false heldout_opened=false "
        "aws_or_bedrock_calls=0 production_config_changed=false"
    )
    return 3 if manifest["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
