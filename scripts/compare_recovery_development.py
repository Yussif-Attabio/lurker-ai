#!/usr/bin/env python3
"""Compare real M5 recovery development runs without reading either held-out set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_RESULTS = ROOT / "results" / "m5_recovery" / "development"


def load_run(spec: str) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    if "=" not in spec:
        raise ValueError("each run must use NAME=/path/to/run-directory")
    name, raw_path = spec.split("=", 1)
    run_dir = Path(raw_path)
    summary = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("development_only") or manifest.get("heldout_opened") is not False:
        raise ValueError(f"{run_dir} is not a recovery development-only run")
    if manifest.get("mock") is not False or manifest.get("aws_or_bedrock_calls") != 0:
        raise ValueError(f"{run_dir} is not valid real-local evidence")
    return name, run_dir, summary, manifest


def rate(metric: dict[str, Any]) -> float | None:
    return metric.get("rate")


def compare(specs: list[str], context_k: int) -> dict[str, Any]:
    loaded = [load_run(spec) for spec in specs]
    hashes = {item[3]["scenario_sha256"] for item in loaded}
    if len(hashes) != 1:
        raise ValueError("all compared runs must use the identical development dataset")
    rows = []
    for name, path, summary, manifest in loaded:
        metrics = summary["context_metrics"][str(context_k)]
        rows.append(
            {
                "name": name,
                "run": str(path),
                "config_sha256": manifest["config_sha256"],
                "thresholds": summary["thresholds"],
                "accuracy": rate(metrics["accuracy"]),
                "unnecessary_interruption_rate": rate(
                    metrics["unnecessary_interruption_rate"]
                ),
                "missed_help_rate": rate(metrics["missed_help_rate"]),
                "react_precision": rate(metrics["react_precision"]),
                "react_recall": rate(metrics["react_recall"]),
                "latency_p50_ms": metrics["latency_ms"]["p50"],
                "latency_p95_ms": metrics["latency_ms"]["p95"],
                "errors": metrics["error_count"],
            }
        )
    return {
        "artifact_version": "lurker-m5-recovery-development-comparison-v1",
        "context_k": context_k,
        "scenario_sha256": hashes.pop(),
        "development_only": True,
        "human_approval_required": True,
        "runs": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", nargs="+", help="NAME=/path/to/run-directory")
    parser.add_argument("--k", type=int, default=3, choices=(0, 3, 5))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if RECOVERY_RESULTS.resolve() not in args.output.resolve().parents:
        raise SystemExit("comparison output must stay under results/m5_recovery/development")
    result = compare(args.run, args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={args.output} runs={len(result['runs'])} heldout_opened=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
