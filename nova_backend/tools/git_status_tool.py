from __future__ import annotations

import subprocess
from pathlib import Path

from nova_backend.tools.base import NovaTool


class GitStatusTool(NovaTool):

    name = "git_status"

    description = (
        "Returns the current Git repository status, active branch, and "
        "list of changed files."
    )

    category = "git"

    capabilities = [
        "git status",
        "repository status",
        "branch inspection",
        "working tree inspection",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path="",
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

            repo_path = (
                Path(path)
                .expanduser()
            )

            if not repo_path.exists():

                return {
                    "ok": False,
                    "error": "path_not_found",
                    "path": str(repo_path),
                }

            result = subprocess.run(
                [
                    "git",
                    "status",
                    "--short",
                    "--branch",
                ],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:

                return {
                    "ok": False,
                    "error": (
                        result.stderr.strip()
                        or "git_status_failed"
                    ),
                    "path": str(repo_path),
                }

            lines = [
                line
                for line in result.stdout.splitlines()
                if line.strip()
            ]

            branch = ""

            if (
                lines
                and lines[0].startswith("##")
            ):

                branch = (
                    lines[0]
                    .replace(
                        "##",
                        "",
                        1,
                    )
                    .strip()
                )

                lines = lines[1:]

            return {
                "ok": True,
                "path": str(
                    repo_path.resolve()
                ),
                "branch": branch,
                "changes": lines,
                "change_count": len(lines),
                "clean": len(lines) == 0,
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "git_status_timeout",
            }

        except FileNotFoundError:

            return {
                "ok": False,
                "error": "git_not_installed",
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }
