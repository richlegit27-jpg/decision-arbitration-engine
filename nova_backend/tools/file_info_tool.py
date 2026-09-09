from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileInfoTool(NovaTool):

    name = "file_info"
    description = "Returns metadata about a local file or directory."
    category = "filesystem"

    capabilities = [
        "file metadata",
        "file inspection",
        "path inspection",
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

            if not target.exists():

                return {
                    "ok": False,
                    "error": "path_not_found",
                    "path": str(target),
                }

            stat = target.stat()

            return {
                "ok": True,
                "path": str(target),
                "name": target.name,
                "suffix": target.suffix,
                "is_file": target.is_file(),
                "is_directory": target.is_dir(),
                "size_bytes": (
                    stat.st_size
                    if target.is_file()
                    else None
                ),
                "modified_at": stat.st_mtime,
                "created_at": stat.st_ctime,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
