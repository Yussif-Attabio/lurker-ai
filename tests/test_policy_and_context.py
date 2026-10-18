"""Unit tests for policy branches and shared context construction."""

from __future__ import annotations

import pytest

from decision_pattern.lurker_gate import OPTIONS, QUESTION, apply_policy
from src.lurker.context import build_state
from src.lurker.schemas import DeciderResult

CFG = {"reply_threshold": 0.7, "react_threshold": 0.6}


def test_decision_wording_keeps_actions_distinct_and_general() -> None:
    assert OPTIONS == ["SILENT", "REACT", "REPLY"]
    assert "Choose REPLY only if someone needs an answer or help" in QUESTION
    assert "meaningfully acknowledge" in QUESTION
    assert "routine updates" in QUESTION
    assert "hackathon finals" not in QUESTION
    assert "accessibility review" not in QUESTION


def test_policy_covers_error_silent_confident_and_low_confidence() -> None:
    assert apply_policy(DeciderResult(error="timeout"), CFG) == (
        "SILENT",
        True,
        "decider_error",
    )
    assert apply_policy(DeciderResult(choice="SILENT", confidence=0.1), CFG) == (
        "SILENT",
        False,
        "chosen",
    )
    assert apply_policy(DeciderResult(choice="REPLY", confidence=0.7), CFG) == (
        "REPLY",
        False,
        "confident",
    )
    assert apply_policy(DeciderResult(choice="REACT", confidence=0.6), CFG) == (
        "REACT",
        False,
        "confident",
    )
    assert apply_policy(DeciderResult(choice="REPLY", confidence=0.69), CFG) == (
        "SILENT",
        True,
        "low_confidence",
    )
    assert apply_policy(DeciderResult(choice="REACT", confidence=0.59), CFG) == (
        "SILENT",
        True,
        "low_confidence",
    )


def test_policy_refuses_unset_human_threshold() -> None:
    with pytest.raises(ValueError, match="reply_threshold"):
        apply_policy(
            DeciderResult(choice="REPLY", confidence=0.9),
            {"reply_threshold": None, "react_threshold": None},
        )


@pytest.mark.parametrize("k, expected", [(0, []), (3, [3, 4, 5]), (5, [1, 2, 3, 4, 5])])
def test_build_state_context_windows(k: int, expected: list[int]) -> None:
    history = [{"sender": "Alex", "text": str(index)} for index in range(1, 6)]
    state = build_state(history, {"sender": "Lea", "text": "latest"}, k)
    assert [int(item["text"]) for item in state["recent_messages"]] == expected
    assert state["latest_message"] == {"sender": "Lea", "text": "latest"}


def test_build_state_rejects_unsupported_context() -> None:
    with pytest.raises(ValueError, match="0, 3, or 5"):
        build_state([], {"sender": "Lea", "text": "latest"}, 2)
