import pytest
from pathlib import Path
from phoenix_agent.patch_applier import PatchApplier, PatchApplicationError
from phoenix_agent.response_schema import RepairProposal, PatchChange


def test_apply_and_rollback(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    target_file = app_dir / "sample.txt"
    target_file.write_text("Hello World! This is original.", encoding="utf-8")

    applier = PatchApplier(workspace_root=str(tmp_path))
    proposal = RepairProposal(
        category="unit_test_regression",
        diagnosis="Fix greeting",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="app/sample.txt",
                operation="replace",
                original="World",
                replacement="PhoenixCI",
                reason="Update greeting"
            )
        ],
        validation_plan=[]
    )

    success, diff, modified = applier.apply_proposal(proposal)
    assert success is True
    assert "PhoenixCI" in target_file.read_text(encoding="utf-8")
    assert "+Hello PhoenixCI! This is original." in diff
    assert modified == ["app/sample.txt"]

    # Test rollback
    applier.rollback()
    assert target_file.read_text(encoding="utf-8") == "Hello World! This is original."


def test_apply_fails_when_original_missing(tmp_path):
    target_file = tmp_path / "sample.txt"
    target_file.write_text("Actual content", encoding="utf-8")

    applier = PatchApplier(workspace_root=str(tmp_path))
    proposal = RepairProposal(
        category="dockerfile_error",
        diagnosis="Fixing broken instruction in Dockerfile",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="sample.txt",
                operation="replace",
                original="Nonexistent string",
                replacement="Foo",
                reason="invalid"
            )
        ],
        validation_plan=[]
    )

    with pytest.raises(PatchApplicationError, match="Original target string not present"):
        applier.apply_proposal(proposal)
