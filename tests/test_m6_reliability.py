"""Offline M6 reliability and replay contracts; never call models or AWS."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from scripts.demo_replay import (
    DEFAULT_FIXTURE,
    ROOT,
    ReplayError,
    load_fixture,
    run_replay,
    validate_unique_events,
)
from scripts.run_m6_acceptance import validate_acceptance_summaries
from scripts.run_m6_failure_drills import run_drills
from src.lurker.decider_adapter import DeciderAdapter


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m6_replay_fixture_is_public_bounded_and_complete() -> None:
    fixture = load_fixture()
    assert [item["expected_action"] for item in fixture["messages"]] == [
        "SILENT", "REACT", "REPLY"
    ]
    assert all(1 <= item["delay_before_seconds"] <= 3 for item in fixture["messages"])
    serialized = json.dumps(fixture).lower()
    assert "heldout" not in serialized
    assert "reserve" not in serialized
    assert "consensus" not in serialized
    assert "labels" not in serialized


def test_replay_refuses_non_demo_fixture_and_unauthorized_real_run(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "scenario.json"
    outside.write_text(DEFAULT_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ReplayError, match="inside data/demo"):
        load_fixture(outside)
    output = tmp_path / "real"
    with pytest.raises(ReplayError, match="allow-real-bedrock"):
        run_replay(
            base_url="http://127.0.0.1:9",
            output_dir=output,
            mode="real",
        )
    assert not output.exists()


def test_replay_evidence_code_does_not_persist_endpoint_addresses() -> None:
    replay_source = (ROOT / "scripts" / "demo_replay.py").read_text(encoding="utf-8")
    acceptance_source = (ROOT / "scripts" / "run_m6_acceptance.py").read_text(
        encoding="utf-8"
    )
    assert '"base_url": base_url' not in replay_source
    assert '"base_url": args.base_url' not in acceptance_source
    assert '"url": ws_url' not in replay_source


def test_duplicate_event_validator_catches_each_live_entity_type() -> None:
    transcript = [
        {"direction": "inbound", "event": {"type": "chat", "id": "m1"}},
        {"direction": "inbound", "event": {"type": "chat", "id": "m1"}},
    ]
    with pytest.raises(ReplayError, match="duplicate live events"):
        validate_unique_events(transcript)


def test_deterministic_failure_drills_pass_and_use_no_real_services(
    tmp_path: Path,
) -> None:
    output_dir, summary = run_drills(tmp_path)
    assert summary["status"] == "PASS"
    assert summary["real_decider_calls"] == 0
    assert summary["real_bedrock_calls"] == 0
    assert summary["aws_resources_launched"] is False
    assert summary["protected_evaluation_data_accessed"] is False
    timeout = json.loads((output_dir / "decider_timeout.json").read_text())
    bedrock = json.loads((output_dir / "bedrock_error.json").read_text())
    reconnect = json.loads((output_dir / "websocket_reconnect.json").read_text())
    assert timeout["decision"]["final_action"] == "SILENT"
    assert timeout["decision"]["error"] == "timeout"
    assert timeout["metrics"]["counters"]["bedrock_calls_made"] == 0
    assert bedrock["injected_reply_attempts"] == 1
    assert bedrock["metrics"]["counters"]["bedrock_calls_made"] == 0
    assert not any(
        event.get("type") == "chat" and event.get("is_agent")
        for event in bedrock["events"]
    )
    assert reconnect["connection_count"] == 2
    assert len({row["message_id"] for row in reconnect["durable_log_rows"]}) == 2
    assert all(reconnect["assertions"].values())


def test_actual_adapter_timeout_path_is_normalized_without_loading_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowEngine:
        def ask(self, state: dict, question: dict) -> object:
            del state, question
            time.sleep(0.02)
            return object()

    monkeypatch.setattr(
        "src.lurker.decider_adapter.load_engine", lambda model_id, device: SlowEngine()
    )
    adapter = DeciderAdapter("offline-stub", "cpu", timeout_ms=1)
    try:
        result = adapter.decide(
            {"agent_name": "Lurker", "recent_messages": [], "latest_message": {}},
            "Choose an action",
            ["SILENT", "REACT", "REPLY"],
        )
    finally:
        adapter._pool.shutdown(wait=True)
    assert result.choice is None
    assert result.error == "timeout"
    assert result.latency_ms >= 1


def test_three_replay_acceptance_validator_rejects_partial_or_dirty_runs() -> None:
    clean = {
        "status": "PASS",
        "acceptance_eligible": True,
        "actions": ["SILENT", "REACT", "REPLY"],
        "message_count": 3,
        "bedrock_calls_made": 1,
        "runtime_errors": 0,
        "duplicate_events": 0,
    }
    aggregate = validate_acceptance_summaries([clean.copy() for _ in range(3)])
    assert aggregate == {
        "replay_count": 3,
        "message_count": 9,
        "actions": {"SILENT": 3, "REACT": 3, "REPLY": 3},
        "bedrock_calls_made": 3,
        "runtime_errors": 0,
        "duplicate_events": 0,
    }
    with pytest.raises(ReplayError, match="exactly three"):
        validate_acceptance_summaries([clean.copy(), clean.copy()])
    dirty = clean | {"duplicate_events": 1}
    with pytest.raises(ReplayError, match="aggregate acceptance counts"):
        validate_acceptance_summaries([clean.copy(), clean.copy(), dirty])


def test_frontend_reconnects_reconciles_and_deduplicates() -> None:
    javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "async function reconcileAfterReconnect()" in javascript
    assert 'loadJson("/api/metrics")' in javascript
    assert 'loadJson("/api/decisions?limit=50")' in javascript
    assert "function mergeDecisions(...groups)" in javascript
    assert "reactionKeys: new Set()" in javascript
    assert "if (state.reactionKeys.has(reactionKey)) return;" in javascript
    assert "const reconnected = state.reconnectAttempts > 0;" in javascript


def test_m6_does_not_change_frozen_runtime_contract() -> None:
    expected = {
        "config/default.yaml": "7e36315af0cd8c389493a711b1b30cf9ca5ddee07b98ab42503a5a9d15e1b832",
        "decision_pattern/lurker_gate.py": "f3318f1ee95a661c720b1f6c770c926a3a1f8f7688e6b83f3825803dfb699a2b",
        "scripts/run_eval.py": "efa7a8107f322e045ab03ee686ebfe78d7289b89158134e5a2819095aa87724a",
    }
    assert {name: sha256(ROOT / name) for name in expected} == expected
    for path in (
        ROOT / "scripts" / "run_m6_failure_drills.py",
        ROOT / "scripts" / "demo_replay.py",
        ROOT / "scripts" / "run_m6_acceptance.py",
    ):
        source = path.read_text(encoding="utf-8").lower()
        assert "m5_heldout" not in source
        assert "locked_reserve" not in source
