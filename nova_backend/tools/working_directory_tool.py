from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class WorkingDirectoryTool(NovaTool):

    name = "working_directory"
    description = "Returns the current working directory."
    category = "system"

    capabilities = [
        "working directory inspection",
        "runtime location",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        **kwargs,
    ):

        path = Path.cwd()

        return {
            "ok": True,
            "path": str(path),
        }
