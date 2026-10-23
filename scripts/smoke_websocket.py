#!/usr/bin/env python3
"""Run the controlled M2 WebSocket acceptance conversation."""

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
DEFAULT_OUTPUT = ROOT / "data" / "websocket_acceptance"
SCENARIOS = [
    ("SILENT", {"type": "message", "sender": "Alex", "text": "Let's meet at four tomorrow."}),
    (
        "REACT",
        {
            "type": "message",
            "sender": "Lea",
            "text": "Congratulations everyone—we made the hackathon finals! 🎉",
        },
    ),
    (
        "REPLY",
        {
            "type": "message",
            "sender": "Maya",
            "text": "Lurker, please answer: why does the API return 401?",
        },
    ),
]
REPLY_TEXT = SCENARIOS[-1][1]["text"]


async def collect_decision(
    websocket: Any, expected: str, transcript: list[dict[str, Any]]
) -> None:
    agent_reply_seen = False
    decision_seen = False
    metrics_seen = False
    while True:
        event = json.loads(await asyncio.wait_for(websocket.recv(), timeout=180))
        transcript.append(event)
        if event.get("type") == "chat" and event.get("is_agent"):
            agent_reply_seen = True
        if event.get("type") == "decision":
            decision_seen = True
            if event.get("final_action") != expected:
                raise RuntimeError(
                    f"expected {expected}, received {event.get('final_action')}"
                )
        if event.get("type") == "metrics":
            metrics_seen = True
        if decision_seen and metrics_seen:
            if expected == "REPLY" and not agent_reply_seen:
                raise RuntimeError("REPLY decision did not include real agent text")
            return


async def run(ws_url: str, transcript: list[dict[str, Any]]) -> None:
    async with websockets.connect(ws_url, open_timeout=30) as websocket:
        for expected, message in SCENARIOS:
            await websocket.send(json.dumps(message))
            await collect_decision(websocket, expected, transcript)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8000/ws")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-real-bedrock",
        action="store_true",
        help="Required acknowledgment that the REPLY scenario invokes Bedrock.",
    )
    args = parser.parse_args()
    if not args.allow_real_bedrock:
        print("refused: pass --allow-real-bedrock only after explicit owner approval")
        return 2

    health = httpx.get(args.health_url, timeout=30).json()
    if health.get("decider_mode") != "real" or health.get("model_ready") is not True:
        print(f"refused: real Decider is not ready: {health}")
        return 2

    transcript: list[dict[str, Any]] = []
    asyncio.run(run(args.ws_url, transcript))
    base_url = args.health_url.rsplit("/health", 1)[0]
    metrics = httpx.get(f"{base_url}/api/metrics", timeout=30).json()
    decisions = httpx.get(f"{base_url}/api/decisions?limit=3", timeout=30).json()
    ordered_decisions = list(reversed(decisions))
    observed_actions = [item.get("final_action") for item in ordered_decisions]
    expected_actions = [expected for expected, _ in SCENARIOS]
    counters = metrics.get("counters", {})
    required_counters = {
        "messages_read": 3,
        "silent": 1,
        "react": 1,
        "reply": 1,
        "errors": 0,
        "bedrock_calls_made": 1,
        "bedrock_calls_avoided_vs_every_message": 2,
    }
    if observed_actions != expected_actions:
        raise RuntimeError(
            f"decision API actions differ: expected {expected_actions}, got {observed_actions}"
        )
    if any(counters.get(key) != value for key, value in required_counters.items()):
        raise RuntimeError(
            f"metrics mismatch: expected {required_counters}, got {counters}"
        )
    if [item.get("bedrock_called") for item in ordered_decisions] != [False, False, True]:
        raise RuntimeError("Bedrock call accounting did not match SILENT/REACT/REPLY")
    reply_decision = ordered_decisions[-1]
    if (
        reply_decision.get("error") is not None
        or not reply_decision.get("bedrock_input_tokens")
        or not reply_decision.get("bedrock_output_tokens")
        or reply_decision.get("bedrock_latency_ms") is None
    ):
        raise RuntimeError(f"REPLY evidence is incomplete: {reply_decision}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "websocket_transcript.json").write_text(
        json.dumps(transcript, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "decisions.json").write_text(
        json.dumps(ordered_decisions, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "status": "PASS",
        "actions": observed_actions,
        "real_bedrock_reply_observed": any(
            event.get("type") == "chat" and event.get("is_agent")
            for event in transcript
        ),
        "bedrock_calls_made": counters["bedrock_calls_made"],
        "bedrock_input_tokens": reply_decision["bedrock_input_tokens"],
        "bedrock_output_tokens": reply_decision["bedrock_output_tokens"],
        "bedrock_latency_ms": reply_decision["bedrock_latency_ms"],
        "decider_latency_ms": [
            item["decider_latency_ms"] for item in ordered_decisions
        ],
        "errors": [item.get("error") for item in ordered_decisions],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"status=PASS output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
