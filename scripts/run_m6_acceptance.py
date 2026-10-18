#!/usr/bin/env python3
"""Run exactly three authorized real M6 replays against a deployed instance."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.demo_replay import DEFAULT_FIXTURE, ROOT, ReplayError, run_replay

DEFAULT_OUTPUT_ROOT = ROOT / "data" / "m6_acceptance"


def validate_acceptance_summaries(
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the no-retry, three-replay deployed acceptance contract."""
    if len(summaries) != 3:
        raise ReplayError("M6 acceptance requires exactly three replay summaries")
    if any(item.get("status") != "PASS" for item in summaries):
        raise ReplayError("all three M6 replays must pass")
    if any(item.get("acceptance_eligible") is not True for item in summaries):
        raise ReplayError("all three replays must be real and acceptance-eligible")
    if any(item.get("actions") != ["SILENT", "REACT", "REPLY"] for item in summaries):
        raise ReplayError("each replay must observe SILENT, REACT, and REPLY")
    messages = sum(int(item.get("message_count", 0)) for item in summaries)
    bedrock_calls = sum(int(item.get("bedrock_calls_made", 0)) for item in summaries)
    errors = sum(int(item.get("runtime_errors", 0)) for item in summaries)
    duplicates = sum(int(item.get("duplicate_events", 0)) for item in summaries)
    if (messages, bedrock_calls, errors, duplicates) != (9, 3, 0, 0):
        raise ReplayError(
            "aggregate acceptance counts must be 9 messages, 3 Bedrock calls, "
            "0 errors, and 0 duplicates"
        )
    return {
        "replay_count": 3,
        "message_count": messages,
        "actions": {"SILENT": 3, "REACT": 3, "REPLY": 3},
        "bedrock_calls_made": bedrock_calls,
        "runtime_errors": errors,
        "duplicate_events": duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--allow-deployed-real", action="store_true")
    parser.add_argument("--allow-real-bedrock", action="store_true")
    parser.add_argument("--confirmed-server-call-cap", type=int)
    args = parser.parse_args()

    if not args.allow_deployed_real or not args.allow_real_bedrock:
        print(
            "refused: deployed acceptance and real Bedrock both require separate "
            "explicit authorization flags"
        )
        return 2
    if args.confirmed_server_call_cap != 3:
        print("refused: confirm BEDROCK_MAX_CALLS=3 on the deployed server")
        return 2
    host = (urlparse(args.base_url).hostname or "").lower()
    if host in {"", "127.0.0.1", "localhost", "::1"}:
        print("refused: final M6 acceptance must target the deployed instance")
        return 2

    now = datetime.now(timezone.utc)
    output_dir = args.output_root / now.strftime("%Y%m%dT%H%M%S%fZ")
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "artifact_version": "lurker-m6-acceptance-run-v1",
        "status": "IN_PROGRESS",
        "started_at": now.isoformat(),
        "target": "deployed_instance",
        "expected_replays": 3,
        "completed_replays": 0,
        "retry_policy": "none; any failure ends this authorized sequence",
        "confirmed_server_bedrock_call_cap": 3,
        "fixture": str(args.fixture.resolve().relative_to(ROOT)),
        "protected_evaluation_data_accessed": False,
        "m5_configuration_changed": False,
    }
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    summaries: list[dict[str, Any]] = []
    for index in range(1, 4):
        summary = run_replay(
            base_url=args.base_url,
            output_dir=output_dir / f"replay_{index:02d}",
            fixture_path=args.fixture,
            mode="real",
            allow_real_bedrock=True,
            delay_scale=1.0,
        )
        summaries.append(summary)
        manifest["completed_replays"] = index
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        if summary.get("status") != "PASS":
            manifest["status"] = "NO_GO"
            manifest["failed_replay"] = index
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            print(f"status=NO_GO failed_replay={index} output={output_dir}")
            return 1

    try:
        aggregate = validate_acceptance_summaries(summaries)
    except ReplayError as exc:
        manifest["status"] = "NO_GO"
        manifest["validation_error"] = str(exc)
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"status=NO_GO error={exc} output={output_dir}")
        return 1

    summary = {
        "artifact_version": "lurker-m6-acceptance-summary-v1",
        "status": "PASS",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **aggregate,
        "protected_evaluation_data_accessed": False,
        "m5_configuration_changed": False,
        "production_readiness": False,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    manifest["status"] = "PASS"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"status=PASS replays=3 bedrock_calls=3 output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
