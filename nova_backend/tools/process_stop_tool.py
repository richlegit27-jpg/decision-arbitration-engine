from __future__ import annotations

import subprocess

from nova_backend.tools.base import NovaTool


class ProcessStopTool(NovaTool):

    name = "process_stop"

    description = (
        "Stops a running local process by process ID."
    )

    category = "process"

    requires_confirmation = True

    risk_level = "high"

    def run(
        self,
        pid: int | str | None = None,
        force: bool = False,
        **kwargs,
    ):

        if pid is None:
            return {
                "ok": False,
                "error": "pid_required",
            }

        try:
            normalized_pid = int(pid)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "error": "invalid_pid",
            }

        command = [
            "taskkill",
            "/PID",
            str(normalized_pid),
        ]

        if force:
            command.append("/F")

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            return {
                "ok": completed.returncode == 0,
                "pid": normalized_pid,
                "force": bool(force),
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "returncode": completed.returncode,
            }

        except Exception as exc:
            return {
                "ok": False,
                "pid": normalized_pid,
                "error": str(exc),
            }
