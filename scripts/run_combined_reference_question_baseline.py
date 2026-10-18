#!/usr/bin/env python3
"""Run the free question-mark baseline on the accessible 90-case reference set."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.baselines import evaluate_question_mark_baseline
from eval.metrics_def import compute_metrics
from scripts.run_combined_reference_wording_candidate import (
    DEVELOPMENT_PATH,
    PROVENANCE_MANIFEST,
    ROOT,
    load_development,
    sha256,
)

OUTPUT_ROOT = ROOT / "results" / "m5_finalization" / "question_mark_baseline"


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    scenarios = load_development()
    rows = evaluate_question_mark_baseline(scenarios, 3)
    metrics = compute_metrics(rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = OUTPUT_ROOT / stamp
    if output.exists():
        raise FileExistsError(f"refusing to overwrite baseline evidence: {output}")
    output.mkdir(parents=True)
    write_rows(output / "always_questions_per_case.csv", rows)
    summary = {
        "artifact_version": "lurker-m5-combined-reference-question-baseline-v1",
        "status": "SUPPLEMENTARY_DEVELOPMENT_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": "always_questions",
        "split": "combined_reference_development",
        "context_k": 3,
        "scenario_count": 90,
        "label_basis": "combined_three_contributor_reference",
        "contributor_count": 3,
        "independent_decisions_available": False,
        "group_consensus_verified": False,
        "model_calls": 0,
        "aws_or_bedrock_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "metrics": metrics,
        "source_path": str(DEVELOPMENT_PATH.relative_to(ROOT)),
        "source_sha256": sha256(DEVELOPMENT_PATH),
        "provenance_manifest_sha256": sha256(PROVENANCE_MANIFEST),
        "reserve_opened": False,
        "original_heldout_opened": False,
        "strict_m5_heldout_baseline": False,
        "limitation": (
            "This free baseline uses the accessible development reference. It is not "
            "a held-out comparison and does not satisfy the strict held-out-baseline gap."
        ),
    }
    (output / "always_questions_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"output={output} rows=90 model_calls=0 aws_or_bedrock_calls=0 "
        "reserve_opened=false heldout_opened=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
