"""PhoenixCI Recovery Orchestrator coordinating the complete self-healing lifecycle."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from phoenix_agent.classifier import FailureClassifier
from phoenix_agent.context_collector import ContextCollector
from phoenix_agent.llm_client import LLMClient, GroqClientError
from phoenix_agent.response_schema import RepairProposal
from phoenix_agent.patch_validator import PatchValidator, PatchValidationError
from phoenix_agent.patch_applier import PatchApplier, PatchApplicationError
from phoenix_agent.retry_manager import RetryManager
from phoenix_agent.audit_logger import AuditLogger
from phoenix_agent.github_client import GitHubClient


class RecoveryOrchestrator:
    """Coordinates detection, diagnosis, validation, patching, and PR creation."""

    def __init__(
        self,
        repo_root: Optional[str] = None,
        policy_path: Optional[str] = None,
        llm_mode: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        require_approval: Optional[bool] = None,
        auto_merge: Optional[bool] = None
    ):
        self.repo_root = Path(repo_root or os.getcwd()).resolve()
        self.policy_path = Path(
            policy_path or (self.repo_root / "config" / "repair-policy.yaml")
        ).resolve()

        self.require_approval = (
            require_approval
            if require_approval is not None
            else os.environ.get("REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"
        )
        self.auto_merge = (
            auto_merge
            if auto_merge is not None
            else os.environ.get("AUTO_MERGE_ENABLED", "false").lower() == "true"
        )

        # Initialize subcomponents
        self.audit_logger = AuditLogger(log_dir=str(self.repo_root / ".phoenix"))
        self.retry_manager = RetryManager(state_dir=str(self.repo_root / ".phoenix"))
        self.context_collector = ContextCollector(repo_root=str(self.repo_root))
        self.patch_validator = PatchValidator(policy_path=str(self.policy_path), repo_root=str(self.repo_root))
        self.patch_applier = PatchApplier(workspace_root=str(self.repo_root))
        self.github_client = GitHubClient(repo_root=str(self.repo_root))
        self.llm_client = LLMClient(
            api_key=groq_api_key,
            model=groq_model,
            mode=llm_mode
        )

    def recover(
        self,
        commit_sha: str,
        ci_logs: str,
        failed_step: str = "",
        git_diff: str = "",
        workflow_run_id: Optional[str] = None,
        skip_local_verification: bool = False,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Executes autonomous recovery pipeline for a CI failure.
        """
        start_time = time.time()
        workflow_run_id = workflow_run_id or os.environ.get("GITHUB_RUN_ID", "local-run")

        # 1. Failure Detection & Classification
        category, confidence, evidence = FailureClassifier.classify(ci_logs, failed_step)
        
        self.audit_logger.log_event(
            event_type="failure_detection",
            incident_id="pending",
            commit_sha=commit_sha,
            status="detected",
            details={"failed_step": failed_step, "log_length": len(ci_logs)},
            workflow_run_id=workflow_run_id
        )

        self.audit_logger.log_event(
            event_type="failure_classification",
            incident_id="pending",
            commit_sha=commit_sha,
            status="classified",
            details={"category": category, "confidence": confidence, "evidence": evidence},
            workflow_run_id=workflow_run_id
        )

        # 2. Check retry bounds & register incident
        incident_id, attempt_num, is_exhausted = self.retry_manager.register_or_get_incident(
            commit_sha=commit_sha,
            category=category,
            workflow_run_id=workflow_run_id
        )

        if is_exhausted:
            self.audit_logger.log_event(
                event_type="retry_exhaustion",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="rejected",
                details={"reason": f"Maximum repair attempts ({self.retry_manager.max_attempts}) reached."},
                workflow_run_id=workflow_run_id,
                elapsed_seconds=time.time() - start_time
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": category,
                "status": "retry_exhausted",
                "message": f"Maximum automated repair attempts reached for commit {commit_sha}."
            }

        # 3. Check if unsupported category
        if category == "unsupported":
            self.audit_logger.log_event(
                event_type="recovery_stopped",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="unsupported",
                details={"reason": "Failure does not match any of the 3 supported categories."},
                workflow_run_id=workflow_run_id,
                elapsed_seconds=time.time() - start_time
            )
            self.retry_manager.record_attempt_result(
                incident_id=incident_id,
                attempt_number=attempt_num,
                repair_branch=None,
                pr_number=None,
                patch_valid=False,
                ci_outcome="unsupported",
                notes="Unsupported failure category"
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": "unsupported",
                "status": "unsupported_category",
                "message": "Failure category unsupported. Halting automated repair."
            }

        # 4. Context Collection & Prompt Injection Protection
        context = self.context_collector.collect_context(category, ci_logs, git_diff)
        if context.get("injection_warnings"):
            self.audit_logger.log_event(
                event_type="prompt_injection_warning",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="warning",
                details={"warnings": context["injection_warnings"]},
                workflow_run_id=workflow_run_id
            )

        self.audit_logger.log_event(
            event_type="context_collection",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="completed",
            details={
                "category": category,
                "bounded_log_chars": len(str(context.get("bounded_logs", ""))),
                "files_included": list(context.get("files", {}).keys())
            },
            workflow_run_id=workflow_run_id
        )

        # 5. Groq LLM Diagnosis & Patch Proposal
        try:
            proposal, llm_meta = self.llm_client.generate_repair_proposal(category, context)
            self.audit_logger.log_event(
                event_type="groq_inference",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="success",
                details={
                    "model": llm_meta.get("model"),
                    "prompt_tokens": llm_meta.get("prompt_tokens"),
                    "completion_tokens": llm_meta.get("completion_tokens"),
                    "total_tokens": llm_meta.get("total_tokens"),
                    "estimated_cost_usd": llm_meta.get("estimated_cost_usd"),
                    "latency_seconds": llm_meta.get("latency_seconds"),
                    "diagnosis": proposal.diagnosis,
                    "changes_count": len(proposal.changes)
                },
                workflow_run_id=workflow_run_id
            )
        except GroqClientError as err:
            self.audit_logger.log_event(
                event_type="groq_inference",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="error",
                details={"error": str(err)},
                workflow_run_id=workflow_run_id,
                elapsed_seconds=time.time() - start_time
            )
            self.retry_manager.record_attempt_result(
                incident_id=incident_id,
                attempt_number=attempt_num,
                repair_branch=None,
                pr_number=None,
                patch_valid=False,
                ci_outcome="llm_error",
                notes=str(err)
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": category,
                "status": "llm_error",
                "message": f"LLM client failure: {str(err)}"
            }

        # 6. Stage 1: Pre-apply Patch Validation
        pre_valid, pre_violations = self.patch_validator.validate_pre_apply(proposal)
        self.audit_logger.log_event(
            event_type="patch_validation_pre",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="passed" if pre_valid else "rejected",
            details={"is_valid": pre_valid, "violations": pre_violations},
            workflow_run_id=workflow_run_id
        )

        if not pre_valid:
            self.retry_manager.record_attempt_result(
                incident_id=incident_id,
                attempt_number=attempt_num,
                repair_branch=None,
                pr_number=None,
                patch_valid=False,
                ci_outcome="policy_violation",
                notes="; ".join(pre_violations)
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": category,
                "status": "pre_validation_failed",
                "violations": pre_violations
            }

        # 7. Apply Patch
        try:
            applied, applied_diff, modified_files = self.patch_applier.apply_proposal(proposal)
            self.audit_logger.log_event(
                event_type="patch_application",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="applied",
                details={"modified_files": modified_files, "diff_length": len(applied_diff)},
                workflow_run_id=workflow_run_id
            )
        except PatchApplicationError as err:
            self.audit_logger.log_event(
                event_type="patch_application",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="failed",
                details={"error": str(err)},
                workflow_run_id=workflow_run_id,
                elapsed_seconds=time.time() - start_time
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": category,
                "status": "application_failed",
                "message": str(err)
            }

        # 8. Stage 2: Post-apply Git Diff Validation
        post_valid, post_violations = self.patch_validator.validate_post_apply(
            category=category,
            git_diff=applied_diff,
            changed_files=modified_files
        )
        self.audit_logger.log_event(
            event_type="patch_validation_post",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="passed" if post_valid else "rejected",
            details={"is_valid": post_valid, "violations": post_violations},
            workflow_run_id=workflow_run_id
        )

        if not post_valid:
            # Revert files
            self.patch_applier.rollback()
            self.retry_manager.record_attempt_result(
                incident_id=incident_id,
                attempt_number=attempt_num,
                repair_branch=None,
                pr_number=None,
                patch_valid=False,
                ci_outcome="post_validation_policy_violation",
                notes="; ".join(post_violations)
            )
            return {
                "success": False,
                "incident_id": incident_id,
                "category": category,
                "status": "post_validation_failed",
                "violations": post_violations
            }

        # 9. Local Verification Check
        if skip_local_verification:
            local_ci_passed = False
            local_ci_msg = "Local execution skipped; CI verification is requested on the repair branch."
        else:
            local_ci_passed, local_ci_msg = self._run_local_verification(category)
        self.audit_logger.log_event(
            event_type="ci_verification_local",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="skipped" if skip_local_verification else "passed" if local_ci_passed else "failed",
            details={"message": local_ci_msg},
            workflow_run_id=workflow_run_id
        )

        # 10. Create Repair Branch and PR
        repair_branch = f"phoenix/repair-{incident_id}-att{attempt_num}"
        pr_title = f"[PhoenixCI Self-Healing] Fix {category} in {commit_sha[:7]} (Attempt {attempt_num})"
        pr_body = GitHubClient.build_pr_body(
            incident_id=incident_id,
            category=category,
            commit_sha=commit_sha,
            diagnosis=proposal.diagnosis,
            evidence=proposal.root_cause_evidence,
            changes_summary=[f"{c.path}: {c.reason}" for c in proposal.changes],
            attempt_number=attempt_num,
            llm_metadata=llm_meta,
            validation_status=(
                "Passed strict policy checks and local verification"
                if local_ci_passed
                else "Passed strict policy checks; CI verification is pending"
            )
        )

        if not self.github_client.mock_mode:
            if not self.github_client.create_repair_branch(repair_branch, commit_sha):
                return self._record_publish_failure(
                    incident_id, attempt_num, commit_sha, workflow_run_id,
                    "repair_branch_creation_failed",
                    "Could not create a repair branch from the failed commit."
                )

            committed, commit_result = self.github_client.commit_changes(
                f"[PhoenixCI] Repair {category} for {commit_sha[:7]}",
                [change.path for change in proposal.changes]
            )
            if not committed:
                return self._record_publish_failure(
                    incident_id, attempt_num, commit_sha, workflow_run_id,
                    "repair_commit_failed", commit_result
                )

            pushed, push_message = self.github_client.push_branch(repair_branch)
            if not pushed:
                return self._record_publish_failure(
                    incident_id, attempt_num, commit_sha, workflow_run_id,
                    "repair_push_failed", push_message
                )

        pr_success, pr_number, pr_url = self.github_client.create_pull_request(
            branch_name=repair_branch,
            base_branch=base_branch,
            title=pr_title,
            body=pr_body
        )

        self.audit_logger.log_event(
            event_type="pr_creation",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="created" if pr_success else "failed",
            details={
                "branch": repair_branch,
                "pr_number": pr_number,
                "pr_url": pr_url,
                "require_human_approval": self.require_approval,
                "auto_merge_enabled": self.auto_merge
            },
            workflow_run_id=workflow_run_id,
            elapsed_seconds=time.time() - start_time
        )

        if not pr_success:
            return self._record_publish_failure(
                incident_id, attempt_num, commit_sha, workflow_run_id,
                "pull_request_creation_failed", pr_url
            )

        if not self.github_client.mock_mode:
            dispatched, dispatch_message = self.github_client.dispatch_workflow(
                "ci.yml", repair_branch
            )
            self.audit_logger.log_event(
                event_type="repair_ci_dispatch",
                incident_id=incident_id,
                commit_sha=commit_sha,
                status="requested" if dispatched else "failed",
                details={"branch": repair_branch, "message": dispatch_message},
                workflow_run_id=workflow_run_id
            )
            if not dispatched:
                self.retry_manager.record_attempt_result(
                    incident_id=incident_id,
                    attempt_number=attempt_num,
                    repair_branch=repair_branch,
                    pr_number=pr_number,
                    patch_valid=True,
                    ci_outcome="ci_dispatch_failed",
                    notes=dispatch_message
                )
                return {
                    "success": False,
                    "incident_id": incident_id,
                    "category": category,
                    "status": "ci_dispatch_failed",
                    "pr_url": pr_url,
                    "message": dispatch_message
                }

        # 11. Approval & Merge Evaluation
        merge_outcome = "pending_human_approval" if self.require_approval else (
            "auto_merged" if (self.auto_merge and local_ci_passed) else "pending_review"
        )

        self.retry_manager.record_attempt_result(
            incident_id=incident_id,
            attempt_number=attempt_num,
            repair_branch=repair_branch,
            pr_number=pr_number,
            patch_valid=True,
            ci_outcome="success" if local_ci_passed else "pending" if skip_local_verification else "failed",
            merge_outcome=merge_outcome,
            notes="Repair generated and validated successfully."
        )

        elapsed = time.time() - start_time

        return {
            "success": True,
            "incident_id": incident_id,
            "category": category,
            "attempt_number": attempt_num,
            "repair_branch": repair_branch,
            "pr_number": pr_number,
            "pr_url": pr_url,
            "proposal": proposal.model_dump(),
            "llm_metadata": llm_meta,
            "local_ci_passed": local_ci_passed,
            "ci_verification": (
                "pending" if skip_local_verification
                else "passed" if local_ci_passed
                else "failed"
            ),
            "merge_outcome": merge_outcome,
            "elapsed_seconds": round(elapsed, 4)
        }

    def _record_publish_failure(
        self,
        incident_id: str,
        attempt_number: int,
        commit_sha: str,
        workflow_run_id: str,
        status: str,
        message: str
    ) -> Dict[str, Any]:
        self.audit_logger.log_event(
            event_type="repair_publish",
            incident_id=incident_id,
            commit_sha=commit_sha,
            status="failed",
            details={"status": status, "message": message},
            workflow_run_id=workflow_run_id
        )
        self.retry_manager.record_attempt_result(
            incident_id=incident_id,
            attempt_number=attempt_number,
            repair_branch=None,
            pr_number=None,
            patch_valid=True,
            ci_outcome=status,
            notes=message
        )
        return {
            "success": False,
            "incident_id": incident_id,
            "status": status,
            "message": message
        }

    def _run_local_verification(self, category: str) -> Tuple[bool, str]:
        """Runs fast local smoke check based on category."""
        import shutil
        npm_bin = shutil.which("npm") or "npm"
        npx_bin = shutil.which("npx") or "npx"

        try:
            if category == "unit_test_regression":
                # Run isolated unit tests without port binding
                res = subprocess.run(
                    [npx_bin, "jest", "tests/priority.test.js", "--forceExit"],
                    cwd=str(self.repo_root / "app"),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0:
                    return True, "Unit tests passed cleanly after repair."
                return False, f"Unit tests failed: {res.stdout[-300:]}"

            elif category == "dependency_version":
                # Check package.json syntax and lockfile consistency
                res = subprocess.run(
                    [npm_bin, "install", "--package-lock-only"],
                    cwd=str(self.repo_root / "app"),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0:
                    return True, "Dependency resolution succeeded."
                return False, f"Dependency check failed: {res.stderr[-300:]}"

            elif category == "dockerfile_error":
                # Check Dockerfile syntax
                dockerfile_path = self.repo_root / "app" / "Dockerfile"
                content = dockerfile_path.read_text(encoding="utf-8")
                # Basic lint: check for unknown or broken instructions
                valid_instructions = {"FROM", "WORKDIR", "COPY", "RUN", "USER", "EXPOSE", "HEALTHCHECK", "CMD", "ENV", "ARG", "ENTRYPOINT"}
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        first_token = line.split()[0].upper()
                        if first_token not in valid_instructions:
                            return False, f"Invalid Dockerfile instruction detected: {first_token}"
                return True, "Dockerfile syntax validated."

            return True, "Verification passed."
        except Exception as e:
            return False, f"Verification execution error: {str(e)}"
