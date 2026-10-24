import pytest
from pathlib import Path
from phoenix_agent.context_collector import ContextCollector


def test_secret_redaction(repo_root):
    collector = ContextCollector(repo_root=repo_root)
    sensitive_log = (
        "Error with Groq: gsk_1234567890abcdef1234567890\n"
        "GitHub token: ghp_abcdefghijklmnopqrstuvwxyz012345\n"
        "AWS Key: AKIAIOSFODNN7EXAMPLE\n"
        "Authorization: Bearer mySuperSecretToken1234567\n"
    )
    redacted = collector.redact_secrets(sensitive_log)
    assert "gsk_1234567890abcdef1234567890" not in redacted
    assert "[REDACTED_GROQ_API_KEY]" in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "[REDACTED_AWS_ACCESS_KEY]" in redacted
    assert "mySuperSecretToken1234567" not in redacted


def test_bounded_log_extraction(repo_root):
    collector = ContextCollector(repo_root=repo_root, max_log_lines=5)
    long_log = "\n".join(f"Log line {i}" for i in range(50))
    bounded = collector.extract_bounded_logs(long_log)
    lines = bounded.splitlines()
    assert len(lines) == 5
    assert lines[0] == "Log line 45"
    assert lines[-1] == "Log line 49"


def test_path_traversal_prohibited(repo_root):
    collector = ContextCollector(repo_root=repo_root)
    with pytest.raises(ValueError, match="Directory traversal prohibited"):
        collector.read_repo_file("../outside_repo.txt")


def test_collect_context_dependency(repo_root, fixtures_dir):
    collector = ContextCollector(repo_root=repo_root)
    raw_log = (fixtures_dir / "mock_dependency_failure.log").read_text(encoding="utf-8")
    ctx = collector.collect_context("dependency_version", raw_log)
    assert ctx["category"] == "dependency_version"
    assert "app/package.json" in ctx["files"]
    assert ctx["lockfile_exists"] is True
