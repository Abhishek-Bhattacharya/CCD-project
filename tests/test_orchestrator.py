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


def test_orchestrator_repairs_failed_source_and_publishes_repair(
    repo_root, policy_path, fixtures_dir, tmp_path, monkeypatch
):
    workspace = tmp_path / "failed-source"
    priority_file = workspace / "app" / "src" / "priority.js"
    priority_file.parent.mkdir(parents=True)
    priority_file.write_text(
        "function calculateIncidentPriority(normalizedSeverity, affectedUsers, isProduction) {\n"
        "  if (normalizedSeverity === 'critical' || affectedUsers >= 1000 || "
        "(isProduction && affectedUsers >= 100)) {\n"
        "    return 'P4'; // INJECTED_REGRESSION\n"
        "  }\n"
        "  return 'P2';\n"
        "}\n",
        encoding="utf-8"
    )

    orchestrator = RecoveryOrchestrator(
        repo_root=str(workspace),
        policy_path=policy_path,
        llm_mode="mock",
        require_approval=True
    )
    orchestrator.github_client.mock_mode = False
    events = []
    monkeypatch.setattr(
        orchestrator,
        "_run_local_verification",
        lambda _category: pytest.fail("Privileged recovery must defer execution to CI")
    )

    def create_branch(branch_name, base_sha):
        events.append(("branch", branch_name, base_sha))
        return True

    def commit_changes(message, files):
        events.append(("commit", message, files))
        return True, "repair-commit"

    def push_branch(branch_name):
        events.append(("push", branch_name))
        return True, "pushed"

    def create_pull_request(branch_name, base_branch, title, body):
        events.append(("pull_request", branch_name, base_branch))
        return True, 123, "https://github.com/example/repo/pull/123"

    def dispatch_workflow(workflow_id, branch_name):
        events.append(("dispatch", workflow_id, branch_name))
        return True, "dispatched"

    monkeypatch.setattr(orchestrator.github_client, "create_repair_branch", create_branch)
    monkeypatch.setattr(orchestrator.github_client, "commit_changes", commit_changes)
    monkeypatch.setattr(orchestrator.github_client, "push_branch", push_branch)
    monkeypatch.setattr(orchestrator.github_client, "create_pull_request", create_pull_request)
    monkeypatch.setattr(orchestrator.github_client, "dispatch_workflow", dispatch_workflow)

    logs = (fixtures_dir / "mock_test_failure.log").read_text(encoding="utf-8")
    failed_sha = "a" * 40
    result = orchestrator.recover(
        commit_sha=failed_sha,
        ci_logs=logs,
        failed_step="npm-test",
        skip_local_verification=True,
        base_branch="demo/source"
    )

    assert result["success"] is True
    assert result["category"] == "unit_test_regression"
    assert result["ci_verification"] == "pending"
    assert result["pr_number"] == 123
    assert priority_file.read_text(encoding="utf-8").count("return 'P1';") == 1
    assert [event[0] for event in events] == [
        "branch", "commit", "push", "pull_request", "dispatch"
    ]
    assert events[0][2] == failed_sha
    assert events[3][2] == "demo/source"
