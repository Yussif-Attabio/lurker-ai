"""Offline checks that preserve M0's real-service boundaries."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

from scripts import smoke_bedrock, smoke_decider

ROOT = Path(__file__).resolve().parents[1]


def test_decider_smoke_has_the_five_required_cases() -> None:
    assert set(smoke_decider.CASES) == {
        "question",
        "joke",
        "plan",
        "already_answered",
        "ambiguous",
    }


def test_bedrock_smoke_refuses_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    assert smoke_bedrock.main() == 2


def test_provisional_m1_thresholds_are_human_approved_and_rollback_is_preserved() -> None:
    config = yaml.safe_load((ROOT / "config/default.yaml").read_text())
    rollback = yaml.safe_load(
        (ROOT / "config/default.pre_m1_provisional.yaml").read_text()
    )
    assert config["context_k"] == 3
    assert config["reply_threshold"] == 0.20
    assert config["react_threshold"] == 0.04
    assert rollback["context_k"] == 3
    assert rollback["reply_threshold"] is None
    assert rollback["react_threshold"] is None
    decision = (ROOT / "GO_NOGO.md").read_text()
    assert "Decision: **PROVISIONAL GO**" in decision


def test_only_adapter_imports_strands_decider() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or path.name == "decider_adapter.py":
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "strands_decider" or name.startswith("strands_decider.") for name in names):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_real_scenario_file_has_no_unreviewed_rows() -> None:
    rows = [line for line in (ROOT / "eval/scenarios.jsonl").read_text().splitlines() if line]
    for line in rows:
        row = json.loads(line)
        assert set(row["labels"]) == {"a1", "a2", "a3"}
        assert row["consensus"] in {"SILENT", "REACT", "REPLY", "AMBIGUOUS"}


def test_candidate_scenarios_are_unlabeled_and_well_formed() -> None:
    allowed_categories = {
        "direct_request",
        "joke",
        "technical_question",
        "ongoing_discussion",
        "already_answered",
        "mention",
        "casual",
        "ambiguous",
    }
    rows = [
        json.loads(line)
        for line in (ROOT / "eval/scenario_candidates.jsonl").read_text().splitlines()
        if line
    ]
    assert len(rows) >= 40
    assert len({row["id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["category"] in allowed_categories
        assert len(row["history"]) <= 5
        assert set(row["message"]) == {"sender", "text"}
        assert "labels" not in row
        assert "consensus" not in row
        assert "split" not in row
