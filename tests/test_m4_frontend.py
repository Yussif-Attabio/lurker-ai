"""Offline M4 frontend contracts; these tests never call real models or AWS."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from decision_pattern.lurker_gate import OPTIONS, POLICY_DESCRIPTIONS, QUESTION
from src.lurker.api import create_app
from src.lurker.bedrock_replier import MockBedrockReplier
from src.lurker.config import AppConfig
from src.lurker.mock_decider import MockDecider


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"


def frontend_config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "context_k": 3,
            "decider_timeout_ms": 120000,
            "decider_model_id": MODEL_ID,
            "decider_device": "cpu",
            "reply_threshold": 0.20,
            "react_threshold": 0.04,
            "force_reply_on_mention": False,
            "mock_decider": True,
            "data_dir": tmp_path / "data",
            "results_dir": tmp_path / "results",
        }
    )


def frontend_client(tmp_path: Path) -> TestClient:
    app = create_app(
        config=frontend_config(tmp_path),
        adapter=MockDecider(),
        replier=MockBedrockReplier(),
    )
    return TestClient(app)


def test_frontend_and_assets_are_served_without_cache(tmp_path: Path) -> None:
    with frontend_client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.headers["cache-control"] == "no-cache"
        assert "Lurker AI - Quiet by design" in page.text
        assert "MOCK DECIDER" in page.text

        css = client.get("/assets/styles.css")
        javascript = client.get("/assets/app.js")
        assert css.status_code == 200
        assert css.headers["content-type"].startswith("text/css")
        assert javascript.status_code == 200
        assert "javascript" in javascript.headers["content-type"]
        assert css.headers["cache-control"] == "no-cache"
        assert javascript.headers["cache-control"] == "no-cache"
        assert client.get("/assets/missing.js").status_code == 404


def test_about_endpoint_uses_shared_policy_constants(tmp_path: Path) -> None:
    with frontend_client(tmp_path) as client:
        response = client.get("/api/about")
        assert response.status_code == 200
        about = response.json()
        assert about["question"] == QUESTION
        assert [item["action"] for item in about["options"]] == OPTIONS
        assert [item["description"] for item in about["options"]] == [
            POLICY_DESCRIPTIONS[action] for action in OPTIONS
        ]
        assert about["policy"] == {
            "context_k": 3,
            "reply_threshold": 0.20,
            "react_threshold": 0.04,
            "force_reply_on_mention": False,
            "low_confidence": POLICY_DESCRIPTIONS["LOW_CONFIDENCE"],
            "error": POLICY_DESCRIPTIONS["ERROR"],
        }


def test_frontend_contains_required_m4_controls() -> None:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    required_ids = {
        "message-list",
        "sender",
        "third-name",
        "message-input",
        "send-button",
        "mock-banner",
        "decision-action",
        "confidence-value",
        "decision-latency",
        "decision-log-body",
        "about-panel",
        "evaluation-tab",
        "evaluation-panel",
        "evaluation-context-body",
        "evaluation-baseline-body",
        "evaluation-calibration-body",
    }
    for element_id in required_ids:
        assert f'id="{element_id}"' in html
    assert ">Evaluation<" in html
    assert "No final M5 result is published" in html


def test_frontend_uses_safe_same_origin_browser_contracts() -> None:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "innerHTML" not in javascript
    assert "eval(" not in javascript
    assert 'new WebSocket(`${protocol}//${window.location.host}/ws`)' in javascript
    assert 'loadJson("/api/eval/latest")' in javascript
    assert 'summary.split !== "heldout"' in javascript


def test_frontend_websocket_inputs_cover_all_three_actions(tmp_path: Path) -> None:
    with frontend_client(tmp_path) as client:
        with client.websocket_connect("/ws") as websocket:
            cases = [
                ("Alex", "Let's meet at four tomorrow.", "SILENT", 3),
                ("Lea", "Great news, we passed!", "REACT", 4),
                ("Sam", "Can someone explain this API error?", "REPLY", 4),
            ]
            for sender, text, expected, event_count in cases:
                websocket.send_json({"type": "message", "sender": sender, "text": text})
                events = [websocket.receive_json() for _ in range(event_count)]
                decision = next(item for item in events if item["type"] == "decision")
                assert decision["final_action"] == expected

        counters = client.get("/api/metrics").json()["counters"]
        assert counters == {
            "messages_read": 3,
            "silent": 1,
            "react": 1,
            "reply": 1,
            "downgraded": 0,
            "errors": 0,
            "bedrock_calls_made": 0,
            "bedrock_calls_avoided_vs_every_message": 3,
        }
