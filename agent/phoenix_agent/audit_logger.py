"""Structured JSONL audit logger for PhoenixCI self-healing pipeline."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """Writes immutable, structured JSONL audit entries with automatic secret filtering."""

    SECRET_MASKS = [
        (r"gsk_[A-Za-z0-9_-]{20,}", "[REDACTED_GROQ_KEY]"),
        (r"ghp_[A-Za-z0-9_]{20,}", "[REDACTED_GITHUB_TOKEN]"),
        (r"github_pat_[A-Za-z0-9_]{20,}", "[REDACTED_GITHUB_PAT]"),
        (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    ]

    def __init__(self, log_dir: str = ".phoenix"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "audit.jsonl"

    def _sanitize(self, data: Any) -> Any:
        """Recursively sanitizes data to guarantee no secrets are logged."""
        if isinstance(data, str):
            res = data
            for pat, mask in self.SECRET_MASKS:
                res = re.sub(pat, mask, res)
            return res
        elif isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in ["api_key", "token", "password", "secret", "private_key"]):
                    clean_dict[k] = "[REDACTED]"
                else:
                    clean_dict[k] = self._sanitize(v)
            return clean_dict
        elif isinstance(data, list):
            return [self._sanitize(item) for item in data]
        return data

    def log_event(
        self,
        event_type: str,
        incident_id: str,
        commit_sha: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        workflow_run_id: Optional[str] = None,
        elapsed_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Appends an event to audit.jsonl.
        
        event_type examples:
            - failure_detection
            - failure_classification
            - context_collection
            - groq_inference
            - patch_validation_pre
            - patch_application
            - patch_validation_post
            - pr_creation
            - ci_verification
            - approval_and_merge
            - deployment_execution
            - retry_exhaustion
        """
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": now,
            "event_type": event_type,
            "incident_id": incident_id,
            "commit_sha": commit_sha,
            "workflow_run_id": workflow_run_id or os.environ.get("GITHUB_RUN_ID", "local"),
            "status": status,
            "elapsed_seconds": round(elapsed_seconds, 4) if elapsed_seconds is not None else None,
            "details": self._sanitize(details or {})
        }

        sanitized_json = json.dumps(entry)
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(sanitized_json + "\n")

        return entry

    def read_all_events(self) -> list:
        """Reads and parses all audit events recorded."""
        if not self.audit_file.is_file():
            return []
        events = []
        with open(self.audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events
