#!/usr/bin/env python3
"""Aggregates and formats experiment metrics for PhoenixCI evaluation."""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List


def compute_metrics(trials: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes rigorous summary metrics across recorded trials."""
    if not trials:
        return {"error": "No trials recorded"}

    total_trials = len(trials)
    successful_trials = sum(1 for t in trials if t.get("success"))
    correct_classifications = sum(1 for t in trials if t.get("classification_correct"))
    patches_passed = sum(1 for t in trials if t.get("patch_validation_passed"))
    ci_passed = sum(1 for t in trials if t.get("ci_passed"))
    deployments_passed = sum(1 for t in trials if t.get("deployment_outcome") in ("simulated_success", "deployed"))

    phoenix_recovery_times = [t["phoenix_recovery_time_s"] for t in trials if "phoenix_recovery_time_s" in t]
    baseline_recovery_times = [t["baseline_recovery_time_s"] for t in trials if "baseline_recovery_time_s" in t]
    repair_attempts = [t["repair_attempts"] for t in trials if "repair_attempts" in t]
    total_tokens = [t["total_tokens"] for t in trials if "total_tokens" in t]
    costs = [t["estimated_cost_usd"] for t in trials if "estimated_cost_usd" in t]

    phoenix_mttr = statistics.mean(phoenix_recovery_times) if phoenix_recovery_times else 0.0
    baseline_mttr = statistics.mean(baseline_recovery_times) if baseline_recovery_times else 0.0
    mttr_reduction_pct = ((baseline_mttr - phoenix_mttr) / baseline_mttr * 100) if baseline_mttr > 0 else 0.0

    return {
        "total_trials": total_trials,
        "successful_repairs": successful_trials,
        "repair_success_rate_pct": round((successful_trials / total_trials) * 100, 2),
        "classification_accuracy_pct": round((correct_classifications / total_trials) * 100, 2),
        "patch_acceptance_rate_pct": round((patches_passed / total_trials) * 100, 2),
        "post_repair_ci_pass_rate_pct": round((ci_passed / total_trials) * 100, 2),
        "deployment_success_rate_pct": round((deployments_passed / total_trials) * 100, 2),
        "phoenix_mttr_seconds": round(phoenix_mttr, 3),
        "baseline_mttr_seconds": round(baseline_mttr, 1),
        "mttr_reduction_percentage": round(mttr_reduction_pct, 2),
        "avg_repair_attempts": round(statistics.mean(repair_attempts), 2) if repair_attempts else 1.0,
        "avg_total_tokens": round(statistics.mean(total_tokens), 1) if total_tokens else 0,
        "total_cost_usd": round(sum(costs), 6),
        "avg_cost_per_repair_usd": round(statistics.mean(costs), 6) if costs else 0.0,
        "experiment_mode": trials[0].get("llm_mode", "unknown") if trials else "unknown"
    }


def main():
    parser = argparse.ArgumentParser(description="PhoenixCI Metrics Collector")
    parser.add_argument("--trials-file", default=None, help="Path to trials.json")
    parser.add_argument("--output-json", default=None, help="Path to output summary JSON")
    parser.add_argument("--repo-root", default=None)

    args = parser.parse_args()
    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)
    trials_path = Path(args.trials_file or (Path(repo_root) / "experiments" / "trials.json"))

    if not trials_path.is_file():
        print(f"Error: Trials file not found: {trials_path}", file=sys.stderr)
        sys.exit(1)

    trials_data = json.loads(trials_path.read_text(encoding="utf-8"))
    metrics = compute_metrics(trials_data)

    print("==================================================")
    print("      [PHOENIXCI] EVALUATION SUMMARY METRICS      ")
    print("==================================================")
    print(f" Total Evaluation Trials:         {metrics['total_trials']}")
    print(f" LLM Mode:                        {metrics['experiment_mode'].upper()}")
    print(f" Repair Success Rate:             {metrics['repair_success_rate_pct']}%")
    print(f" Failure Classification Accuracy: {metrics['classification_accuracy_pct']}%")
    print(f" Patch Policy Acceptance Rate:    {metrics['patch_acceptance_rate_pct']}%")
    print(f" Post-Repair CI Pass Rate:        {metrics['post_repair_ci_pass_rate_pct']}%")
    print(f" Deployment Success Rate:         {metrics['deployment_success_rate_pct']}%")
    print("--------------------------------------------------")
    print(f" PhoenixCI MTTR:                  {metrics['phoenix_mttr_seconds']} seconds")
    print(f" Baseline Human MTTR:             {metrics['baseline_mttr_seconds']} seconds")
    print(f" MTTR Reduction:                  {metrics['mttr_reduction_percentage']}%")
    print("--------------------------------------------------")
    print(f" Average Tokens / Repair:         {metrics['avg_total_tokens']}")
    print(f" Average Cost / Repair:           ${metrics['avg_cost_per_repair_usd']}")
    print(f" Total Suite Cost:                ${metrics['total_cost_usd']}")
    print("==================================================")

    out_file = args.output_json or (Path(repo_root) / "experiments" / "metrics_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[OK] Metrics written to {out_file}")


if __name__ == "__main__":
    main()
