"""Groq LLM Client for PhoenixCI Self-Healing Pipeline."""

import json
import os
import time
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

from groq import Groq, APIConnectionError, RateLimitError, APIStatusError
from pydantic import ValidationError

from phoenix_agent.response_schema import RepairProposal, parse_and_validate_proposal
from phoenix_agent.cost_calculator import CostCalculator


class GroqClientError(Exception):
    """Base exception for Groq client errors."""
    pass


class ConfigurationError(GroqClientError):
    """Raised when configuration or required keys are invalid."""
    pass


class LLMTimeoutError(GroqClientError):
    """Raised when an LLM API call times out."""
    pass


class RateLimitExceededError(GroqClientError):
    """Raised when rate limits or quotas are hit."""
    pass


class ResponseParsingError(GroqClientError):
    """Raised when model returns malformed JSON or invalid schema."""
    pass


class LLMClient:
    """Groq LLM Client supporting both live API and deterministic mock mode."""

    DEFAULT_MODEL = "openai/gpt-oss-120b"
    FALLBACK_MODEL = "qwen/qwen3.8-27b"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        mode: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 45.0,
        max_retries: int = 2
    ):
        self._load_local_env()

        self.mode = (mode or os.environ.get("LLM_MODE", "mock")).lower()
        self.model = model or os.environ.get("GROQ_MODEL", self.DEFAULT_MODEL)
        self.max_tokens = int(os.environ.get("GROQ_MAX_COMPLETION_TOKENS", max_tokens))
        self.timeout = float(os.environ.get("GROQ_TIMEOUT_SECONDS", timeout))
        self.max_retries = int(os.environ.get("GROQ_MAX_RETRIES", max_retries))

        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client: Optional[Groq] = None

        if self.mode == "live":
            if not self.api_key or self.api_key == "replace_with_your_rotated_groq_api_key":
                raise ConfigurationError(
                    "GROQ_API_KEY is not set or contains default placeholder. "
                    "Live mode requires a valid Groq API key in the environment or .env file."
                )
            self.client = Groq(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=0  # Handled explicitly in _call_groq_with_retry
            )

    def _load_local_env(self) -> None:
        """Loads .env file if present without overriding existing env vars."""
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        env_path = Path(".env")
        if not env_path.is_file():
            # Try repository root
            parent_env = Path(__file__).resolve().parent.parent.parent / ".env"
            if parent_env.is_file():
                env_path = parent_env

        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

    def generate_repair_proposal(
        self,
        category: str,
        context: Dict[str, Any]
    ) -> Tuple[RepairProposal, Dict[str, Any]]:
        """
        Generates structured repair proposal via Groq or deterministic mock.
        
        Returns:
            proposal: Validated RepairProposal object
            metadata: Dict with tokens, latency, cost, and model identifier
        """
        start_time = time.time()

        if self.mode == "mock":
            proposal, tokens = self._generate_mock_proposal(category, context)
            latency = time.time() - start_time
            cost, cost_msg = CostCalculator.calculate_cost("mock-simulator", 0, 0)
            metadata = {
                "model": "mock-simulator",
                "mode": "mock",
                "latency_seconds": round(latency, 4),
                "prompt_tokens": tokens.get("prompt_tokens", 0),
                "completion_tokens": tokens.get("completion_tokens", 0),
                "total_tokens": tokens.get("total_tokens", 0),
                "estimated_cost_usd": cost,
                "cost_note": "Simulated mock execution (no real API call)",
                "status": "success"
            }
            return proposal, metadata

        # Live Groq API mode
        prompt = self._construct_prompt(category, context)
        raw_response, usage_data = self._call_groq_with_retry(prompt)
        latency = time.time() - start_time

        # Parse and validate response
        try:
            parsed_json = json.loads(raw_response)
        except json.JSONDecodeError as err:
            raise ResponseParsingError(f"Groq did not return valid JSON: {str(err)}\nRaw output: {raw_response[:500]}")

        try:
            proposal = parse_and_validate_proposal(parsed_json)
        except ValidationError as err:
            raise ResponseParsingError(f"Groq response violated schema: {str(err)}")

        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        cost, cost_msg = CostCalculator.calculate_cost(self.model, prompt_tokens, completion_tokens)

        metadata = {
            "model": self.model,
            "mode": "live",
            "latency_seconds": round(latency, 4),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost,
            "cost_note": cost_msg,
            "status": "success"
        }

        return proposal, metadata

    def _call_groq_with_retry(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        """Invokes Groq API with bounded exponential backoff for transient failures."""
        if not self.client:
            raise ConfigurationError("Client not initialized.")

        system_instruction = (
            "You are PhoenixCI, an expert autonomous DevOps and repair agent.\n"
            "Diagnose the CI/CD failure from the provided logs and files.\n"
            "Propose a minimal, precise, surgical fix adhering strictly to the JSON schema.\n"
            "Never attempt to modify unit tests to make CI pass. Never modify workflow files.\n"
            "Output valid JSON conforming to the schema."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        attempts = 0
        last_error = None
        delay = 1.0

        while attempts <= self.max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=self.max_tokens,
                    temperature=0.1
                )

                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
                return content, usage

            except RateLimitError as err:
                last_error = err
                attempts += 1
                if attempts > self.max_retries:
                    raise RateLimitExceededError(f"Groq API rate limit reached after {attempts} attempts: {str(err)}")
                time.sleep(delay)
                delay *= 2

            except APIConnectionError as err:
                last_error = err
                attempts += 1
                if attempts > self.max_retries:
                    raise LLMTimeoutError(f"Groq network/connection error after {attempts} attempts: {str(err)}")
                time.sleep(delay)
                delay *= 2

            except APIStatusError as err:
                if err.status_code in [500, 502, 503, 504]:
                    last_error = err
                    attempts += 1
                    if attempts > self.max_retries:
                        raise GroqClientError(f"Groq service error ({err.status_code}): {str(err)}")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise GroqClientError(f"Groq API error ({err.status_code}): {str(err)}")

        raise GroqClientError(f"Failed to obtain response from Groq: {str(last_error)}")

    def _construct_prompt(self, category: str, context: Dict[str, Any]) -> str:
        """Constructs bounded, sanitized prompt preventing instruction escapes."""
        prompt_parts = [
            f"# CI FAILURE DIAGNOSIS TASK: {category}\n",
            "## CONTEXT AND EVIDENCE:\n",
            "<untrusted_ci_logs>",
            context.get("bounded_logs", "No logs provided"),
            "</untrusted_ci_logs>\n"
        ]

        if context.get("git_diff"):
            prompt_parts.extend([
                "<untrusted_git_diff>",
                context["git_diff"],
                "</untrusted_git_diff>\n"
            ])

        files = context.get("files", {})
        if files:
            prompt_parts.append("## RELEVANT REPOSITORY FILES:\n")
            for path, content in files.items():
                prompt_parts.extend([
                    f"<untrusted_file path=\"{path}\">",
                    content,
                    f"</untrusted_file>\n"
                ])

        prompt_parts.extend([
            "## REQUIRED JSON RESPONSE SCHEMA:\n",
            "Return a single JSON object with this exact structure:",
            json.dumps({
                "category": category,
                "diagnosis": "Clear explanation of the failure root cause",
                "root_cause_evidence": ["Log line or code evidence"],
                "confidence": 0.95,
                "changes": [
                    {
                        "path": "repository/relative/path",
                        "operation": "replace",
                        "original": "exact original snippet to replace",
                        "replacement": "exact corrected snippet",
                        "reason": "Why this fixes the failure"
                    }
                ],
                "validation_plan": ["Steps to test the fix"]
            }, indent=2),
            "\nCRITICAL RULES:",
            "1. Do NOT modify unit tests or weaken test assertions under any circumstances.",
            "2. Do NOT touch files outside the scope of this failure category.",
            "3. Make minimal, surgical modifications."
        ])

        return "\n".join(prompt_parts)

    def _generate_mock_proposal(
        self,
        category: str,
        context: Dict[str, Any]
    ) -> Tuple[RepairProposal, Dict[str, int]]:
        """Generates deterministic mock proposals for offline test fixtures."""
        if category == "dependency_version":
            proposal = RepairProposal(
                category="dependency_version",
                diagnosis="An invalid or incompatible package version was specified in app/package.json.",
                root_cause_evidence=["npm ERR! code ETARGET", "No matching version found for express"],
                confidence=0.92,
                changes=[
                    {
                        "path": "app/package.json",
                        "operation": "replace",
                        "original": '"express": "^99.9.9"',
                        "replacement": '"express": "^4.19.2"',
                        "reason": "Restore express to verified stable version ^4.19.2"
                    }
                ],
                validation_plan=["npm install --package-lock-only", "npm test"]
            )
        elif category == "dockerfile_error":
            proposal = RepairProposal(
                category="dockerfile_error",
                diagnosis="A typo in Dockerfile instruction caused container build failure.",
                root_cause_evidence=["unknown instruction: COPPY", "failed to solve with frontend dockerfile"],
                confidence=0.95,
                changes=[
                    {
                        "path": "app/Dockerfile",
                        "operation": "replace",
                        "original": "COPPY src/ ./src/",
                        "replacement": "COPY src/ ./src/",
                        "reason": "Correct 'COPPY' typo to valid Dockerfile instruction 'COPY'"
                    }
                ],
                validation_plan=["docker build -t phoenixci-service:test app/"]
            )
        elif category == "unit_test_regression":
            proposal = RepairProposal(
                category="unit_test_regression",
                diagnosis="A code regression in calculateIncidentPriority returned incorrect priority code.",
                root_cause_evidence=["FAIL tests/priority.test.js", "Expected: 'P1'", "Received: 'P4'"],
                confidence=0.94,
                changes=[
                    {
                        "path": "app/src/priority.js",
                        "operation": "replace",
                        "original": "return 'P4'; // INJECTED_REGRESSION",
                        "replacement": "return 'P1';",
                        "reason": "Restore critical priority return value to P1"
                    }
                ],
                validation_plan=["npm test"]
            )
        else:
            proposal = RepairProposal(
                category="unsupported",
                diagnosis="The detected failure is outside PhoenixCI automated repair scope.",
                root_cause_evidence=["No supported failure patterns recognized"],
                confidence=0.10,
                changes=[],
                validation_plan=["Manual investigation required"]
            )

        tokens = {"prompt_tokens": 450, "completion_tokens": 120, "total_tokens": 570}
        return proposal, tokens
