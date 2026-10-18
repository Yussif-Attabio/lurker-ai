#!/usr/bin/env python3
"""Run one required M5 baseline with explicit held-out and call-budget guards."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from eval.baselines import (
    BedrockJudge,
    evaluate_bedrock_baseline,
    evaluate_question_mark_baseline,
)
from eval.metrics_def import compute_metrics
from scripts.run_eval import guard_heldout, load_scenarios, validate_scenarios

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "eval" / "scenarios.jsonl"


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write baseline rows with a stable union of observed fields."""
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, choices=("always_questions", "bedrock_judge"))
    parser.add_argument("--split", default="heldout", choices=("tuning", "heldout"))
    parser.add_argument("--allow-heldout", action="store_true")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--context-k", type=int, default=3, choices=(0, 3, 5))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-calls", type=int, default=15)
    parser.add_argument("--max-prompt-bytes", type=int, default=1000)
    args = parser.parse_args()

    try:
        guard_heldout(args.split, args.allow_heldout)
        scenarios = load_scenarios(args.scenarios, args.split)
        validate_scenarios(scenarios, args.split)
        if args.output_dir.exists() and any(args.output_dir.iterdir()):
            raise ValueError("baseline output directory must be new or empty")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.baseline == "always_questions":
            rows = evaluate_question_mark_baseline(scenarios, args.context_k)
            model_calls = 0
            model_id = None
        else:
            if args.max_calls < len(scenarios) or args.max_calls > 15:
                raise ValueError(
                    "Bedrock judge max-calls must cover every scenario and must not exceed 15"
                )
            model_id = os.getenv("BASELINE_MODEL_ID")
            region = os.getenv("AWS_REGION")
            if not model_id or not region:
                raise ValueError("Set BASELINE_MODEL_ID and AWS_REGION")
            judge = BedrockJudge(
                model_id,
                region,
                max_calls=args.max_calls,
                max_prompt_bytes=args.max_prompt_bytes,
            )
            rows = evaluate_bedrock_baseline(scenarios, args.context_k, judge)
            model_calls = judge.calls
        metrics = compute_metrics(rows)
    except (OSError, ValueError) as exc:
        print(f"baseline refused: {exc}", file=sys.stderr)
        return 2

    stem = args.baseline
    write_rows(args.output_dir / f"{stem}_per_case.csv", rows)
    summary = {
        "artifact_version": "lurker-baseline-v1",
        "baseline": args.baseline,
        "split": args.split,
        "context_k": args.context_k,
        "model_id": model_id,
        "model_calls": model_calls,
        "max_prompt_bytes": args.max_prompt_bytes if args.baseline == "bedrock_judge" else 0,
        "input_tokens": sum(int(row.get("input_tokens", 0)) for row in rows),
        "output_tokens": sum(int(row.get("output_tokens", 0)) for row in rows),
        "metrics": metrics,
    }
    (args.output_dir / f"{stem}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"baseline={args.baseline} rows={len(rows)} calls={model_calls} "
        f"errors={metrics['error_count']} output={args.output_dir}"
    )
    return 3 if metrics["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
