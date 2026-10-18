"""Offline contracts for the guarded Playwright demo recorder."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_node_manifest_pins_playwright_and_exposes_both_modes() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["private"] is True
    assert package["devDependencies"]["playwright"] == "1.64.1"
    assert package["scripts"] == {
        "demo:record:preview": "node scripts/record_demo.mjs --mode preview",
        "demo:record:final": "node scripts/record_demo.mjs --mode final",
    }


def test_recorder_has_real_mode_and_one_call_fail_closed_guards() -> None:
    script = (ROOT / "scripts" / "record_demo.mjs").read_text(encoding="utf-8")
    required = {
        'DEMO_ALLOW_ONE_BEDROCK_CALL: "I_APPROVE_ONE_CALL"',
        'MOCK_DECIDER: "false"',
        'BEDROCK_MAX_CALLS: "1"',
        'AWS_REGION: "us-east-2"',
        "Expected ${expectedMode} Decider",
        "Frozen policy mismatch",
        "Final recording refuses to capture a MOCK banner",
        'delete serverEnv[name]',
        "submission_eligible: false",
        'manifest.submission_eligible = options.mode === "final"',
        "manifest.bedrock_call_delta !== expectedCalls",
    }
    for value in required:
        assert value in script


def test_recorder_uses_only_the_approved_synthetic_demo_messages() -> None:
    script = (ROOT / "scripts" / "record_demo.mjs").read_text(encoding="utf-8")
    for message in (
        "Let's meet at four tomorrow.",
        "Congratulations everyone—we made the hackathon finals! 🎉",
        "Lurker, please answer: why does the API return 401?",
    ):
        assert message in script
    assert "BEDROCK_ALLOWED_LATEST_TEXT: FINAL_REPLY_TEXT" in script


def test_demo_artifacts_and_node_modules_are_not_publishable() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in ignore
    assert "artifacts/demo-recordings/" in ignore


def test_pattern_scene_describes_the_frozen_reusable_contract() -> None:
    page = (ROOT / "web" / "pattern.html").read_text(encoding="utf-8")
    assert "Decide before generating" in page
    assert "ChimeInGate + ChimeInIntervention" in page
    assert "SILENT" in page
    assert "REACT" in page
    assert "REPLY" in page
    assert "k=3 · reply 0.20 · react 0.04" in page


def test_recording_guide_never_calls_preview_submission_eligible() -> None:
    guide = (ROOT / "DEMO_RECORDING.md").read_text(encoding="utf-8")
    assert "preview is not\nsubmission eligible" in guide
    assert "Do not run final mode" in guide
    assert "exactly one\nBedrock call" in guide
    assert "does not retry" in guide
