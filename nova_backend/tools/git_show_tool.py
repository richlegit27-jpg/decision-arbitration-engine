from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

from nova_backend.tools.base import NovaTool


class GitShowTool(NovaTool):

    name = "git_show"

    description = (
        "Shows the details, content, and changes for a specific Git "
        "commit, with optional commit statistics."
    )

    category = "git"

    capabilities = [
        "git show",
        "commit details",
        "commit inspection",
        "commit change inspection",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path: str,
        commit: str,
        stat_only: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        repo_path = Path(
            path
        ).resolve()

        if not repo_path.exists():

            return {
                "ok": False,
                "error": "path_not_found",
                "path": str(repo_path),
            }

        if not commit:

            return {
                "ok": False,
                "error": "commit_required",
            }

        command = [
            "git",
            "-C",
            str(repo_path),
            "show",
        ]

        if stat_only:

            command.append(
                "--stat"
            )

        command.append(
            commit
        )

        try:

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "git_command_timeout",
            }

        if completed.returncode != 0:

            return {
                "ok": False,
                "error": "git_show_failed",
                "details": (
                    completed.stderr.strip()
                ),
                "commit": commit,
            }

        output = completed.stdout

        return {
            "ok": True,
            "path": str(repo_path),
            "commit": commit,
            "stat_only": stat_only,
            "output": output,
            "chars": len(output),
        }
