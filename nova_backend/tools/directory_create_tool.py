from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class DirectoryCreateTool(NovaTool):

    name = "directory_create"

    description = (
        "Creates a directory in the local workspace, including any "
        "missing parent directories."
    )

    category = "filesystem"

    capabilities = [
        "directory creation",
        "folder creation",
        "workspace organization",
        "parent directory creation",
    ]

    risk_level = "medium"

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

        try:

            target = (
                Path(path)
                .expanduser()
            )

            target.mkdir(
                parents=True,
                exist_ok=True,
            )

            return {
                "ok": True,
                "path": str(
                    target.resolve()
                ),
                "created": True,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
