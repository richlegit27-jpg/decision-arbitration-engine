from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileExistsTool(NovaTool):

    name = "file_exists"
    description = "Checks whether a file or directory exists."
    category = "filesystem"

    capabilities = [
        "file existence checking",
        "path validation",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        path: str,
        **kwargs,
    ):

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        try:

            target = Path(path)

            return {
                "ok": True,
                "path": str(target),
                "exists": target.exists(),
                "is_file": target.is_file(),
                "is_directory": target.is_dir(),
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
