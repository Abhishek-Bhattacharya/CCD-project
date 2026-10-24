import pytest
from phoenix_agent.context_collector import ContextCollector


def test_detect_prompt_injection_in_logs(repo_root, fixtures_dir):
    collector = ContextCollector(repo_root=repo_root)
    malicious_log = (fixtures_dir / "mock_prompt_injection.log").read_text(encoding="utf-8")
    injections = collector.detect_prompt_injections(malicious_log)
    assert len(injections) > 0

    ctx = collector.collect_context("dependency_version", malicious_log)
    assert len(ctx["injection_warnings"]) > 0

    # Ensure context logs are bounded and sanitized
    assert "System:" not in ctx["bounded_logs"] or "<untrusted_ci_logs>" not in ctx["bounded_logs"]
