#!/usr/bin/env python3
"""Run deterministic, offline M6 reliability drills and save auditable evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient

from src.lurker.api import create_app
from src.lurker.bedrock_replier import BedrockReplyError, MockBedrockReplier
from src.lurker.config import AppConfig
from src.lurker.mock_decider import MockDecider
from src.lurker.schemas import DeciderResult

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "m6_local_verification"
MODEL_ID = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"


class InjectedAdapter:
    """Return one deterministic result without loading or calling a model."""

    mock = True

    def __init__(self, result: DeciderResult) -> None:
        self.result = result
        self.calls = 0

    def warmup(self) -> DeciderResult:
        return DeciderResult(choice="SILENT", confidence=1.0)

    def decide(
        self, state: dict[str, Any], question: str, options: list[str]
    ) -> DeciderResult:
        del state, question, options
        self.calls += 1
        return self.result.model_copy(deep=True)


class InjectedBedrockFailure:
    """Fail before any provider call while counting the single attempted reply."""

    mock = True

    def __init__(self) -> None:
        self.attempts = 0

    def reply(self, state: dict[str, Any]) -> tuple[str, float, int, int]:
        del state
        self.attempts += 1
        raise BedrockReplyError(
            "injected_m6_bedrock_error", 7.5, invoked=False
        )


def _config(data_dir: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "context_k": 3,
            "decider_timeout_ms": 120000,
            "decider_model_id": MODEL_ID,
            "decider_device": "cpu",
            "reply_threshold": 0.20,
            "react_threshold": 0.04,
            "force_reply_on_mention": False,
            "mock_decider": True,
            "data_dir": data_dir,
            "results_dir": data_dir / "unused-results",
        }
    )


def _collect_one(websocket: Any, message: dict[str, str]) -> list[dict[str, Any]]:
    websocket.send_json(message)
    events: list[dict[str, Any]] = []
    for _ in range(8):
        event = websocket.receive_json()
        events.append(event)
        if event.get("type") == "metrics":
            return events
    raise AssertionError("message did not produce a metrics event within eight events")


def _event_keys(events: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for event in events:
        event_type = event.get("type")
        if event_type == "chat":
            keys.append(f"chat:{event.get('id')}")
        elif event_type == "decision":
            keys.append(f"decision:{event.get('message_id')}")
        elif event_type == "reaction":
            keys.append(
                f"reaction:{event.get('message_id')}:{event.get('emoji')}"
            )
    return keys


def _assert_unique(events: list[dict[str, Any]]) -> None:
    keys = _event_keys(events)
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise AssertionError(f"duplicate live events: {duplicates}")


def _snapshot(client: TestClient) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = client.get("/api/metrics").json()
    decisions = client.get("/api/decisions?limit=50").json()
    return metrics, decisions


def _log_rows(app: Any) -> list[dict[str, Any]]:
    path = app.state.metrics.path
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def decider_timeout_drill(runtime_dir: Path) -> dict[str, Any]:
    adapter = InjectedAdapter(DeciderResult(error="timeout", latency_ms=12.5))
    replier = MockBedrockReplier()
    app = create_app(config=_config(runtime_dir), adapter=adapter, replier=replier)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            events = _collect_one(
                websocket,
                {"type": "message", "sender": "Lea", "text": "Can you help?"},
            )
        _assert_unique(events)
        metrics, decisions = _snapshot(client)
        rows = _log_rows(app)
        health = client.get("/health").json()

    decision = decisions[0]
    assertions = {
        "one_decider_call": adapter.calls == 1,
        "safe_final_action": decision["final_action"] == "SILENT",
        "timeout_recorded": decision["error"] == "timeout",
        "reason_is_decider_error": decision["reason"] == "decider_error",
        "zero_reply_attempts": replier.calls == 0,
        "zero_real_bedrock_calls": metrics["counters"]["bedrock_calls_made"] == 0,
        "one_message_one_decision": len(rows) == 1 == len(decisions),
        "api_still_healthy": health["status"] == "ok",
        "no_duplicate_events": len(_event_keys(events)) == len(set(_event_keys(events))),
    }
    if not all(assertions.values()):
        raise AssertionError(f"Decider timeout drill failed: {assertions}")
    return {
        "drill": "decider_timeout",
        "status": "PASS",
        "fault_injected": True,
        "real_decider_calls": 0,
        "real_bedrock_calls": 0,
        "events": events,
        "decision": decision,
        "metrics": metrics,
        "durable_log_rows": rows,
        "assertions": assertions,
    }


def bedrock_error_drill(runtime_dir: Path) -> dict[str, Any]:
    adapter = InjectedAdapter(
        DeciderResult(choice="REPLY", confidence=0.95, latency_ms=8.0)
    )
    replier = InjectedBedrockFailure()
    app = create_app(config=_config(runtime_dir), adapter=adapter, replier=replier)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            events = _collect_one(
                websocket,
                {
                    "type": "message",
                    "sender": "Maya",
                    "text": "Lurker, please answer the API question.",
                },
            )
        _assert_unique(events)
        metrics, decisions = _snapshot(client)
        rows = _log_rows(app)
        health = client.get("/health").json()

    decision = decisions[0]
    agent_chats = [
        event for event in events
        if event.get("type") == "chat" and event.get("is_agent") is True
    ]
    assertions = {
        "one_decider_call": adapter.calls == 1,
        "one_injected_reply_attempt": replier.attempts == 1,
        "no_fabricated_agent_reply": agent_chats == [],
        "bedrock_error_recorded": str(decision["error"]).startswith("bedrock_error:"),
        "reason_is_bedrock_error": decision["reason"] == "bedrock_error",
        "zero_real_bedrock_calls": metrics["counters"]["bedrock_calls_made"] == 0,
        "one_message_one_decision": len(rows) == 1 == len(decisions),
        "api_still_healthy": health["status"] == "ok",
        "no_duplicate_events": len(_event_keys(events)) == len(set(_event_keys(events))),
    }
    if not all(assertions.values()):
        raise AssertionError(f"Bedrock error drill failed: {assertions}")
    return {
        "drill": "bedrock_error",
        "status": "PASS",
        "fault_injected": True,
        "injected_reply_attempts": replier.attempts,
        "real_decider_calls": 0,
        "real_bedrock_calls": 0,
        "events": events,
        "decision": decision,
        "metrics": metrics,
        "durable_log_rows": rows,
        "assertions": assertions,
    }


def websocket_reconnect_drill(runtime_dir: Path) -> dict[str, Any]:
    replier = MockBedrockReplier()
    app = create_app(
        config=_config(runtime_dir), adapter=MockDecider(), replier=replier
    )
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first:
            before = _collect_one(
                first,
                {
                    "type": "message",
                    "sender": "Alex",
                    "text": "Let's meet at four tomorrow.",
                },
            )
        with client.websocket_connect("/ws") as second:
            after = _collect_one(
                second,
                {
                    "type": "message",
                    "sender": "Lea",
                    "text": "Congratulations, we shipped!",
                },
            )
        events = before + after
        _assert_unique(events)
        metrics, decisions = _snapshot(client)
        rows = _log_rows(app)
        health = client.get("/health").json()

    chronological = list(reversed(decisions))
    actions = [decision["final_action"] for decision in chronological]
    event_counts = Counter(event.get("type") for event in events)
    assertions = {
        "two_distinct_connections_completed": bool(before) and bool(after),
        "expected_actions": actions == ["SILENT", "REACT"],
        "two_messages_two_decisions": len(rows) == 2 == len(decisions),
        "one_reaction_only": event_counts["reaction"] == 1,
        "two_decision_events": event_counts["decision"] == 2,
        "two_metrics_events": event_counts["metrics"] == 2,
        "zero_reply_attempts": replier.calls == 0,
        "zero_real_bedrock_calls": metrics["counters"]["bedrock_calls_made"] == 0,
        "no_duplicate_events": len(_event_keys(events)) == len(set(_event_keys(events))),
        "api_still_healthy": health["status"] == "ok",
    }
    if not all(assertions.values()):
        raise AssertionError(f"WebSocket reconnect drill failed: {assertions}")
    return {
        "drill": "websocket_reconnect",
        "status": "PASS",
        "fault_injected": True,
        "connection_count": 2,
        "real_decider_calls": 0,
        "real_bedrock_calls": 0,
        "events": events,
        "decisions": chronological,
        "metrics": metrics,
        "durable_log_rows": rows,
        "assertions": assertions,
    }


DRILLS: tuple[tuple[str, Callable[[Path], dict[str, Any]]], ...] = (
    ("decider_timeout", decider_timeout_drill),
    ("bedrock_error", bedrock_error_drill),
    ("websocket_reconnect", websocket_reconnect_drill),
)


def run_drills(output_root: Path = DEFAULT_OUTPUT_ROOT) -> tuple[Path, dict[str, Any]]:
    """Run all offline drills once and preserve pass or failure evidence."""
    now = datetime.now(timezone.utc)
    output_dir = output_root / now.strftime("%Y%m%dT%H%M%S%fZ")
    output_dir.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="lurker-m6-drills-") as temp:
        temp_root = Path(temp)
        for name, drill in DRILLS:
            try:
                record = drill(temp_root / name)
            except Exception as exc:
                record = {
                    "drill": name,
                    "status": "FAIL",
                    "fault_injected": True,
                    "real_decider_calls": 0,
                    "real_bedrock_calls": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.append(record)
            (output_dir / f"{name}.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )

    status = "PASS" if all(record["status"] == "PASS" for record in records) else "FAIL"
    summary = {
        "artifact_version": "lurker-m6-local-drills-v1",
        "status": status,
        "generated_at": now.isoformat(),
        "scope": "local_offline_injected_failures",
        "drills": [record["drill"] for record in records],
        "drill_statuses": {
            record["drill"]: record["status"] for record in records
        },
        "real_decider_calls": 0,
        "real_bedrock_calls": 0,
        "aws_resources_launched": False,
        "protected_evaluation_data_accessed": False,
        "m5_configuration_changed": False,
        "m6_deployed_acceptance": "NOT_RUN_REQUIRES_SEPARATE_APPROVAL",
        "production_readiness": False,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return output_dir, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    output_dir, summary = run_drills(args.output_root)
    print(f"status={summary['status']} output={output_dir} real_bedrock_calls=0")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
