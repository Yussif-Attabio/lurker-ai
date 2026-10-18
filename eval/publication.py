"""Validate and explicitly publish final M5 evaluation summaries."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

M5_ARTIFACT_VERSION = "lurker-m5-v1"
M5_CLOSURE_ARTIFACT_VERSION = "lurker-m5-closure-v1"
PUBLISHED_FILENAME = "published.json"
CONTEXT_KEYS = {"0", "3", "5"}


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _validate_rate(metric: Any, label: str) -> None:
    if not isinstance(metric, dict):
        raise ValueError(f"{label} must contain numerator, denominator, and rate")
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    rate = metric.get("rate")
    if isinstance(numerator, bool) or not isinstance(numerator, int):
        raise ValueError(f"{label}.numerator must be an integer")
    if isinstance(denominator, bool) or not isinstance(denominator, int):
        raise ValueError(f"{label}.denominator must be an integer")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError(f"{label} has invalid raw counts")
    if denominator == 0:
        if rate is not None:
            raise ValueError(f"{label}.rate must be null when denominator is zero")
        return
    observed = _finite_number(rate, f"{label}.rate")
    expected = numerator / denominator
    if not math.isclose(observed, expected, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError(f"{label}.rate does not match its raw counts")


def _validate_metrics(metrics: Any, label: str) -> None:
    if not isinstance(metrics, dict):
        raise ValueError(f"{label} must be an object")
    for key in (
        "accuracy",
        "unnecessary_interruption_rate",
        "missed_help_rate",
    ):
        _validate_rate(metrics.get(key), f"{label}.{key}")
    for key in ("total_count", "non_ambiguous_count", "ambiguous_count", "error_count"):
        value = metrics.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{label}.{key} must be a non-negative integer")
    if metrics["total_count"] != metrics["non_ambiguous_count"] + metrics["ambiguous_count"]:
        raise ValueError(f"{label} total count does not match scored plus ambiguous counts")
    latency = metrics.get("latency_ms")
    if not isinstance(latency, dict):
        raise ValueError(f"{label}.latency_ms must be an object")
    for key in ("p50", "p95"):
        value = latency.get(key)
        if value is not None and _finite_number(value, f"{label}.latency_ms.{key}") < 0:
            raise ValueError(f"{label}.latency_ms.{key} must not be negative")
    calibration = metrics.get("calibration")
    if not isinstance(calibration, list) or len(calibration) != 4:
        raise ValueError(f"{label}.calibration must contain four confidence bins")
    for index, bucket in enumerate(calibration):
        if not isinstance(bucket, dict) or not isinstance(bucket.get("bin"), str):
            raise ValueError(f"{label}.calibration[{index}] is invalid")
        _validate_rate(bucket, f"{label}.calibration[{index}]")


def validate_m5_summary(payload: Any, *, expected_status: str | None = None) -> dict[str, Any]:
    """Validate the stable summary contract consumed by the Evaluation tab."""
    if not isinstance(payload, dict):
        raise ValueError("M5 summary must be a JSON object")
    if payload.get("artifact_version") != M5_ARTIFACT_VERSION:
        raise ValueError(f"artifact_version must be {M5_ARTIFACT_VERSION}")
    status = payload.get("publication_status")
    if status not in {"ready", "published"}:
        raise ValueError("publication_status must be ready or published")
    if expected_status is not None and status != expected_status:
        raise ValueError(f"publication_status must be {expected_status}")
    if payload.get("split") != "heldout":
        raise ValueError("final M5 summary must use the heldout split")

    primary_context = payload.get("primary_context_k")
    if primary_context not in {0, 3, 5}:
        raise ValueError("primary_context_k must be 0, 3, or 5")
    contexts = payload.get("context_metrics")
    if not isinstance(contexts, dict) or set(contexts) != CONTEXT_KEYS:
        raise ValueError("context_metrics must contain exactly k=0, k=3, and k=5")
    for key, metrics in contexts.items():
        _validate_metrics(metrics, f"context_metrics.{key}")

    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be an object")
    for key in ("reply_threshold", "react_threshold"):
        value = _finite_number(thresholds.get(key), f"thresholds.{key}")
        if not 0 <= value <= 1:
            raise ValueError(f"thresholds.{key} must be between 0 and 1")

    criteria = payload.get("criteria")
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be an object")
    for key in (
        "accuracy_min",
        "unnecessary_interruption_rate_max",
        "missed_help_rate_max",
    ):
        value = _finite_number(criteria.get(key), f"criteria.{key}")
        if not 0 <= value <= 1:
            raise ValueError(f"criteria.{key} must be between 0 and 1")

    baselines = payload.get("baselines")
    if not isinstance(baselines, dict) or set(baselines) != {
        "always_reply_to_questions",
        "bedrock_judge",
    }:
        raise ValueError("baselines must contain both required comparisons")
    for name, baseline in baselines.items():
        if not isinstance(baseline, dict):
            raise ValueError(f"baselines.{name} must be an object")
        _validate_metrics(baseline.get("metrics"), f"baselines.{name}.metrics")
        calls = baseline.get("model_calls")
        if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
            raise ValueError(f"baselines.{name}.model_calls must be a non-negative integer")
        for token_key in ("input_tokens", "output_tokens"):
            tokens = baseline.get(token_key)
            if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
                raise ValueError(f"baselines.{name}.{token_key} must be a non-negative integer")
        if baseline["metrics"]["total_count"] != contexts[str(primary_context)]["total_count"]:
            raise ValueError(f"baselines.{name} must cover the primary heldout cases")
    if baselines["always_reply_to_questions"]["model_calls"] != 0:
        raise ValueError("the question-mark baseline must make zero model calls")
    bedrock_calls = baselines["bedrock_judge"]["model_calls"]
    if bedrock_calls > 15:
        raise ValueError("Bedrock judge model_calls exceeds the approved maximum of 15")

    manifest = payload.get("run_manifest")
    if not isinstance(manifest, dict) or manifest.get("mock") is not False:
        raise ValueError("run_manifest must prove mock=false")
    expected = manifest.get("expected_predictions")
    actual = manifest.get("actual_predictions")
    if (
        isinstance(expected, bool)
        or not isinstance(expected, int)
        or expected <= 0
        or actual != expected
    ):
        raise ValueError("run_manifest must prove a complete prediction set")
    context_total = sum(metrics["total_count"] for metrics in contexts.values())
    if expected != context_total:
        raise ValueError("run_manifest prediction count does not match context metrics")
    if manifest.get("split") != "heldout" or int(manifest.get("error_count", -1)) != 0:
        raise ValueError("run_manifest must prove an error-free heldout run")

    for key in ("generated_at", "model_id", "device", "hardware"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be non-empty text")
    return payload


def validate_m5_closure(payload: Any, *, expected_status: str = "published") -> dict[str, Any]:
    """Validate an honest M5 NO-GO closure with explicitly incomplete baselines."""
    if not isinstance(payload, dict):
        raise ValueError("M5 closure must be a JSON object")
    if payload.get("artifact_version") != M5_CLOSURE_ARTIFACT_VERSION:
        raise ValueError(f"artifact_version must be {M5_CLOSURE_ARTIFACT_VERSION}")
    if payload.get("publication_status") != expected_status:
        raise ValueError(f"publication_status must be {expected_status}")
    if payload.get("split") != "heldout" or payload.get("primary_context_k") != 3:
        raise ValueError("M5 closure must preserve the heldout k=3 contract")
    contexts = payload.get("context_metrics")
    if not isinstance(contexts, dict) or set(contexts) != CONTEXT_KEYS:
        raise ValueError("context_metrics must contain exactly k=0, k=3, and k=5")
    for key, metrics in contexts.items():
        _validate_metrics(metrics, f"context_metrics.{key}")
    primary = contexts["3"]
    if primary["accuracy"] != {
        "numerator": 6,
        "denominator": 9,
        "rate": 2 / 3,
    }:
        raise ValueError("closure must preserve the original 6/9 heldout accuracy")
    if primary["unnecessary_interruption_rate"] != {
        "numerator": 2,
        "denominator": 3,
        "rate": 2 / 3,
    }:
        raise ValueError("closure must preserve the original 2/3 interruption rate")
    react_recall = primary.get("react_recall")
    if react_recall != {"numerator": 0, "denominator": 0, "rate": None}:
        raise ValueError("closure must preserve unavailable heldout REACT recall")
    thresholds = payload.get("thresholds")
    if thresholds != {"reply_threshold": 0.2, "react_threshold": 0.04}:
        raise ValueError("closure thresholds differ from the frozen configuration")
    acceptance = payload.get("acceptance")
    if not isinstance(acceptance, dict):
        raise ValueError("closure acceptance status is missing")
    if acceptance.get("model_performance") != "NO_GO":
        raise ValueError("closure must preserve the heldout performance NO-GO")
    implementation_status = acceptance.get("implementation_completion")
    if implementation_status not in {"PENDING_OWNER_APPROVAL", "TECHNICALLY_COMPLETE"}:
        raise ValueError("implementation closure has an unsupported approval status")
    if implementation_status == "TECHNICALLY_COMPLETE":
        owner_approval = payload.get("owner_approval")
        if not isinstance(owner_approval, dict) or owner_approval.get("status") != "APPROVED":
            raise ValueError("technical completion requires recorded owner approval")
        for key in ("approved_at", "scope"):
            value = owner_approval.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"owner_approval.{key} must be non-empty text")
    if acceptance.get("strict_spec_completion") != "INCOMPLETE_BEDROCK_BASELINE":
        raise ValueError("strict spec status must disclose the incomplete Bedrock baseline")
    baselines = payload.get("baselines")
    if not isinstance(baselines, dict) or set(baselines) != {
        "always_reply_to_questions", "bedrock_judge"
    }:
        raise ValueError("closure must disclose both baseline statuses")
    question = baselines["always_reply_to_questions"]
    if question.get("status") != "COMPLETE_HELDOUT" or question.get("scope") != "heldout":
        raise ValueError("question-mark baseline must cover the heldout cases")
    if question.get("model_calls") != 0 or question.get("aws_or_bedrock_calls") != 0:
        raise ValueError("question-mark baseline must be free and local")
    _validate_metrics(question.get("metrics"), "baselines.always_reply_to_questions.metrics")
    if question["metrics"]["total_count"] != primary["total_count"]:
        raise ValueError("question-mark baseline must cover all heldout cases")
    bedrock = baselines["bedrock_judge"]
    if bedrock.get("status") != "NOT_RUN_REQUIRES_APPROVAL":
        raise ValueError("Bedrock baseline status must remain not run")
    if bedrock.get("model_calls") != 0 or bedrock.get("metrics") is not None:
        raise ValueError("Bedrock baseline must not contain fabricated evidence")
    if bedrock.get("max_calls") != 15:
        raise ValueError("Bedrock baseline plan must remain capped at 15 calls")
    manifest = payload.get("run_manifest")
    if not isinstance(manifest, dict) or manifest.get("mock") is not False:
        raise ValueError("closure must preserve the real heldout run manifest")
    if manifest.get("actual_predictions") != 45 or manifest.get("expected_predictions") != 45:
        raise ValueError("closure must preserve exactly 45 heldout predictions")
    if manifest.get("error_count") != 0:
        raise ValueError("closure heldout run contains errors")
    if payload.get("reserve_opened") is not False or payload.get("heldout_rerun") is not False:
        raise ValueError("closure reports prohibited evaluation access")
    return payload


def load_published_results(results_dir: Path) -> dict[str, Any] | None:
    """Load the explicitly published M5 result, or return None when absent."""
    path = results_dir / PUBLISHED_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"published evaluation is unreadable: {exc}") from exc
    if payload.get("artifact_version") == M5_CLOSURE_ARTIFACT_VERSION:
        return validate_m5_closure(payload)
    return validate_m5_summary(payload, expected_status="published")


def publish_results(source: Path, results_dir: Path) -> Path:
    """Atomically publish one ready M5 summary without overwriting prior evidence."""
    root = results_dir.resolve()
    resolved_source = source.resolve()
    if root not in resolved_source.parents:
        raise ValueError("M5 result source must be inside the configured results directory")
    target = root / PUBLISHED_FILENAME
    if target.exists():
        raise FileExistsError(f"published evaluation already exists: {target}")
    try:
        payload = json.loads(resolved_source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"M5 result source is unreadable: {exc}") from exc
    validate_m5_summary(payload, expected_status="ready")
    payload = {
        **payload,
        "publication_status": "published",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "source_results": str(resolved_source.relative_to(root)),
    }
    validate_m5_summary(payload, expected_status="published")
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / f".{PUBLISHED_FILENAME}.tmp"
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target
