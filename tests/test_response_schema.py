import pytest
from pydantic import ValidationError
from phoenix_agent.response_schema import RepairProposal, PatchChange, parse_and_validate_proposal


def test_valid_proposal():
    raw = {
        "category": "dependency_version",
        "diagnosis": "Package express has invalid version",
        "root_cause_evidence": ["npm ERR! code ETARGET"],
        "confidence": 0.95,
        "changes": [
            {
                "path": "app/package.json",
                "operation": "replace",
                "original": '"express": "^99.9.9"',
                "replacement": '"express": "^4.19.2"',
                "reason": "Fix version"
            }
        ],
        "validation_plan": ["npm test"]
    }
    proposal = parse_and_validate_proposal(raw)
    assert proposal.category == "dependency_version"
    assert proposal.confidence == 0.95
    assert len(proposal.changes) == 1
    assert proposal.changes[0].path == "app/package.json"


def test_reject_missing_changes_for_supported_category():
    raw = {
        "category": "unit_test_regression",
        "diagnosis": "Test failed due to regression",
        "root_cause_evidence": ["FAIL"],
        "confidence": 0.8,
        "changes": [],  # empty changes for supported category!
        "validation_plan": []
    }
    with pytest.raises(ValidationError, match="Supported failure categories must propose at least one change"):
        parse_and_validate_proposal(raw)


def test_reject_changes_for_unsupported_category():
    raw = {
        "category": "unsupported",
        "diagnosis": "Merge conflict is outside automated scope",
        "root_cause_evidence": [],
        "confidence": 0.1,
        "changes": [
            {
                "path": "README.md",
                "operation": "replace",
                "original": "foo",
                "replacement": "bar",
                "reason": "illegal change"
            }
        ],
        "validation_plan": []
    }
    with pytest.raises(ValidationError, match="Unsupported failure category should not propose code changes"):
        parse_and_validate_proposal(raw)


def test_reject_path_traversal_in_change():
    with pytest.raises(ValidationError, match="Path traversal detected"):
        PatchChange(
            path="../../etc/passwd",
            operation="replace",
            original="a",
            replacement="b",
            reason="evil"
        )


def test_reject_absolute_path_in_change():
    with pytest.raises(ValidationError, match="Path must be relative"):
        PatchChange(
            path="/etc/hosts",
            operation="replace",
            original="a",
            replacement="b",
            reason="evil"
        )


def test_reject_confidence_out_of_range():
    raw = {
        "category": "dockerfile_error",
        "diagnosis": "Docker error",
        "root_cause_evidence": [],
        "confidence": 1.5,  # > 1.0!
        "changes": [
            {
                "path": "app/Dockerfile",
                "operation": "replace",
                "original": "a",
                "replacement": "b",
                "reason": "fix"
            }
        ],
        "validation_plan": []
    }
    with pytest.raises(ValidationError):
        parse_and_validate_proposal(raw)
