"""Validated runtime configuration for the local Lurker backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config" / "default.yaml"


class AppConfig(BaseModel):
    """Configuration shared by the pipeline and API."""

    context_k: int = 3
    decider_timeout_ms: int = Field(default=120000, gt=0)
    decider_model_id: str
    decider_device: str = "cpu"
    reply_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    react_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    force_reply_on_mention: bool = False
    mock_decider: bool = False
    bedrock_model_id: str | None = None
    aws_region: str | None = None
    bedrock_max_calls: int | None = Field(default=None, ge=1)
    bedrock_allowed_latest_text: str | None = None
    data_dir: Path = ROOT / "data"
    results_dir: Path = ROOT / "results"

    @field_validator("context_k")
    @classmethod
    def validate_context_k(cls, value: int) -> int:
        if value not in {0, 3, 5}:
            raise ValueError("context_k must be one of 0, 3, or 5")
        return value

    @field_validator("decider_model_id", "decider_device")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value.strip()

    def require_runtime_ready(self) -> None:
        """Reject unsafe non-mock startup and incomplete Bedrock settings."""
        if not self.mock_decider and (
            self.reply_threshold is None or self.react_threshold is None
        ):
            raise ValueError(
                "non-mock mode requires human-approved reply_threshold and react_threshold"
            )
        if not self.mock_decider and (not self.bedrock_model_id or not self.aws_region):
            raise ValueError(
                "non-mock mode requires BEDROCK_MODEL_ID and AWS_REGION"
            )

    def policy_config(self) -> dict[str, float]:
        """Return thresholds in the shape expected by the shared pure policy."""
        if self.reply_threshold is None or self.react_threshold is None:
            raise ValueError("reply_threshold and react_threshold must be set")
        return {
            "reply_threshold": self.reply_threshold,
            "react_threshold": self.react_threshold,
        }


ENV_FIELDS = {
    "CONTEXT_K": "context_k",
    "DECIDER_TIMEOUT_MS": "decider_timeout_ms",
    "DECIDER_MODEL_ID": "decider_model_id",
    "DECIDER_DEVICE": "decider_device",
    "REPLY_THRESHOLD": "reply_threshold",
    "REACT_THRESHOLD": "react_threshold",
    "FORCE_REPLY_ON_MENTION": "force_reply_on_mention",
    "MOCK_DECIDER": "mock_decider",
    "BEDROCK_MODEL_ID": "bedrock_model_id",
    "AWS_REGION": "aws_region",
    "BEDROCK_MAX_CALLS": "bedrock_max_calls",
    "BEDROCK_ALLOWED_LATEST_TEXT": "bedrock_allowed_latest_text",
    "LURKER_DATA_DIR": "data_dir",
    "LURKER_RESULTS_DIR": "results_dir",
}


def _parse_env_value(field: str, value: str) -> Any:
    if field in {"mock_decider", "force_reply_on_mention"}:
        normalized = value.strip().lower()
        if normalized not in {"1", "0", "true", "false", "yes", "no", "on", "off"}:
            raise ValueError(f"{field} must be a boolean")
        return normalized in {"1", "true", "yes", "on"}
    if field in {"context_k", "decider_timeout_ms", "bedrock_max_calls"}:
        return int(value)
    if field in {"reply_threshold", "react_threshold"}:
        return float(value)
    return value


def load_config(
    path: Path = DEFAULT_CONFIG_PATH,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load YAML defaults and explicit environment overrides."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    env = os.environ if environ is None else environ
    for env_name, field in ENV_FIELDS.items():
        if env_name in env and env[env_name] != "":
            raw[field] = _parse_env_value(field, env[env_name])
    return AppConfig.model_validate(raw)
