#!/usr/bin/env python3
"""Run the real local Decider on the new recovery development split only."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import time
from collections import Counter
from pathlib import Path

import yaml

from eval.metrics_def import compute_metrics
from eval.reporting import base_summary, build_report, create_run_directory, write_summary
from scripts.run_eval import evaluate_scenarios, validate_evaluation_rows, write_per_case
from src.lurker.schemas import Scenario

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_PATH = ROOT / "eval" / "recovery" / "development" / "development.jsonl"
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"
DEFAULT_RESULTS = ROOT / "results" / "m5_recovery" / "development"
BASELINE_THRESHOLDS = {"reply_threshold": 0.20, "react_threshold": 0.04}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_recovery_development(path: Path = DEVELOPMENT_PATH) -> list[Scenario]:
    """Load only the one physically isolated recovery development file."""
    if path.resolve() != DEVELOPMENT_PATH.resolve():
        raise ValueError("recovery evaluation accepts only the fixed development file")
    scenarios = [
        Scenario.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(scenarios) != 90:
        raise ValueError("recovery development file must contain exactly 90 rows")
    if any(scenario.split != "tuning" for scenario in scenarios):
        raise ValueError("recovery development file may contain tuning rows only")
    if any(not scenario.id.startswith("rc") for scenario in scenarios):
        raise ValueError("recovery development ids must use the rc prefix")
    counts = Counter(scenario.consensus for scenario in scenarios)
    if counts != Counter({"SILENT": 30, "REACT": 30, "REPLY": 30}):
        raise ValueError("recovery development must contain 30 unanimous rows per class")
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, nargs="+", default=[0, 3, 5], choices=(0, 3, 5))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--variant", default="frozen-baseline")
    args = parser.parse_args()

    scenarios = load_recovery_development()
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

    started = time.perf_counter()
    adapter = DeciderAdapter(
        config["decider_model_id"], config["decider_device"], int(config["decider_timeout_ms"])
    )
    initialization_ms = (time.perf_counter() - started) * 1000
    rows = evaluate_scenarios(adapter, scenarios, list(args.k), thresholds)
    validate_evaluation_rows(rows, scenarios, list(args.k))
    metrics = {
        str(context_k): compute_metrics(
            [row for row in rows if int(row["context_k"]) == context_k]
        )
        for context_k in args.k
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
    summary["recovery_variant"] = args.variant
    summary["development_only"] = True
    summary["react_criteria"] = {"precision_min": 0.70, "recall_min": 0.70}
    run_dir = create_run_directory(args.output_root)
    write_per_case(run_dir / "per_case.csv", rows)
    write_summary(run_dir / "results.json", summary)
    (run_dir / "report.md").write_text(build_report(summary), encoding="utf-8")
    (run_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "artifact_version": "lurker-m5-recovery-development-run-v1",
        "variant": args.variant,
        "development_only": True,
        "scenario_path": str(DEVELOPMENT_PATH.relative_to(ROOT)),
        "scenario_sha256": sha256(DEVELOPMENT_PATH),
        "scenario_count": len(scenarios),
        "expected_predictions": len(scenarios) * len(args.k),
        "actual_predictions": len(rows),
        "context_values": list(args.k),
        "mock": False,
        "aws_or_bedrock_calls": 0,
        "heldout_opened": False,
        "config_sha256": sha256(args.config),
        "starting_baseline_thresholds": BASELINE_THRESHOLDS,
        "uses_starting_baseline_thresholds": thresholds == BASELINE_THRESHOLDS,
        "error_count": sum(bool(row["error"]) for row in rows),
        "observability": {
            "adapter_initialization_ms": initialization_ms,
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"results={run_dir} development_cases=90 predictions={len(rows)}")
    print("heldout_opened=false aws_or_bedrock_calls=0 production_config_changed=false")
    return 3 if manifest["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
