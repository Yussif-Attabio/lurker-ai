"""Deterministic Decider substitute for UI work and offline tests only."""

from __future__ import annotations

import re
from typing import Any, Sequence

from .schemas import DeciderResult


_QUESTION_OPENERS = frozenset(
    {
        "am",
        "are",
        "can",
        "could",
        "did",
        "do",
        "does",
        "had",
        "has",
        "have",
        "how",
        "is",
        "may",
        "might",
        "should",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "whose",
        "why",
        "will",
        "would",
    }
)

_QUESTION_PHRASES = (
    "any idea",
    "can anyone",
    "can someone",
    "could anyone",
    "could someone",
    "do you know",
    "does anyone",
    "help me",
    "i need help",
    "please explain",
)

_REACTION_SIGNALS = (
    "appreciate it",
    "congratulations",
    "congrats",
    "finally launched",
    "finally released",
    "finally shipped",
    "funny",
    "great news",
    "haha",
    "lol",
    "passed",
    "thank you",
    "thanks",
    "we did it",
    "😂",
    "🎉",
)


def _looks_like_question(text: str) -> bool:
    """Recognize direct questions and help requests without requiring punctuation."""
    normalized = " ".join(text.lower().strip().split())
    if not normalized:
        return False
    if "?" in normalized:
        return True

    first_word = normalized.split(maxsplit=1)[0].strip("\"'([{“‘")
    if first_word in _QUESTION_OPENERS:
        return True

    return any(
        normalized == phrase or normalized.startswith(f"{phrase} ")
        for phrase in _QUESTION_PHRASES
    )


def _looks_reactable(text: str) -> bool:
    """Recognize lightweight gratitude, humor, and celebration messages."""
    normalized = " ".join(text.lower().strip().split())
    return any(
        re.search(rf"(?<!\w){re.escape(signal)}(?!\w)", normalized)
        for signal in _REACTION_SIGNALS
    )


class MockDecider:
    """Return fixed-confidence semantic decisions without model inference."""

    mock = True

    def decide(
        self, state: dict[str, Any], question: str, options: Sequence[str]
    ) -> DeciderResult:
        del question, options
        text = str(state["latest_message"]["text"])
        if "[decider-error]" in text.lower():
            return DeciderResult(error="mock_error", latency_ms=0.1)
        if _looks_like_question(text):
            choice = "REPLY"
        elif _looks_reactable(text):
            choice = "REACT"
        else:
            choice = "SILENT"
        scores = {item: 0.05 for item in ("SILENT", "REACT", "REPLY")}
        scores[choice] = 0.90
        return DeciderResult(
            choice=choice,
            confidence=0.90,
            scores=scores,
            latency_ms=0.1,
            raw={"mock": True},
        )

    def warmup(self) -> DeciderResult:
        """Return a harmless mock warmup result."""
        return DeciderResult(choice="SILENT", confidence=0.90, latency_ms=0.1)
