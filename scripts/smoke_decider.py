#!/usr/bin/env python3
"""Run the five required M0 examples through the real Decider model."""

from __future__ import annotations

import argparse
import os

from decision_pattern.lurker_gate import OPTIONS, QUESTION
from src.lurker.decider_adapter import DeciderAdapter

MODEL_ID = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"

CASES = {
    "question": ([], {"sender": "Lea", "text": "Why is the API returning 401?"}),
    "joke": ([], {"sender": "Alex", "text": "Our bug fixed itself. Very professional 😂"}),
    "plan": ([], {"sender": "Lea", "text": "Let's meet at 4 tomorrow."}),
    "already_answered": (
        [
            {"sender": "Alex", "text": "Why is the API returning 401?"},
            {"sender": "Lea", "text": "The token expired; refresh it."},
        ],
        {"sender": "Alex", "text": "Thanks, fixed."},
    ),
    "ambiguous": ([], {"sender": "Lea", "text": "Interesting result."}),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=os.getenv("DECIDER_MODEL_ID", MODEL_ID))
    parser.add_argument("--device", default=os.getenv("DECIDER_DEVICE", "cpu"))
    parser.add_argument("--timeout-ms", type=int, default=120000)
    args = parser.parse_args()

    adapter = DeciderAdapter(args.model_id, args.device, args.timeout_ms)
    for name, (history, latest) in CASES.items():
        state = {
            "agent_name": "Lurker",
            "recent_messages": history,
            "latest_message": latest,
        }
        result = adapter.decide(state, QUESTION, OPTIONS)
        print(
            f"{name:18} choice={result.choice or '-':6} "
            f"confidence={result.confidence:.4f} latency_ms={result.latency_ms:.2f} "
            f"error={result.error or '-'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

