#!/usr/bin/env python3
"""Verify one real, non-Bedrock decision through a deployed WebSocket."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "deployment_acceptance"
MESSAGE = {
    "type": "message",
    "sender": "Alex",
    "text": "Let's meet at four tomorrow.",
}


async def collect(ws_url: str) -> list[dict[str, Any]]:
    """Send the stable SILENT case and collect events through metrics."""
    transcript: list[dict[str, Any]] = []
    decision_seen = False
    metrics_seen = False
    async with websockets.connect(ws_url, open_timeout=30) as websocket:
        await websocket.send(json.dumps(MESSAGE))
        while not (decision_seen and metrics_seen):
            event = json.loads(
                await asyncio.wait_for(websocket.recv(), timeout=180)
            )
            transcript.append(event)
            decision_seen = decision_seen or event.get("type") == "decision"
            metrics_seen = metrics_seen or event.get("type") == "metrics"
    return transcript


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Public HTTP origin")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    ws_scheme = "wss" if base_url.startswith("https://") else "ws"
    ws_host = base_url.split("://", 1)[1]
    ws_url = f"{ws_scheme}://{ws_host}/ws"

    health_response = httpx.get(f"{base_url}/health", timeout=30)
    health_response.raise_for_status()
    health = health_response.json()
    if health.get("decider_mode") != "real" or health.get("model_ready") is not True:
        raise RuntimeError(f"deployed real Decider is not ready: {health}")

    transcript = asyncio.run(collect(ws_url))
    decisions = [event for event in transcript if event.get("type") == "decision"]
    if len(decisions) != 1:
        raise RuntimeError(f"expected one decision event, got {len(decisions)}")
    decision = decisions[0]
    if decision.get("raw_choice") != "SILENT":
        raise RuntimeError(f"expected stable SILENT case, got {decision}")
    if decision.get("final_action") != "SILENT" or decision.get("error"):
        raise RuntimeError(f"deployed decision failed safe acceptance: {decision}")

    recent_response = httpx.get(
        f"{base_url}/api/decisions", params={"limit": 1}, timeout=30
    )
    recent_response.raise_for_status()
    recent = recent_response.json()
    if len(recent) != 1 or recent[0].get("message_id") != decision.get("message_id"):
        raise RuntimeError("decision REST evidence does not match WebSocket evidence")
    if recent[0].get("bedrock_called") is not False:
        raise RuntimeError("the M3 SILENT smoke case unexpectedly invoked Bedrock")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    summary = {
        "status": "PASS",
        "checked_from": "outside_deployed_instance",
        "base_url": base_url,
        "health": health,
        "decision": recent[0],
        "bedrock_calls_made_by_case": 0,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "websocket_transcript.json").write_text(
        json.dumps(transcript, indent=2) + "\n", encoding="utf-8"
    )
    print(f"status=PASS output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
