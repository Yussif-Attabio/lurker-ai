"""Official Strands intervention wiring for the reusable Chime-In gate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from strands.interventions import Deny, InterventionHandler, Proceed

from .chime_in_gate import ChimeInGate, GateDecision

StateProvider = Callable[[Any], tuple[list[dict[str, str]], dict[str, str]]]


def state_from_invocation(event: Any) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Convert human-readable Strands input messages to Lurker chat state."""
    rendered: list[dict[str, str]] = []
    for message in event.messages or []:
        sender = str(message.get("role", "participant"))
        text = " ".join(
            str(block["text"])
            for block in message.get("content", [])
            if isinstance(block, dict) and block.get("text")
        ).strip()
        if text:
            rendered.append({"sender": sender, "text": text})
    if not rendered:
        return [], {"sender": "participant", "text": ""}
    return rendered[:-1], rendered[-1]


class ChimeInIntervention(InterventionHandler):
    """Run Lurker before a Strands model call and fail closed on non-REPLY."""

    name = "lurker-chime-in-gate"

    def __init__(
        self,
        gate: ChimeInGate,
        state_provider: StateProvider = state_from_invocation,
    ) -> None:
        self.gate = gate
        self.state_provider = state_provider
        self.last_decision: GateDecision | None = None

    @property
    def on_error(self) -> str:
        """Convert handler failures to a typed Deny rather than fail open."""
        return "deny"

    def before_invocation(self, event: Any, **kwargs: Any) -> Proceed | Deny:
        """Allow Bedrock only for REPLY; expose other actions to the host."""
        del kwargs
        recent, latest = self.state_provider(event)
        decision = self.gate.decide(recent, latest)
        self.last_decision = decision
        if decision.action == "REPLY":
            return Proceed(reason="Lurker selected REPLY")
        if decision.action == "REACT":
            return Deny(
                reason=(
                    "Lurker selected REACT; skip text generation and let the host "
                    "render one local emoji reaction"
                )
            )
        return Deny(reason="Lurker selected SILENT; skip text generation")
