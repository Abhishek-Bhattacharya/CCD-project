import pytest
from phoenix_agent.retry_manager import RetryManager


def test_retry_manager_lifecycle(tmp_path):
    mgr = RetryManager(state_dir=str(tmp_path), max_attempts=2)
    commit = "commit-abc1234"

    # Attempt 1
    inc_id, attempt, is_exhausted = mgr.register_or_get_incident(commit, "dependency_version")
    assert attempt == 1
    assert is_exhausted is False

    mgr.record_attempt_result(
        incident_id=inc_id,
        attempt_number=1,
        repair_branch="phoenix/repair-1",
        pr_number=101,
        patch_valid=True,
        ci_outcome="failed",
        notes="First attempt failed CI"
    )

    # Attempt 2
    inc_id_2, attempt_2, is_exhausted_2 = mgr.register_or_get_incident(commit, "dependency_version")
    assert inc_id_2 == inc_id
    assert attempt_2 == 2
    assert is_exhausted_2 is False

    mgr.record_attempt_result(
        incident_id=inc_id,
        attempt_number=2,
        repair_branch="phoenix/repair-2",
        pr_number=102,
        patch_valid=True,
        ci_outcome="failed",
        notes="Second attempt failed CI"
    )

    # Attempt 3 -> Should be exhausted!
    inc_id_3, attempt_3, is_exhausted_3 = mgr.register_or_get_incident(commit, "dependency_version")
    assert is_exhausted_3 is True
    assert attempt_3 == 2

    # Verify incident state persisted
    incident = mgr.get_incident(inc_id)
    assert incident["status"] == "exhausted"
    assert len(incident["attempts"]) == 2
