from __future__ import annotations

import subprocess

from nova_backend.tools.base import NovaTool


class GitDiffTool(NovaTool):

    name = "git_diff"

    description = (
        "Shows Git differences for a repository or specific file, "
        "including staged changes when requested."
    )

    category = "git"

    capabilities = [
        "git diff",
        "repository diff",
        "file change inspection",
        "staged change inspection",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path="",
        file="",
        staged=False,
        **kwargs,
    ):

        path = str(
            path or ""
        ).strip()

        file = str(
            file or ""
        ).strip()

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        command = [
            "git",
            "-C",
            path,
            "diff",
        ]

        if staged:

            command.append(
                "--staged"
            )

        if file:

            command.extend([
                "--",
                file,
            ])

        try:

            process = subprocess.run(
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
                "error": "git_diff_timeout",
            }

        if process.returncode != 0:

            return {
                "ok": False,
                "error": "git_diff_failed",
                "message": (
                    process.stderr.strip()
                    or "Git diff failed."
                ),
            }

        diff = process.stdout

        return {
            "ok": True,
            "path": path,
            "file": file or None,
            "staged": bool(staged),
            "diff": diff,
            "has_changes": bool(
                diff.strip()
            ),
            "chars": len(diff),
        }
