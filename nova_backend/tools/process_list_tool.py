from __future__ import annotations

import json
import subprocess

from nova_backend.tools.base import NovaTool


class ProcessListTool(NovaTool):

    name = "process_list"

    description = (
        "Lists running processes on the local computer. "
        "Can filter processes by name and limit the number returned."
    )

    category = "system"

    capabilities = [
        "process inspection",
        "system monitoring",
        "running process discovery",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        name: str | None = None,
        limit: int = 100,
    ):

        try:

            command = (
                "Get-Process | "
                "Select-Object "
                "Id,ProcessName,CPU,WorkingSet64 | "
                "Sort-Object ProcessName | "
                "ConvertTo-Json -Compress"
            )

            process = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )

            if process.returncode != 0:

                return {
                    "ok": False,
                    "error": "process_query_failed",
                    "stderr": process.stderr.strip(),
                }

            output = process.stdout.strip()

            if not output:

                processes = []

            else:

                processes = json.loads(output)

                if isinstance(processes, dict):

                    processes = [processes]

            if name:

                search = name.lower()

                processes = [
                    item
                    for item in processes
                    if search in str(
                        item.get(
                            "ProcessName",
                            "",
                        )
                    ).lower()
                ]

            safe_limit = max(
                1,
                min(
                    int(limit),
                    500,
                ),
            )

            processes = processes[:safe_limit]

            normalized = []

            for item in processes:

                normalized.append(
                    {
                        "pid": item.get("Id"),
                        "name": item.get(
                            "ProcessName"
                        ),
                        "cpu": item.get("CPU"),
                        "memory_bytes": item.get(
                            "WorkingSet64"
                        ),
                    }
                )

            return {
                "ok": True,
                "processes": normalized,
                "count": len(normalized),
                "filter": name,
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "process_query_timeout",
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }