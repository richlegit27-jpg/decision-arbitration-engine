from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from nova_backend.tools.base import NovaTool


class GitCommitTool(NovaTool):

    name = "git_commit"

    description = (
        "Stages selected files and creates a Git commit with the "
        "provided commit message."
    )

    category = "git"

    capabilities = [
        "git commit",
        "repository commit",
        "commit creation",
        "version control changes",
    ]

    risk_level = "high"

    requires_confirmation = True

    def run(
        self,
        path: str,
        message: str,
        files: List[str] | None = None,
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

        if not message or not message.strip():

            return {
                "ok": False,
                "error": "commit_message_required",
            }

        try:

            if files:

                add_command = [
                    "git",
                    "-C",
                    str(repo_path),
                    "add",
                    "--",
                    *files,
                ]

            else:

                add_command = [
                    "git",
                    "-C",
                    str(repo_path),
                    "add",
                    "-A",
                ]

            add_result = subprocess.run(
                add_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            if add_result.returncode != 0:

                return {
                    "ok": False,
                    "error": "git_add_failed",
                    "details": add_result.stderr.strip(),
                }

            status_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "diff",
                    "--cached",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if status_result.returncode == 0:

                return {
                    "ok": False,
                    "error": "nothing_to_commit",
                }

            commit_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "commit",
                    "-m",
                    message.strip(),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            if commit_result.returncode != 0:

                return {
                    "ok": False,
                    "error": "git_commit_failed",
                    "details": (
                        commit_result.stderr.strip()
                    ),
                    "output": (
                        commit_result.stdout.strip()
                    ),
                }

            hash_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "rev-parse",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

            commit_hash = (
                hash_result.stdout.strip()
                if hash_result.returncode == 0
                else None
            )

            return {
                "ok": True,
                "path": str(repo_path),
                "message": message.strip(),
                "files": files,
                "commit": commit_hash,
                "output": (
                    commit_result.stdout.strip()
                ),
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "git_command_timeout",
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": "git_commit_exception",
                "details": repr(exc),
            }
