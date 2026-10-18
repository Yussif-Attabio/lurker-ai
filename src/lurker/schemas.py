"""Typed contracts shared by Lurker's decision pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

Action = Literal["SILENT", "REACT", "REPLY"]
Consensus = Literal["SILENT", "REACT", "REPLY", "AMBIGUOUS"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ChatMessage(BaseModel):
    """One user or agent message in the live synthetic chat."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    ts: datetime = Field(default_factory=utc_now)
    is_agent: bool = False


class WebSocketMessage(BaseModel):
    """Validated client-to-server WebSocket payload."""

    type: Literal["message"]
    sender: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)


class DeciderResult(BaseModel):
    """Normalized result from Strands Decider."""

    choice: Action | None = None
    confidence: float = 0.0
    scores: dict[str, float] | None = None
    latency_ms: float = 0.0
    error: str | None = None
    raw: dict[str, Any] | None = None


class DecisionEvent(BaseModel):
    """Auditable result of processing one user message."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime = Field(default_factory=utc_now)
    message_id: str
    sender: str
    text: str
    context_k: int
    raw_choice: Action | None = None
    confidence: float = 0.0
    final_action: Action
    downgraded: bool
    reason: str
    decider_latency_ms: float = 0.0
    bedrock_latency_ms: float | None = None
    bedrock_input_tokens: int | None = None
    bedrock_output_tokens: int | None = None
    bedrock_called: bool = False
    direct_mention: bool = False
    mock: bool = False
    error: str | None = None


class ScenarioMessage(BaseModel):
    """A synthetic chat message used in human evaluation."""

    sender: str
    text: str


class Scenario(BaseModel):
    """A fully human-reviewed evaluation scenario."""

    id: str
    split: Literal["tuning", "heldout"]
    category: Literal[
        "direct_request",
        "joke",
        "technical_question",
        "ongoing_discussion",
        "already_answered",
        "mention",
        "casual",
        "ambiguous",
    ]
    history: list[ScenarioMessage]
    message: ScenarioMessage
    labels: dict[Literal["a1", "a2", "a3"], Action]
    consensus: Consensus
    notes: str = ""
