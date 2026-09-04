from __future__ import annotations

import subprocess
from pathlib import Path

from nova_backend.tools.base import NovaTool


class TerminalExecuteTool(NovaTool):

    name = "terminal_execute"

    description = (
        "Executes a PowerShell command in the local workspace and "
        "returns its standard output, error output, and exit status."
    )

    category = "terminal"

    capabilities = [
        "PowerShell command execution",
        "terminal command execution",
        "local command execution",
        "workspace command execution",
    ]

    risk_level = "high"

    requires_confirmation = True

    def execute(
        self,
        command: str,
        path: str | None = None,
        timeout: int = 30,
        **kwargs,
    ):

        if not command or not command.strip():

            return {
                "ok": False,
                "error": "missing_command",
            }

        working_directory = None

        if path:

            working_path = Path(path)

            if not working_path.exists():

                return {
                    "ok": False,
                    "error": "path_not_found",
                    "path": str(working_path),
                }

            working_directory = str(
                working_path.resolve()
            )

        try:

            timeout = int(timeout)

        except (
            TypeError,
            ValueError,
        ):

            timeout = 30

        timeout = max(
            1,
            min(
                timeout,
                300,
            ),
        )

        try:

            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                cwd=working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )

            stdout = (
                completed.stdout or ""
            )

            stderr = (
                completed.stderr or ""
            )

            return {
                "ok": completed.returncode == 0,
                "command": command,
                "path": working_directory,
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "command_timeout",
                "command": command,
                "timeout": timeout,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": "terminal_execution_failed",
                "message": str(exc),
            }
