#!/usr/bin/env python3
"""Run one guarded external reconnect drill against the deployed M6 service."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets

from scripts.demo_replay import DEFAULT_FIXTURE, ROOT, ReplayError, load_fixture


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def collect_step(
    websocket: Any,
    step: dict[str, Any],
    transcript: list[dict[str, Any]],
    connection: int,
) -> dict[str, Any]:
    outbound = {"type": "message", "sender": step["sender"], "text": step["text"]}
    await websocket.send(json.dumps(outbound))
    transcript.append(
        {
            "direction": "outbound",
            "at": utc_now(),
            "connection": connection,
            "step_id": step["step_id"],
            "event": outbound,
        }
    )
    events: list[dict[str, Any]] = []
    for _ in range(8):
        event = json.loads(await asyncio.wait_for(websocket.recv(), timeout=180))
        transcript.append(
            {
                "direction": "inbound",
                "at": utc_now(),
                "connection": connection,
                "event": event,
            }
        )
        events.append(event)
        if event.get("type") == "error":
            raise ReplayError(f"server error during reconnect drill: {event}")
        if event.get("type") == "metrics":
            break
    decisions = [event for event in events if event.get("type") == "decision"]
    metrics = [event for event in events if event.get("type") == "metrics"]
    if len(decisions) != 1 or len(metrics) != 1:
        raise ReplayError("each reconnect step requires one decision and metrics event")
    if decisions[0].get("final_action") != step["expected_action"]:
        raise ReplayError(
            f"reconnect step expected {step['expected_action']}, received "
            f"{decisions[0].get('final_action')}"
        )
    return decisions[0]


async def run_socket_drill(
    ws_url: str, steps: list[dict[str, Any]], transcript: list[dict[str, Any]]
) -> None:
    for connection, step in enumerate(steps, start=1):
        async with websockets.connect(
            ws_url, open_timeout=30, close_timeout=10, max_size=1_000_000
        ) as websocket:
            transcript.append(
                {
                    "direction": "connection",
                    "at": utc_now(),
                    "connection": connection,
                    "event": {"type": "connected", "target": "deployed_instance"},
                }
            )
            await collect_step(websocket, step, transcript, connection)
            transcript.append(
                {
                    "direction": "connection",
                    "at": utc_now(),
                    "connection": connection,
                    "event": {"type": "closed_by_client"},
                }
            )


def validate_unique(transcript: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for item in transcript:
        event = item.get("event", {})
        if item.get("direction") != "inbound":
            continue
        if event.get("type") == "chat":
            keys.append(f"chat:{event.get('id')}")
        elif event.get("type") == "decision":
            keys.append(f"decision:{event.get('message_id')}")
        elif event.get("type") == "reaction":
            keys.append(f"reaction:{event.get('message_id')}:{event.get('emoji')}")
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ReplayError(f"duplicate reconnect events: {duplicates}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-deployed-real", action="store_true")
    args = parser.parse_args()

    host = (urlparse(args.base_url).hostname or "").lower()
    if not args.allow_deployed_real or host in {"", "localhost", "127.0.0.1", "::1"}:
        print("refused: reconnect drill requires an explicitly authorized deployed host")
        return 2
    if args.output_dir.exists():
        print("refused: reconnect evidence directory already exists")
        return 2

    args.output_dir.mkdir(parents=True)
    transcript: list[dict[str, Any]] = []
    summary: dict[str, Any]
    try:
        fixture = load_fixture(DEFAULT_FIXTURE)
        steps = fixture["messages"][:2]
        with httpx.Client(base_url=args.base_url, timeout=30) as client:
            health = client.get("/health").json()
            if health != {"status": "ok", "decider_mode": "real", "model_ready": True}:
                raise ReplayError(f"deployed real service is not ready: {health}")
            client.post("/api/reset").raise_for_status()

        ws_url = args.base_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        ).rstrip("/") + "/ws"
        asyncio.run(run_socket_drill(ws_url, steps, transcript))
        validate_unique(transcript)

        with httpx.Client(base_url=args.base_url, timeout=30) as client:
            metrics = client.get("/api/metrics").json()
            decisions = client.get("/api/decisions?limit=50").json()
        chronological = list(reversed(decisions))
        if [item.get("final_action") for item in chronological] != ["SILENT", "REACT"]:
            raise ReplayError("REST decisions do not preserve SILENT then REACT")
        counters = metrics.get("counters", {})
        expected = {
            "messages_read": 2,
            "silent": 1,
            "react": 1,
            "reply": 0,
            "errors": 0,
            "bedrock_calls_made": 0,
            "bedrock_calls_avoided_vs_every_message": 2,
        }
        if any(counters.get(key) != value for key, value in expected.items()):
            raise ReplayError(f"reconnect metrics mismatch: {counters}")
        summary = {
            "artifact_version": "lurker-m6-deployed-reconnect-v1",
            "status": "PASS",
            "completed_at": utc_now(),
            "connections": 2,
            "messages": 2,
            "actions": ["SILENT", "REACT"],
            "bedrock_calls_made": 0,
            "duplicate_events": 0,
            "runtime_errors": 0,
            "target": "deployed_instance",
            "protected_evaluation_data_accessed": False,
            "m5_configuration_changed": False,
        }
    except Exception as exc:
        metrics = {}
        decisions = []
        summary = {
            "artifact_version": "lurker-m6-deployed-reconnect-v1",
            "status": "FAIL",
            "completed_at": utc_now(),
            "error": f"{type(exc).__name__}: {exc}",
            "target": "deployed_instance",
            "protected_evaluation_data_accessed": False,
            "m5_configuration_changed": False,
        }

    for name, value in (
        ("transcript.json", transcript),
        ("metrics.json", metrics),
        ("decisions.json", decisions),
        ("summary.json", summary),
    ):
        (args.output_dir / name).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8"
        )
    print(f"status={summary['status']} output={args.output_dir}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
