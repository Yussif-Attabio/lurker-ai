"""Shared decision question and confidence policy used by app and evaluation."""

from __future__ import annotations

from typing import Any, Mapping

QUESTION = (
    "Given the recent conversation and latest message, what should Lurker do? "
    "Choose REPLY only if someone needs an answer or help that nobody has given yet. "
    "Otherwise, choose REACT if a brief emoji would meaningfully acknowledge a "
    "noteworthy achievement, gratitude, support, or shared humor. Otherwise choose "
    "SILENT, including for routine updates, ordinary back-and-forth, already-handled "
    "points, or when a reaction would add noise."
)

OPTIONS = ["SILENT", "REACT", "REPLY"]

POLICY_DESCRIPTIONS = {
    "SILENT": "Stay quiet when speaking or reacting would add noise.",
    "REACT": "Add one lightweight local emoji when acknowledgment has clear value.",
    "REPLY": "Ask Bedrock for a concise answer only when someone still needs help.",
    "LOW_CONFIDENCE": "Downgrade REACT or REPLY to SILENT below its approved threshold.",
    "ERROR": "Fail closed to SILENT if the Decider errors or returns an unknown choice.",
}


def _config_value(config: object, key: str) -> float | None:
    if isinstance(config, Mapping):
        value = config.get(key)
    else:
        value = getattr(config, key)
    return None if value is None else float(value)


def apply_policy(result: Any, config: object) -> tuple[str, bool, str]:
    """Apply the human-owned confidence thresholds with a SILENT safe default."""
    if result.error:
        return "SILENT", True, "decider_error"
    if result.choice == "SILENT":
        return "SILENT", False, "chosen"
    if result.choice not in {"REACT", "REPLY"}:
        return "SILENT", True, "decider_error"

    key = "reply_threshold" if result.choice == "REPLY" else "react_threshold"
    threshold = _config_value(config, key)
    if threshold is None:
        raise ValueError(f"{key} must be set before applying the real-model policy")
    if result.confidence >= threshold:
        return result.choice, False, "confident"
    return "SILENT", True, "low_confidence"
