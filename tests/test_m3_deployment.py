"""Static contract tests for the M3 deployment skeleton."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _dockerfile() -> str:
    return (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_dockerfile_runs_the_required_api_command() -> None:
    text = _dockerfile()
    assert "uvicorn src.lurker.api:app" in text
    assert "--host 0.0.0.0" in text
    assert "--port ${PORT:-8000}" in text


def test_dockerfile_uses_cpu_inference_and_cpu_torch() -> None:
    text = _dockerfile()
    assert "DECIDER_DEVICE=cpu" in text
    assert "https://download.pytorch.org/whl/cpu" in text


def test_dockerfile_drops_root_privileges() -> None:
    text = _dockerfile()
    assert "USER lurker" in text


def test_dockerfile_has_a_real_healthcheck() -> None:
    text = _dockerfile()
    assert "HEALTHCHECK" in text
    assert "http://127.0.0.1:8000/health" in text
    assert "data.get('status') == 'ok'" in text


def test_sensitive_and_runtime_files_are_excluded() -> None:
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in {".env", ".venv", ".git", "data/", "results/"}:
        assert entry in ignored


def test_decider_dependency_is_commit_pinned() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert (
        "strands-decider @ git+https://github.com/strands-labs/"
        "strands-decider.git@6039cf8b64c6074e75804000c07ac3d4cce795f7"
    ) in requirements


def test_deployed_smoke_is_one_safe_silent_case() -> None:
    script = (ROOT / "scripts" / "smoke_deployed.py").read_text(encoding="utf-8")
    assert "Let's meet at four tomorrow." in script
    assert 'decision.get("raw_choice") != "SILENT"' in script
    assert 'recent[0].get("bedrock_called") is not False' in script
    assert "eval/scenarios.jsonl" not in script
