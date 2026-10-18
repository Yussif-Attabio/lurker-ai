"""Standalone orchestration wrapper for Lurker's frozen decision contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .lurker_gate import OPTIONS, QUESTION, apply_policy


class DecisionAdapter(Protocol):
    """Small adapter boundary required by :class:`ChimeInGate`."""

    def decide(
        self, state: dict[str, Any], question: str, options: Sequence[str]
    ) -> Any:
        """Return an object with choice, confidence, latency_ms, and error fields."""


@dataclass(frozen=True)
class GateDecision:
    """Policy result returned to a host application or Strands intervention."""

    action: str
    confidence: float | None
    downgraded: bool
    reason: str
    latency_ms: float
    raw_choice: str | None = None
    error: str | None = None


class ChimeInGate:
    """Apply the reusable SILENT/REACT/REPLY policy to recent chat state."""

    def __init__(
        self,
        adapter: DecisionAdapter,
        reply_threshold: float,
        react_threshold: float,
        k: int = 3,
    ) -> None:
        if k not in {0, 3, 5}:
            raise ValueError("k must be one of 0, 3, or 5")
        for name, value in (
            ("reply_threshold", reply_threshold),
            ("react_threshold", react_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        self.adapter = adapter
        self.reply_threshold = reply_threshold
        self.react_threshold = react_threshold
        self.k = k

    def decide(
        self,
        recent_messages: Sequence[dict[str, Any]],
        latest_message: dict[str, Any],
    ) -> GateDecision:
        """Return the gated action for one latest message."""
        recent = [] if self.k == 0 else list(recent_messages[-self.k :])
        state = {
            "agent_name": "Lurker",
            "recent_messages": [dict(message) for message in recent],
            "latest_message": dict(latest_message),
        }
        result = self.adapter.decide(state, QUESTION, OPTIONS)
        action, downgraded, reason = apply_policy(
            result,
            {
                "reply_threshold": self.reply_threshold,
                "react_threshold": self.react_threshold,
            },
        )
        return GateDecision(
            action=action,
            confidence=result.confidence,
            downgraded=downgraded,
            reason=reason,
            latency_ms=float(result.latency_ms),
            raw_choice=result.choice,
            error=result.error,
        )
