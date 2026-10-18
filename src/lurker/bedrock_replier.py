"""Amazon Bedrock Converse wrapper used only for final REPLY actions."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import boto3

SYSTEM_PROMPT = (
    "You are Lurker, a quiet teammate in a group chat. Answer only what was asked, "
    "in at most two short sentences. Do not repeat what others already said. If you "
    "are unsure, say so briefly. Never invent project facts you were not given."
)


class BedrockReplyError(RuntimeError):
    """A normalized Bedrock failure with measured elapsed time."""

    def __init__(self, message: str, latency_ms: float, *, invoked: bool) -> None:
        super().__init__(message)
        self.latency_ms = latency_ms
        self.invoked = invoked


class BedrockReplier:
    """Generate one short reply through Bedrock Runtime Converse."""

    mock = False

    def __init__(
        self,
        model_id: str,
        region: str,
        client: Any | None = None,
        *,
        max_calls: int | None = None,
        allowed_latest_text: str | None = None,
    ) -> None:
        if not model_id or not region:
            raise ValueError("BEDROCK_MODEL_ID and AWS_REGION are required")
        if max_calls is not None and max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        self.model_id = model_id
        self.region = region
        self.max_calls = max_calls
        self.allowed_latest_text = allowed_latest_text
        self._client = client or boto3.client("bedrock-runtime", region_name=region)
        self._calls = 0
        self._lock = threading.Lock()

    @property
    def calls(self) -> int:
        """Return the number of reserved real Converse invocations."""
        with self._lock:
            return self._calls

    def _reserve_call(self) -> None:
        with self._lock:
            if self.max_calls is not None and self._calls >= self.max_calls:
                raise BedrockReplyError(
                    "Bedrock invocation budget exhausted", 0.0, invoked=False
                )
            self._calls += 1

    def reply(self, state: dict[str, Any]) -> tuple[str, float, int, int]:
        """Return generated text, latency, input tokens, and output tokens."""
        latest_text = str(state.get("latest_message", {}).get("text", ""))
        if (
            self.allowed_latest_text is not None
            and latest_text != self.allowed_latest_text
        ):
            raise BedrockReplyError(
                "latest message is not authorized for Bedrock invocation",
                0.0,
                invoked=False,
            )
        prompt = (
            "Conversation state:\n"
            + json.dumps(state, ensure_ascii=False, separators=(",", ":"))
            + "\nWrite Lurker's reply."
        )
        self._reserve_call()
        started = time.perf_counter()
        try:
            response = self._client.converse(
                modelId=self.model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 160, "temperature": 0.2},
            )
            latency_ms = (time.perf_counter() - started) * 1000
            text = str(response["output"]["message"]["content"][0]["text"]).strip()
            usage = response["usage"]
            input_tokens = int(usage["inputTokens"])
            output_tokens = int(usage["outputTokens"])
            if not text:
                raise ValueError("empty Bedrock reply")
            return text, latency_ms, input_tokens, output_tokens
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            raise BedrockReplyError(
                f"{type(exc).__name__}: {exc}", latency_ms, invoked=True
            ) from exc


class MockBedrockReplier:
    """Offline-only replier that is visibly mock and never calls AWS."""

    mock = True

    def __init__(self, text: str = "[MOCK] Here is a short test reply.") -> None:
        self.text = text
        self.calls = 0

    def reply(self, state: dict[str, Any]) -> tuple[str, float, int, int]:
        del state
        self.calls += 1
        return self.text, 0.1, 0, 0
