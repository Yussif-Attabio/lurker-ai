"""Exact M1 metric definitions with raw counts beside every rate."""

from __future__ import annotations

import math
from typing import Any, Iterable


def rate_metric(numerator: int, denominator: int) -> dict[str, float | int | None]:
    """Represent a rate with its numerator and denominator."""
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def percentile(values: Iterable[float], percentile_value: float) -> float | None:
    """Compute a linearly interpolated percentile for a finite sequence."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _accuracy(rows: list[dict[str, Any]], prediction_key: str) -> dict[str, float | int | None]:
    correct = sum(row.get(prediction_key) == row["consensus"] for row in rows)
    return rate_metric(correct, len(rows))


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _calibration(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definitions = [
        ("0.0-0.5", 0.0, 0.5, False),
        ("0.5-0.7", 0.5, 0.7, False),
        ("0.7-0.9", 0.7, 0.9, False),
        ("0.9-1.0", 0.9, 1.0, True),
    ]
    bins: list[dict[str, Any]] = []
    for label, low, high, inclusive_high in definitions:
        selected = [
            row
            for row in rows
            if float(row["confidence"]) >= low
            and (
                float(row["confidence"]) <= high
                if inclusive_high
                else float(row["confidence"]) < high
            )
        ]
        correct = sum(row["final_action"] == row["consensus"] for row in selected)
        bins.append({"bin": label, **rate_metric(correct, len(selected))})
    return bins


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute all specified metrics, excluding ambiguous cases from rates."""
    scored = [row for row in rows if row["consensus"] != "AMBIGUOUS"]
    ambiguous = [row for row in rows if row["consensus"] == "AMBIGUOUS"]
    silent = [row for row in scored if row["consensus"] == "SILENT"]
    reply = [row for row in scored if row["consensus"] == "REPLY"]
    downgraded = [row for row in scored if _as_bool(row.get("downgraded"))]

    interruptions = sum(row["final_action"] in {"REACT", "REPLY"} for row in silent)
    missed_help = sum(row["final_action"] in {"SILENT", "REACT"} for row in reply)
    predicted_react = [row for row in scored if row["final_action"] == "REACT"]
    actual_react = [row for row in scored if row["consensus"] == "REACT"]
    correct_react = sum(row["consensus"] == "REACT" for row in predicted_react)
    latencies = [float(row["decider_latency_ms"]) for row in rows]

    return {
        "total_count": len(rows),
        "non_ambiguous_count": len(scored),
        "ambiguous_count": len(ambiguous),
        "error_count": sum(bool(row.get("error")) for row in rows),
        "consensus_counts": {
            action: sum(row["consensus"] == action for row in scored)
            for action in ("SILENT", "REACT", "REPLY")
        },
        "prediction_counts": {
            action: sum(row.get("final_action") == action for row in rows)
            for action in ("SILENT", "REACT", "REPLY")
        },
        "accuracy": _accuracy(scored, "final_action"),
        "unnecessary_interruption_rate": rate_metric(interruptions, len(silent)),
        "missed_help_rate": rate_metric(missed_help, len(reply)),
        "react_precision": rate_metric(correct_react, len(predicted_react)),
        "react_recall": rate_metric(correct_react, len(actual_react)),
        "low_confidence": {
            "downgraded_count": len(downgraded),
            "before_accuracy": _accuracy(downgraded, "raw_choice"),
            "after_accuracy": _accuracy(downgraded, "final_action"),
        },
        "calibration": _calibration(scored),
        "latency_ms": {
            "count": len(latencies),
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
        },
        "ambiguous_predictions": [
            {
                "id": row["id"],
                "raw_choice": row.get("raw_choice"),
                "final_action": row.get("final_action"),
                "confidence": row.get("confidence"),
            }
            for row in ambiguous
        ],
    }


def meets_criteria(metrics: dict[str, Any], criteria: dict[str, float]) -> bool:
    """Return true only when every human-approved M1 criterion is measurable and met."""
    accuracy = metrics["accuracy"]["rate"]
    interruption = metrics["unnecessary_interruption_rate"]["rate"]
    missed_help = metrics["missed_help_rate"]["rate"]
    return (
        int(metrics.get("error_count", 0)) == 0
        and
        accuracy is not None
        and interruption is not None
        and missed_help is not None
        and accuracy >= criteria["accuracy_min"]
        and interruption <= criteria["unnecessary_interruption_rate_max"]
        and missed_help <= criteria["missed_help_rate_max"]
    )
