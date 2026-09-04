from __future__ import annotations

from nova_backend.tools.base import NovaTool


class FileReadTool(NovaTool):

    name = "file_read"

    description = (
        "Reads the contents of a file from the local Nova workspace."
    )

    category = "filesystem"

    capabilities = [
        "file reading",
        "local file inspection",
        "workspace file access",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        path: str,
        encoding: str = "utf-8",
        **kwargs,
    ):

        from pathlib import Path

        if not path:

            return {
                "ok": False,
                "error": "path_required",
            }

        try:

            file_path = Path(path)

            if not file_path.exists():

                return {
                    "ok": False,
                    "error": "file_not_found",
                    "path": str(file_path),
                }

            if not file_path.is_file():

                return {
                    "ok": False,
                    "error": "not_a_file",
                    "path": str(file_path),
                }

            content = file_path.read_text(
                encoding=encoding
            )

            return {
                "ok": True,
                "path": str(file_path),
                "content": content,
            }

        except UnicodeDecodeError:

            return {
                "ok": False,
                "error": "file_encoding_error",
                "path": path,
                "encoding": encoding,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
