#!/usr/bin/env python3
"""Create the blank human-labeling sheet required by the build specification."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "eval" / "scenario_candidates.jsonl"
DEFAULT_OUTPUT = ROOT / "eval" / "labels" / "labels_blank.csv"
FIELDNAMES = ["id", "history text", "message", "a1", "a2", "a3"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSON objects from a JSONL file."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def format_history(history: list[dict[str, str]]) -> str:
    """Render conversation history as readable, single-cell text."""
    return "\n".join(f"{item['sender']}: {item['text']}" for item in history)


def write_blank_sheet(candidates: Path, output: Path) -> int:
    """Write one blank row per candidate and return the row count."""
    rows = load_jsonl(candidates)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            message = row["message"]
            writer.writerow(
                {
                    "id": row["id"],
                    "history text": format_history(row["history"]),
                    "message": f"{message['sender']}: {message['text']}",
                    "a1": "",
                    "a2": "",
                    "a3": "",
                }
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = write_blank_sheet(args.candidates, args.output)
    print(f"wrote={args.output} rows={count} labels=blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
