#!/usr/bin/env python3
"""Record owner approval for M5 technical closure without changing evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone

from eval.publication import validate_m5_closure
from scripts.finalize_m5_no_go import OUTPUT_ROOT, PUBLISHED, report


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    source_bytes = PUBLISHED.read_bytes()
    source = json.loads(source_bytes)
    validate_m5_closure(source)
    if source["acceptance"]["implementation_completion"] != "PENDING_OWNER_APPROVAL":
        raise ValueError("published M5 closure is not awaiting owner approval")

    approved = deepcopy(source)
    now = datetime.now(timezone.utc)
    approved["generated_at"] = now.isoformat()
    approved["published_at"] = now.isoformat()
    approved["acceptance"]["implementation_completion"] = "TECHNICALLY_COMPLETE"
    approved["owner_approval"] = {
        "status": "APPROVED",
        "approved_at": now.isoformat(),
        "scope": "technical closure with documented performance NO-GO and Bedrock-baseline deviation",
        "production_readiness": False,
    }
    approved["approval_source"] = {
        "candidate_sha256": sha256_bytes(source_bytes),
        "method": "explicit project-owner approval in the Codex task",
    }
    validate_m5_closure(approved)

    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    output = OUTPUT_ROOT / stamp
    output.mkdir(parents=True)
    result_path = output / "results.json"
    report_path = output / "M5_FINAL_ACCEPTANCE.md"
    result_path.write_text(json.dumps(approved, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report(approved), encoding="utf-8")
    PUBLISHED.write_text(json.dumps(approved, indent=2) + "\n", encoding="utf-8")
    print(
        f"published={PUBLISHED} report={report_path} "
        "implementation_completion=TECHNICALLY_COMPLETE model_performance=NO_GO "
        "bedrock_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
