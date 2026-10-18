"""Offline least-privilege checks for the proposed M6 IAM recovery policy."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "deploy" / "m6_bedrock_invoke_policy.template.json"
PROFILE = (
    "arn:aws:bedrock:us-east-2:<ACCOUNT_ID>:inference-profile/"
    "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
MODELS = {
    "arn:aws:bedrock:us-east-1::foundation-model/"
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-east-2::foundation-model/"
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-west-2::foundation-model/"
    "anthropic.claude-haiku-4-5-20251001-v1:0",
}


def load_statements() -> list[dict]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))["Statement"]


def test_policy_grants_only_invoke_model_without_wildcard_actions() -> None:
    statements = load_statements()
    assert len(statements) == 2
    assert {row["Effect"] for row in statements} == {"Allow"}
    assert {row["Action"] for row in statements} == {"bedrock:InvokeModel"}
    assert all("*" not in row["Action"] for row in statements)


def test_profile_authorization_is_exact_and_unconditional() -> None:
    profile_statement = load_statements()[0]
    assert profile_statement["Resource"] == PROFILE
    assert "Condition" not in profile_statement
    assert "*" not in profile_statement["Resource"]


def test_all_profile_destinations_are_exact_and_profile_conditioned() -> None:
    model_statement = load_statements()[1]
    assert set(model_statement["Resource"]) == MODELS
    assert model_statement["Condition"] == {
        "ArnEquals": {"bedrock:InferenceProfileArn": PROFILE}
    }
    assert all("*" not in resource for resource in model_statement["Resource"])


def test_policy_does_not_grant_admin_streaming_or_control_plane_access() -> None:
    serialized = POLICY_PATH.read_text(encoding="utf-8")
    forbidden = (
        "bedrock:*",
        "InvokeModelWithResponseStream",
        "ConverseStream",
        "CreateModel",
        "PutModel",
        "DeleteModel",
        '"Resource": "*"',
    )
    assert not any(value in serialized for value in forbidden)
