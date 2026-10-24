"""Patch applier for PhoenixCI in isolated working directories or worktrees."""

import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

from phoenix_agent.response_schema import RepairProposal, PatchChange


class PatchApplicationError(Exception):
    """Raised when a patch cannot be cleanly applied."""
    pass


class PatchApplier:
    """Applies validated patches to target working tree with rollback capability."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.backups: Dict[str, str] = {}

    def apply_proposal(self, proposal: RepairProposal) -> Tuple[bool, str, List[str]]:
        """
        Applies changes proposed in the RepairProposal.
        
        Returns:
            (success, unified_diff, list_of_modified_files)
        """
        self.backups.clear()
        modified_files: List[str] = []
        diff_outputs: List[str] = []

        try:
            for change in proposal.changes:
                target_rel = change.path.strip().replace("\\", "/").lstrip("/")
                target_path = (self.workspace_root / target_rel).resolve()

                if not target_path.is_file():
                    raise PatchApplicationError(f"Target file does not exist: {target_rel}")

                original_content = target_path.read_text(encoding="utf-8")
                # Save backup for rollback if needed
                self.backups[str(target_path)] = original_content

                if change.operation == "replace":
                    if change.original not in original_content:
                        raise PatchApplicationError(
                            f"Original target string not present in {target_rel}. Patch rejected."
                        )
                    if original_content.count(change.original) > 1:
                        raise PatchApplicationError(
                            f"Ambiguous replacement target: '{change.original}' occurs multiple times in {target_rel}."
                        )

                    new_content = original_content.replace(change.original, change.replacement, 1)
                    target_path.write_text(new_content, encoding="utf-8")
                    modified_files.append(target_rel)

                    # Compute unified diff
                    orig_lines = original_content.splitlines(keepends=True)
                    new_lines = new_content.splitlines(keepends=True)
                    file_diff = "".join(
                        difflib.unified_diff(
                            orig_lines,
                            new_lines,
                            fromfile=f"a/{target_rel}",
                            tofile=f"b/{target_rel}"
                        )
                    )
                    diff_outputs.append(file_diff)

                else:
                    raise PatchApplicationError(f"Unsupported patch operation: {change.operation}")

            full_diff = "\n".join(diff_outputs)
            return True, full_diff, modified_files

        except Exception as err:
            # Revert any files modified so far
            self.rollback()
            raise PatchApplicationError(f"Patch application failed: {str(err)}") from err

    def rollback(self) -> None:
        """Rolls back all files modified during the current patch application."""
        for file_path_str, original_content in self.backups.items():
            try:
                Path(file_path_str).write_text(original_content, encoding="utf-8")
            except Exception:
                pass
        self.backups.clear()
