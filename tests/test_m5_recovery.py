"""Offline recovery-dataset preparation, isolation, and labeling contracts."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.audit_recovery_candidates import audit
from scripts.build_recovery_candidates import build_rows, evaluator_order, write_outputs
from scripts.labeling_server import DATASETS, public_dataset
from scripts.merge_recovery_labels import fleiss_kappa, merge_recovery_labels
from scripts.prepare_single_rater_recovery import build_single_rater_split
from scripts.prepare_combined_reference import build_combined_reference
from scripts.run_combined_reference_wording_candidate import (
    DEVELOPMENT_PATH as COMBINED_REFERENCE_DEVELOPMENT,
    load_candidate as load_concise_candidate,
    load_development as load_combined_reference_development,
)
from eval.baselines import evaluate_question_mark_baseline
from eval.metrics_def import compute_metrics
from scripts.run_recovery_development import load_recovery_development
from scripts.run_single_rater_recovery import load_single_rater_development
from scripts.run_single_rater_wording_candidate import load_candidate
from scripts.split_recovery_dataset import (
    choose_partition,
    deterministic_pick,
)

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "eval" / "recovery"
ORIGINAL_HELDOUT = ROOT / "results" / "m5_heldout" / "20261017T053719Z" / "heldout_locked.jsonl"


def test_recovery_candidates_are_balanced_grouped_and_reproducible() -> None:
    rows, manifest = build_rows()
    assert len(rows) == 195
    assert len({row["id"] for row in rows}) == 195
    assert Counter(row["family_id"] for row in rows) == Counter(
        {family["family_id"]: 5 for family in manifest["families"]}
    )
    assert manifest["design_action_counts"] == {"SILENT": 65, "REACT": 65, "REPLY": 65}
    assert not any(
        {"label", "labels", "consensus", "prediction", "split", "design_action"} & set(row)
        for row in rows
    )


def test_recovery_public_payload_and_orders_are_blind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidates = tmp_path / "candidates.jsonl"
    write_outputs(candidates, tmp_path / "design_manifest.json", tmp_path / "labels")
    recovery_config = {**DATASETS["recovery"], "candidate_path": candidates}
    monkeypatch.setitem(DATASETS, "recovery", recovery_config)
    payload = public_dataset("recovery")
    assert payload["dataset"]["scenario_count"] == 195
    assert payload["dataset"]["export_prefix"] == "recovery_labels"
    for row in payload["scenarios"]:
        assert set(row) == {"id", "history", "message"}
    orders = [
        [row["id"] for row in evaluator_order(payload["scenarios"], evaluator)]
        for evaluator in ("a1", "a2", "a3")
    ]
    assert len({tuple(order) for order in orders}) == 3
    assert all(set(order) == set(orders[0]) for order in orders)


def write_labels(path: Path, rows: list[dict], labels: dict[str, str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "label", "optional note"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"id": row["id"], "label": labels[row["id"]], "optional note": ""})


def test_recovery_merge_is_unanimous_and_keeps_ambiguity_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = build_rows()
    design_by_id = {
        scenario_id: family["design_action"]
        for family in manifest["families"]
        for scenario_id in family["candidate_ids"]
    }
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    paths = [tmp_path / f"a{index}.csv" for index in range(1, 4)]
    for path in paths:
        write_labels(path, rows, design_by_id)
    # A temporary disagreement proves that no majority label is forced.
    with paths[2].open(newline="", encoding="utf-8") as stream:
        csv_rows = list(csv.DictReader(stream))
    csv_rows[0]["label"] = "REPLY" if csv_rows[0]["label"] != "REPLY" else "SILENT"
    with paths[2].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "label", "optional note"])
        writer.writeheader()
        writer.writerows(csv_rows)

    monkeypatch.setattr("scripts.merge_recovery_labels.RECOVERY_ROOT", tmp_path)
    unanimous = tmp_path / "labeling" / "unanimous.jsonl"
    ambiguous = tmp_path / "labeling" / "ambiguity_audit.jsonl"
    report_path = tmp_path / "labeling" / "agreement.json"
    report = merge_recovery_labels(candidates, paths, unanimous, ambiguous, report_path)
    assert report["unanimous_count"] == 194
    assert report["ambiguous_count"] == 1
    assert len(ambiguous.read_text().splitlines()) == 1
    assert "AMBIGUOUS" in ambiguous.read_text()


def test_family_grouped_split_can_reach_balanced_targets_without_leakage() -> None:
    rows, manifest = build_rows()
    design_by_id = {
        scenario_id: family["design_action"]
        for family in manifest["families"]
        for scenario_id in family["candidate_ids"]
    }
    unanimous = [{**row, "consensus": design_by_id[row["id"]]} for row in rows]
    development_families, heldout_families = choose_partition(unanimous)
    assert not (development_families & heldout_families)
    development = deterministic_pick(unanimous, development_families, 30, "development", 20261017)
    heldout = deterministic_pick(unanimous, heldout_families, 20, "heldout", 20261017)
    assert Counter(row["consensus"] for row in development) == Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    )
    assert Counter(row["consensus"] for row in heldout) == Counter(
        {"SILENT": 20, "REACT": 20, "REPLY": 20}
    )
    assert not ({row["family_id"] for row in development} & {row["family_id"] for row in heldout})


def test_agreement_metric_and_candidate_audit(tmp_path: Path) -> None:
    assert fleiss_kappa([["SILENT"] * 3, ["REACT"] * 3, ["REPLY"] * 3]) == pytest.approx(1.0)
    candidates = tmp_path / "candidates.jsonl"
    manifest = tmp_path / "design_manifest.json"
    label_dir = tmp_path / "labels"
    original_evidence = tmp_path / "original_evidence"
    original_evidence.mkdir()
    preserved = original_evidence / "acceptance.json"
    preserved.write_text('{"model_performance":"NO_GO"}\n', encoding="utf-8")
    digest = hashlib.sha256(preserved.read_bytes()).hexdigest()
    (original_evidence / "evidence.sha256").write_text(
        f"{digest}  acceptance.json\n", encoding="utf-8"
    )
    write_outputs(candidates, manifest, label_dir)
    report = audit(candidates, manifest, label_dir, original_evidence)
    assert report["status"] == "PASS"
    assert report["checks"]["original_nogo_evidence_unchanged"] is True
    assert report["model_calls"] == 0
    assert report["aws_or_bedrock_calls"] == 0


def test_development_loader_rejects_original_heldout_before_reading() -> None:
    with pytest.raises(ValueError, match="fixed development file"):
        load_recovery_development(ORIGINAL_HELDOUT)


def test_label_templates_are_complete_blank_and_do_not_expose_family(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    label_dir = tmp_path / "labels"
    write_outputs(candidates, tmp_path / "design_manifest.json", label_dir)
    for evaluator in ("a1", "a2", "a3"):
        path = label_dir / f"recovery_labels_{evaluator}.csv"
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 195
        assert set(rows[0]) == {"id", "history text", "message", "label", "optional note"}
        assert all(not row["label"] and "family" not in row for row in rows)


def test_single_rater_path_is_balanced_family_isolated_and_explicitly_exploratory() -> None:
    rows, design_manifest = build_rows()
    design_by_id = {
        scenario_id: family["design_action"]
        for family in design_manifest["families"]
        for scenario_id in family["candidate_ids"]
    }
    labels = {
        scenario_id: {"label": label, "note": ""}
        for scenario_id, label in design_by_id.items()
    }
    development, reserve, manifest = build_single_rater_split(rows, labels)
    assert Counter(row["reference_label"] for row in development) == Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    )
    assert len(development) == 90
    assert len(reserve) == 105
    assert not (
        {row["family_id"] for row in development}
        & {row["family_id"] for row in reserve}
    )
    assert manifest["human_consensus"] is False
    assert manifest["new_heldout_created"] is False
    assert manifest["heldout_opened"] is False


def test_single_rater_loader_rejects_original_heldout_before_reading() -> None:
    with pytest.raises(ValueError, match="fixed development file"):
        load_single_rater_development(ORIGINAL_HELDOUT)


def test_wording_candidate_is_versioned_general_and_development_only() -> None:
    candidate = load_candidate()
    assert candidate["candidate_id"] == "m5-recovery-social-value-v1"
    assert candidate["status"] == "development_only_not_production"
    assert candidate["model"]["architecture_changed"] is False
    assert candidate["baseline"]["reply_threshold"] == pytest.approx(0.20)
    assert candidate["baseline"]["react_threshold"] == pytest.approx(0.04)
    evaluation = candidate["evaluation"]
    assert evaluation["expected_cases"] == 90
    assert evaluation["reserve_allowed"] is False
    assert evaluation["heldout_allowed"] is False
    assert evaluation["aws_or_bedrock_allowed"] is False
    wording = candidate["decision_contract"]["question"]
    assert "unresolved" in wording
    assert "meaningful social value" in wording
    assert "not punctuation alone" in wording
    assert not any(f"rc{index:03d}" in wording for index in range(1, 196))


def test_combined_reference_provenance_is_accurate_and_reserve_stays_locked(
    tmp_path: Path,
) -> None:
    development_path = RECOVERY / "single_rater" / "development" / "development.jsonl"
    source_rows = [
        json.loads(line)
        for line in development_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    development_families = sorted({row["family_id"] for row in source_rows})
    source_manifest = {
        "development": {"family_ids": development_families},
        "locked_reserve": {
            "count": 105,
            "family_ids": [f"reserve-{index:02d}" for index in range(1, 22)],
        },
        "reserve_path": "protected/reserve.jsonl",
        "reserve_sha256": "0" * 64,
        "source_export": "private/combined-label-document.csv",
        "source_export_sha256": "1" * 64,
    }
    source_manifest_path = tmp_path / "split_manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")

    rows, manifest = build_combined_reference(development_path, source_manifest_path)
    assert len(rows) == 90
    assert Counter(row["reference_label"] for row in rows) == Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    )
    assert manifest["contributor_count"] == 3
    assert manifest["independent_decisions_available"] is False
    assert manifest["group_consensus_verified"] is False
    assert manifest["inter_rater_agreement_calculable"] is False
    assert manifest["locked_reserve"]["count"] == 105
    assert manifest["locked_reserve"]["opened_by_migration"] is False
    assert manifest["locked_reserve"]["model_predictions_allowed"] is False
    assert manifest["original_m5_heldout_opened"] is False
    assert all(
        row["label_basis"] == "combined_three_contributor_reference" for row in rows
    )


def test_combined_reference_loader_is_fixed_balanced_and_development_only() -> None:
    rows = load_combined_reference_development()
    assert len(rows) == 90
    assert Counter(row.reference_label for row in rows) == Counter(
        {"SILENT": 30, "REACT": 30, "REPLY": 30}
    )
    assert len({row.family_id for row in rows}) == 18
    with pytest.raises(ValueError, match="fixed combined-reference development"):
        load_combined_reference_development(ORIGINAL_HELDOUT)


def test_concise_v2_candidate_changes_only_wording() -> None:
    candidate = load_concise_candidate()
    assert candidate["candidate_id"] == "m5-recovery-concise-boundaries-v2"
    assert candidate["status"] == "development_only_not_production"
    assert candidate["model"]["architecture_changed"] is False
    assert candidate["decision_contract"]["policy_changed"] is False
    assert candidate["decision_contract"]["context_changed"] is False
    assert candidate["baseline"]["reply_threshold"] == pytest.approx(0.20)
    assert candidate["baseline"]["react_threshold"] == pytest.approx(0.04)
    evaluation = candidate["evaluation"]
    assert evaluation["dataset"] == str(COMBINED_REFERENCE_DEVELOPMENT.relative_to(ROOT))
    assert evaluation["expected_cases"] == 90
    assert evaluation["context_values"] == [3]
    assert evaluation["contributor_count"] == 3
    assert evaluation["independent_decisions_available"] is False
    assert evaluation["group_consensus_verified"] is False
    assert evaluation["reserve_allowed"] is False
    assert evaluation["heldout_allowed"] is False
    assert evaluation["aws_or_bedrock_allowed"] is False
    wording = candidate["decision_contract"]["question"]
    assert "answers to earlier questions are not requests" in wording
    assert "not punctuation" in wording
    assert not any(f"rc{index:03d}" in wording for index in range(1, 196))


def test_combined_reference_question_mark_baseline_is_free_and_complete() -> None:
    rows = evaluate_question_mark_baseline(load_combined_reference_development(), 3)
    metrics = compute_metrics(rows)
    assert len(rows) == 90
    assert metrics["total_count"] == 90
    assert metrics["error_count"] == 0
    assert all(row["decider_latency_ms"] == 0 for row in rows)
    assert all(row["final_action"] in {"SILENT", "REPLY"} for row in rows)
