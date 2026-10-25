"""Context collector and prompt injection defense for PhoenixCI."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional


class ContextCollector:
    """Collects bounded context, redacts secrets, and sanitizes untrusted CI logs and files."""

    FRONTEND_SOURCE_PATTERN = re.compile(
        r"(?<![\w/])((?:frontend/)?src/(?:[\w.-]+/)*[\w.-]+\.(?:tsx?|css))(?=[:\s():]|$)"
    )

    # Patterns for secret redaction
    SECRET_PATTERNS = [
        (r"gsk_[A-Za-z0-9_-]{20,}", "[REDACTED_GROQ_API_KEY]"),
        (r"ghp_[A-Za-z0-9_]{20,}", "[REDACTED_GITHUB_TOKEN]"),
        (r"github_pat_[A-Za-z0-9_]{20,}", "[REDACTED_GITHUB_PAT]"),
        (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_ACCESS_KEY]"),
        (r"(?i)bearer\s+[A-Za-z0-9+/=_\-\.]{8,}", "Bearer [REDACTED_SECRET]"),
        (r"(?i)(password|secret|token)\s*[:=]\s*['\"]?([A-Za-z0-9+/=_\-\.]{8,})['\"]?", r"\1: [REDACTED_SECRET]"),
        (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC )?PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    ]

    # Suspicious prompt injection indicators in logs or source files
    INJECTION_INDICATORS = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)disregard\s+(all\s+)?rules",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)print\s+(the\s+)?(api[_\s]?key|secret|password|token)",
        r"(?i)modify\s+\.github/workflows",
        r"(?i)give\s+me\s+admin",
        r"(?i)system\s*:\s*you\s+are",
    ]

    def __init__(self, repo_root: str, max_log_lines: int = 100, max_file_chars: int = 15000):
        self.repo_root = Path(repo_root).resolve()
        self.max_log_lines = max_log_lines
        self.max_file_chars = max_file_chars

    def redact_secrets(self, text: str) -> str:
        """Redacts sensitive credentials and tokens."""
        if not text:
            return ""
        result = text
        for pattern, replacement in self.SECRET_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    def detect_prompt_injections(self, text: str) -> List[str]:
        """Detects prompt injection attempts embedded in untrusted data."""
        detected = []
        for pattern in self.INJECTION_INDICATORS:
            if re.search(pattern, text):
                detected.append(pattern)
        return detected

    def sanitize_untrusted_text(self, text: str) -> str:
        """Sanitizes text by redacting secrets and neutralizing injection tokens."""
        redacted = self.redact_secrets(text)
        # Neutralize common markdown/format breakout tricks
        sanitized = redacted.replace("```json", "```_json").replace("```yaml", "```_yaml")
        return sanitized

    def extract_bounded_logs(self, raw_logs: str) -> str:
        """Extracts the last N relevant log lines, redacting sensitive data."""
        if not raw_logs:
            return ""
        lines = raw_logs.strip().splitlines()
        bounded_lines = lines[-self.max_log_lines:]
        extracted = "\n".join(bounded_lines)
        return self.sanitize_untrusted_text(extracted)

    def read_repo_file(self, rel_path: str) -> Optional[str]:
        """Safely reads a repository file with bounded size and secret redaction."""
        clean_rel = rel_path.replace("\\", "/").lstrip("/")
        if ".." in clean_rel.split("/"):
            raise ValueError(f"Directory traversal prohibited: {rel_path}")

        full_path = (self.repo_root / clean_rel).resolve()
        try:
            full_path.relative_to(self.repo_root)
        except ValueError:
            raise ValueError(f"Path outside repository: {rel_path}")

        if not full_path.is_file():
            return None

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > self.max_file_chars:
                content = content[:self.max_file_chars] + f"\n... [TRUNCATED at {self.max_file_chars} chars] ..."
            return self.sanitize_untrusted_text(content)
        except Exception as e:
            return f"Error reading {rel_path}: {str(e)}"

    def collect_context(
        self,
        category: str,
        raw_logs: str,
        git_diff: str = ""
    ) -> Dict[str, object]:
        """
        Collects minimal category-specific context for LLM diagnosis.
        """
        bounded_logs = self.extract_bounded_logs(raw_logs)
        injections = self.detect_prompt_injections(raw_logs) + self.detect_prompt_injections(git_diff)

        context: Dict[str, object] = {
            "category": category,
            "bounded_logs": bounded_logs,
            "git_diff": self.sanitize_untrusted_text(git_diff),
            "files": {},
            "injection_warnings": injections,
        }

        # Category-specific files
        if category == "dependency_version":
            pkg_json = self.read_repo_file("app/package.json")
            if pkg_json:
                context["files"]["app/package.json"] = pkg_json
            # Don't embed huge package-lock, but check existence
            lock_path = self.repo_root / "app" / "package-lock.json"
            context["lockfile_exists"] = lock_path.is_file()

            frontend_pkg = self.read_repo_file("frontend/package.json")
            if frontend_pkg:
                context["files"]["frontend/package.json"] = frontend_pkg
            frontend_lock = self.repo_root / "frontend" / "package-lock.json"
            context["frontend_lockfile_exists"] = frontend_lock.is_file()

        elif category == "dockerfile_error":
            dockerfile = self.read_repo_file("app/Dockerfile")
            if dockerfile:
                context["files"]["app/Dockerfile"] = dockerfile
            # Provide directory listing of app
            app_dir = self.repo_root / "app"
            if app_dir.is_dir():
                context["app_directory_structure"] = [
                    str(p.relative_to(self.repo_root)).replace("\\", "/")
                    for p in app_dir.rglob("*")
                    if "node_modules" not in p.parts and ".git" not in p.parts
                ]

        elif category == "unit_test_regression":
            priority_impl = self.read_repo_file("app/src/priority.js")
            if priority_impl:
                context["files"]["app/src/priority.js"] = priority_impl
            api_impl = self.read_repo_file("app/src/app.js")
            if api_impl:
                context["files"]["app/src/app.js"] = api_impl
            server_impl = self.read_repo_file("app/src/server.js")
            if server_impl:
                context["files"]["app/src/server.js"] = server_impl
            test_file = self.read_repo_file("app/tests/priority.test.js")
            if test_file:
                context["files"]["app/tests/priority.test.js (READ ONLY REFERENCE)"] = test_file

            frontend_paths = set()
            for match in self.FRONTEND_SOURCE_PATTERN.finditer(raw_logs):
                source_path = match.group(1).replace("\\", "/")
                if source_path.startswith("src/"):
                    source_path = f"frontend/{source_path}"
                parts = source_path.split("/")
                if (
                    not source_path.startswith("frontend/src/")
                    or any(part in {"test", "tests", "__tests__"} for part in parts)
                    or ".test." in source_path
                    or ".spec." in source_path
                ):
                    continue
                frontend_paths.add(source_path)

            for source_path in sorted(frontend_paths)[:5]:
                source = self.read_repo_file(source_path)
                if source:
                    context["files"][source_path] = source

        return context
