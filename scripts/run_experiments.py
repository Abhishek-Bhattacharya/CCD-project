#!/usr/bin/env python3
"""Experiment harness for PhoenixCI evaluating recovery across 20 trials."""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure agent is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from phoenix_agent.classifier import FailureClassifier
from phoenix_agent.orchestrator import RecoveryOrchestrator
from phoenix_agent.retry_manager import RetryManager


# Deterministic simulated baseline human recovery times (seconds) based on DORA benchmarks
# Dependency: ~15 mins (900s), Docker: ~25 mins (1500s), Regression: ~35 mins (2100s)
BASELINE_HUMAN_MTTR = {
    "dependency_version": 900.0,
    "dockerfile_error": 1500.0,
    "unit_test_regression": 2100.0,
}

SAMPLE_LOGS = {
    "dependency_version": """
npm ERR! code ETARGET
npm ERR! notarget No matching version found for express@^99.9.9.
npm ERR! notarget In most cases you or one of your dependencies are requesting
npm ERR! notarget a package version that doesn't exist.
npm ERR! A complete log of this run can be found in:
npm ERR!     /root/.npm/_logs/2026-10-24T18_00_00_000Z-debug-0.log
""",
    "dockerfile_error": """
#7 [2/4] COPY package*.json ./
#7 DONE 0.1s
#8 [3/4] RUN npm ci --omit=dev
#8 DONE 4.2s
#9 [4/4] COPPY src/ ./src/
#9 ERROR: failed to solve with frontend dockerfile.v0: unknown instruction: COPPY
------
 > [4/4] COPPY src/ ./src/:
------
Dockerfile:14
--------------------
  12 |     RUN npm ci --omit=dev
  13 |     # Copy application source code
  14 | >>> COPPY src/ ./src/
  15 |     # Run with unprivileged user
--------------------
error: failed to solve: process returned error
""",
    "unit_test_regression": """
FAIL tests/priority.test.js
  calculateIncidentPriority
    ✕ returns P1 for critical severity regardless of user count (5 ms)
    ✓ returns P1 for >= 1000 affected users regardless of severity (1 ms)

  ● calculateIncidentPriority › returns P1 for critical severity regardless of user count

    expect(received).toBe(expected) // Object.is equality

    Expected: "P1"
    Received: "P4"

      5 | describe('calculateIncidentPriority', () => {
      6 |   test('returns P1 for critical severity regardless of user count', () => {
    > 7 |     expect(calculateIncidentPriority('critical', 0)).toBe('P1');
        |                                                      ^

Test Suites: 1 failed, 1 passed, 2 total
Tests:       1 failed, 13 passed, 14 total
Snapshots:   0 total
Time:        1.12 s
"""
}


def run_experiment_suite(
    repo_root: str,
    trials_count: int = 20,
    mode: str = "mock",
    model: str = "openai/gpt-oss-120b"
) -> List[Dict[str, Any]]:
    """Runs designated number of repair trials across the 3 categories."""
    output_dir = Path(repo_root) / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_json = output_dir / "trials.json"
    results_csv = output_dir / "trials.csv"

    # Distribute trials across 3 categories
    categories = [
        "dependency_version",
        "dockerfile_error",
        "unit_test_regression"
    ]
    
    trials_schedule = []
    for i in range(trials_count):
        cat = categories[i % len(categories)]
        trials_schedule.append((i + 1, cat))

    print(f"=== Starting PhoenixCI Evaluation Harness ({trials_count} Trials, Mode: {mode}) ===")
    orchestrator = RecoveryOrchestrator(
        repo_root=repo_root,
        llm_mode=mode,
        groq_model=model,
        require_approval=False,
        auto_merge=True
    )

    records = []

    eval_run_id = f"eval-{int(time.time())}"
    for trial_id, scenario in trials_schedule:
        print(f"\n[Trial {trial_id}/{trials_count}] Running Scenario: {scenario} ...")
        ci_log = SAMPLE_LOGS[scenario]
        commit_sha = f"{eval_run_id}-{trial_id:03d}-{scenario[:4]}"
        step_hint = scenario

        # Prepare target file with the injected failure
        saved_content = {}
        if scenario == "dependency_version":
            target = Path(repo_root) / "app" / "package.json"
            content = target.read_text(encoding="utf-8")
            saved_content[target] = content
            target.write_text(content.replace('"express": "^4.19.2"', '"express": "^99.9.9"'), encoding="utf-8")

        elif scenario == "dockerfile_error":
            target = Path(repo_root) / "app" / "Dockerfile"
            content = target.read_text(encoding="utf-8")
            saved_content[target] = content
            target.write_text(content.replace("COPY src/ ./src/", "COPPY src/ ./src/"), encoding="utf-8")

        elif scenario == "unit_test_regression":
            target = Path(repo_root) / "app" / "src" / "priority.js"
            content = target.read_text(encoding="utf-8")
            saved_content[target] = content
            target.write_text(
                content.replace("return 'P1';", "return 'P4'; // INJECTED_REGRESSION"),
                encoding="utf-8"
            )

        start_time = time.time()
        try:
            result = orchestrator.recover(
                commit_sha=commit_sha,
                ci_logs=ci_log,
                failed_step=step_hint,
                workflow_run_id=f"eval-run-{trial_id}"
            )
        finally:
            # Ensure workspace is restored to pristine clean state
            for target_file, orig_text in saved_content.items():
                target_file.write_text(orig_text, encoding="utf-8")

        duration = time.time() - start_time

        meta = result.get("llm_metadata", {})
        proposal = result.get("proposal", {})
        baseline_time = BASELINE_HUMAN_MTTR.get(scenario, 1200.0)

        record = {
            "trial_id": trial_id,
            "scenario": scenario,
            "commit_sha": commit_sha,
            "failure_category": scenario,
            "classified_category": proposal.get("category", result.get("category")),
            "classification_correct": proposal.get("category") == scenario,
            "baseline_recovery_time_s": baseline_time,
            "phoenix_recovery_time_s": round(duration, 3),
            "repair_attempts": result.get("attempt_number", 1),
            "patch_validation_passed": result.get("success", False),
            "ci_passed": result.get("local_ci_passed", False),
            "merge_outcome": result.get("merge_outcome", "none"),
            "deployment_outcome": "simulated_success" if result.get("success") else "failed",
            "groq_model": meta.get("model", model),
            "llm_mode": mode,
            "input_tokens": meta.get("prompt_tokens", 0),
            "output_tokens": meta.get("completion_tokens", 0),
            "total_tokens": meta.get("total_tokens", 0),
            "estimated_cost_usd": meta.get("estimated_cost_usd", 0.0) or 0.0,
            "success": result.get("success", False)
        }

        records.append(record)
        print(f"  -> Outcome: {'SUCCESS' if record['success'] else 'FAILED'} | MTTR: {record['phoenix_recovery_time_s']}s | Cost: ${record['estimated_cost_usd']}")

    # Save to JSON
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    # Save to CSV
    if records:
        keys = list(records[0].keys())
        with open(results_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)

    print(f"\n[OK] All {trials_count} trials completed! Results saved to:")
    print(f"    - {results_json}")
    print(f"    - {results_csv}")
    return records


def main():
    parser = argparse.ArgumentParser(description="PhoenixCI Evaluation Experiment Suite")
    parser.add_argument("--trials", type=int, default=20, help="Number of trials to execute (default: 20)")
    parser.add_argument("--mode", choices=["live", "mock"], default="mock", help="Inference mode (live or mock)")
    parser.add_argument("--model", default="openai/gpt-oss-120b", help="Groq model ID")
    parser.add_argument("--repo-root", default=None)

    args = parser.parse_args()
    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)

    run_experiment_suite(
        repo_root=repo_root,
        trials_count=args.trials,
        mode=args.mode,
        model=args.model
    )


if __name__ == "__main__":
    main()
