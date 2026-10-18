#!/usr/bin/env python3
"""Assemble and explicitly publish one complete M5 evidence summary."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.publication import M5_ARTIFACT_VERSION, publish_results, validate_m5_summary
from eval.reporting import build_m5_report


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def assemble_summary(
    decider: dict[str, Any],
    question_baseline: dict[str, Any],
    bedrock_baseline: dict[str, Any],
    manifest: dict[str, Any],
    primary_context_k: int,
) -> dict[str, Any]:
    """Combine complete real artifacts without recomputing or inventing metrics."""
    if decider.get("split") != "heldout":
        raise ValueError("Decider results must be from the heldout split")
    if decider.get("policy_mode") != "configured_thresholds":
        raise ValueError("Decider results must use frozen configured thresholds")
    if set(decider.get("context_metrics", {})) != {"0", "3", "5"}:
        raise ValueError("Decider results must include k=0, k=3, and k=5")
    if manifest.get("mock") is not False or manifest.get("split") != "heldout":
        raise ValueError("run manifest must prove a real heldout evaluation")
    if manifest.get("actual_predictions") != manifest.get("expected_predictions"):
        raise ValueError("run manifest prediction count is incomplete")
    if int(manifest.get("error_count", -1)) != 0:
        raise ValueError("run manifest contains Decider errors")

    expected_baselines = {
        "always_questions": question_baseline,
        "bedrock_judge": bedrock_baseline,
    }
    for expected_name, baseline in expected_baselines.items():
        if baseline.get("baseline") != expected_name or baseline.get("split") != "heldout":
            raise ValueError(f"invalid {expected_name} baseline summary")
        if int(baseline.get("context_k", -1)) != primary_context_k:
            raise ValueError(f"{expected_name} baseline used the wrong context")

    return {
        "artifact_version": M5_ARTIFACT_VERSION,
        "publication_status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split": "heldout",
        "primary_context_k": primary_context_k,
        "model_id": decider["model_id"],
        "device": decider["device"],
        "hardware": decider["hardware"],
        "thresholds": decider["thresholds"],
        "criteria": decider["criteria"],
        "context_metrics": decider["context_metrics"],
        "baselines": {
            "always_reply_to_questions": {
                "model_calls": question_baseline["model_calls"],
                "input_tokens": question_baseline["input_tokens"],
                "output_tokens": question_baseline["output_tokens"],
                "metrics": question_baseline["metrics"],
            },
            "bedrock_judge": {
                "model_id": bedrock_baseline.get("model_id"),
                "model_calls": bedrock_baseline["model_calls"],
                "input_tokens": bedrock_baseline["input_tokens"],
                "output_tokens": bedrock_baseline["output_tokens"],
                "metrics": bedrock_baseline["metrics"],
            },
        },
        "run_manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decider-results", type=Path, required=True)
    parser.add_argument("--always-baseline", type=Path, required=True)
    parser.add_argument("--bedrock-baseline", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--primary-k", type=int, choices=(0, 3, 5), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.output_dir.exists() and any(args.output_dir.iterdir()):
            raise ValueError("M5 output directory must be new or empty")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        summary = assemble_summary(
            read_json(args.decider_results),
            read_json(args.always_baseline),
            read_json(args.bedrock_baseline),
            read_json(args.manifest),
            args.primary_k,
        )
        validate_m5_summary(summary, expected_status="ready")
        source = args.output_dir / "results.json"
        source.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        (args.output_dir / "report.md").write_text(
            build_m5_report(summary), encoding="utf-8"
        )
        published = publish_results(source, args.results_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"M5 publication refused: {exc}", file=sys.stderr)
        return 2
    print(f"published={published} source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
