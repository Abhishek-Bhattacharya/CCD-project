from pathlib import Path
import uuid
import pytest
from phoenix_agent.orchestrator import RecoveryOrchestrator


def test_orchestrator_mock_recovery_dependency(repo_root, fixtures_dir, tmp_path):
    pkg_file = Path(repo_root) / "app" / "package.json"
    orig_text = pkg_file.read_text(encoding="utf-8")
    pkg_file.write_text(orig_text.replace('"express": "^4.19.2"', '"express": "^99.9.9"'), encoding="utf-8")
    try:
        orch = RecoveryOrchestrator(
            repo_root=repo_root,
            llm_mode="mock",
            require_approval=True,
            auto_merge=False
        )
        # Use an isolated retry manager state dir
        orch.retry_manager.state_dir = tmp_path
        orch.retry_manager.state_file = tmp_path / "incidents.json"
        orch.retry_manager.state = {"incidents": {}, "commits": {}}

        log_content = (fixtures_dir / "mock_dependency_failure.log").read_text(encoding="utf-8")
        result = orch.recover(
            commit_sha=f"commit-{uuid.uuid4().hex[:8]}",
            ci_logs=log_content,
            failed_step="npm-install"
        )

        assert result["success"] is True
        assert result["category"] == "dependency_version"
        assert result["attempt_number"] == 1
        assert "pr_url" in result
        assert result["merge_outcome"] == "pending_human_approval"
        assert result["llm_metadata"]["mode"] == "mock"
    finally:
        pkg_file.write_text(orig_text, encoding="utf-8")


def test_orchestrator_mock_recovery_unsupported(repo_root, fixtures_dir):
    orch = RecoveryOrchestrator(
        repo_root=repo_root,
        llm_mode="mock"
    )
    log_content = (fixtures_dir / "mock_unsupported_failure.log").read_text(encoding="utf-8")
    result = orch.recover(
        commit_sha=f"commit-unsupported-{uuid.uuid4().hex[:8]}",
        ci_logs=log_content,
        failed_step="merge-conflict"
    )

    assert result["success"] is False
    assert result["category"] == "unsupported"
    assert result["status"] == "unsupported_category"
