from __future__ import annotations

import shutil
from pathlib import Path

from nova_backend.tools.base import NovaTool


class DirectoryDeleteTool(NovaTool):

    name = "directory_delete"

    description = (
        "Deletes a directory from the local workspace."
    )

    category = "filesystem"

    requires_confirmation = True

    risk_level = "high"

    def run(
        self,
        path: str | None = None,
        recursive: bool = False,
        **kwargs,
    ):

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        target = Path(path).expanduser()

        if not target.exists():
            return {
                "ok": False,
                "error": "directory_not_found",
                "path": str(target),
            }

        if not target.is_dir():
            return {
                "ok": False,
                "error": "path_is_not_directory",
                "path": str(target),
            }

        try:

            if recursive:
                shutil.rmtree(target)

            else:
                target.rmdir()

            return {
                "ok": True,
                "path": str(target),
                "recursive": bool(recursive),
            }

        except OSError as exc:
            return {
                "ok": False,
                "path": str(target),
                "error": str(exc),
            }
