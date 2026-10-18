"""Offline M2 backend tests; no real Decider or Bedrock calls are allowed."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.lurker.api import create_app
from src.lurker.bedrock_replier import (
    BedrockReplier,
    BedrockReplyError,
    MockBedrockReplier,
)
from src.lurker.config import AppConfig, load_config
from src.lurker.context import ChatContext
from src.lurker.metrics import MetricsStore
from src.lurker.mock_decider import MockDecider
from src.lurker.pipeline import MessagePipeline
from src.lurker.reactor import Reactor
from src.lurker.schemas import ChatMessage, DeciderResult, DecisionEvent

MODEL_ID = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"


def app_config(tmp_path: Path, **overrides: Any) -> AppConfig:
    values: dict[str, Any] = {
        "context_k": 3,
        "decider_timeout_ms": 120000,
        "decider_model_id": MODEL_ID,
        "decider_device": "cpu",
        "reply_threshold": 0.20,
        "react_threshold": 0.04,
        "force_reply_on_mention": False,
        "mock_decider": True,
        "data_dir": tmp_path / "data",
        "results_dir": tmp_path / "results",
    }
    values.update(overrides)
    return AppConfig.model_validate(values)


def test_config_loads_environment_overrides_and_validates_runtime(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "context_k: 3",
                "decider_timeout_ms: 1000",
                f"decider_model_id: {MODEL_ID}",
                "decider_device: cpu",
                "reply_threshold: null",
                "react_threshold: null",
                "force_reply_on_mention: false",
            ]
        )
        + "\n"
    )
    config = load_config(
        config_path,
        {
            "MOCK_DECIDER": "true",
            "REPLY_THRESHOLD": "0.2",
            "REACT_THRESHOLD": "0.04",
            "LURKER_DATA_DIR": str(tmp_path / "runtime"),
        },
    )
    config.require_runtime_ready()
    assert config.mock_decider is True
    assert config.policy_config() == {
        "reply_threshold": 0.2,
        "react_threshold": 0.04,
    }
    assert config.data_dir == tmp_path / "runtime"

    unsafe = config.model_copy(
        update={
            "mock_decider": False,
            "bedrock_model_id": None,
            "aws_region": None,
        }
    )
    with pytest.raises(ValueError, match="BEDROCK_MODEL_ID"):
        unsafe.require_runtime_ready()


def test_mock_decider_context_and_reactor_are_deterministic() -> None:
    decider = MockDecider()
    base = {"recent_messages": [], "agent_name": "Lurker"}
    assert decider.decide(
        {**base, "latest_message": {"sender": "A", "text": "Can you help?"}},
        "question",
        ["SILENT", "REACT", "REPLY"],
    ).choice == "REPLY"
    assert decider.decide(
        {**base, "latest_message": {"sender": "A", "text": "Great news!"}},
        "question",
        ["SILENT", "REACT", "REPLY"],
    ).choice == "REACT"
    assert decider.decide(
        {**base, "latest_message": {"sender": "A", "text": "Meet at four."}},
        "question",
        ["SILENT", "REACT", "REPLY"],
    ).choice == "SILENT"
    reactor = Reactor()
    assert reactor.choose("Congratulations, we passed!") == "🎉"
    assert reactor.choose("ordinary acknowledgment") == "👍"


def test_chat_context_is_bounded_and_resettable() -> None:
    async def exercise() -> None:
        context = ChatContext(max_messages=5)
        for index in range(7):
            await context.append(ChatMessage(sender="A", text=str(index)))
        assert [message.text for message in await context.messages()] == [
            "2",
            "3",
            "4",
            "5",
            "6",
        ]
        await context.reset()
        assert await context.messages() == []

    asyncio.run(exercise())


class FakeBedrockClient:
    def __init__(self, response: dict[str, Any] | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def test_bedrock_replier_parses_converse_and_normalizes_errors() -> None:
    client = FakeBedrockClient(
        {
            "output": {"message": {"content": [{"text": "Use a fresh token."}]}},
            "usage": {"inputTokens": 31, "outputTokens": 6},
        }
    )
    replier = BedrockReplier(
        "model",
        "us-east-2",
        client=client,
        max_calls=1,
        allowed_latest_text="Why 401?",
    )
    text, latency, input_tokens, output_tokens = replier.reply(
        {"recent_messages": [], "latest_message": {"sender": "A", "text": "Why 401?"}}
    )
    assert text == "Use a fresh token."
    assert latency >= 0
    assert (input_tokens, output_tokens) == (31, 6)
    assert client.requests[0]["modelId"] == "model"
    assert replier.calls == 1
    assert "latest_message" in client.requests[0]["messages"][0]["content"][0]["text"]

    failing = BedrockReplier(
        "model", "us-east-2", client=FakeBedrockClient(error=RuntimeError("denied"))
    )
    with pytest.raises(BedrockReplyError, match="RuntimeError"):
        failing.reply({"recent_messages": [], "latest_message": {}})


def test_bedrock_replier_enforces_message_and_call_budget() -> None:
    response = {
        "output": {"message": {"content": [{"text": "Answer"}]}},
        "usage": {"inputTokens": 1, "outputTokens": 1},
    }
    client = FakeBedrockClient(response)
    replier = BedrockReplier(
        "model",
        "us-east-2",
        client=client,
        max_calls=1,
        allowed_latest_text="Approved question?",
    )
    with pytest.raises(BedrockReplyError) as unauthorized:
        replier.reply(
            {"recent_messages": [], "latest_message": {"text": "Wrong question?"}}
        )
    assert unauthorized.value.invoked is False
    assert replier.calls == 0
    replier.reply(
        {"recent_messages": [], "latest_message": {"text": "Approved question?"}}
    )
    with pytest.raises(BedrockReplyError) as exhausted:
        replier.reply(
            {"recent_messages": [], "latest_message": {"text": "Approved question?"}}
        )
    assert exhausted.value.invoked is False
    assert replier.calls == 1
    assert len(client.requests) == 1


def event(action: str, latency: float, **overrides: Any) -> DecisionEvent:
    values: dict[str, Any] = {
        "message_id": f"m-{action}-{latency}",
        "sender": "A",
        "text": "test",
        "context_k": 3,
        "raw_choice": action,
        "confidence": 0.9,
        "final_action": action,
        "downgraded": False,
        "reason": "confident",
        "decider_latency_ms": latency,
    }
    values.update(overrides)
    return DecisionEvent.model_validate(values)


def test_metrics_store_counters_latency_and_rotation(tmp_path: Path) -> None:
    store = MetricsStore(tmp_path)
    original_path = store.path
    store.record(event("SILENT", 10))
    store.record(event("REACT", 20, downgraded=True))
    store.record(event("REPLY", 30, error="bedrock_error", bedrock_called=True))
    assert store.counters() == {
        "messages_read": 3,
        "silent": 1,
        "react": 1,
        "reply": 1,
        "downgraded": 1,
        "errors": 1,
        "bedrock_calls_made": 1,
        "bedrock_calls_avoided_vs_every_message": 2,
    }
    assert store.latency() == {"count": 3, "p50": 20.0, "p95": 29.0}
    rotated = store.reset()
    assert original_path.exists() and rotated.exists() and original_path != rotated
    assert store.counters()["messages_read"] == 0
    assert len(original_path.read_text().splitlines()) == 3


class StaticAdapter:
    mock = True

    def __init__(self, result: DeciderResult) -> None:
        self.result = result

    def decide(self, state: dict[str, Any], question: str, options: list[str]) -> DeciderResult:
        del state, question, options
        return self.result

    def warmup(self) -> DeciderResult:
        return DeciderResult(choice="SILENT", confidence=0.9)


class TrackingReplier(MockBedrockReplier):
    pass


@pytest.mark.parametrize(
    ("choice", "expected_calls", "event_type"),
    [("SILENT", 0, None), ("REACT", 0, "reaction"), ("REPLY", 1, "chat")],
)
def test_pipeline_routes_each_action_without_extra_bedrock_calls(
    tmp_path: Path, choice: str, expected_calls: int, event_type: str | None
) -> None:
    async def exercise() -> None:
        output: list[dict[str, Any]] = []

        async def broadcast(payload: dict[str, Any]) -> None:
            output.append(payload)

        replier = TrackingReplier("[MOCK] useful answer")
        pipeline = MessagePipeline(
            config=app_config(tmp_path),
            adapter=StaticAdapter(
                DeciderResult(choice=choice, confidence=0.9, latency_ms=4)
            ),
            replier=replier,
            context=ChatContext(),
            metrics=MetricsStore(tmp_path / choice.lower()),
            broadcast=broadcast,
        )
        task = await pipeline.process_message(
            ChatMessage(sender="Alex", text="Great news" if choice == "REACT" else "Test")
        )
        decision = await task
        assert decision.final_action == choice
        assert replier.calls == expected_calls
        if event_type == "reaction":
            assert any(item["type"] == "reaction" for item in output)
        elif event_type == "chat":
            assert sum(item["type"] == "chat" for item in output) == 2
        else:
            assert not any(item["type"] == "reaction" for item in output)
            assert sum(item["type"] == "chat" for item in output) == 1

    asyncio.run(exercise())


def test_pipeline_decider_error_fails_closed_without_bedrock(tmp_path: Path) -> None:
    async def exercise() -> None:
        replier = TrackingReplier()
        pipeline = MessagePipeline(
            config=app_config(tmp_path),
            adapter=StaticAdapter(DeciderResult(error="timeout", latency_ms=5)),
            replier=replier,
            context=ChatContext(),
            metrics=MetricsStore(tmp_path / "error"),
        )
        task = await pipeline.process_message(ChatMessage(sender="Lea", text="Help?"))
        decision = await task
        assert decision.final_action == "SILENT"
        assert decision.reason == "decider_error"
        assert decision.error == "timeout"
        assert replier.calls == 0

    asyncio.run(exercise())


def test_api_websocket_contract_and_rest_metrics(tmp_path: Path) -> None:
    cfg = app_config(tmp_path)
    cfg.results_dir.mkdir(parents=True)
    result_dir = cfg.results_dir / "test-run"
    result_dir.mkdir()
    (result_dir / "results.json").write_text(json.dumps({"run": "real-evidence"}))
    replier = TrackingReplier("[MOCK] Check the expired token.")
    app = create_app(config=cfg, adapter=MockDecider(), replier=replier)

    with TestClient(app) as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "decider_mode": "mock",
            "model_ready": True,
        }
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "message", "sender": "Alex", "text": "Meet at four."})
            silent = [websocket.receive_json() for _ in range(3)]
            assert [item["type"] for item in silent] == ["chat", "decision", "metrics"]
            assert silent[1]["final_action"] == "SILENT"

            websocket.send_json({"type": "message", "sender": "Lea", "text": "Great news!"})
            react = [websocket.receive_json() for _ in range(4)]
            assert [item["type"] for item in react] == [
                "chat",
                "reaction",
                "decision",
                "metrics",
            ]
            assert react[2]["final_action"] == "REACT"

            websocket.send_json({"type": "message", "sender": "Alex", "text": "Why a 401?"})
            reply = [websocket.receive_json() for _ in range(4)]
            assert [item["type"] for item in reply] == [
                "chat",
                "chat",
                "decision",
                "metrics",
            ]
            assert reply[1]["is_agent"] is True
            assert reply[2]["final_action"] == "REPLY"

        metrics = client.get("/api/metrics").json()
        assert metrics["counters"]["messages_read"] == 3
        assert metrics["counters"]["bedrock_calls_made"] == 0
        assert len(client.get("/api/decisions").json()) == 3
        evaluation = client.get("/api/eval/latest")
        assert evaluation.status_code == 404
        assert evaluation.json()["detail"] == "no evaluation results found"
        reset = client.post("/api/reset")
        assert reset.status_code == 200
        assert client.get("/api/metrics").json()["counters"]["messages_read"] == 0
