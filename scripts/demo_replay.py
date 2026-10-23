#!/usr/bin/env python3
"""Replay the versioned M6 demo conversation through Lurker's WebSocket API."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "data" / "demo" / "three_action_conversation_v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "reliability_verification" / "replays"
VALID_ACTIONS = {"SILENT", "REACT", "REPLY"}


class ReplayError(RuntimeError):
    """Raised when a replay violates its evidence or safety contract."""


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp for evidence records."""
    return datetime.now(timezone.utc).isoformat()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    """Load and validate the public, non-evaluation M6 replay fixture."""
    if not _inside(path, ROOT / "data" / "demo"):
        raise ReplayError("replay fixture must stay inside data/demo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("artifact_version") != "lurker-m6-demo-conversation-v1":
        raise ReplayError("unsupported replay fixture version")
    messages = payload.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ReplayError("M6 replay fixture must contain exactly three messages")
    bounds = payload.get("delay_bounds_seconds")
    if bounds != {"minimum": 1.0, "maximum": 3.0}:
        raise ReplayError("M6 replay delay bounds must remain 1.0 to 3.0 seconds")
    actions: list[str] = []
    step_ids: list[str] = []
    for item in messages:
        if set(item) != {
            "step_id", "sender", "text", "expected_action", "delay_before_seconds"
        }:
            raise ReplayError("replay message contains unexpected or missing fields")
        if not all(isinstance(item[key], str) and item[key].strip() for key in (
            "step_id", "sender", "text", "expected_action"
        )):
            raise ReplayError("replay message text fields must be non-empty")
        action = item["expected_action"]
        if action not in VALID_ACTIONS:
            raise ReplayError(f"invalid expected action: {action}")
        delay = float(item["delay_before_seconds"])
        if not 1.0 <= delay <= 3.0:
            raise ReplayError("fixture delay falls outside the realistic range")
        actions.append(action)
        step_ids.append(item["step_id"])
    if actions != ["SILENT", "REACT", "REPLY"]:
        raise ReplayError("M6 replay must cover SILENT, REACT, and REPLY in order")
    if len(step_ids) != len(set(step_ids)):
        raise ReplayError("M6 replay step IDs must be unique")
    return payload


def _record(
    transcript: list[dict[str, Any]], direction: str, event: dict[str, Any]
) -> None:
    transcript.append({"direction": direction, "at": utc_now(), "event": event})


def _inbound(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item["event"] for item in transcript if item.get("direction") == "inbound"
    ]


def validate_unique_events(transcript: list[dict[str, Any]]) -> None:
    """Reject duplicate chat, decision, or reaction events."""
    keys: list[str] = []
    for event in _inbound(transcript):
        if event.get("type") == "chat":
            keys.append(f"chat:{event.get('id')}")
        elif event.get("type") == "decision":
            keys.append(f"decision:{event.get('message_id')}")
        elif event.get("type") == "reaction":
            keys.append(
                f"reaction:{event.get('message_id')}:{event.get('emoji')}"
            )
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ReplayError(f"duplicate live events: {duplicates}")


async def _collect_step(
    websocket: Any,
    step: dict[str, Any],
    transcript: list[dict[str, Any]],
    timeout_seconds: float,
) -> dict[str, Any]:
    outbound = {
        "type": "message",
        "sender": step["sender"],
        "text": step["text"],
    }
    await websocket.send(json.dumps(outbound))
    _record(transcript, "outbound", {**outbound, "step_id": step["step_id"]})

    events: list[dict[str, Any]] = []
    for _ in range(8):
        raw = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ReplayError("WebSocket event is not an object")
        _record(transcript, "inbound", event)
        events.append(event)
        if event.get("type") == "error":
            raise ReplayError(f"server returned an error event: {event}")
        if event.get("type") == "metrics":
            break
    else:
        raise ReplayError(f"step {step['step_id']} exceeded eight inbound events")

    user_chats = [
        event for event in events
        if event.get("type") == "chat" and event.get("is_agent") is False
    ]
    agent_chats = [
        event for event in events
        if event.get("type") == "chat" and event.get("is_agent") is True
    ]
    reactions = [event for event in events if event.get("type") == "reaction"]
    decisions = [event for event in events if event.get("type") == "decision"]
    metrics = [event for event in events if event.get("type") == "metrics"]
    if len(user_chats) != 1 or user_chats[0].get("sender") != step["sender"]:
        raise ReplayError(f"step {step['step_id']} did not echo its user chat once")
    if user_chats[0].get("text") != step["text"]:
        raise ReplayError(f"step {step['step_id']} echoed different message text")
    if len(decisions) != 1 or len(metrics) != 1:
        raise ReplayError(f"step {step['step_id']} lacks one decision/metrics pair")
    decision = decisions[0]
    if decision.get("final_action") != step["expected_action"]:
        raise ReplayError(
            f"step {step['step_id']} expected {step['expected_action']}, "
            f"received {decision.get('final_action')}"
        )
    if step["expected_action"] == "SILENT" and (agent_chats or reactions):
        raise ReplayError("SILENT produced an agent chat or reaction")
    if step["expected_action"] == "REACT" and (
        len(reactions) != 1 or agent_chats
    ):
        raise ReplayError("REACT did not produce exactly one reaction and no reply")
    if step["expected_action"] == "REPLY" and (
        len(agent_chats) != 1 or reactions
    ):
        raise ReplayError("REPLY did not produce exactly one agent chat and no reaction")
    return decision


async def replay_websocket(
    ws_url: str,
    fixture: dict[str, Any],
    transcript: list[dict[str, Any]],
    *,
    delay_scale: float,
    timeout_seconds: float,
) -> list[float]:
    """Send all fixture messages in order and collect complete live evidence."""
    observed_delays: list[float] = []
    async with websockets.connect(
        ws_url, open_timeout=30, close_timeout=10, max_size=1_000_000
    ) as websocket:
        _record(
            transcript,
            "connection",
            {"type": "connected", "target": "configured_websocket"},
        )
        for step in fixture["messages"]:
            started = time.monotonic()
            await asyncio.sleep(float(step["delay_before_seconds"]) * delay_scale)
            observed_delays.append(time.monotonic() - started)
            await _collect_step(websocket, step, transcript, timeout_seconds)
        _record(transcript, "connection", {"type": "completed"})
    return observed_delays


def _validate_rest_evidence(
    fixture: dict[str, Any],
    metrics: dict[str, Any],
    decisions: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    if len(decisions) != 3:
        raise ReplayError(f"expected three REST decisions, received {len(decisions)}")
    chronological = list(reversed(decisions))
    expected_actions = [item["expected_action"] for item in fixture["messages"]]
    actions = [item.get("final_action") for item in chronological]
    if actions != expected_actions:
        raise ReplayError(f"REST decision actions differ: {actions}")
    if len({item.get("message_id") for item in chronological}) != 3:
        raise ReplayError("REST decisions contain duplicate message IDs")
    if any(item.get("error") is not None for item in chronological):
        raise ReplayError("REST decisions contain runtime errors")
    expected_mock = mode == "mock"
    if any(bool(item.get("mock")) is not expected_mock for item in chronological):
        raise ReplayError("decision mock flags do not match replay mode")

    counters = metrics.get("counters", {})
    expected_counters = {
        "messages_read": 3,
        "silent": 1,
        "react": 1,
        "reply": 1,
        "errors": 0,
        "bedrock_calls_made": 0 if mode == "mock" else 1,
        "bedrock_calls_avoided_vs_every_message": 3 if mode == "mock" else 2,
    }
    mismatches = {
        key: {"expected": value, "actual": counters.get(key)}
        for key, value in expected_counters.items()
        if counters.get(key) != value
    }
    if mismatches:
        raise ReplayError(f"metrics mismatch: {mismatches}")
    expected_calls = [False, False, mode == "real"]
    if [bool(item.get("bedrock_called")) for item in chronological] != expected_calls:
        raise ReplayError("per-decision Bedrock call accounting is inconsistent")
    if mode == "real":
        reply = chronological[-1]
        if (
            not reply.get("bedrock_input_tokens")
            or not reply.get("bedrock_output_tokens")
            or reply.get("bedrock_latency_ms") is None
        ):
            raise ReplayError("real REPLY token/latency evidence is incomplete")
    return {"chronological": chronological, "counters": counters}


def run_replay(
    *,
    base_url: str,
    output_dir: Path,
    fixture_path: Path = DEFAULT_FIXTURE,
    mode: str,
    allow_real_bedrock: bool = False,
    delay_scale: float = 1.0,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    """Execute one replay, always preserving a summary and transcript."""
    if mode not in {"mock", "real"}:
        raise ReplayError("mode must be mock or real")
    if mode == "real" and not allow_real_bedrock:
        raise ReplayError("real replay refused without --allow-real-bedrock")
    if mode == "real" and delay_scale != 1.0:
        raise ReplayError("real acceptance requires unscaled realistic delays")
    if delay_scale < 0:
        raise ReplayError("delay scale cannot be negative")
    if _inside(output_dir, ROOT / "results"):
        raise ReplayError("M6 replay evidence may not be written under results/")

    fixture = load_fixture(fixture_path)
    output_dir.mkdir(parents=True, exist_ok=False)
    transcript: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)
    manifest = {
        "artifact_version": "lurker-m6-replay-run-v1",
        "status": "IN_PROGRESS",
        "started_at": started.isoformat(),
        "mode": mode,
        "target": "local_mock" if mode == "mock" else "deployed_instance",
        "fixture": str(fixture_path.resolve().relative_to(ROOT)),
        "fixture_artifact_version": fixture["artifact_version"],
        "delay_scale": delay_scale,
        "real_bedrock_authorized": bool(allow_real_bedrock),
        "protected_evaluation_data_accessed": False,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    summary: dict[str, Any]
    metrics: dict[str, Any] = {}
    decisions: list[dict[str, Any]] = []
    try:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            health = client.get("/health").json()
            expected_mode = "mock" if mode == "mock" else "real"
            if (
                health.get("status") != "ok"
                or health.get("decider_mode") != expected_mode
                or health.get("model_ready") is not True
            ):
                raise ReplayError(f"service is not ready for {mode} replay: {health}")
            reset = client.post("/api/reset")
            reset.raise_for_status()

        ws_url = base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        ).rstrip("/") + "/ws"
        observed_delays = asyncio.run(
            replay_websocket(
                ws_url,
                fixture,
                transcript,
                delay_scale=delay_scale,
                timeout_seconds=timeout_seconds,
            )
        )
        validate_unique_events(transcript)

        with httpx.Client(base_url=base_url, timeout=30) as client:
            metrics = client.get("/api/metrics").json()
            decisions = client.get("/api/decisions?limit=50").json()
        rest = _validate_rest_evidence(fixture, metrics, decisions, mode=mode)
        inbound_counts = Counter(
            event.get("type") for event in _inbound(transcript)
        )
        summary = {
            "artifact_version": "lurker-m6-replay-summary-v1",
            "status": "PASS",
            "acceptance_eligible": mode == "real" and delay_scale == 1.0,
            "mode": mode,
            "started_at": started.isoformat(),
            "completed_at": utc_now(),
            "fixture_artifact_version": fixture["artifact_version"],
            "actions": [item["final_action"] for item in rest["chronological"]],
            "message_count": 3,
            "event_counts": dict(inbound_counts),
            "bedrock_calls_made": rest["counters"]["bedrock_calls_made"],
            "real_bedrock_calls": 0 if mode == "mock" else 1,
            "observed_delay_seconds": observed_delays,
            "realistic_delays_enforced": delay_scale == 1.0,
            "duplicate_events": 0,
            "runtime_errors": 0,
            "protected_evaluation_data_accessed": False,
            "m5_configuration_changed": False,
            "production_readiness": False,
        }
        manifest["status"] = "PASS"
    except Exception as exc:
        summary = {
            "artifact_version": "lurker-m6-replay-summary-v1",
            "status": "FAIL",
            "acceptance_eligible": False,
            "mode": mode,
            "started_at": started.isoformat(),
            "completed_at": utc_now(),
            "error": f"{type(exc).__name__}: {exc}",
            "real_bedrock_calls": 0 if mode == "mock" else None,
            "protected_evaluation_data_accessed": False,
            "m5_configuration_changed": False,
            "production_readiness": False,
        }
        manifest["status"] = "FAIL"

    (output_dir / "transcript.json").write_text(
        json.dumps(transcript, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "decisions.json").write_text(
        json.dumps(decisions, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--allow-mock", action="store_true")
    mode.add_argument("--allow-real-bedrock", action="store_true")
    parser.add_argument("--delay-scale", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()

    selected_mode = "mock" if args.allow_mock else "real"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = args.output_root / stamp
    try:
        summary = run_replay(
            base_url=args.base_url,
            output_dir=output_dir,
            fixture_path=args.fixture,
            mode=selected_mode,
            allow_real_bedrock=args.allow_real_bedrock,
            delay_scale=args.delay_scale,
            timeout_seconds=args.timeout_seconds,
        )
    except ReplayError as exc:
        print(f"refused: {exc}")
        return 2
    print(
        f"status={summary['status']} mode={selected_mode} output={output_dir} "
        f"acceptance_eligible={summary['acceptance_eligible']}"
    )
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
