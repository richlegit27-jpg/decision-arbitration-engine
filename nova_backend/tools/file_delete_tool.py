from __future__ import annotations

import os

from nova_backend.tools.base import NovaTool


class FileDeleteTool(NovaTool):

    name = "file_delete"

    description = (
        "Deletes a specific file from the local workspace. "
        "The operation permanently removes the file from disk."
    )

    category = "filesystem"

    capabilities = [
        "file deletion",
        "file removal",
        "workspace cleanup",
        "local file management",
    ]

    risk_level = "high"

    requires_confirmation = True

    def run(
        self,
        path="",
        **kwargs,
    ):

        path = str(
            path or ""
        ).strip()

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        path = os.path.abspath(path)

        if not os.path.exists(path):

            return {
                "ok": False,
                "error": "file_not_found",
                "path": path,
            }

        if not os.path.isfile(path):

            return {
                "ok": False,
                "error": "not_a_file",
                "path": path,
            }

        try:

            os.remove(path)

            return {
                "ok": True,
                "path": path,
                "deleted": True,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
