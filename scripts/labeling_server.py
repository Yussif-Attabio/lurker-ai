#!/usr/bin/env python3
"""Serve the local-only human labeling interface without exposing split data."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "labeling"
CANDIDATES_PATH = ROOT / "eval" / "scenario_candidates.jsonl"
CALIBRATION_CANDIDATES_PATH = ROOT / "eval" / "react_calibration_candidates.jsonl"
RECOVERY_CANDIDATES_PATH = ROOT / "eval" / "recovery" / "candidates.jsonl"

DATASETS: dict[str, dict[str, Any]] = {
    "original": {
        "id": "original-m1-v1",
        "title": "Initial evaluation",
        "candidate_path": CANDIDATES_PATH,
        "export_prefix": "labels",
        "storage_version": "v1",
    },
    "calibration": {
        "id": "calibration-m1-v1",
        "title": "Calibration review",
        "candidate_path": CALIBRATION_CANDIDATES_PATH,
        "export_prefix": "calibration_labels",
        "storage_version": "v2",
    },
    "recovery": {
        "id": "m5-recovery-candidates-v1",
        "title": "M5 recovery evaluation",
        "candidate_path": RECOVERY_CANDIDATES_PATH,
        "export_prefix": "recovery_labels",
        "storage_version": "v3",
    },
}


def public_scenarios(path: Path = CANDIDATES_PATH) -> list[dict[str, Any]]:
    """Return only information a human evaluator is allowed to see."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [
        {
            "id": row["id"],
            "history": row["history"],
            "message": row["message"],
        }
        for row in rows
    ]


def public_dataset(dataset_key: str) -> dict[str, Any]:
    """Return redacted scenarios plus neutral UI metadata for one dataset."""
    if dataset_key not in DATASETS:
        raise ValueError(f"unknown labeling dataset: {dataset_key}")
    config = DATASETS[dataset_key]
    scenarios = public_scenarios(Path(config["candidate_path"]))
    return {
        "dataset": {
            "id": config["id"],
            "title": config["title"],
            "export_prefix": config["export_prefix"],
            "storage_version": config["storage_version"],
            "scenario_count": len(scenarios),
        },
        "scenarios": scenarios,
    }


class LabelingHandler(BaseHTTPRequestHandler):
    """Serve static UI assets and a redacted scenario API."""

    dataset_key = "original"

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        route = urlparse(self.path).path
        if route == "/health":
            body = json.dumps(
                {
                    "status": "ok",
                    "mode": "human-labeling",
                    "dataset": DATASETS[self.dataset_key]["id"],
                }
            ).encode()
            self._send_bytes(body, "application/json")
            return
        if route == "/api/scenarios":
            body = json.dumps(public_dataset(self.dataset_key)).encode()
            self._send_bytes(body, "application/json; charset=utf-8")
            return

        relative = "index.html" if route in {"/", "/index.html"} else route.lstrip("/")
        if relative not in {"index.html", "app.js", "styles.css"}:
            self._send_bytes(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
            return
        path = STATIC_ROOT / relative
        if not path.is_file():
            self._send_bytes(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send_bytes(path.read_bytes(), f"{content_type}; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        """Keep local output compact."""
        print(f"labeling-ui: {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--dataset", choices=tuple(DATASETS), default="original")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing non-local host; this labeling server is local-only.")
    LabelingHandler.dataset_key = args.dataset
    server = ThreadingHTTPServer((args.host, args.port), LabelingHandler)
    print(
        f"Open http://{args.host}:{args.port} in a browser. "
        f"Dataset={DATASETS[args.dataset]['id']}. Press Ctrl+C to stop."
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
