#!/usr/bin/env python3
"""Run the real Decider on reviewed scenarios and save auditable evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import yaml

from decision_pattern.lurker_gate import OPTIONS, QUESTION, apply_policy
from eval.metrics_def import compute_metrics
from eval.reporting import base_summary, build_report, create_run_directory, write_summary
from src.lurker.context import build_state
from src.lurker.schemas import Scenario

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "eval" / "scenarios.jsonl"
DEFAULT_TUNING_SCENARIOS = ROOT / "eval" / "tuning_scenarios.jsonl"
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_CRITERIA = ROOT / "eval" / "criteria.yaml"
DEFAULT_RESULTS = ROOT / "results"

PER_CASE_FIELDS = [
    "id",
    "split",
    "category",
    "context_k",
    "consensus",
    "raw_choice",
    "confidence",
    "final_action",
    "downgraded",
    "reason",
    "decider_latency_ms",
    "error",
    "scores_json",
]


def guard_heldout(split: str, allow_heldout: bool) -> None:
    """Prevent accidental held-out evaluation before the explicit M5 run."""
    if split == "heldout" and not allow_heldout:
        raise ValueError(
            "heldout evaluation is locked until M5; pass --allow-heldout only during the approved M5 run"
        )


def scenario_path_for_split(split: str, explicit_path: Path | None) -> Path:
    """Keep ordinary tuning runs physically separate from the held-out source."""
    if explicit_path is not None:
        return explicit_path
    return DEFAULT_TUNING_SCENARIOS if split == "tuning" else DEFAULT_SCENARIOS


def load_scenarios(path: Path, split: str) -> list[Scenario]:
    """Load only fully reviewed scenarios for the requested split."""
    scenarios = [
        Scenario.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    selected = [scenario for scenario in scenarios if scenario.split == split]
    if not selected:
        raise ValueError(
            f"no reviewed {split} scenarios found; merge three complete human label exports first"
        )
    return selected


def validate_scenarios(scenarios: list[Scenario], split: str) -> None:
    """Reject duplicate, cross-split, or structurally incomplete evaluation cases."""
    if not scenarios:
        raise ValueError(f"no {split} scenarios were supplied")
    ids = [scenario.id for scenario in scenarios]
    duplicates = sorted({scenario_id for scenario_id in ids if ids.count(scenario_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate scenario ids: {', '.join(duplicates)}")
    if any(scenario.split != split for scenario in scenarios):
        raise ValueError(f"scenario collection contains rows outside split={split}")
    if any(len(scenario.history) > 5 for scenario in scenarios):
        raise ValueError("scenario history must contain at most five messages")


def validate_evaluation_rows(
    rows: list[dict[str, Any]],
    scenarios: list[Scenario],
    context_values: list[int],
) -> None:
    """Require one finite, auditable prediction for every scenario/context pair."""
    expected = {(scenario.id, context_k) for scenario in scenarios for context_k in context_values}
    observed = {(str(row["id"]), int(row["context_k"])) for row in rows}
    if len(rows) != len(expected) or observed != expected:
        raise ValueError("evaluation did not produce exactly one row per scenario/context pair")
    for row in rows:
        confidence = float(row["confidence"])
        latency = float(row["decider_latency_ms"])
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError(f"invalid confidence for scenario {row['id']}")
        if not math.isfinite(latency) or latency < 0:
            raise ValueError(f"invalid latency for scenario {row['id']}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_scenarios(
    adapter: Any,
    scenarios: Iterable[Scenario],
    context_values: Iterable[int],
    policy_config: dict[str, float],
) -> list[dict[str, Any]]:
    """Evaluate reviewed scenarios with a real, non-mock adapter."""
    if bool(getattr(adapter, "mock", False)):
        raise ValueError("run_eval refuses MockDecider")
    rows: list[dict[str, Any]] = []
    for context_k in context_values:
        for scenario in scenarios:
            state = build_state(
                [message.model_dump() for message in scenario.history],
                scenario.message.model_dump(),
                context_k,
            )
            result = adapter.decide(state, QUESTION, OPTIONS)
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


def write_per_case(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write one auditable prediction row per scenario and context value."""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PER_CASE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("tuning", "heldout"), default="tuning")
    parser.add_argument("--k", type=int, nargs="+", default=[0, 3, 5], choices=(0, 3, 5))
    parser.add_argument("--scenarios", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args()
    scenario_path = scenario_path_for_split(args.split, args.scenarios)

    try:
        guard_heldout(args.split, args.allow_heldout)
        scenarios = load_scenarios(scenario_path, args.split)
        validate_scenarios(scenarios, args.split)
    except (ValueError, OSError) as exc:
        print(f"evaluation refused: {exc}", file=sys.stderr)
        return 2

    config = yaml.safe_load(args.config.read_text())
    criteria_payload = yaml.safe_load(args.criteria.read_text())
    criteria = {
        "accuracy_min": float(criteria_payload["accuracy_min"]),
        "unnecessary_interruption_rate_max": float(
            criteria_payload["unnecessary_interruption_rate_max"]
        ),
        "missed_help_rate_max": float(criteria_payload["missed_help_rate_max"]),
    }
    thresholds_set = config.get("reply_threshold") is not None and config.get("react_threshold") is not None
    thresholds = {
        "reply_threshold": (
            float(config["reply_threshold"]) if config.get("reply_threshold") is not None else None
        ),
        "react_threshold": (
            float(config["react_threshold"]) if config.get("react_threshold") is not None else None
        ),
    }
    policy_config = {
        "reply_threshold": thresholds["reply_threshold"] if thresholds_set else 0.0,
        "react_threshold": thresholds["react_threshold"] if thresholds_set else 0.0,
    }
    policy_mode = "configured_thresholds" if thresholds_set else "unthresholded_tuning"

    from src.lurker.decider_adapter import DeciderAdapter

    initialization_started = time.perf_counter()
    adapter = DeciderAdapter(
        config["decider_model_id"], config["decider_device"], int(config["decider_timeout_ms"])
    )
    initialization_ms = (time.perf_counter() - initialization_started) * 1000
    context_values = list(args.k)
    rows = evaluate_scenarios(adapter, scenarios, context_values, policy_config)
    validate_evaluation_rows(rows, scenarios, context_values)
    context_metrics = {
        str(context_k): compute_metrics(
            [row for row in rows if int(row["context_k"]) == context_k]
        )
        for context_k in args.k
    }
    summary = base_summary(
        split=args.split,
        model_id=config["decider_model_id"],
        device=config["decider_device"],
        policy_mode=policy_mode,
        thresholds=thresholds,
        criteria=criteria,
        context_metrics=context_metrics,
    )
    run_dir = create_run_directory(args.output_root)
    write_per_case(run_dir / "per_case.csv", rows)
    write_summary(run_dir / "results.json", summary)
    (run_dir / "report.md").write_text(build_report(summary), encoding="utf-8")
    (run_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "artifact_version": "lurker-eval-manifest-v1",
        "split": args.split,
        "scenario_count": len(scenarios),
        "expected_predictions": len(scenarios) * len(context_values),
        "actual_predictions": len(rows),
        "context_values": context_values,
        "model_id": config["decider_model_id"],
        "device": config["decider_device"],
        "mock": False,
        "scenario_sha256": _sha256(scenario_path),
        "config_sha256": _sha256(args.config),
        "error_count": sum(bool(row["error"]) for row in rows),
        "observability": {
            "adapter_initialization_ms": initialization_ms,
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "command": ["scripts/run_eval.py", *sys.argv[1:]],
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"results={run_dir} cases={len(scenarios)} predictions={len(rows)}")
    if manifest["error_count"]:
        print(f"status=EVALUATION_FAILED errors={manifest['error_count']}")
        return 3
    if not thresholds_set:
        print("status=THRESHOLDS_PENDING next=tune_thresholds.py")
    else:
        print("status=REPORT_READY human_go_no_go_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
