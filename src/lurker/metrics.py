"""Append-only runtime decision storage and derived counters."""

from __future__ import annotations

import json
import math
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .schemas import DecisionEvent


def _percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


class MetricsStore:
    """Keep runtime events in memory and append every event to JSONL."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[DecisionEvent] = []
        self._lock = threading.RLock()
        self._path = self.data_dir / "decisions.jsonl"
        self._path.touch(exist_ok=True)

    @property
    def path(self) -> Path:
        """Return the active append-only file."""
        return self._path

    def record(self, event: DecisionEvent) -> None:
        """Append one event to memory and durable JSONL."""
        encoded = event.model_dump_json()
        with self._lock:
            with self._path.open("a", encoding="utf-8") as stream:
                stream.write(encoded + "\n")
            self._events.append(event)

    def recent(self, limit: int = 50) -> list[DecisionEvent]:
        """Return recent events newest first."""
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock:
            return list(reversed(self._events[-limit:]))

    def counters(self) -> dict[str, int]:
        """Compute the exact live counters from recorded events."""
        with self._lock:
            events = list(self._events)
        bedrock_calls = sum(event.bedrock_called for event in events)
        return {
            "messages_read": len(events),
            "silent": sum(event.final_action == "SILENT" for event in events),
            "react": sum(event.final_action == "REACT" for event in events),
            "reply": sum(event.final_action == "REPLY" for event in events),
            "downgraded": sum(event.downgraded for event in events),
            "errors": sum(event.error is not None for event in events),
            "bedrock_calls_made": bedrock_calls,
            "bedrock_calls_avoided_vs_every_message": len(events) - bedrock_calls,
        }

    def latency(self) -> dict[str, float | int | None]:
        """Return Decider latency count, p50, and p95."""
        with self._lock:
            values = [event.decider_latency_ms for event in self._events]
        return {
            "count": len(values),
            "p50": _percentile(values, 0.50),
            "p95": _percentile(values, 0.95),
        }

    def snapshot(self) -> dict[str, object]:
        """Return counters and latency for the metrics endpoint."""
        return {"counters": self.counters(), "decider_latency_ms": self.latency()}

    def reset(self) -> Path:
        """Clear memory and rotate to a new file without deleting history."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        with self._lock:
            self._events.clear()
            self._path = self.data_dir / f"decisions-{stamp}.jsonl"
            self._path.touch(exist_ok=False)
            return self._path
