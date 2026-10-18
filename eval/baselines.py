"""Evaluation baselines; no baseline is invoked automatically."""

from __future__ import annotations

import os
import time
from typing import Any, Iterable

import boto3

from decision_pattern.lurker_gate import OPTIONS, QUESTION
from src.lurker.context import build_state
from src.lurker.schemas import Scenario


class BaselineError(RuntimeError):
    """A Bedrock judge request failed or returned an invalid decision."""

    def __init__(self, message: str, *, invoked: bool, latency_ms: float = 0.0) -> None:
        super().__init__(message)
        self.invoked = invoked
        self.latency_ms = latency_ms


def always_reply_to_questions(message: dict[str, str]) -> str:
    """Return REPLY for a question mark and SILENT otherwise."""
    return "REPLY" if "?" in message["text"] else "SILENT"


class BedrockJudge:
    """Bounded, injectable Converse judge used only by an approved M5 run."""

    def __init__(
        self,
        model_id: str,
        region: str,
        *,
        client: Any | None = None,
        max_calls: int = 15,
        max_prompt_bytes: int = 1000,
    ) -> None:
        if not model_id.strip() or not region.strip():
            raise ValueError("Bedrock judge requires non-empty model_id and region")
        if max_calls < 1:
            raise ValueError("Bedrock judge max_calls must be at least 1")
        if max_prompt_bytes < 1:
            raise ValueError("Bedrock judge max_prompt_bytes must be at least 1")
        self.model_id = model_id
        self.region = region
        self.client = client or boto3.client("bedrock-runtime", region_name=region)
        self.max_calls = max_calls
        self.max_prompt_bytes = max_prompt_bytes
        self.calls = 0

    def decide(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return one normalized action with latency and token accounting."""
        if self.calls >= self.max_calls:
            raise BaselineError("Bedrock judge call budget exhausted", invoked=False)
        prompt = (
            f"{QUESTION}\nOptions: {', '.join(OPTIONS)}\n"
            f"Conversation state: {state}\nReturn exactly one option."
        )
        prompt_bytes = len(prompt.encode("utf-8"))
        if prompt_bytes > self.max_prompt_bytes:
            raise BaselineError(
                f"Bedrock judge prompt exceeds {self.max_prompt_bytes} UTF-8 bytes",
                invoked=False,
            )
        self.calls += 1
        started = time.perf_counter()
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 8, "temperature": 0},
            )
            text = response["output"]["message"]["content"][0]["text"].strip().upper()
            if text not in OPTIONS:
                raise ValueError(f"invalid option: {text}")
            usage = response.get("usage", {})
            return {
                "choice": text,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "input_tokens": int(usage.get("inputTokens", 0)),
                "output_tokens": int(usage.get("outputTokens", 0)),
            }
        except BaselineError:
            raise
        except Exception as exc:
            raise BaselineError(
                f"Bedrock judge failed after invocation: {type(exc).__name__}: {exc}",
                invoked=True,
                latency_ms=(time.perf_counter() - started) * 1000,
            ) from exc


def bedrock_judge(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper for one explicitly configured Bedrock judge call."""
    model_id = os.getenv("BASELINE_MODEL_ID")
    region = os.getenv("AWS_REGION")
    if not model_id or not region:
        raise RuntimeError("Set BASELINE_MODEL_ID and AWS_REGION for the Bedrock baseline")
    return BedrockJudge(model_id, region, max_calls=1).decide(state)


def _baseline_row(scenario: Scenario, context_k: int, choice: str) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "split": scenario.split,
        "category": scenario.category,
        "context_k": context_k,
        "consensus": scenario.consensus,
        "raw_choice": choice,
        "confidence": 1.0,
        "final_action": choice,
        "downgraded": False,
        "reason": "baseline",
        "decider_latency_ms": 0.0,
        "error": "",
    }


def evaluate_question_mark_baseline(
    scenarios: Iterable[Scenario], context_k: int
) -> list[dict[str, Any]]:
    """Evaluate the required no-model punctuation baseline."""
    return [
        _baseline_row(
            scenario,
            context_k,
            always_reply_to_questions(scenario.message.model_dump()),
        )
        for scenario in scenarios
    ]


def evaluate_bedrock_baseline(
    scenarios: Iterable[Scenario], context_k: int, judge: BedrockJudge
) -> list[dict[str, Any]]:
    """Evaluate reviewed scenarios once each, preserving errors without retrying."""
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        state = build_state(
            [message.model_dump() for message in scenario.history],
            scenario.message.model_dump(),
            context_k,
        )
        try:
            result = judge.decide(state)
            row = _baseline_row(scenario, context_k, result["choice"])
            row.update(
                {
                    "decider_latency_ms": result["latency_ms"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                }
            )
        except BaselineError as exc:
            row = _baseline_row(scenario, context_k, "")
            row.update(
                {
                    "error": str(exc),
                    "decider_latency_ms": exc.latency_ms,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            )
        rows.append(row)
    return rows
