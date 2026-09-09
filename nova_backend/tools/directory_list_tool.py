from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class DirectoryListTool(NovaTool):

    name = "directory_list"
    description = "Lists files and directories in a local directory."
    category = "filesystem"

    capabilities = [
        "directory listing",
        "filesystem inspection",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        path: str = ".",
        recursive: bool = False,
        max_results: int = 500,
        **kwargs,
    ):

        try:

            target = Path(path)

            if not target.exists():

                return {
                    "ok": False,
                    "error": "directory_not_found",
                    "path": str(target),
                }

            if not target.is_dir():

                return {
                    "ok": False,
                    "error": "not_a_directory",
                    "path": str(target),
                }

            iterator = (
                target.rglob("*")
                if recursive
                else target.iterdir()
            )

            items = []

            for item in iterator:

                items.append(
                    {
                        "path": str(item),
                        "name": item.name,
                        "is_file": item.is_file(),
                        "is_directory": item.is_dir(),
                    }
                )

                if len(items) >= int(max_results):
                    break

            return {
                "ok": True,
                "path": str(target),
                "count": len(items),
                "items": items,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
