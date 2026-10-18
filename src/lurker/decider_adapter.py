"""The only module allowed to import and call Strands Decider."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Sequence

from strands_decider.infer import SystemOneEngine, load_engine
from strands_decider.schema import ChoiceQuestion

from .schemas import DeciderResult

VALID_CHOICES = {"SILENT", "REACT", "REPLY"}


def normalize_choice_answer(answer: Any, latency_ms: float) -> DeciderResult:
    """Normalize an official ChoiceAnswer; fail closed on any unexpected shape."""
    try:
        raw = answer.model_dump(mode="json")
        choice = str(raw.get("choice", "")).upper()
        confidence = float(raw["confidence"])
        probabilities = raw["probabilities"]
        scores = {str(key): float(value) for key, value in probabilities.items()}
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return DeciderResult(
            latency_ms=latency_ms,
            error=f"unparseable_response: {type(exc).__name__}",
        )
    if choice not in VALID_CHOICES:
        return DeciderResult(latency_ms=latency_ms, error="unparseable_choice", raw=raw)
    if not 0.0 <= confidence <= 1.0:
        return DeciderResult(latency_ms=latency_ms, error="invalid_confidence", raw=raw)
    return DeciderResult(
        choice=choice,
        confidence=confidence,
        scores=scores,
        latency_ms=latency_ms,
        raw=raw,
    )


class DeciderAdapter:
    """Load one real Decider engine and normalize its typed choice response."""

    def __init__(self, model_id: str, device: str, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms
        self._engine: SystemOneEngine = load_engine(model_id, device=device)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="decider")

    def decide(
        self, state: dict[str, Any], question: str, options: Sequence[str]
    ) -> DeciderResult:
        """Run one structured choice question with a safe, normalized result."""
        criteria = {option: None for option in options}
        typed_question = ChoiceQuestion(instructions=question, criteria=criteria)
        started = time.perf_counter()
        future = self._pool.submit(self._engine.ask, state, {"action": typed_question})
        try:
            response = future.result(timeout=self.timeout_ms / 1000)
        except FutureTimeoutError:
            return DeciderResult(
                latency_ms=(time.perf_counter() - started) * 1000,
                error="timeout",
            )
        except Exception as exc:  # the safe default is handled by policy later
            return DeciderResult(
                latency_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
            )

        latency_ms = (time.perf_counter() - started) * 1000
        try:
            answer = response.answers["action"]
        except (AttributeError, KeyError, TypeError) as exc:
            return DeciderResult(
                latency_ms=latency_ms,
                error=f"unparseable_response: {type(exc).__name__}",
            )
        return normalize_choice_answer(answer, latency_ms)

    def warmup(self) -> DeciderResult:
        """Compile/cache the model path with one harmless request."""
        return self.decide(
            {"agent_name": "Lurker", "recent_messages": [], "latest_message": {"sender": "System", "text": "Warm up."}},
            "Should Lurker stay silent, react, or reply?",
            ["SILENT", "REACT", "REPLY"],
        )
