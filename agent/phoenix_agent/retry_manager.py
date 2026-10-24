"""Retry manager and persistent incident state tracker for PhoenixCI."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class RetryManager:
    """Manages repair attempt limits, duplicate detection, and incident state."""

    DEFAULT_MAX_ATTEMPTS = 2

    def __init__(self, state_dir: str = ".phoenix", max_attempts: int = DEFAULT_MAX_ATTEMPTS):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "incidents.json"
        self.max_attempts = max_attempts
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads persistent incident records from JSON file."""
        if not self.state_file.is_file():
            return {"incidents": {}, "commits": {}}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {"incidents": {}, "commits": {}}

    def _save_state(self) -> None:
        """Saves persistent incident records to disk."""
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def register_or_get_incident(
        self,
        commit_sha: str,
        category: str,
        workflow_run_id: Optional[str] = None
    ) -> Tuple[str, int, bool]:
        """
        Registers an incident or retrieves existing incident for a commit.
        
        Returns:
            (incident_id, current_attempt_number, is_retry_exhausted)
        """
        clean_sha = commit_sha.strip()
        commits = self.state.setdefault("commits", {})
        incidents = self.state.setdefault("incidents", {})

        if clean_sha in commits:
            incident_id = commits[clean_sha]
            incident = incidents[incident_id]
            current_attempts = incident.get("attempt_count", 0)

            if current_attempts >= self.max_attempts:
                return incident_id, current_attempts, True

            new_attempt = current_attempts + 1
            incident["attempt_count"] = new_attempt
            incident["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return incident_id, new_attempt, False

        # New incident
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "incident_id": incident_id,
            "commit_sha": clean_sha,
            "category": category,
            "workflow_run_id": workflow_run_id or "local",
            "attempt_count": 1,
            "max_attempts": self.max_attempts,
            "created_at": now,
            "updated_at": now,
            "status": "in_progress",
            "attempts": [],
            "repair_branch": None,
            "pull_request_number": None,
            "ci_outcome": None,
            "merge_outcome": None,
            "deployment_outcome": None
        }

        commits[clean_sha] = incident_id
        incidents[incident_id] = record
        self._save_state()

        return incident_id, 1, False

    def record_attempt_result(
        self,
        incident_id: str,
        attempt_number: int,
        repair_branch: Optional[str],
        pr_number: Optional[int],
        patch_valid: bool,
        ci_outcome: str,
        merge_outcome: Optional[str] = None,
        deployment_outcome: Optional[str] = None,
        notes: str = ""
    ) -> None:
        """Records the outcome of an automated repair attempt."""
        incidents = self.state.get("incidents", {})
        if incident_id not in incidents:
            return

        incident = incidents[incident_id]
        attempt_info = {
            "attempt_number": attempt_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repair_branch": repair_branch,
            "pull_request_number": pr_number,
            "patch_valid": patch_valid,
            "ci_outcome": ci_outcome,
            "merge_outcome": merge_outcome,
            "deployment_outcome": deployment_outcome,
            "notes": notes
        }

        incident.setdefault("attempts", []).append(attempt_info)
        incident["repair_branch"] = repair_branch
        incident["pull_request_number"] = pr_number
        incident["ci_outcome"] = ci_outcome
        incident["merge_outcome"] = merge_outcome
        incident["deployment_outcome"] = deployment_outcome

        if ci_outcome == "success" and merge_outcome == "merged":
            incident["status"] = "resolved"
        elif attempt_number >= self.max_attempts and ci_outcome != "success":
            incident["status"] = "exhausted"

        self._save_state()

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an incident by its ID."""
        return self.state.get("incidents", {}).get(incident_id)
