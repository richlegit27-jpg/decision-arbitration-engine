from __future__ import annotations

import subprocess
from pathlib import Path

from nova_backend.tools.base import NovaTool


class ProcessStartTool(NovaTool):

    name = "process_start"

    description = (
        "Starts a local process or program using a PowerShell command. "
        "Can optionally run the command from a specified working directory."
    )

    category = "system"

    capabilities = [
        "process execution",
        "program launching",
        "local command execution",
    ]

    risk_level = "high"

    requires_confirmation = True

    def run(
        self,
        command: str,
        cwd: str | None = None,
    ):

        if not command:

            return {
                "ok": False,
                "error": "command_required",
            }

        try:

            working_directory = (
                cwd
                or str(Path.cwd())
            )

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                cwd=working_directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )

            return {
                "ok": True,
                "command": command,
                "cwd": working_directory,
                "pid": process.pid,
                "started": True,
            }

        except Exception as exc:

            return {
                "ok": False,
                "command": command,
                "error": str(exc),
            }
