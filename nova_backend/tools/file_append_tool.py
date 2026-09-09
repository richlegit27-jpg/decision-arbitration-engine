from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileAppendTool(NovaTool):

    name = "file_append"
    description = "Appends text to a local file."
    category = "filesystem"

    capabilities = [
        "file appending",
        "text writing",
    ]

    risk_level = "medium"
    requires_confirmation = False

    def run(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_parents: bool = True,
        **kwargs,
    ):

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        if content is None:

            return {
                "ok": False,
                "error": "content_required",
            }

        try:

            target = Path(path)

            if create_parents:

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

            with target.open(
                "a",
                encoding=encoding,
            ) as handle:

                handle.write(
                    str(content)
                )

            return {
                "ok": True,
                "path": str(target),
                "appended_chars": len(
                    str(content)
                ),
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
