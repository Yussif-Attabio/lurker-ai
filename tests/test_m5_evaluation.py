"""Offline M5 publication, baseline, and Evaluation-tab contracts."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eval.baselines import (
    BaselineError,
    BedrockJudge,
    evaluate_bedrock_baseline,
    evaluate_question_mark_baseline,
)
from eval.metrics_def import compute_metrics
from eval.publication import (
    load_published_results,
    publish_results,
    validate_m5_closure,
    validate_m5_summary,
)
from scripts.publish_m5 import assemble_summary
from scripts.run_eval import validate_evaluation_rows, validate_scenarios
from src.lurker.api import create_app
from src.lurker.bedrock_replier import MockBedrockReplier
from src.lurker.config import AppConfig
from src.lurker.mock_decider import MockDecider
from src.lurker.schemas import Scenario

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "StrandsAgents/strands-decider-2B-qwen3.5-v1-2610"


def reviewed_scenario(
    scenario_id: str = "s1", message: str = "Is this safe?", consensus: str = "REPLY"
) -> Scenario:
    return Scenario.model_validate(
        {
            "id": scenario_id,
            "split": "heldout",
            "category": "technical_question",
            "history": [],
            "message": {"sender": "Alex", "text": message},
            "labels": {"a1": consensus, "a2": consensus, "a3": consensus},
            "consensus": consensus,
            "notes": "",
        }
    )


def metric_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "silent",
            "consensus": "SILENT",
            "raw_choice": "SILENT",
            "final_action": "SILENT",
            "confidence": 0.8,
            "decider_latency_ms": 10.0,
            "downgraded": False,
            "error": "",
        },
        {
            "id": "react",
            "consensus": "REACT",
            "raw_choice": "REACT",
            "final_action": "REACT",
            "confidence": 0.7,
            "decider_latency_ms": 20.0,
            "downgraded": False,
            "error": "",
        },
        {
            "id": "reply",
            "consensus": "REPLY",
            "raw_choice": "REPLY",
            "final_action": "REPLY",
            "confidence": 0.9,
            "decider_latency_ms": 30.0,
            "downgraded": False,
            "error": "",
        },
    ]


def valid_summary(status: str = "ready") -> dict[str, Any]:
    metrics = compute_metrics(metric_rows())
    return {
        "artifact_version": "lurker-m5-v1",
        "publication_status": status,
        "generated_at": "2026-10-16T00:00:00+00:00",
        "split": "heldout",
        "primary_context_k": 3,
        "model_id": MODEL_ID,
        "device": "cpu",
        "hardware": "test cpu",
        "thresholds": {"reply_threshold": 0.2, "react_threshold": 0.04},
        "criteria": {
            "accuracy_min": 0.7,
            "unnecessary_interruption_rate_max": 0.2,
            "missed_help_rate_max": 0.25,
        },
        "context_metrics": {key: deepcopy(metrics) for key in ("0", "3", "5")},
        "baselines": {
            "always_reply_to_questions": {
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "metrics": deepcopy(metrics),
            },
            "bedrock_judge": {
                "model_id": "baseline-model",
                "model_calls": 3,
                "input_tokens": 30,
                "output_tokens": 3,
                "metrics": deepcopy(metrics),
            },
        },
        "run_manifest": {
            "mock": False,
            "split": "heldout",
            "expected_predictions": 9,
            "actual_predictions": 9,
            "error_count": 0,
        },
    }


def config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "context_k": 3,
            "decider_timeout_ms": 1000,
            "decider_model_id": MODEL_ID,
            "decider_device": "cpu",
            "reply_threshold": 0.2,
            "react_threshold": 0.04,
            "mock_decider": True,
            "data_dir": tmp_path / "data",
            "results_dir": tmp_path / "results",
        }
    )


def test_publication_requires_complete_raw_count_contract_and_is_immutable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "results"
    run = root / "run"
    run.mkdir(parents=True)
    source = run / "results.json"
    source.write_text(json.dumps(valid_summary()) + "\n", encoding="utf-8")

    target = publish_results(source, root)
    published = load_published_results(root)
    assert target == root / "published.json"
    assert published is not None
    assert published["publication_status"] == "published"
    assert published["source_results"] == "run/results.json"
    with pytest.raises(FileExistsError):
        publish_results(source, root)

    broken = valid_summary()
    broken["context_metrics"]["3"]["accuracy"]["rate"] = 0.5
    with pytest.raises(ValueError, match="does not match"):
        validate_m5_summary(broken)


def test_api_serves_only_explicitly_published_m5_result(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    legacy = cfg.results_dir / "old"
    legacy.mkdir(parents=True)
    (legacy / "results.json").write_text('{"legacy": true}\n', encoding="utf-8")
    app = create_app(config=cfg, adapter=MockDecider(), replier=MockBedrockReplier())
    with TestClient(app) as client:
        assert client.get("/api/eval/latest").status_code == 404

    run = cfg.results_dir / "m5"
    run.mkdir()
    source = run / "results.json"
    source.write_text(json.dumps(valid_summary()) + "\n", encoding="utf-8")
    publish_results(source, cfg.results_dir)
    with TestClient(app) as client:
        response = client.get("/api/eval/latest")
        assert response.status_code == 200
        assert response.json()["artifact_version"] == "lurker-m5-v1"


def test_malformed_published_result_fails_closed(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    cfg.results_dir.mkdir(parents=True)
    (cfg.results_dir / "published.json").write_text('{"fake": true}\n', encoding="utf-8")
    app = create_app(config=cfg, adapter=MockDecider(), replier=MockBedrockReplier())
    with TestClient(app) as client:
        response = client.get("/api/eval/latest")
        assert response.status_code == 503
        assert "invalid" in response.json()["detail"]


def test_published_no_go_closure_accepts_only_real_incomplete_baseline_status(
    tmp_path: Path,
) -> None:
    approved = json.loads((ROOT / "results" / "published.json").read_text(encoding="utf-8"))
    validate_m5_closure(approved)
    primary = approved["context_metrics"]["3"]
    assert primary["accuracy"]["rate"] == pytest.approx(2 / 3)
    assert primary["unnecessary_interruption_rate"]["rate"] == pytest.approx(2 / 3)
    assert approved["baselines"]["bedrock_judge"]["metrics"] is None

    pending = deepcopy(approved)
    pending["acceptance"]["implementation_completion"] = "PENDING_OWNER_APPROVAL"
    pending.pop("owner_approval")
    validate_m5_closure(pending)

    missing_approval = deepcopy(approved)
    del missing_approval["owner_approval"]
    with pytest.raises(ValueError, match="requires recorded owner approval"):
        validate_m5_closure(missing_approval)
    cfg = config(tmp_path)
    cfg.results_dir.mkdir(parents=True)
    (cfg.results_dir / "published.json").write_text(
        json.dumps(approved) + "\n", encoding="utf-8"
    )
    app = create_app(config=cfg, adapter=MockDecider(), replier=MockBedrockReplier())
    with TestClient(app) as client:
        response = client.get("/api/eval/latest")
        assert response.status_code == 200
        assert response.json()["acceptance"]["model_performance"] == "NO_GO"
    broken = deepcopy(approved)
    broken["baselines"]["bedrock_judge"]["metrics"] = approved["baselines"][
        "always_reply_to_questions"
    ]["metrics"]
    with pytest.raises(ValueError, match="must not contain fabricated"):
        validate_m5_closure(broken)


class FakeConverseClient:
    def __init__(self, choices: list[str]) -> None:
        self.choices = choices
        self.requests: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        choice = self.choices.pop(0)
        return {
            "output": {"message": {"content": [{"text": choice}]}},
            "usage": {"inputTokens": 12, "outputTokens": 1},
        }


def test_required_baselines_are_bounded_and_auditable() -> None:
    scenarios = [reviewed_scenario()]
    weak = evaluate_question_mark_baseline(scenarios, 3)
    assert weak[0]["final_action"] == "REPLY"
    assert weak[0]["decider_latency_ms"] == 0

    client = FakeConverseClient(["REPLY"])
    judge = BedrockJudge("model", "us-east-2", client=client, max_calls=1)
    rows = evaluate_bedrock_baseline(scenarios, 3, judge)
    assert rows[0]["final_action"] == "REPLY"
    assert rows[0]["input_tokens"] == 12
    assert rows[0]["output_tokens"] == 1
    assert judge.calls == 1
    assert client.requests[0]["inferenceConfig"] == {"maxTokens": 8, "temperature": 0}
    with pytest.raises(BaselineError, match="budget") as exhausted:
        judge.decide({"latest_message": {"text": "another"}})
    assert exhausted.value.invoked is False


def test_bedrock_baseline_records_invalid_output_without_retry() -> None:
    client = FakeConverseClient(["MAYBE"])
    judge = BedrockJudge("model", "us-east-2", client=client, max_calls=1)
    rows = evaluate_bedrock_baseline([reviewed_scenario()], 3, judge)
    assert rows[0]["final_action"] == ""
    assert "invalid option" in rows[0]["error"]
    assert judge.calls == 1
    assert len(client.requests) == 1
    assert compute_metrics(rows)["error_count"] == 1


def test_bedrock_baseline_refuses_oversized_prompt_before_invocation() -> None:
    client = FakeConverseClient(["REPLY"])
    judge = BedrockJudge("model", "us-east-2", client=client, max_calls=1, max_prompt_bytes=40)
    with pytest.raises(BaselineError, match="prompt exceeds") as oversized:
        judge.decide({"latest_message": {"text": "This prompt is intentionally too long."}})
    assert oversized.value.invoked is False
    assert judge.calls == 0
    assert client.requests == []


def test_m5_assembly_refuses_mock_or_incomplete_evidence() -> None:
    summary = valid_summary()
    decider = {
        "split": "heldout",
        "policy_mode": "configured_thresholds",
        "model_id": summary["model_id"],
        "device": summary["device"],
        "hardware": summary["hardware"],
        "thresholds": summary["thresholds"],
        "criteria": summary["criteria"],
        "context_metrics": summary["context_metrics"],
    }
    question = {
        "baseline": "always_questions",
        "split": "heldout",
        "context_k": 3,
        **summary["baselines"]["always_reply_to_questions"],
    }
    bedrock = {
        "baseline": "bedrock_judge",
        "split": "heldout",
        "context_k": 3,
        **summary["baselines"]["bedrock_judge"],
    }
    manifest = {
        "mock": False,
        "split": "heldout",
        "expected_predictions": 9,
        "actual_predictions": 9,
        "error_count": 0,
    }
    assembled = assemble_summary(decider, question, bedrock, manifest, 3)
    validate_m5_summary(assembled, expected_status="ready")
    manifest["mock"] = True
    with pytest.raises(ValueError, match="real heldout"):
        assemble_summary(decider, question, bedrock, manifest, 3)


def test_eval_validation_requires_unique_complete_context_rows() -> None:
    scenario = reviewed_scenario()
    validate_scenarios([scenario], "heldout")
    with pytest.raises(ValueError, match="duplicate"):
        validate_scenarios([scenario, scenario], "heldout")
    rows = [
        {
            "id": "s1",
            "context_k": context_k,
            "confidence": 0.8,
            "decider_latency_ms": 10,
        }
        for context_k in (0, 3, 5)
    ]
    validate_evaluation_rows(rows, [scenario], [0, 3, 5])
    with pytest.raises(ValueError, match="exactly one row"):
        validate_evaluation_rows(rows[:-1], [scenario], [0, 3, 5])


def test_evaluation_frontend_uses_safe_published_result_contract() -> None:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    for element_id in (
        "evaluation-tab",
        "evaluation-panel",
        "evaluation-status",
        "evaluation-context-body",
        "evaluation-baseline-body",
        "evaluation-baseline-note",
        "evaluation-boundary-text",
        "evaluation-calibration-body",
    ):
        assert f'id="{element_id}"' in html
    assert 'loadJson("/api/eval/latest")' in javascript
    assert 'summary.publication_status !== "published"' in javascript
    assert 'summary?.artifact_version === "lurker-m5-closure-v1"' in javascript
    assert '"Not run"' in javascript
    assert "[hidden] { display: none !important; }" in stylesheet
    assert "innerHTML" not in javascript
    assert "70.0%" not in html
