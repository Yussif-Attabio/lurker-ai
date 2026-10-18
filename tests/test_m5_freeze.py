"""Offline checks for the owner-approved M5 evaluation freeze."""

from __future__ import annotations

from scripts.verify_m5_freeze import verify_freeze


def test_frozen_m5_contract_and_preserved_evidence_pass() -> None:
    result = verify_freeze()
    assert result["status"] == "PASS"
    assert result["heldout_dataset_opened"] is False
    assert result["model_loaded"] is False
    assert result["aws_or_bedrock_calls"] == 0
    assert result["checks"]["tuning_dataset_isolation"]["row_count"] == 30
    assert all(check["pass"] for check in result["checks"].values())
