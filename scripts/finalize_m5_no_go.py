#!/usr/bin/env python3
"""Publish an honest M5 technical-closure candidate from recorded evidence only."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.publication import M5_CLOSURE_ARTIFACT_VERSION, validate_m5_closure
from eval.reporting import rate_text

ROOT = Path(__file__).resolve().parents[1]
HELDOUT_RESULTS = (
    ROOT / "results" / "m5_heldout" / "20261017T053719Z" / "decider"
    / "20261017T053818Z" / "results.json"
)
HELDOUT_MANIFEST = HELDOUT_RESULTS.with_name("run_manifest.json")
QUESTION_BASELINE = (
    ROOT / "results" / "m5_finalization" / "heldout_question_baseline"
    / "20261018T003000Z" / "always_questions_summary.json"
)
COMBINED_BASELINE = (
    ROOT / "results" / "m5_recovery" / "single_rater" / "development"
    / "20261017T221429Z" / "results.json"
)
COMBINED_PROVENANCE = (
    ROOT / "eval" / "recovery" / "combined_reference" / "provenance_manifest.json"
)
PIPELINE_EVIDENCE = (
    ROOT
    / "data"
    / "archive"
    / "websocket_acceptance"
    / "20261016T071233Z"
    / "summary.json"
)
FROZEN_CONFIG = ROOT / "config" / "m5_frozen_evaluation.yaml"
PUBLISHED = ROOT / "results" / "published.json"
OUTPUT_ROOT = ROOT / "results" / "m5_finalization" / "closure"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(payload: dict[str, Any]) -> str:
    primary = payload["context_metrics"]["3"]
    question = payload["baselines"]["always_reply_to_questions"]
    technically_complete = (
        payload["acceptance"]["implementation_completion"] == "TECHNICALLY_COMPLETE"
    )
    status = (
        "TECHNICALLY COMPLETE / MODEL PERFORMANCE NO-GO"
        if technically_complete
        else "TECHNICAL CLOSURE PENDING OWNER APPROVAL / MODEL PERFORMANCE NO-GO"
    )
    implementation_line = (
        "technically complete by owner approval, with documented limitations."
        if technically_complete
        else "pending owner approval for technical closure."
    )
    lines = [
        "# M5 final acceptance candidate",
        "",
        f"Status: **{status}**",
        "",
        "This report publishes only recorded evidence. It does not rerun held-out data, "
        "invoke Bedrock, open the protected reserve, or claim production readiness.",
        "",
        "## Frozen original configuration",
        "",
        "- Context: k=3",
        "- REPLY threshold: 0.20",
        "- REACT threshold: 0.04",
        f"- Model: `{payload['model_id']}`",
        f"- Revision: `{payload['model_revision']}`",
        "- Original decision wording and action policy: unchanged",
        "",
        "## Original one-time held-out result",
        "",
        "| Metric | Result | Acceptance |",
        "|---|---:|---:|",
        f"| Accuracy | {rate_text(primary['accuracy'])} | FAIL (requires >=70%) |",
        f"| Unnecessary interruption | {rate_text(primary['unnecessary_interruption_rate'])} | FAIL (requires <=20%) |",
        f"| Missed help | {rate_text(primary['missed_help_rate'])} | PASS (requires <=25%) |",
        f"| REACT precision | {rate_text(primary['react_precision'])} | report only |",
        f"| REACT recall | {rate_text(primary['react_recall'])} | unavailable: no unanimous REACT cases |",
        f"| Latency p50 / p95 | {primary['latency_ms']['p50']:.2f} / {primary['latency_ms']['p95']:.2f} ms | report only |",
        "",
        "The held-out result remains NO-GO and was not rerun or modified.",
        "",
        "## Baseline status",
        "",
        "The free question-mark rule was run once on the same 15 held-out cases. "
        "It did not invoke a model or modify the frozen Decider result.",
        "",
        "| Baseline | Scope | Accuracy | Interruption | Missed help | Calls |",
        "|---|---|---:|---:|---:|---:|",
        f"| Question-mark rule | held-out | {rate_text(question['metrics']['accuracy'])} | {rate_text(question['metrics']['unnecessary_interruption_rate'])} | {rate_text(question['metrics']['missed_help_rate'])} | 0 |",
        "| Bedrock judge | held-out | Not run | Not run | Not run | 0 |",
        "",
        "The strict build specification now lacks only the held-out Bedrock judge. "
        "Completing it requires separate permission for up to 15 paid calls.",
        "",
        "## Implementation and pipeline evidence",
        "",
        "- Context comparison k=0/3/5: complete",
        "- Threshold tuning and frozen configuration: complete",
        "- One-time held-out Decider run: complete, NO-GO",
        "- SILENT / REACT / REPLY real WebSocket pipeline: previously passed",
        "- SILENT and REACT avoided Bedrock; REPLY invoked Bedrock exactly once",
        "- Evaluation tab: publishes this real-evidence NO-GO closure candidate",
        "- Bedrock judge held-out baseline: not run, separate approval required",
        "",
        "## Acceptance distinction",
        "",
        f"- **Implementation completion:** {implementation_line}",
        "- **Model-performance acceptance:** NO-GO.",
        "- **Strict original M5 checklist:** incomplete because the Bedrock held-out baseline is absent.",
        "- **Production readiness:** not approved.",
        "",
        ("M5 is technically closed with a performance NO-GO and explicit "
         "Bedrock-baseline deviation. This is not model-performance or production "
         "approval."
         if technically_complete else
         "M5 may be closed only as a documented technical closure with a performance "
         "NO-GO and explicit Bedrock-baseline deviation, unless that paid baseline is "
         "separately authorized and completed."),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if PUBLISHED.exists():
        raise FileExistsError(f"refusing to overwrite published evidence: {PUBLISHED}")
    heldout = read_json(HELDOUT_RESULTS)
    manifest = read_json(HELDOUT_MANIFEST)
    question = read_json(QUESTION_BASELINE)
    combined = read_json(COMBINED_BASELINE)
    provenance = read_json(COMBINED_PROVENANCE)
    pipeline = read_json(PIPELINE_EVIDENCE)
    if heldout.get("publication_status") != "unpublished" or heldout.get("split") != "heldout":
        raise ValueError("recorded heldout result has an unexpected status")
    if heldout.get("policy_mode") != "configured_thresholds":
        raise ValueError("heldout result did not use configured thresholds")
    if manifest.get("actual_predictions") != 45 or manifest.get("error_count") != 0:
        raise ValueError("heldout evidence is incomplete")
    if question.get("split") != "heldout" or question.get("model_calls") != 0:
        raise ValueError("question baseline scope is incorrectly represented")
    if provenance.get("contributor_count") != 3:
        raise ValueError("combined-reference provenance is missing")
    if provenance.get("independent_decisions_available") is not False:
        raise ValueError("combined-reference provenance overstates independence")
    if pipeline.get("status") != "PASS" or pipeline.get("actions") != [
        "SILENT", "REACT", "REPLY"
    ]:
        raise ValueError("real pipeline evidence is incomplete")

    generated = datetime.now(timezone.utc)
    payload = {
        "artifact_version": M5_CLOSURE_ARTIFACT_VERSION,
        "publication_status": "published",
        "generated_at": generated.isoformat(),
        "published_at": generated.isoformat(),
        "split": "heldout",
        "primary_context_k": 3,
        "model_id": heldout["model_id"],
        "model_revision": "216d1ccb46a9e9b036eb9187b248db98480f77d4",
        "device": heldout["device"],
        "hardware": heldout["hardware"],
        "thresholds": heldout["thresholds"],
        "criteria": heldout["criteria"],
        "context_metrics": heldout["context_metrics"],
        "acceptance": {
            "implementation_completion": "PENDING_OWNER_APPROVAL",
            "model_performance": "NO_GO",
            "strict_spec_completion": "INCOMPLETE_BEDROCK_BASELINE",
            "production_readiness": False,
        },
        "baselines": {
            "always_reply_to_questions": {
                "status": "COMPLETE_HELDOUT",
                "scope": "heldout",
                "model_calls": 0,
                "aws_or_bedrock_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "metrics": question["metrics"],
                "source_evidence": str(QUESTION_BASELINE.relative_to(ROOT)),
            },
            "bedrock_judge": {
                "status": "NOT_RUN_REQUIRES_APPROVAL",
                "scope": "heldout",
                "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                "region": "us-east-2",
                "model_calls": 0,
                "max_calls": 15,
                "metrics": None,
                "pricing_usd_per_million_tokens": {"input": 1.10, "output": 5.50},
                "pricing_source": "https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/",
                "planned_output_token_cap_per_call": 8,
                "planned_prompt_utf8_byte_cap_per_call": 1000,
                "maximum_estimated_charge_usd": 0.01716,
                "cost_formula": "input_tokens*1.10/1000000 + output_tokens*5.50/1000000",
                "separate_owner_approval_required": True,
            },
        },
        "supplementary_combined_reference": {
            "label_basis": "combined_three_contributor_reference",
            "contributor_count": 3,
            "independent_decisions_available": False,
            "group_consensus_verified": False,
            "inter_rater_agreement_calculable": False,
            "development_metrics_k3": combined["context_metrics"]["3"],
            "reserve_count": 105,
            "reserve_opened": False,
        },
        "pipeline_evidence": {
            "status": pipeline["status"],
            "actions": pipeline["actions"],
            "bedrock_calls_made": pipeline["bedrock_calls_made"],
            "silent_and_react_bedrock_calls": 0,
            "reply_bedrock_calls": 1,
            "source": str(PIPELINE_EVIDENCE.relative_to(ROOT)),
        },
        "limitations": [
            "Heldout accuracy is 6/9 (66.7%).",
            "Heldout unnecessary-interruption rate is 2/3 (66.7%).",
            "Heldout REACT recall is unavailable because there are no unanimous REACT cases.",
            "Only three unanimous SILENT and six unanimous REPLY cases were scored.",
            "The combined 195-label reference does not retain independent decisions or verifiable consensus.",
            "The question-mark baseline ran locally on the same 15 heldout cases with zero model calls.",
            "The Bedrock heldout judge baseline was not run and has no fabricated metrics.",
            "This milestone does not establish production readiness, high availability, or generalization.",
        ],
        "minimum_remaining_strict_spec_actions": [
            "Run at most 15 Claude Haiku 4.5 Bedrock judge calls on those same heldout cases.",
        ],
        "run_manifest": manifest,
        "source_evidence": {
            "heldout_results": str(HELDOUT_RESULTS.relative_to(ROOT)),
            "heldout_results_sha256": sha256(HELDOUT_RESULTS),
            "heldout_manifest": str(HELDOUT_MANIFEST.relative_to(ROOT)),
            "heldout_manifest_sha256": sha256(HELDOUT_MANIFEST),
            "frozen_config": str(FROZEN_CONFIG.relative_to(ROOT)),
            "frozen_config_sha256": sha256(FROZEN_CONFIG),
            "question_baseline": str(QUESTION_BASELINE.relative_to(ROOT)),
            "combined_provenance": str(COMBINED_PROVENANCE.relative_to(ROOT)),
        },
        "reserve_opened": False,
        "heldout_rerun": False,
        "aws_resources_launched": False,
        "bedrock_calls_this_finalization": 0,
        "m6_started": False,
    }
    validate_m5_closure(payload)
    stamp = generated.strftime("%Y%m%dT%H%M%SZ")
    output = OUTPUT_ROOT / stamp
    output.mkdir(parents=True)
    result_path = output / "results.json"
    report_path = output / "M5_FINAL_ACCEPTANCE.md"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report(payload), encoding="utf-8")
    PUBLISHED.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"published={PUBLISHED} report={report_path} model_performance=NO_GO "
        "implementation_completion=PENDING_OWNER_APPROVAL bedrock_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
