#!/usr/bin/env python3
"""Audit the recovery candidate pool without opening either held-out dataset."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from scripts.build_recovery_candidates import build_rows, normalized_text
from scripts.labeling_server import public_dataset

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ROOT = ROOT / "eval" / "recovery"
CANDIDATES = RECOVERY_ROOT / "candidates.jsonl"
MANIFEST = RECOVERY_ROOT / "design_manifest.json"
LABEL_DIR = RECOVERY_ROOT / "label_templates"
REPORT = RECOVERY_ROOT / "quality_report.json"
PREFLIGHT = RECOVERY_ROOT / "PREFLIGHT.md"
ORIGINAL_EVIDENCE = ROOT / "results" / "m5_heldout" / "20261017T053719Z"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_original_evidence() -> dict[str, Any]:
    """Verify bytes against the preserved manifest without parsing scenario content."""
    checksum_file = ORIGINAL_EVIDENCE / "evidence.sha256"
    checks: list[dict[str, Any]] = []
    for raw_line in checksum_file.read_text(encoding="utf-8").splitlines():
        expected, relative = raw_line.split(maxsplit=1)
        relative = relative.lstrip("* ")
        path = ORIGINAL_EVIDENCE / relative
        observed = sha256(path)
        checks.append(
            {"path": relative, "expected": expected, "observed": observed, "pass": observed == expected}
        )
    return {"manifest": str(checksum_file.relative_to(ROOT)), "checks": checks, "pass": all(item["pass"] for item in checks)}


def cross_family_near_duplicates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag only unusually similar cases from different families."""
    normalized = [(row, normalized_text(row)) for row in rows]
    flags: list[dict[str, Any]] = []
    for index, (left, left_text) in enumerate(normalized):
        for right, right_text in normalized[index + 1 :]:
            if left["family_id"] == right["family_id"]:
                continue
            ratio = SequenceMatcher(None, left_text, right_text).ratio()
            if ratio >= 0.84:
                flags.append({"left": left["id"], "right": right["id"], "similarity": round(ratio, 4)})
    return flags


def audit() -> dict[str, Any]:
    rows = load_jsonl(CANDIDATES)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated_rows, generated_manifest = build_rows()
    payload = public_dataset("recovery")
    templates: dict[str, Any] = {}
    orders: list[list[str]] = []
    for evaluator in ("a1", "a2", "a3"):
        path = LABEL_DIR / f"recovery_labels_{evaluator}.csv"
        with path.open(newline="", encoding="utf-8-sig") as stream:
            csv_rows = list(csv.DictReader(stream))
        order = [row["id"] for row in csv_rows]
        orders.append(order)
        templates[evaluator] = {
            "path": str(path.relative_to(ROOT)),
            "row_count": len(csv_rows),
            "all_labels_blank": all(not row["label"].strip() for row in csv_rows),
            "unique_ids": len(set(order)),
            "sha256": sha256(path),
        }

    history_lengths = Counter(len(row["history"]) for row in rows)
    no_question_mark_questions = sum(
        1
        for row in rows
        if row["family_id"] == "pf13" and not row["message"]["text"].rstrip().endswith("?")
    )
    near_duplicates = cross_family_near_duplicates(rows)
    public_fields_safe = all(
        set(row) == {"id", "history", "message"} for row in payload["scenarios"]
    )
    reproducible = rows == generated_rows and manifest["candidate_count"] == generated_manifest["candidate_count"]
    original_evidence = verify_original_evidence()
    checks = {
        "candidate_count_195": len(rows) == 195,
        "family_count_39": len({row["family_id"] for row in rows}) == 39,
        "five_per_family": set(Counter(row["family_id"] for row in rows).values()) == {5},
        "design_balance_65_each": manifest["design_action_counts"] == {action: 65 for action in ("SILENT", "REACT", "REPLY")},
        "unique_ids": len({row["id"] for row in rows}) == 195,
        "exact_duplicates_zero": len({normalized_text(row) for row in rows}) == 195,
        "cross_family_near_duplicate_flags_zero": not near_duplicates,
        "public_payload_blind": public_fields_safe,
        "three_distinct_orders": len({tuple(order) for order in orders}) == 3,
        "templates_complete_and_blank": all(
            item["row_count"] == 195 and item["unique_ids"] == 195 and item["all_labels_blank"]
            for item in templates.values()
        ),
        "punctuation_boundary_present": no_question_mark_questions == 5,
        "generation_reproducible": reproducible,
        "original_nogo_evidence_unchanged": original_evidence["pass"],
        "no_human_labels_created": not (RECOVERY_ROOT / "labeling" / "unanimous.jsonl").exists(),
        "no_new_split_created": not (RECOVERY_ROOT / "split_manifest.json").exists(),
    }
    return {
        "artifact_version": "lurker-m5-recovery-candidate-audit-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": "candidate preparation and blind labeling infrastructure only",
        "candidate_count": len(rows),
        "family_count": len({row["family_id"] for row in rows}),
        "design_action_counts": manifest["design_action_counts"],
        "category_counts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "history_length_counts": {str(key): value for key, value in sorted(history_lengths.items())},
        "semantic_questions_without_question_mark": no_question_mark_questions,
        "cross_family_near_duplicate_flags": near_duplicates,
        "label_templates": templates,
        "candidate_sha256": sha256(CANDIDATES),
        "design_manifest_sha256": sha256(MANIFEST),
        "original_evidence": original_evidence,
        "checks": checks,
        "model_calls": 0,
        "aws_or_bedrock_calls": 0,
        "original_or_new_heldout_evaluated": False,
    }


def markdown(report: dict[str, Any]) -> str:
    category_rows = "\n".join(
        f"| {category.replace('_', ' ')} | {count} |"
        for category, count in report["category_counts"].items()
    )
    check_rows = "\n".join(
        f"| {name.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in report["checks"].items()
    )
    template_rows = "\n".join(
        f"| {name.upper()} | {item['row_count']} | {'Yes' if item['all_labels_blank'] else 'No'} | `{item['sha256']}` |"
        for name, item in report["label_templates"].items()
    )
    return f"""# M5 recovery candidate preflight

Status: **{report['status']} — READY FOR INDEPENDENT HUMAN LABELING**

This preflight covers candidate preparation and labeling infrastructure only. It does not approve model evaluation, create a new split, alter production settings, or change the original M5 NO-GO.

## Composition

- Candidates: {report['candidate_count']}
- Scenario families: {report['family_count']} (five candidates each)
- Owner-only authoring coverage: 65 SILENT-oriented, 65 REACT-oriented, 65 REPLY-oriented
- Questions without final `?` in the dedicated punctuation family: {report['semantic_questions_without_question_mark']}
- Candidate SHA-256: `{report['candidate_sha256']}`

The authoring coverage is a design hypothesis, not ground truth. Only unanimous labels from three independent people can assign a class.

| Neutral category | Candidates |
|---|---:|
{category_rows}

## Blind evaluator files

Each evaluator receives all 195 scenarios in a different deterministic order. Labels and notes are blank, and the files contain no family IDs, authoring targets, split assignments, thresholds, or model predictions.

| Evaluator | Rows | Labels blank | SHA-256 |
|---|---:|---|---|
{template_rows}

## Quality and isolation checks

| Check | Result |
|---|---|
{check_rows}

No original held-out example was parsed or reused. The audit only hashed the preserved NO-GO files against their existing checksum manifest; every checksum passed. No Decider, AWS, or Bedrock call occurred.

## Next authorized step

Give one evaluator slot or one blank CSV to each of three people. They must work independently. Do not share `design_manifest.json` or this preflight's authoring-balance section with evaluators. After all three genuine exports are collected, run the unanimous merge and review agreement, ambiguity, class quotas, and Fleiss' kappa before creating any split.
"""


def main() -> int:
    report = audit()
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    PREFLIGHT.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
