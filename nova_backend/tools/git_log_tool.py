from __future__ import annotations

import subprocess

from nova_backend.tools.base import NovaTool


class GitLogTool(NovaTool):

    name = "git_log"

    description = (
        "Shows recent Git commit history for a repository, including "
        "commit hashes, authors, dates, and commit messages."
    )

    category = "git"

    capabilities = [
        "git log",
        "commit history",
        "repository history",
        "commit inspection",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path="",
        limit=10,
        **kwargs,
    ):

        path = str(
            path or ""
        ).strip()

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        try:

            limit = int(
                limit
            )

        except (
            TypeError,
            ValueError,
        ):

            limit = 10

        limit = max(
            1,
            min(
                limit,
                100,
            ),
        )

        command = [
            "git",
            "-C",
            path,
            "log",
            f"-{limit}",
            "--pretty=format:%H%x1f%h%x1f%an%x1f%ad%x1f%s",
            "--date=iso",
        ]

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
                "error": "git_log_timeout",
            }

        if process.returncode != 0:

            return {
                "ok": False,
                "error": "git_log_failed",
                "message": (
                    process.stderr.strip()
                    or "Git log failed."
                ),
            }

        commits = []

        for line in process.stdout.splitlines():

            parts = line.split(
                "\x1f"
            )

            if len(parts) != 5:
                continue

            commits.append(
                {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                }
            )

        return {
            "ok": True,
            "path": path,
            "commits": commits,
            "count": len(commits),
        }
