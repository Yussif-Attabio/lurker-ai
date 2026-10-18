#!/usr/bin/env python3
"""Verify the frozen M5 contract without opening held-out data or loading a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "config" / "m5_frozen_evaluation.yaml"
MODEL_CACHE = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--StrandsAgents--strands-decider-2B-qwen3.5-v1-2610"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> tuple[int, str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return len(files), digest.hexdigest()


def canonical_config_digest(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def verify_freeze(path: Path = DEFAULT_FREEZE) -> dict[str, Any]:
    frozen = yaml.safe_load(path.read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}

    for relative, expected in frozen["checksums"].items():
        observed = sha256(ROOT / relative)
        checks[f"sha256:{relative}"] = {
            "pass": observed == expected,
            "expected": expected,
            "observed": observed,
        }

    live_config = yaml.safe_load((ROOT / "config" / "default.yaml").read_text())
    frozen_config = {
        key: frozen["configuration"][key]
        for key in (
            "context_k",
            "decider_timeout_ms",
            "decider_model_id",
            "decider_device",
            "reply_threshold",
            "react_threshold",
            "force_reply_on_mention",
        )
    }
    config_digest = canonical_config_digest(frozen_config)
    checks["frozen_configuration"] = {
        "pass": live_config == frozen_config
        and config_digest == frozen["configuration"]["canonical_sha256"],
        "expected_digest": frozen["configuration"]["canonical_sha256"],
        "observed_digest": config_digest,
    }

    tuning_path = ROOT / "eval" / "tuning_scenarios.jsonl"
    tuning_rows = [
        json.loads(line) for line in tuning_path.read_text().splitlines() if line.strip()
    ]
    checks["tuning_dataset_isolation"] = {
        "pass": len(tuning_rows) == 30
        and {row.get("split") for row in tuning_rows} == {"tuning"},
        "path": str(tuning_path.relative_to(ROOT)),
        "row_count": len(tuning_rows),
        "observed_splits": sorted({str(row.get("split")) for row in tuning_rows}),
        "shared_or_heldout_source_opened": False,
    }

    revision = frozen["configuration"]["decider_model_revision"]
    snapshot = MODEL_CACHE / "snapshots" / revision
    model_expected = frozen["model_artifacts"]
    model_observed = {
        "cache_ref": (MODEL_CACHE / "refs" / "main").read_text().strip(),
        "manifest_sha256": sha256(snapshot / "MANIFEST.sha256"),
        "provenance_sha256": sha256(snapshot / "provenance.json"),
        "strands_decider_config_sha256": sha256(snapshot / "strands_decider_config.json"),
        "tokenizer_config_sha256": sha256(snapshot / "tokenizer_config.json"),
    }
    checks["model_revision"] = {
        "pass": model_observed == model_expected,
        "expected": model_expected,
        "observed": model_observed,
    }

    for name, evidence in frozen["preserved_evidence"].items():
        count, digest = tree_digest(ROOT / evidence["path"])
        checks[f"preserved_evidence:{name}"] = {
            "pass": count == evidence["file_count"] and digest == evidence["tree_sha256"],
            "expected_file_count": evidence["file_count"],
            "observed_file_count": count,
            "expected_tree_sha256": evidence["tree_sha256"],
            "observed_tree_sha256": digest,
        }

    passed = all(item["pass"] for item in checks.values())
    return {
        "artifact_version": "lurker-m5-freeze-preflight-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL",
        "freeze_file": str(path.relative_to(ROOT)),
        "freeze_sha256": sha256(path),
        "heldout_dataset_opened": False,
        "model_loaded": False,
        "aws_or_bedrock_calls": 0,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_freeze(args.freeze)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
