#!/usr/bin/env python3
"""Create corrected provenance for the fixed 90-case recovery development set.

This migration intentionally reads only the already-selected development file and
its manifest. It never opens the 105-case reserve or either M5 held-out dataset.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DEVELOPMENT = (
    ROOT / "eval" / "recovery" / "single_rater" / "development" / "development.jsonl"
)
SOURCE_MANIFEST = ROOT / "eval" / "recovery" / "single_rater" / "split_manifest.json"
OUTPUT_ROOT = ROOT / "eval" / "recovery" / "combined_reference"
OUTPUT_DEVELOPMENT = OUTPUT_ROOT / "development" / "development.jsonl"
OUTPUT_MANIFEST = OUTPUT_ROOT / "provenance_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_combined_reference(
    source_development: Path = SOURCE_DEVELOPMENT,
    source_manifest_path: Path = SOURCE_MANIFEST,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_rows = [
        json.loads(line)
        for line in source_development.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(source_rows) != 90 or len({row["id"] for row in source_rows}) != 90:
        raise ValueError("source development must contain exactly 90 unique cases")
    if Counter(row["reference_label"] for row in source_rows) != Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    ):
        raise ValueError("source development must contain 30 labels per class")
    if len({row["family_id"] for row in source_rows}) != 18:
        raise ValueError("source development must contain 18 complete families")
    if source_manifest.get("locked_reserve", {}).get("count") != 105:
        raise ValueError("source manifest does not preserve the 105-case reserve")
    development_families = set(source_manifest["development"]["family_ids"])
    reserve_families = set(source_manifest["locked_reserve"]["family_ids"])
    if development_families & reserve_families:
        raise ValueError("development and reserve families overlap")

    rows: list[dict[str, object]] = []
    for source in source_rows:
        row = dict(source)
        row.pop("evaluator_id", None)
        row["label_basis"] = "combined_three_contributor_reference"
        row["contributor_count"] = 3
        row["independent_decisions_available"] = False
        row["group_consensus_verified"] = False
        row["aggregation_method"] = "combined_document_process_not_reconstructable"
        row["notes"] = (
            "One final label from a document to which three people contributed; "
            "individual decisions and the aggregation process are unavailable."
        )
        rows.append(row)

    manifest: dict[str, object] = {
        "artifact_version": "lurker-m5-recovery-combined-reference-v1",
        "status": "DEVELOPMENT_ONLY",
        "label_basis": "combined_three_contributor_reference",
        "contributor_count": 3,
        "independent_decisions_available": False,
        "group_consensus_verified": False,
        "inter_rater_agreement_calculable": False,
        "aggregation_method": "combined_document_process_not_reconstructable",
        "provenance_statement": (
            "Three people contributed to one combined evaluation document. Because "
            "individual responses were not retained, the final labels cannot be "
            "verified as independent decisions or unanimous/group consensus."
        ),
        "development": {
            "count": 90,
            "class_counts": {"SILENT": 30, "REACT": 30, "REPLY": 30},
            "family_count": 18,
            "family_ids": sorted(development_families),
        },
        "locked_reserve": {
            "count": 105,
            "family_count": 21,
            "family_ids": sorted(reserve_families),
            "path": source_manifest["reserve_path"],
            "recorded_sha256": source_manifest["reserve_sha256"],
            "opened_by_migration": False,
            "model_predictions_allowed": False,
        },
        "family_leakage_count": 0,
        "source_combined_document": source_manifest["source_export"],
        "source_combined_document_sha256": source_manifest["source_export_sha256"],
        "source_development_path": str(source_development.relative_to(ROOT)),
        "source_development_sha256": sha256(source_development),
        "development_path": str(OUTPUT_DEVELOPMENT.relative_to(ROOT)),
        "original_m5_heldout_opened": False,
        "reserve_opened": False,
        "aws_or_bedrock_calls": 0,
        "limitations": [
            "Individual evaluator decisions are unavailable.",
            "Independence, unanimity, consensus method, and inter-rater agreement cannot be verified.",
            "Development metrics are reference-label evidence only and cannot complete M5.",
        ],
    }
    return rows, manifest


def main() -> int:
    if OUTPUT_DEVELOPMENT.exists() or OUTPUT_MANIFEST.exists():
        raise FileExistsError("refusing to overwrite combined-reference evidence")
    rows, manifest = build_combined_reference()
    OUTPUT_DEVELOPMENT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DEVELOPMENT.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest["development_sha256"] = sha256(OUTPUT_DEVELOPMENT)
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "development_cases=90 reserve_cases=105 contributors=3 "
        "independence_verifiable=false consensus_verifiable=false reserve_opened=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
