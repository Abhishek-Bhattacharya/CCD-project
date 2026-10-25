"""GitHub integration client for PhoenixCI PR creation and branch management."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


class GitHubClient:
    """Manages git branches and pull requests for automated repairs."""

    def __init__(
        self,
        repo_root: str,
        token: Optional[str] = None,
        repository: Optional[str] = None,
        mock_mode: bool = False
    ):
        self.repo_root = Path(repo_root).resolve()
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repository = repository or os.environ.get("GITHUB_REPOSITORY", "owner/phoenixci")
        self.mock_mode = mock_mode or not self.token or self.token == "replace_with_scoped_github_token"

    def create_repair_branch(self, branch_name: str, base_sha: str) -> bool:
        """Creates and checks out a new repair branch from base_sha."""
        try:
            # Check out the base commit
            subprocess.run(
                ["git", "checkout", base_sha],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True
            )
            # Create and switch to repair branch
            subprocess.run(
                ["git", "checkout", "-B", branch_name],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            return False

    def commit_changes(self, message: str, files: List[str]) -> Tuple[bool, str]:
        """Stages files and creates a git commit."""
        try:
            for f in files:
                subprocess.run(
                    ["git", "add", f],
                    cwd=str(self.repo_root),
                    check=True,
                    capture_output=True,
                    text=True
                )
            result = subprocess.run(
                [
                    "git", "-c", "user.name=github-actions[bot]",
                    "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                    "commit", "-m", message
                ],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True
            )
            # Get latest commit SHA
            rev_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True
            )
            return True, rev_res.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def push_branch(self, branch_name: str) -> Tuple[bool, str]:
        """Pushes the committed repair branch to the configured origin."""
        try:
            result = subprocess.run(
                ["git", "push", "origin", f"{branch_name}:{branch_name}"],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def create_pull_request(
        self,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str
    ) -> Tuple[bool, Optional[int], str]:
        """
        Creates a pull request on GitHub or records a simulated PR in mock mode.
        Returns:
            (success, pr_number, pr_url_or_message)
        """
        if self.mock_mode:
            # Deterministic simulated PR for local/mock demonstration
            mock_pr_num = 42
            mock_url = f"https://github.com/{self.repository}/pull/{mock_pr_num}"
            return True, mock_pr_num, mock_url

        url = f"https://api.github.com/repos/{self.repository}/pulls"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": base_branch
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=15)
            if res.status_code in (200, 201):
                data = res.json()
                return True, data.get("number"), data.get("html_url", "")
            else:
                return False, None, f"GitHub API error ({res.status_code}): {res.text}"
        except Exception as e:
            return False, None, f"Request failed: {str(e)}"

    def dispatch_workflow(self, workflow_id: str, branch_name: str) -> Tuple[bool, str]:
        """Requests CI for the repair branch after creating the pull request."""
        if self.mock_mode:
            return True, "Workflow dispatch simulated in mock mode."

        url = f"https://api.github.com/repos/{self.repository}/actions/workflows/{workflow_id}/dispatches"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            response = requests.post(url, json={"ref": branch_name}, headers=headers, timeout=15)
            if response.status_code == 204:
                return True, f"Dispatched {workflow_id} for {branch_name}."
            return False, f"GitHub API error ({response.status_code}): {response.text}"
        except requests.RequestException as err:
            return False, f"Request failed: {err}"

    @staticmethod
    def build_pr_body(
        incident_id: str,
        category: str,
        commit_sha: str,
        diagnosis: str,
        evidence: List[str],
        changes_summary: List[str],
        attempt_number: int,
        llm_metadata: Dict[str, Any],
        validation_status: str
    ) -> str:
        """Constructs markdown body for repair pull request."""
        evidence_list = "\n".join(f"- `{e}`" for e in evidence) if evidence else "- None provided"
        changes_list = "\n".join(f"- `{c}`" for c in changes_summary)

        return f"""## 🦅 PhoenixCI Self-Healing Repair Proposal

### Incident Metadata
- **Incident ID:** `{incident_id}`
- **Failure Category:** `{category}`
- **Failed Commit SHA:** `{commit_sha}`
- **Repair Attempt:** `{attempt_number}` of 2
- **Validation Status:** `{validation_status}`

---

### Diagnosis & Root Cause
{diagnosis}

#### Supporting Log Evidence:
{evidence_list}

---

### Proposed Modifications
{changes_list}

---

### Groq LLM Diagnostics
- **Model:** `{llm_metadata.get('model', 'unknown')}`
- **Tokens:** Prompt `{llm_metadata.get('prompt_tokens', 0)}` | Completion `{llm_metadata.get('completion_tokens', 0)}` | Total `{llm_metadata.get('total_tokens', 0)}`
- **Inference Latency:** `{llm_metadata.get('latency_seconds', 0)}s`
- **Estimated Cost:** `${llm_metadata.get('estimated_cost_usd', 0.0) or 'N/A'}`

> [!NOTE]
> This repair pull request was autonomously synthesized by PhoenixCI.
> CI verification is requested for the repair branch. Human review is required before merging.
"""
