#!/usr/bin/env python3
"""Materialize the held-out input once, only after explicit owner authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.run_eval import load_scenarios, validate_scenarios

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "eval" / "scenarios.jsonl"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def guard_unlock(allow_heldout: bool, authorization_id: str) -> None:
    if not allow_heldout:
        raise ValueError("held-out unlock requires --allow-heldout")
    if not authorization_id.strip():
        raise ValueError("held-out unlock requires a recorded owner authorization ID")


def prepare_locked_input(
    source: Path,
    output: Path,
    authorization_id: str,
    *,
    expected_count: int = 15,
) -> dict[str, object]:
    """Create one exclusive held-out file and manifest without printing its rows."""
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        raise FileExistsError("held-out output and manifest paths must be new")
    scenarios = load_scenarios(source, "heldout")
    validate_scenarios(scenarios, "heldout")
    if len(scenarios) != expected_count:
        raise ValueError(
            f"expected {expected_count} held-out scenarios, observed {len(scenarios)}"
        )
    payload = ("\n".join(item.model_dump_json() for item in scenarios) + "\n").encode()
    manifest = {
        "artifact_version": "lurker-m5-heldout-unlock-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authorization_id": authorization_id,
        "scenario_count": len(scenarios),
        "split": "heldout",
        "output_sha256": sha256_bytes(payload),
        "source_sha256": sha256_bytes(source.read_bytes()),
        "scenario_text_printed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(payload)
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args()
    try:
        guard_unlock(args.allow_heldout, args.authorization_id)
        manifest = prepare_locked_input(args.source, args.output, args.authorization_id)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"held-out unlock refused: {exc}") from exc
    print(
        f"status=LOCKED_INPUT_READY count={manifest['scenario_count']} "
        f"sha256={manifest['output_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
