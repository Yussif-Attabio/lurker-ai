"""Local deterministic emoji selection for REACT decisions."""

from __future__ import annotations


class Reactor:
    """Choose a lightweight emoji without a model or network call."""

    KEYWORDS = (
        (("haha", "lol", "funny", "joke", "😂"), "😂"),
        (("congrats", "congratulations", "great news", "passed", "approved"), "🎉"),
        (("thanks", "thank you", "appreciate"), "🙏"),
        (("sorry", "tough", "support"), "❤️"),
    )

    def choose(self, text: str) -> str:
        """Return the first matching emoji or a neutral acknowledgment."""
        normalized = text.lower()
        for keywords, emoji in self.KEYWORDS:
            if any(keyword in normalized for keyword in keywords):
                return emoji
        return "👍"
