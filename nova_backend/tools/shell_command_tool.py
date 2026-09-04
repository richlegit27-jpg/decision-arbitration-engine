from __future__ import annotations

import subprocess
from pathlib import Path

from nova_backend.tools.base import NovaTool


class ShellCommandTool(NovaTool):

    name = "shell_command"

    description = (
        "Executes a command in the local terminal using PowerShell or "
        "CMD and returns the command output, error output, and exit code."
    )

    category = "terminal"

    capabilities = [
        "command execution",
        "powershell execution",
        "cmd execution",
        "terminal automation",
    ]

    risk_level = "high"

    requires_confirmation = True

    def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 30,
        shell: str = "powershell",
    ):

        if not command:

            return {
                "ok": False,
                "error": "command_required",
            }

        working_directory = cwd or str(
            Path.cwd()
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

            if shell.lower() in (
                "powershell",
                "pwsh",
            ):

                process = subprocess.run(
                    [
                        "powershell.exe",
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

            elif shell.lower() == "cmd":

                process = subprocess.run(
                    command,
                    cwd=working_directory,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    shell=True,
                )

            else:

                return {
                    "ok": False,
                    "error": "unsupported_shell",
                    "shell": shell,
                }

            return {
                "ok": process.returncode == 0,
                "command": command,
                "cwd": working_directory,
                "shell": shell,
                "returncode": process.returncode,
                "stdout": (
                    process.stdout or ""
                ),
                "stderr": (
                    process.stderr or ""
                ),
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "command": command,
                "cwd": working_directory,
                "error": "command_timeout",
                "timeout": timeout,
            }

        except Exception as exc:

            return {
                "ok": False,
                "command": command,
                "cwd": working_directory,
                "error": "shell_command_failed",
                "message": str(exc),
            }
