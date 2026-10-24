"""Strict patch validation for PhoenixCI self-healing pipeline."""

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

from phoenix_agent.response_schema import RepairProposal, PatchChange


class PatchValidationError(Exception):
    """Raised when a proposed patch violates security or integrity policy."""
    pass


class PatchValidator:
    """Enforces category-specific allowlists and global deny rules on patches."""

    def __init__(self, policy_path: str, repo_root: str):
        self.repo_root = Path(repo_root).resolve()
        self.policy_path = Path(policy_path).resolve()
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict:
        """Loads and parses repair-policy.yaml."""
        if not self.policy_path.is_file():
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")
        with open(self.policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def validate_pre_apply(self, proposal: RepairProposal) -> Tuple[bool, List[str]]:
        """
        Stage 1 Validation: Checks proposed changes before applying to files.
        Returns:
            (is_valid, list_of_violations)
        """
        violations: List[str] = []
        category = proposal.category

        if category == "unsupported":
            if proposal.changes:
                violations.append("Unsupported category must not propose any file changes.")
            return len(violations) == 0, violations

        cat_policy = self.policy.get("categories", {}).get(category)
        if not cat_policy:
            violations.append(f"Category '{category}' has no policy configuration defined.")
            return False, violations

        allowed_files = [f.replace("\\", "/") for f in cat_policy.get("allowed_files", [])]
        allowed_ops = cat_policy.get("allowed_operations", ["replace"])
        max_changes = cat_policy.get("max_file_changes", 2)
        global_denials = self.policy.get("global_denials", {}).get("patterns", [])

        if len(proposal.changes) == 0:
            violations.append("Proposal contains no changes.")

        if len(proposal.changes) > max_changes:
            violations.append(
                f"Proposal modifies {len(proposal.changes)} files, exceeding limit of {max_changes} for {category}."
            )

        for change in proposal.changes:
            norm_path = change.path.strip().replace("\\", "/").lstrip("/")

            # Check directory traversal & absolute path
            if ".." in norm_path.split("/") or change.path.startswith("/"):
                violations.append(f"Illegal path or directory traversal: {change.path}")
                continue

            # Check global denials
            for deny_pat in global_denials:
                if fnmatch.fnmatch(norm_path, deny_pat) or fnmatch.fnmatch(norm_path, f"*/{deny_pat}"):
                    violations.append(f"File matches global denial rule: {norm_path} (rule: {deny_pat})")

            # Check category allowlist
            matched_allowed = any(
                fnmatch.fnmatch(norm_path, allowed_pat)
                for allowed_pat in allowed_files
            )
            if not matched_allowed:
                violations.append(
                    f"File '{norm_path}' is not in allowed files for category '{category}' ({allowed_files})"
                )

            # Check operation
            if change.operation not in allowed_ops:
                violations.append(
                    f"Operation '{change.operation}' not permitted for {category}. Allowed: {allowed_ops}"
                )

            # Check original content exists in target file
            target_file = (self.repo_root / norm_path).resolve()
            if not target_file.is_file():
                violations.append(f"Target file does not exist in repo: {norm_path}")
            else:
                try:
                    file_text = target_file.read_text(encoding="utf-8")
                    if change.original not in file_text:
                        violations.append(
                            f"Original snippet not found in target file '{norm_path}'. Cannot safely replace."
                        )
                    elif file_text.count(change.original) > 1:
                        violations.append(
                            f"Original snippet is ambiguous (occurs {file_text.count(change.original)} times) in '{norm_path}'."
                        )
                except Exception as err:
                    violations.append(f"Error reading target file '{norm_path}': {str(err)}")

        return len(violations) == 0, violations

    def validate_post_apply(
        self,
        category: str,
        git_diff: str,
        changed_files: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Stage 2 Validation: Checks complete Git diff and modified file list.
        Returns:
            (is_valid, list_of_violations)
        """
        violations: List[str] = []

        if not git_diff.strip():
            violations.append("Post-apply diff is empty. No modifications were recorded.")
            return False, violations

        max_patch_bytes = self.policy.get("global_denials", {}).get("max_total_patch_bytes", 16384)
        if len(git_diff.encode("utf-8")) > max_patch_bytes:
            violations.append(f"Git diff size ({len(git_diff.encode('utf-8'))} bytes) exceeds limit ({max_patch_bytes} bytes).")

        cat_policy = self.policy.get("categories", {}).get(category, {})
        allowed_files = [f.replace("\\", "/") for f in cat_policy.get("allowed_files", [])]
        global_denials = self.policy.get("global_denials", {}).get("patterns", [])

        for file_path in changed_files:
            norm_path = file_path.strip().replace("\\", "/").lstrip("/")

            # Check global denials
            for deny_pat in global_denials:
                if fnmatch.fnmatch(norm_path, deny_pat) or fnmatch.fnmatch(norm_path, f"*/{deny_pat}"):
                    violations.append(f"Post-apply diff touches forbidden file: {norm_path} (pattern: {deny_pat})")

            # Check category allowlist
            matched_allowed = any(
                fnmatch.fnmatch(norm_path, allowed_pat)
                for allowed_pat in allowed_files
            )
            if not matched_allowed:
                violations.append(
                    f"Post-apply diff modified unauthorized file for {category}: {norm_path}"
                )

        # Check for test weakening patterns in the diff
        test_weakening_patterns = [
            "test.skip",
            "describe.skip",
            "it.skip",
            "xit(",
            "xdescribe(",
            "// expect(",
            "/* expect(",
            "--bail=0"
        ]
        for pattern in test_weakening_patterns:
            if pattern in git_diff:
                violations.append(f"Diff appears to weaken or bypass tests: detected '{pattern}'.")

        return len(violations) == 0, violations
