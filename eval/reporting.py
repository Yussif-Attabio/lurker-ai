"""Generate evidence files from real evaluation rows."""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.metrics_def import meets_criteria


def rate_text(metric: dict[str, Any]) -> str:
    """Format a rate with raw counts."""
    rate = metric["rate"]
    suffix = "N/A" if rate is None else f"{rate * 100:.1f}%"
    return f"{metric['numerator']}/{metric['denominator']} ({suffix})"


def _latency(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f} ms"


def build_report(summary: dict[str, Any]) -> str:
    """Build the Markdown report saved with a real evaluation run."""
    split = summary["split"]
    thresholds = summary["thresholds"]
    lines = [
        "# Lurker AI evaluation report",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Split: `{split}`",
        f"- Model: `{summary['model_id']}`",
        f"- Device: `{summary['device']}`",
        f"- Hardware: {summary['hardware']}",
        f"- Policy mode: `{summary['policy_mode']}`",
        f"- Reply threshold: `{thresholds['reply_threshold']}`",
        f"- React threshold: `{thresholds['react_threshold']}`",
        "",
        "## Human-approved success criteria",
        "",
        f"- Accuracy >= {summary['criteria']['accuracy_min'] * 100:.0f}%",
        "- Unnecessary-interruption rate <= "
        f"{summary['criteria']['unnecessary_interruption_rate_max'] * 100:.0f}%",
        f"- Missed-help rate <= {summary['criteria']['missed_help_rate_max'] * 100:.0f}%",
        "",
    ]
    if summary["policy_mode"] != "configured_thresholds":
        lines.extend(
            [
                "> This is an unthresholded tuning run. Use `tune_thresholds.py`, have a human choose thresholds, update config, and rerun before making a go/no-go decision.",
                "",
            ]
        )

    lines.extend(
        [
            "## Context comparison",
            "",
            "| k | Scored | Ambiguous | Errors | Accuracy | Unnecessary interruption | Missed help | Latency p50 | Latency p95 | Criteria |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, metrics in summary["context_metrics"].items():
        criteria_status = (
            "PASS" if meets_criteria(metrics, summary["criteria"]) else "FAIL"
        )
        if summary["policy_mode"] != "configured_thresholds":
            criteria_status = "PENDING"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(key),
                    str(metrics["non_ambiguous_count"]),
                    str(metrics["ambiguous_count"]),
                    str(metrics.get("error_count", 0)),
                    rate_text(metrics["accuracy"]),
                    rate_text(metrics["unnecessary_interruption_rate"]),
                    rate_text(metrics["missed_help_rate"]),
                    _latency(metrics["latency_ms"]["p50"]),
                    _latency(metrics["latency_ms"]["p95"]),
                    criteria_status,
                ]
            )
            + " |"
        )

    lines.extend(["", "## Low-confidence handling", ""])
    for key, metrics in summary["context_metrics"].items():
        low = metrics["low_confidence"]
        lines.extend(
            [
                f"### k = {key}",
                "",
                f"- Downgraded: {low['downgraded_count']}",
                f"- Accuracy before downgrade: {rate_text(low['before_accuracy'])}",
                f"- Accuracy after downgrade: {rate_text(low['after_accuracy'])}",
                "",
            ]
        )

    lines.extend(["## Calibration", ""])
    for key, metrics in summary["context_metrics"].items():
        lines.extend(
            [
                f"### k = {key}",
                "",
                "| Confidence bin | Correct / count | Accuracy |",
                "|---|---:|---:|",
            ]
        )
        for bucket in metrics["calibration"]:
            accuracy = "N/A" if bucket["rate"] is None else f"{bucket['rate'] * 100:.1f}%"
            lines.append(
                f"| {bucket['bin']} | {bucket['numerator']}/{bucket['denominator']} | {accuracy} |"
            )
        lines.append("")

    ambiguous = [
        {**row, "context_k": key}
        for key, metrics in summary["context_metrics"].items()
        for row in metrics["ambiguous_predictions"]
    ]
    lines.extend(["## Ambiguous cases", ""])
    if not ambiguous:
        lines.append("No human-ambiguous cases were present in this split.")
    else:
        lines.extend(
            [
                "Ambiguous cases are listed but excluded from every scored rate.",
                "",
                "| k | ID | Raw choice | Final action | Confidence |",
                "|---:|---|---|---|---:|",
            ]
        )
        for row in ambiguous:
            lines.append(
                f"| {row['context_k']} | {row['id']} | {row['raw_choice']} | "
                f"{row['final_action']} | {float(row['confidence']):.4f} |"
            )

    lines.extend(
        [
            "",
            "## Decision status",
            "",
            "This report is evidence only. The project owner must record the final decision in `GO_NOGO.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def build_m5_report(summary: dict[str, Any]) -> str:
    """Build the final held-out and baseline comparison report."""
    primary_key = str(summary["primary_context_k"])
    primary = summary["context_metrics"][primary_key]
    lines = [
        "# Lurker AI M5 final evaluation",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Split: `{summary['split']}`",
        f"- Model: `{summary['model_id']}`",
        f"- Device: `{summary['device']}`",
        f"- Hardware: {summary['hardware']}",
        f"- Pre-registered context: k = {primary_key}",
        f"- Reply threshold: {summary['thresholds']['reply_threshold']}",
        f"- REACT threshold: {summary['thresholds']['react_threshold']}",
        f"- Primary status: **{'PASS' if meets_criteria(primary, summary['criteria']) else 'FAIL'}**",
        "",
        "## Held-out context comparison",
        "",
        "| k | Scored | Ambiguous | Errors | Accuracy | Unnecessary interruption | Missed help | p50 | p95 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, metrics in summary["context_metrics"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    key,
                    str(metrics["non_ambiguous_count"]),
                    str(metrics["ambiguous_count"]),
                    str(metrics["error_count"]),
                    rate_text(metrics["accuracy"]),
                    rate_text(metrics["unnecessary_interruption_rate"]),
                    rate_text(metrics["missed_help_rate"]),
                    _latency(metrics["latency_ms"]["p50"]),
                    _latency(metrics["latency_ms"]["p95"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Baseline comparison at the pre-registered context",
            "",
            "| System | Model calls | Errors | Accuracy | Unnecessary interruption | Missed help | p50 | p95 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    systems = {"Strands Decider": {"metrics": primary, "model_calls": 0}, **summary["baselines"]}
    for name, baseline in systems.items():
        metrics = baseline["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    name.replace("_", " "),
                    str(baseline["model_calls"]),
                    str(metrics["error_count"]),
                    rate_text(metrics["accuracy"]),
                    rate_text(metrics["unnecessary_interruption_rate"]),
                    rate_text(metrics["missed_help_rate"]),
                    _latency(metrics["latency_ms"]["p50"]),
                    _latency(metrics["latency_ms"]["p95"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Ambiguous cases are excluded from scored rates. This synthetic held-out evaluation is small and does not establish production readiness or statistical generalization. The project owner must record the final M5 GO/NO-GO.",
            "",
        ]
    )
    return "\n".join(lines)


def create_run_directory(root: Path) -> Path:
    """Create a unique UTC-stamped directory for real run artifacts."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = root / stamp
    suffix = 1
    while candidate.exists():
        candidate = root / f"{stamp}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def base_summary(
    *,
    split: str,
    model_id: str,
    device: str,
    policy_mode: str,
    thresholds: dict[str, float | None],
    criteria: dict[str, float],
    context_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Create metadata shared by JSON and Markdown evidence."""
    return {
        "artifact_version": "lurker-eval-v1",
        "publication_status": "unpublished",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "model_id": model_id,
        "device": device,
        "hardware": f"{platform.system()} {platform.machine()} / {platform.processor() or 'processor unknown'}",
        "policy_mode": policy_mode,
        "thresholds": thresholds,
        "criteria": criteria,
        "context_metrics": context_metrics,
    }


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    """Write stable, human-readable summary JSON."""
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
