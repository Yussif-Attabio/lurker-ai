"""Offline tests for real-run boundaries, reporting, and threshold tuning."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from eval.metrics_def import compute_metrics
from eval.reporting import build_report
from scripts.run_eval import (
    DEFAULT_SCENARIOS,
    DEFAULT_TUNING_SCENARIOS,
    evaluate_scenarios,
    guard_heldout,
    load_scenarios,
    scenario_path_for_split,
)
from scripts.tune_thresholds import (
    apply_threshold_pair,
    conservative_recommendation_pool,
    load_tuning_rows,
    sweep_thresholds,
    threshold_evidence,
)
from src.lurker.schemas import DeciderResult, Scenario


def scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "id": "s1",
            "split": "tuning",
            "category": "technical_question",
            "history": [{"sender": "Alex", "text": "Earlier"}],
            "message": {"sender": "Lea", "text": "Why?"},
            "labels": {"a1": "REPLY", "a2": "REPLY", "a3": "REPLY"},
            "consensus": "REPLY",
            "notes": "",
        }
    )


class FakeAdapter:
    mock = False

    def decide(self, state, question, options):
        assert state["agent_name"] == "Lurker"
        return DeciderResult(choice="REPLY", confidence=0.8, latency_ms=12)


class MockAdapter(FakeAdapter):
    mock = True


def test_eval_uses_shared_policy_and_refuses_mock() -> None:
    rows = evaluate_scenarios(
        FakeAdapter(),
        [scenario()],
        [0, 3, 5],
        {"reply_threshold": 0.85, "react_threshold": 0.5},
    )
    assert len(rows) == 3
    assert all(row["raw_choice"] == "REPLY" for row in rows)
    assert all(row["final_action"] == "SILENT" for row in rows)
    assert all(row["reason"] == "low_confidence" for row in rows)
    with pytest.raises(ValueError, match="MockDecider"):
        evaluate_scenarios(
            MockAdapter(),
            [scenario()],
            [3],
            {"reply_threshold": 0.5, "react_threshold": 0.5},
        )


def test_heldout_is_locked_without_explicit_m5_override() -> None:
    guard_heldout("tuning", False)
    with pytest.raises(ValueError, match="locked until M5"):
        guard_heldout("heldout", False)
    guard_heldout("heldout", True)


def test_tuning_default_is_physically_separate_from_heldout_source() -> None:
    assert scenario_path_for_split("tuning", None) == DEFAULT_TUNING_SCENARIOS
    assert scenario_path_for_split("tuning", None) != DEFAULT_SCENARIOS
    assert scenario_path_for_split("heldout", None) == DEFAULT_SCENARIOS
    rows = load_scenarios(DEFAULT_TUNING_SCENARIOS, "tuning")
    assert len(rows) == 30
    assert {row.split for row in rows} == {"tuning"}


def test_tuning_load_never_opens_shared_source(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[Path] = []
    original = Path.read_text

    def audited_read_text(path: Path, *args, **kwargs) -> str:
        resolved = path.resolve()
        opened.append(resolved)
        if resolved == DEFAULT_SCENARIOS.resolve():
            raise AssertionError("tuning attempted to open the shared scenario source")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", audited_read_text)
    selected = scenario_path_for_split("tuning", None)
    rows = load_scenarios(selected, "tuning")
    assert len(rows) == 30
    assert opened == [DEFAULT_TUNING_SCENARIOS.resolve()]


def write_predictions(path: Path, splits: list[str]) -> None:
    fields = [
        "id",
        "split",
        "context_k",
        "consensus",
        "raw_choice",
        "confidence",
        "final_action",
        "downgraded",
        "reason",
        "decider_latency_ms",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, split in enumerate(splits):
            writer.writerow(
                {
                    "id": f"s{index}",
                    "split": split,
                    "context_k": 3,
                    "consensus": "REPLY" if index == 0 else "SILENT",
                    "raw_choice": "REPLY",
                    "confidence": 0.6,
                    "final_action": "REPLY",
                    "downgraded": False,
                    "reason": "confident",
                    "decider_latency_ms": 10,
                    "error": "",
                }
            )


def test_tuning_refuses_heldout_rows(tmp_path: Path) -> None:
    path = tmp_path / "mixed.csv"
    write_predictions(path, ["tuning", "heldout"])
    with pytest.raises(ValueError, match="tuning predictions only"):
        load_tuning_rows(path, 3)


def test_threshold_sweep_reapplies_policy_with_counts(tmp_path: Path) -> None:
    path = tmp_path / "tuning.csv"
    write_predictions(path, ["tuning", "tuning"])
    rows = load_tuning_rows(path, 3)
    adjusted = apply_threshold_pair(rows, reply_threshold=0.7, react_threshold=0.7)
    assert [item["final_action"] for item in adjusted] == ["SILENT", "SILENT"]
    metrics = compute_metrics(adjusted)
    assert metrics["accuracy"]["rate"] == 0.5
    sweep = sweep_thresholds(
        rows,
        {
            "accuracy_min": 0.5,
            "unnecessary_interruption_rate_max": 0.0,
            "missed_help_rate_max": 1.0,
        },
        step=0.5,
    )
    assert len(sweep) == 9
    assert any(item["meets_all_criteria"] for item in sweep)

    evidence = threshold_evidence(rows)
    assert evidence["unidentifiable_thresholds"] == ["react_threshold"]
    conservative = conservative_recommendation_pool(sweep, evidence)
    assert conservative
    assert all(item["react_threshold"] == 1.0 for item in conservative)


def test_report_shows_raw_counts_and_pending_status() -> None:
    metrics = compute_metrics(
        [
            {
                "id": "s1",
                "consensus": "REPLY",
                "raw_choice": "REPLY",
                "final_action": "REPLY",
                "confidence": 0.8,
                "decider_latency_ms": 12,
                "downgraded": False,
            },
            {
                "id": "s2",
                "consensus": "SILENT",
                "raw_choice": "SILENT",
                "final_action": "SILENT",
                "confidence": 0.7,
                "decider_latency_ms": 10,
                "downgraded": False,
            },
        ]
    )
    report = build_report(
        {
            "generated_at": "2026-10-15T00:00:00+00:00",
            "split": "tuning",
            "model_id": "model",
            "device": "cpu",
            "hardware": "test",
            "policy_mode": "unthresholded_tuning",
            "thresholds": {"reply_threshold": None, "react_threshold": None},
            "criteria": {
                "accuracy_min": 0.7,
                "unnecessary_interruption_rate_max": 0.2,
                "missed_help_rate_max": 0.25,
            },
            "context_metrics": {"3": metrics},
        }
    )
    assert "2/2 (100.0%)" in report
    assert "PENDING" in report
    assert "human choose thresholds" in report
