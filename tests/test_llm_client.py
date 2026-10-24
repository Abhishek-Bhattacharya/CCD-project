import os
import pytest
from phoenix_agent.llm_client import (
    LLMClient,
    ConfigurationError,
    ResponseParsingError
)


def test_missing_api_key_in_live_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY is not set"):
        LLMClient(mode="live", api_key=None)


def test_mock_mode_no_api_key_required():
    client = LLMClient(mode="mock", api_key=None)
    assert client.mode == "mock"
    proposal, meta = client.generate_repair_proposal("dependency_version", {})
    assert proposal.category == "dependency_version"
    assert len(proposal.changes) > 0
    assert meta["mode"] == "mock"
    assert meta["model"] == "mock-simulator"
    assert meta["total_tokens"] > 0


def test_mock_mode_dockerfile_error():
    client = LLMClient(mode="mock")
    proposal, meta = client.generate_repair_proposal("dockerfile_error", {})
    assert proposal.category == "dockerfile_error"
    assert proposal.changes[0].path == "app/Dockerfile"
    assert "COPPY" in proposal.changes[0].original


def test_mock_mode_unit_test_regression():
    client = LLMClient(mode="mock")
    proposal, meta = client.generate_repair_proposal("unit_test_regression", {})
    assert proposal.category == "unit_test_regression"
    assert proposal.changes[0].path == "app/src/priority.js"
    assert "priority.test.js" not in [c.path for c in proposal.changes]


def test_mock_mode_unsupported():
    client = LLMClient(mode="mock")
    proposal, meta = client.generate_repair_proposal("unsupported", {})
    assert proposal.category == "unsupported"
    assert len(proposal.changes) == 0
