#!/usr/bin/env python3
"""Make the single real Bedrock Converse call required by M0."""

from __future__ import annotations

import os
import sys
import time

import boto3


def main() -> int:
    model_id = os.getenv("BEDROCK_MODEL_ID")
    region = os.getenv("AWS_REGION")
    if not model_id or not region:
        print("Set BEDROCK_MODEL_ID and AWS_REGION before running.", file=sys.stderr)
        return 2

    client = boto3.client("bedrock-runtime", region_name=region)
    started = time.perf_counter()
    response = client.converse(
        modelId=model_id,
        system=[{"text": "You are Lurker, a quiet group-chat teammate. Reply in one short sentence."}],
        messages=[{"role": "user", "content": [{"text": "Say that the Bedrock smoke test worked."}]}],
        inferenceConfig={"maxTokens": 40, "temperature": 0},
    )
    latency_ms = (time.perf_counter() - started) * 1000
    text = response["output"]["message"]["content"][0]["text"]
    usage = response.get("usage", {})
    print(f"text={text}")
    print(
        f"latency_ms={latency_ms:.2f} input_tokens={usage.get('inputTokens', 0)} "
        f"output_tokens={usage.get('outputTokens', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

