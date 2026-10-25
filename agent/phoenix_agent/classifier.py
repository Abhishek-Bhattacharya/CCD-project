"""Failure classifier for PhoenixCI.

Classifies CI failure logs and context into one of the 3 supported categories:
- dependency_version
- dockerfile_error
- unit_test_regression
or unsupported.
"""

import re
from typing import Dict, List, Tuple


class FailureClassifier:
    """Classifies CI failure logs into supported categories."""

    DEPENDENCY_PATTERNS = [
        r"npm ERR! code ETARGET",
        r"npm ERR! notarget No matching version found",
        r"npm ERR! code ERESOLVE",
        r"npm ERR! code ENOVERSIONS",
        r"npm ERR! 404 Not Found",
        r"npm ERR! Could not resolve dependency",
        r"npm error code ETARGET",
        r"npm error notarget No matching version found",
        r"No matching version found for",
        r"Cannot find module",
        r"npm ERR! A complete log of this run can be found in",
    ]

    DOCKER_PATTERNS = [
        r"failed to solve: process",
        r"failed to solve with frontend dockerfile",
        r"docker build.*failed",
        r"COPY failed: file not found",
        r"unknown instruction:",
        r"Dockerfile parse error",
        r"returned a non-zero code:\s*\d+",
        r"Step \d+/\d+ :",
        r"failed to compute cache key",
    ]

    UNIT_TEST_PATTERNS = [
        r"FAIL\s+.*\.(?:test|spec)\.[jt]sx?",
        r"●\s+calculateIncidentPriority",
        r"●\s+PhoenixCI Express Endpoints",
        r"expect\(received\)\.toBe\(expected\)",
        r"Tests:\s+\d+\s+failed",
        r"Test Files\s+\d+\s+failed",
        r"Jest:.*failed",
        r"AssertionError",
        r"Received:\s+",
        r"error TS\d+:",
        r"Failed to compile",
        r"error during build",
    ]

    @classmethod
    def classify(cls, log_content: str, failed_step: str = "") -> Tuple[str, float, List[str]]:
        """
        Classifies log content.
        
        Returns:
            category: "dependency_version" | "dockerfile_error" | "unit_test_regression" | "unsupported"
            confidence: float between 0.0 and 1.0
            evidence: List of matched lines
        """
        if not log_content:
            return "unsupported", 0.0, ["Empty log content provided"]

        dep_matches = []
        docker_matches = []
        test_matches = []

        lines = log_content.splitlines()

        for line in lines:
            line_str = line.strip()
            for pattern in cls.DEPENDENCY_PATTERNS:
                if re.search(pattern, line_str, re.IGNORECASE):
                    dep_matches.append(line_str)
                    break
            for pattern in cls.DOCKER_PATTERNS:
                if re.search(pattern, line_str, re.IGNORECASE):
                    docker_matches.append(line_str)
                    break
            for pattern in cls.UNIT_TEST_PATTERNS:
                if re.search(pattern, line_str, re.IGNORECASE):
                    test_matches.append(line_str)
                    break

        # Check step hints
        step_lower = failed_step.lower()
        if "dependency" in step_lower or "install" in step_lower:
            dep_score = len(dep_matches) * 2 + 1
        else:
            dep_score = len(dep_matches)

        if "docker" in step_lower or "build" in step_lower and "docker" in log_content.lower():
            docker_score = len(docker_matches) * 2 + 1
        else:
            docker_score = len(docker_matches)

        if "test" in step_lower or "jest" in step_lower:
            test_score = len(test_matches) * 2 + 1
        else:
            test_score = len(test_matches)

        scores = {
            "dependency_version": (dep_score, dep_matches),
            "dockerfile_error": (docker_score, docker_matches),
            "unit_test_regression": (test_score, test_matches)
        }

        # Select highest scoring category
        best_cat, (best_score, best_matches) = max(scores.items(), key=lambda x: x[1][0])

        if best_score == 0:
            return "unsupported", 0.1, ["No recognized failure patterns found in logs"]

        # Calculate confidence based on matched evidence count
        confidence = min(0.95, 0.65 + (0.05 * min(best_score, 6)))

        return best_cat, round(confidence, 2), best_matches[:5]
