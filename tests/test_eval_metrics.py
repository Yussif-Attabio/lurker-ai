"""Hand-computed tests for the exact evaluation metric definitions."""

from __future__ import annotations

import pytest

from eval.metrics_def import compute_metrics, meets_criteria, percentile


def row(
    scenario_id: str,
    consensus: str,
    raw_choice: str,
    final_action: str,
    confidence: float,
    latency: float,
    downgraded: bool = False,
) -> dict:
    return {
        "id": scenario_id,
        "consensus": consensus,
        "raw_choice": raw_choice,
        "final_action": final_action,
        "confidence": confidence,
        "decider_latency_ms": latency,
        "downgraded": downgraded,
    }


def test_metrics_match_hand_computed_counts() -> None:
    metrics = compute_metrics(
        [
            row("s1", "SILENT", "REPLY", "SILENT", 0.4, 10, True),
            row("s2", "SILENT", "REACT", "REACT", 0.8, 20),
            row("s3", "REPLY", "REPLY", "REPLY", 0.9, 30),
            row("s4", "REPLY", "REPLY", "SILENT", 0.6, 40, True),
            row("s5", "AMBIGUOUS", "SILENT", "SILENT", 0.2, 50),
        ]
    )

    assert metrics["total_count"] == 5
    assert metrics["non_ambiguous_count"] == 4
    assert metrics["ambiguous_count"] == 1
    assert metrics["accuracy"] == {"numerator": 2, "denominator": 4, "rate": 0.5}
    assert metrics["unnecessary_interruption_rate"] == {
        "numerator": 1,
        "denominator": 2,
        "rate": 0.5,
    }
    assert metrics["missed_help_rate"] == {"numerator": 1, "denominator": 2, "rate": 0.5}
    assert metrics["low_confidence"]["downgraded_count"] == 2
    assert metrics["low_confidence"]["before_accuracy"]["rate"] == 0.5
    assert metrics["low_confidence"]["after_accuracy"]["rate"] == 0.5
    assert [bucket["rate"] for bucket in metrics["calibration"]] == [1.0, 0.0, 0.0, 1.0]
    assert metrics["latency_ms"] == {"count": 5, "p50": 30.0, "p95": 48.0}
    assert metrics["react_precision"] == {
        "numerator": 0,
        "denominator": 1,
        "rate": 0.0,
    }
    assert metrics["react_recall"] == {
        "numerator": 0,
        "denominator": 0,
        "rate": None,
    }
    assert metrics["ambiguous_predictions"] == [
        {"id": "s5", "raw_choice": "SILENT", "final_action": "SILENT", "confidence": 0.2}
    ]


def test_empty_class_rates_are_explicitly_unavailable() -> None:
    metrics = compute_metrics([row("s1", "REACT", "REACT", "REACT", 0.7, 4)])
    assert metrics["react_precision"] == {
        "numerator": 1,
        "denominator": 1,
        "rate": 1.0,
    }
    assert metrics["react_recall"] == {
        "numerator": 1,
        "denominator": 1,
        "rate": 1.0,
    }
    assert metrics["unnecessary_interruption_rate"] == {
        "numerator": 0,
        "denominator": 0,
        "rate": None,
    }
    assert metrics["missed_help_rate"]["rate"] is None
    assert not meets_criteria(
        metrics,
        {
            "accuracy_min": 0.7,
            "unnecessary_interruption_rate_max": 0.2,
            "missed_help_rate_max": 0.25,
        },
    )


def test_percentile_edge_cases() -> None:
    assert percentile([], 0.95) is None
    assert percentile([7], 0.95) == 7
    assert percentile([0, 10], 0.5) == 5
