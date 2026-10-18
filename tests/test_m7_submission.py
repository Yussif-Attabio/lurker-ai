"""Offline M7 reusable-pattern and submission-package contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from strands.interventions import Deny, Proceed

from decision_pattern import ChimeInGate, GateDecision, OPTIONS, QUESTION
from decision_pattern.strands_hook import ChimeInIntervention, state_from_invocation

ROOT = Path(__file__).resolve().parents[1]


class StubAdapter:
    """Return one normalized offline result and retain the received state."""

    def __init__(self, choice: str | None, confidence: float | None, error: str | None = None) -> None:
        self.result = SimpleNamespace(
            choice=choice,
            confidence=confidence,
            latency_ms=12.5,
            error=error,
        )
        self.state: dict | None = None

    def decide(self, state: dict, question: str, options: list[str]) -> object:
        assert question == QUESTION
        assert options == OPTIONS
        self.state = state
        return self.result


def sha256(path: Path) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("choice", "confidence", "expected"),
    [("SILENT", 0.9, "SILENT"), ("REACT", 0.7, "REACT"), ("REPLY", 0.8, "REPLY")],
)
def test_chime_in_gate_is_standalone_and_bounded(
    choice: str, confidence: float, expected: str
) -> None:
    adapter = StubAdapter(choice, confidence)
    gate = ChimeInGate(adapter, reply_threshold=0.2, react_threshold=0.04, k=3)
    history = [{"sender": "Alex", "text": str(index)} for index in range(5)]
    decision = gate.decide(history, {"sender": "Lea", "text": "latest"})
    assert isinstance(decision, GateDecision)
    assert decision.action == expected
    assert adapter.state is not None
    assert [row["text"] for row in adapter.state["recent_messages"]] == ["2", "3", "4"]


def test_chime_in_gate_fails_closed_on_error_and_low_confidence() -> None:
    failed = ChimeInGate(StubAdapter(None, None, "timeout"), 0.2, 0.04)
    assert failed.decide([], {"sender": "Lea", "text": "help"}).action == "SILENT"
    low = ChimeInGate(StubAdapter("REPLY", 0.19), 0.2, 0.04)
    decision = low.decide([], {"sender": "Lea", "text": "help"})
    assert (decision.action, decision.downgraded, decision.reason) == (
        "SILENT", True, "low_confidence"
    )


def test_official_strands_intervention_allows_only_reply() -> None:
    event = SimpleNamespace(
        messages=[
            {"role": "user", "content": [{"text": "hello"}]},
            {"role": "user", "content": [{"text": "latest"}]},
        ]
    )
    recent, latest = state_from_invocation(event)
    assert recent == [{"sender": "user", "text": "hello"}]
    assert latest == {"sender": "user", "text": "latest"}

    for choice, action_type in (("SILENT", Deny), ("REACT", Deny), ("REPLY", Proceed)):
        gate = ChimeInGate(StubAdapter(choice, 0.9), 0.2, 0.04)
        intervention = ChimeInIntervention(gate)
        action = intervention.before_invocation(event)
        assert isinstance(action, action_type)
        assert intervention.last_decision is not None
        assert intervention.last_decision.action == choice
        assert intervention.on_error == "deny"


def test_m7_docs_cover_submission_contract_with_real_evidence() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    article = (ROOT / "ARTICLE_NOTES.md").read_text(encoding="utf-8")
    demo = (ROOT / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
    pattern = (ROOT / "decision_pattern" / "README.md").read_text(encoding="utf-8")
    acceptance = (ROOT / "M7_ACCEPTANCE.md").read_text(encoding="utf-8")

    for required in (
        "## Architecture", "## Quick start", "## Reusable policy pattern",
        "## Submission results snapshot", "## Submission limitations", "## License",
    ):
        assert required in readme
    for tag in ("#strands-decider-2b", "#policy"):
        assert tag in readme and tag in article and tag in acceptance
    assert "2 minutes 45 seconds" in demo
    assert "actual Bedrock response" in demo
    assert "production readiness" in readme.lower()
    for required in (
        "## What it decides", "## Typed question and options", "## Confidence policy",
        "## Install", "## Drop-in example", "## Tune it on your data", "## Limitations",
    ):
        assert required in pattern

    published = json.loads((ROOT / "results" / "published.json").read_text())
    metrics = published["context_metrics"]["3"]
    assert metrics["accuracy"] == {"numerator": 6, "denominator": 9, "rate": 2 / 3}
    assert metrics["unnecessary_interruption_rate"] == {
        "numerator": 2, "denominator": 3, "rate": 2 / 3
    }
    recovery = json.loads(
        (ROOT / "data" / "m6_recovery_acceptance" / "20261018T201525Z" / "summary.json").read_text()
    )
    assert recovery["authorized_replays"]["passed"] == 3
    assert recovery["bedrock_calls"] == 3
    assert recovery["runtime_errors"] == 0
    assert "6/9 = 66.7%" in readme and "2/3 = 66.7%" in article


def test_m7_preserves_frozen_and_failed_evidence() -> None:
    expected = {
        "config/default.yaml": "7e36315af0cd8c389493a711b1b30cf9ca5ddee07b98ab42503a5a9d15e1b832",
        "decision_pattern/lurker_gate.py": "f3318f1ee95a661c720b1f6c770c926a3a1f8f7688e6b83f3825803dfb699a2b",
        "results/published.json": "35d97340eebba2a2a34ecdfd816246f8a81fdd00712531b2dba1d92ed239805c",
        "data/m6_acceptance/20261018T192248Z/summary.json": "c34f2cfacdb4102e9d4ca8b290e141da3640784254e29db310bf8020501b384b",
    }
    assert {name: sha256(ROOT / name) for name in expected} == expected
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "decision_pattern/chime_in_gate.py",
            "decision_pattern/strands_hook.py",
            "ARTICLE_NOTES.md",
            "DEMO_SCRIPT.md",
        )
    ).lower()
    assert "locked_reserve" not in source
    assert "m5_heldout" not in source


def test_example_is_short_and_does_not_run_on_import() -> None:
    path = ROOT / "decision_pattern" / "example_usage.py"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) <= 25
    assert 'if __name__ == "__main__":' in path.read_text(encoding="utf-8")
