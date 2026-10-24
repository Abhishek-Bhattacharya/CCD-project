#!/usr/bin/env python3
"""Fault injection utility for PhoenixCI experiments and demonstrations.

Supports exactly 3 scenarios:
1. dependency_version - corrupts express version in app/package.json
2. dockerfile_error - introduces invalid instruction in app/Dockerfile
3. unit_test_regression - breaks priority logic in app/src/priority.js without touching tests
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROTECTED_BRANCHES = {"main", "master", "production", "release"}


class FaultInjector:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root).resolve()
        self.state_dir = self.repo_root / ".phoenix"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "injected_fault.json"

    def get_current_branch(self) -> str:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True
        )
        return res.stdout.strip() if res.returncode == 0 else "unknown"

    def get_head_sha(self) -> str:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True
        )
        return res.stdout.strip() if res.returncode == 0 else "unknown"

    def is_dirty(self) -> bool:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True
        )
        return bool(res.stdout.strip())

    def inject(self, scenario: str, disposable_branch: bool = True, force: bool = False):
        branch = self.get_current_branch()
        if branch in PROTECTED_BRANCHES and not disposable_branch and not force:
            print(
                f"ERROR: Cannot inject faults into protected branch '{branch}' without --disposable-branch or --force.",
                file=sys.stderr
            )
            sys.exit(1)

        head_sha = self.get_head_sha()

        if disposable_branch:
            disp_branch_name = f"fault/{scenario}-{int(time.time())}"
            print(f"[*] Creating disposable branch: {disp_branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", disp_branch_name],
                cwd=str(self.repo_root),
                check=True
            )
            branch = disp_branch_name

        print(f"[*] Injecting scenario '{scenario}' on branch '{branch}' (Base commit: {head_sha[:8]})...")

        injected_files = {}

        if scenario == "dependency_version":
            pkg_path = self.repo_root / "app" / "package.json"
            content = pkg_path.read_text(encoding="utf-8")
            if '"express": "^4.19.2"' not in content:
                print("ERROR: Target dependency string not found in package.json", file=sys.stderr)
                sys.exit(1)
            new_content = content.replace('"express": "^4.19.2"', '"express": "^99.9.9"')
            injected_files[str(pkg_path)] = content
            pkg_path.write_text(new_content, encoding="utf-8")
            print("  -> Corrupted package.json with non-existent express version ^99.9.9")

        elif scenario == "dockerfile_error":
            df_path = self.repo_root / "app" / "Dockerfile"
            content = df_path.read_text(encoding="utf-8")
            if "COPY src/ ./src/" not in content:
                print("ERROR: Target Dockerfile instruction not found", file=sys.stderr)
                sys.exit(1)
            new_content = content.replace("COPY src/ ./src/", "COPPY src/ ./src/")
            injected_files[str(df_path)] = content
            df_path.write_text(new_content, encoding="utf-8")
            print("  -> Corrupted Dockerfile with invalid instruction 'COPPY'")

        elif scenario == "unit_test_regression":
            src_path = self.repo_root / "app" / "src" / "priority.js"
            content = src_path.read_text(encoding="utf-8")
            target = "if (normalizedSeverity === 'critical' || affectedUsers >= 1000 || (isProduction && affectedUsers >= 100)) {\n    return 'P1';\n  }"
            replacement = "if (normalizedSeverity === 'critical' || affectedUsers >= 1000 || (isProduction && affectedUsers >= 100)) {\n    return 'P4'; // INJECTED_REGRESSION\n  }"
            if target not in content:
                print("ERROR: Target priority logic snippet not found in priority.js", file=sys.stderr)
                sys.exit(1)
            new_content = content.replace(target, replacement)
            injected_files[str(src_path)] = content
            src_path.write_text(new_content, encoding="utf-8")
            print("  -> Injected regression in priority.js (tests remain 100% untouched)")

        else:
            print(f"ERROR: Unknown scenario '{scenario}'. Choose from: dependency_version, dockerfile_error, unit_test_regression", file=sys.stderr)
            sys.exit(1)

        # Save state for rollback
        state = {
            "scenario": scenario,
            "branch": branch,
            "original_sha": head_sha,
            "injected_files": {k: v for k, v in injected_files.items()}
        }
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"[OK] Fault injection complete for scenario: {scenario}")

    def rollback(self):
        if not self.state_file.is_file():
            print("[!] No active injected fault state found. Performing git checkout on app/ directory...")
            subprocess.run(["git", "checkout", "--", "app/"], cwd=str(self.repo_root))
            return

        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        injected_files = state.get("injected_files", {})
        for path_str, orig_content in injected_files.items():
            p = Path(path_str)
            if p.is_file():
                p.write_text(orig_content, encoding="utf-8")
                print(f"  -> Restored original content for: {p.relative_to(self.repo_root)}")

        self.state_file.unlink(missing_ok=True)
        print("[OK] Fault rollback completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="PhoenixCI Fault Injection Tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inject = sub.add_parser("inject", help="Inject a synthetic CI fault")
    p_inject.add_argument(
        "--scenario",
        required=True,
        choices=["dependency_version", "dockerfile_error", "unit_test_regression"],
        help="Failure scenario to inject"
    )
    p_inject.add_argument("--disposable-branch", action="store_true", default=False, help="Create disposable branch")
    p_inject.add_argument("--force", action="store_true", default=False, help="Force injection on current branch")
    p_inject.add_argument("--repo-root", default=None)

    p_rollback = sub.add_parser("rollback", help="Revert injected faults")
    p_rollback.add_argument("--repo-root", default=None)

    args = parser.parse_args()
    repo_root = args.repo_root or str(Path(__file__).resolve().parent.parent)
    injector = FaultInjector(repo_root=repo_root)

    if args.command == "inject":
        injector.inject(scenario=args.scenario, disposable_branch=args.disposable_branch, force=args.force)
    elif args.command == "rollback":
        injector.rollback()


if __name__ == "__main__":
    main()
