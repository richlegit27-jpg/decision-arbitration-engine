from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileWriteTool(NovaTool):

    name = "file_write"

    description = (
        "Writes or appends text content to a file in the local workspace. "
        "Can create missing parent directories when needed."
    )

    category = "filesystem"

    capabilities = [
        "file writing",
        "file creation",
        "file modification",
        "workspace file editing",
    ]

    risk_level = "medium"

    requires_confirmation = True

    def run(
        self,
        path="",
        content="",
        append=False,
        encoding="utf-8",
        create_parents=True,
        **kwargs,
    ):

        path = str(path or "").strip()

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        if content is None:

            content = ""

        if not isinstance(
            content,
            str,
        ):

            content = str(content)

        try:

            file_path = (
                Path(path)
                .expanduser()
                .resolve()
            )

        except Exception as exc:

            return {
                "ok": False,
                "error": "invalid_path",
                "message": str(exc),
            }

        try:

            if create_parents:

                file_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

        except Exception as exc:

            return {
                "ok": False,
                "error": "directory_create_failed",
                "path": str(
                    file_path.parent
                ),
                "message": str(exc),
            }

        try:

            append = bool(append)

            mode = (
                "a"
                if append
                else "w"
            )

            with file_path.open(
                mode,
                encoding=encoding or "utf-8",
            ) as handle:

                handle.write(content)

        except Exception as exc:

            return {
                "ok": False,
                "error": "file_write_failed",
                "path": str(file_path),
                "message": str(exc),
            }

        return {
            "ok": True,
            "path": str(file_path),
            "chars_written": len(content),
            "append": append,
        }
