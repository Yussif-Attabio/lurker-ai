"""Pure context construction shared by evaluation and the future live pipeline."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Sequence

from .schemas import ChatMessage


def build_state(
    history: Sequence[dict[str, Any]], latest_message: dict[str, Any], k: int
) -> dict[str, Any]:
    """Build the documented Decider state using the last `k` messages."""
    if k not in {0, 3, 5}:
        raise ValueError("context k must be one of 0, 3, or 5")
    recent = [] if k == 0 else list(history[-k:])
    return {
        "agent_name": "Lurker",
        "recent_messages": recent,
        "latest_message": dict(latest_message),
    }


class ChatContext:
    """Bounded one-room message history used by the live pipeline."""

    def __init__(self, max_messages: int = 200) -> None:
        if max_messages < 5:
            raise ValueError("max_messages must be at least 5")
        self._messages: deque[ChatMessage] = deque(maxlen=max_messages)
        self._lock = asyncio.Lock()

    async def append(self, message: ChatMessage) -> list[dict[str, Any]]:
        """Append a message and return a frozen copy of the preceding history."""
        async with self._lock:
            history = [
                {"sender": item.sender, "text": item.text}
                for item in self._messages
            ]
            self._messages.append(message)
            return history

    async def messages(self) -> list[ChatMessage]:
        """Return the current bounded history oldest first."""
        async with self._lock:
            return list(self._messages)

    async def reset(self) -> None:
        """Clear the in-memory room history."""
        async with self._lock:
            self._messages.clear()
