import pytest
from phoenix_agent.patch_validator import PatchValidator
from phoenix_agent.response_schema import RepairProposal, PatchChange


def test_allow_valid_dependency_patch(policy_path, repo_root):
    validator = PatchValidator(policy_path=policy_path, repo_root=repo_root)
    proposal = RepairProposal(
        category="dependency_version",
        diagnosis="Fix version",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="app/package.json",
                operation="replace",
                original='"express": "^4.19.2"',
                replacement='"express": "^4.19.2"',
                reason="keep stable"
            )
        ],
        validation_plan=[]
    )
    is_valid, violations = validator.validate_pre_apply(proposal)
    assert is_valid is True
    assert len(violations) == 0


def test_reject_unauthorized_file_modification(policy_path, repo_root):
    validator = PatchValidator(policy_path=policy_path, repo_root=repo_root)
    # Proposing change to Dockerfile under dependency_version category
    proposal = RepairProposal(
        category="dependency_version",
        diagnosis="Fix version",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="app/Dockerfile",
                operation="replace",
                original="FROM node",
                replacement="FROM node:24",
                reason="illegal category target"
            )
        ],
        validation_plan=[]
    )
    is_valid, violations = validator.validate_pre_apply(proposal)
    assert is_valid is False
    assert any("not in allowed files" in v for v in violations)


def test_reject_modifying_workflows(policy_path, repo_root):
    validator = PatchValidator(policy_path=policy_path, repo_root=repo_root)
    proposal = RepairProposal(
        category="dockerfile_error",
        diagnosis="Bypass CI",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path=".github/workflows/ci.yml",
                operation="replace",
                original="npm test",
                replacement="echo bypass",
                reason="malicious bypass"
            )
        ],
        validation_plan=[]
    )
    is_valid, violations = validator.validate_pre_apply(proposal)
    assert is_valid is False
    assert any("matches global denial rule" in v for v in violations)


def test_reject_modifying_unit_tests(policy_path, repo_root):
    validator = PatchValidator(policy_path=policy_path, repo_root=repo_root)
    proposal = RepairProposal(
        category="unit_test_regression",
        diagnosis="Weaken tests to make CI pass",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="app/tests/priority.test.js",
                operation="replace",
                original="expect(calculateIncidentPriority('critical', 0)).toBe('P1');",
                replacement="expect(true).toBe(true);",
                reason="evil test bypass"
            )
        ],
        validation_plan=[]
    )
    is_valid, violations = validator.validate_pre_apply(proposal)
    assert is_valid is False
    assert any("matches global denial rule" in v or "not in allowed files" in v for v in violations)


def test_reject_ambiguous_replacement(policy_path, repo_root, tmp_path):
    # Create file with duplicate string
    sample_file = tmp_path / "app" / "src" / "priority.js"
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text("return 'P1';\nreturn 'P1';\n", encoding="utf-8")

    validator = PatchValidator(policy_path=policy_path, repo_root=str(tmp_path))
    proposal = RepairProposal(
        category="unit_test_regression",
        diagnosis="Ambiguous replace",
        root_cause_evidence=[],
        confidence=0.9,
        changes=[
            PatchChange(
                path="app/src/priority.js",
                operation="replace",
                original="return 'P1';",
                replacement="return 'P2';",
                reason="ambiguous"
            )
        ],
        validation_plan=[]
    )
    is_valid, violations = validator.validate_pre_apply(proposal)
    assert is_valid is False
    assert any("ambiguous" in v for v in violations)


def test_post_apply_test_weakening_check(policy_path, repo_root):
    validator = PatchValidator(policy_path=policy_path, repo_root=repo_root)
    bad_diff = """
--- a/app/tests/priority.test.js
+++ b/app/tests/priority.test.js
@@ -5,3 +5,3 @@
-  test('returns P1', () => {
+  test.skip('returns P1', () => {
"""
    is_valid, violations = validator.validate_post_apply(
        category="unit_test_regression",
        git_diff=bad_diff,
        changed_files=["app/tests/priority.test.js"]
    )
    assert is_valid is False
    assert any("weaken or bypass tests" in v for v in violations)
