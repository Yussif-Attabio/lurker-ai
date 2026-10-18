"""Offline tests for the safe Decider response boundary."""

from __future__ import annotations

from typing import Any

import pytest

from src.lurker.decider_adapter import normalize_choice_answer


class FakeAnswer:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self.payload


@pytest.mark.parametrize("choice", ["SILENT", "REACT", "REPLY"])
def test_normalizes_each_valid_choice(choice: str) -> None:
    result = normalize_choice_answer(
        FakeAnswer(
            {
                "choice": choice.lower(),
                "confidence": 0.75,
                "probabilities": {"SILENT": 0.1, "REACT": 0.15, "REPLY": 0.75},
            }
        ),
        12.5,
    )
    assert result.choice == choice
    assert result.confidence == 0.75
    assert result.latency_ms == 12.5
    assert result.error is None


def test_unexpected_choice_fails_closed() -> None:
    result = normalize_choice_answer(
        FakeAnswer(
            {"choice": "ANSWER", "confidence": 0.9, "probabilities": {"ANSWER": 0.9}}
        ),
        1.0,
    )
    assert result.choice is None
    assert result.error == "unparseable_choice"


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_out_of_range_confidence_is_an_error(confidence: float) -> None:
    result = normalize_choice_answer(
        FakeAnswer(
            {
                "choice": "SILENT",
                "confidence": confidence,
                "probabilities": {"SILENT": 1.0},
            }
        ),
        1.0,
    )
    assert result.choice is None
    assert result.error == "invalid_confidence"


def test_malformed_answer_is_an_error() -> None:
    result = normalize_choice_answer(object(), 1.0)
    assert result.choice is None
    assert result.error == "unparseable_response: AttributeError"

