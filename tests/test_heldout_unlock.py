"""Synthetic-only tests for the guarded, one-time held-out materialization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_heldout_unlock import guard_unlock, prepare_locked_input


def synthetic_scenario(split: str = "heldout") -> dict:
    return {
        "id": "synthetic-1",
        "split": split,
        "category": "technical_question",
        "history": [],
        "message": {"sender": "Alex", "text": "Synthetic test only."},
        "labels": {"a1": "REPLY", "a2": "REPLY", "a3": "REPLY"},
        "consensus": "REPLY",
        "notes": "synthetic fixture",
    }


def test_unlock_requires_explicit_flag_and_authorization() -> None:
    with pytest.raises(ValueError, match="allow-heldout"):
        guard_unlock(False, "approval-1")
    with pytest.raises(ValueError, match="authorization ID"):
        guard_unlock(True, "")
    guard_unlock(True, "approval-1")


def test_locked_input_is_exclusive_and_auditable(tmp_path: Path) -> None:
    source = tmp_path / "mixed.jsonl"
    source.write_text(json.dumps(synthetic_scenario()) + "\n", encoding="utf-8")
    output = tmp_path / "run" / "heldout_locked.jsonl"
    manifest = prepare_locked_input(
        source, output, "synthetic-approval", expected_count=1
    )
    assert manifest["scenario_count"] == 1
    assert manifest["scenario_text_printed"] is False
    assert output.is_file()
    assert output.with_suffix(".jsonl.manifest.json").is_file()
    with pytest.raises(FileExistsError):
        prepare_locked_input(source, output, "synthetic-approval", expected_count=1)
