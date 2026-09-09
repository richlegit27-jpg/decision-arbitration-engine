from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from nova_backend.tools.base import NovaTool


class PythonRunTool(NovaTool):

    name = "python_run"
    description = "Runs a Python script."
    category = "development"

    capabilities = [
        "python execution",
        "script running",
    ]

    risk_level = "medium"
    requires_confirmation = False

    def run(
        self,
        path: str,
        args=None,
        timeout: int = 30,
        **kwargs,
    ):

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        try:

            target = Path(path)

            if not target.exists():

                return {
                    "ok": False,
                    "error": "file_not_found",
                    "path": str(target),
                }

            command = [
                sys.executable,
                str(target),
            ]

            if isinstance(args, list):

                command.extend(
                    [str(item) for item in args]
                )

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=int(timeout),
            )

            return {
                "ok": result.returncode == 0,
                "path": str(target),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "path": path,
                "error": "execution_timeout",
            }

        except Exception as exc:

            return {
                "ok": False,
                "path": path,
                "error": str(exc),
            }
