from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileListTool(NovaTool):

    name = "file_list"

    description = (
        "Lists files and directories from a local workspace path. "
        "Can optionally search directories recursively."
    )

    category = "filesystem"

    capabilities = [
        "directory listing",
        "file discovery",
        "workspace inspection",
        "recursive file discovery",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path="",
        recursive=False,
        max_items=200,
        **kwargs,
    ):

        path = str(path or "").strip()

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        try:
            directory = Path(path).expanduser().resolve()

        except Exception as exc:
            return {
                "ok": False,
                "error": "invalid_path",
                "message": str(exc),
            }

        if not directory.exists():
            return {
                "ok": False,
                "error": "path_not_found",
                "path": str(directory),
            }

        if not directory.is_dir():
            return {
                "ok": False,
                "error": "not_a_directory",
                "path": str(directory),
            }

        try:
            max_items = int(max_items or 200)

        except Exception:
            max_items = 200

        if max_items < 1:
            max_items = 200

        try:
            recursive = bool(recursive)

            if recursive:
                iterator = directory.rglob("*")
            else:
                iterator = directory.iterdir()

            items = []

            for item in iterator:

                if len(items) >= max_items:
                    break

                try:
                    items.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "type": (
                                "directory"
                                if item.is_dir()
                                else "file"
                            ),
                        }
                    )

                except Exception:
                    continue

            return {
                "ok": True,
                "path": str(directory),
                "items": items,
                "count": len(items),
                "truncated": len(items) >= max_items,
                "recursive": recursive,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": "directory_list_failed",
                "path": str(directory),
                "message": str(exc),
            }
