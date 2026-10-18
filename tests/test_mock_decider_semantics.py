"""Regression coverage for the deterministic mock Decider heuristics."""

from __future__ import annotations

import pytest

from src.lurker.mock_decider import MockDecider


def decide(message: str) -> str | None:
    result = MockDecider().decide(
        {"latest_message": {"text": message}},
        "Choose an action",
        ("SILENT", "REACT", "REPLY"),
    )
    return result.choice


@pytest.mark.parametrize(
    "message",
    (
        "is 401 safe",
        "is 401 safe?",
        "Can someone explain why the API returns 401",
        "what time is the meeting",
        "Does anyone know why this failed",
    ),
)
def test_questions_are_detected_with_or_without_punctuation(message: str) -> None:
    assert decide(message) == "REPLY"


@pytest.mark.parametrize(
    "message",
    (
        "We finally shipped the project! 🎉",
        "We finally shipped the project",
        "Thanks for the help",
        "Great news, the build passed",
    ),
)
def test_lightweight_positive_messages_are_reactable(message: str) -> None:
    assert decide(message) == "REACT"


@pytest.mark.parametrize(
    "message",
    (
        "The API returns 401.",
        "I know how the API works.",
        "Let's meet at four tomorrow.",
        "We bypassed authentication during the local test.",
        "Someone brought a lollipop to the meeting.",
    ),
)
def test_ordinary_statements_remain_silent(message: str) -> None:
    assert decide(message) == "SILENT"


def test_question_takes_priority_over_celebration_signal() -> None:
    assert decide("Did we finally ship the project 🎉") == "REPLY"
