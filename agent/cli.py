#!/usr/bin/env python3
"""PhoenixCI Command Line Interface for automated CI/CD self-healing."""

import argparse
import json
import sys
from pathlib import Path

# Add agent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phoenix_agent.classifier import FailureClassifier
from phoenix_agent.orchestrator import RecoveryOrchestrator
from phoenix_agent.audit_logger import AuditLogger
from phoenix_agent.retry_manager import RetryManager


def cmd_classify(args):
    """Classifies a log file into supported categories."""
    log_path = Path(args.log_file)
    if not log_path.is_file():
        print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    cat, conf, evidence = FailureClassifier.classify(log_text, args.failed_step or "")

    print(json.dumps({
        "category": cat,
        "confidence": conf,
        "evidence": evidence
    }, indent=2))


def cmd_recover(args):
    """Executes the full recovery cycle on a failed commit."""
    log_path = Path(args.log_file)
    if not log_path.is_file():
        print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
        sys.exit(1)

    log_text = log_path.read_text(encoding="utf-8", errors="replace")

    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)
    orchestrator = RecoveryOrchestrator(
        repo_root=repo_root,
        llm_mode=args.mode,
        groq_model=args.model
    )

    result = orchestrator.recover(
        commit_sha=args.commit,
        ci_logs=log_text,
        failed_step=args.failed_step or "",
        workflow_run_id=args.run_id
    )

    print(json.dumps(result, indent=2))
    if not result.get("success"):
        sys.exit(2)


def cmd_status(args):
    """Displays current incident status and retry counts."""
    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)
    manager = RetryManager(state_dir=str(Path(repo_root) / ".phoenix"))
    print(json.dumps(manager.state, indent=2))


def cmd_audit(args):
    """Outputs recent audit trail records."""
    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)
    logger = AuditLogger(log_dir=str(Path(repo_root) / ".phoenix"))
    events = logger.read_all_events()
    print(f"--- PhoenixCI Audit Trail ({len(events)} events) ---")
    for ev in events[-args.limit:]:
        print(f"[{ev['timestamp']}] {ev['event_type']} | Status: {ev['status']} | Incident: {ev['incident_id']}")


def main():
    parser = argparse.ArgumentParser(description="PhoenixCI: Groq-Powered Self-Healing CI/CD Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # classify
    p_classify = subparsers.add_parser("classify", help="Classify a CI failure log")
    p_classify.add_argument("--log-file", required=True, help="Path to CI log file")
    p_classify.add_argument("--failed-step", default="", help="Name of failed CI step")
    p_classify.set_defaults(func=cmd_classify)

    # recover
    p_recover = subparsers.add_parser("recover", help="Diagnose and propose repair for failed commit")
    p_recover.add_argument("--commit", required=True, help="Failed git commit SHA")
    p_recover.add_argument("--log-file", required=True, help="Path to CI log file")
    p_recover.add_argument("--failed-step", default="", help="Name of failed CI step")
    p_recover.add_argument("--run-id", default=None, help="CI workflow run ID")
    p_recover.add_argument("--mode", default=None, choices=["live", "mock"], help="LLM mode override")
    p_recover.add_argument("--model", default=None, help="Groq model override")
    p_recover.add_argument("--repo-root", default=None, help="Root path of repository")
    p_recover.set_defaults(func=cmd_recover)

    # status
    p_status = subparsers.add_parser("status", help="Inspect incident and retry status")
    p_status.add_argument("--repo-root", default=None)
    p_status.set_defaults(func=cmd_status)

    # audit
    p_audit = subparsers.add_parser("audit", help="Inspect audit log")
    p_audit.add_argument("--limit", type=int, default=20, help="Number of records to show")
    p_audit.add_argument("--repo-root", default=None)
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
