from __future__ import annotations

import shutil
from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileMoveTool(NovaTool):

    name = "file_move"

    description = (
        "Moves or renames a local file or directory to another path. "
        "Can create missing destination parent directories."
    )

    category = "filesystem"

    capabilities = [
        "file moving",
        "file renaming",
        "directory moving",
        "workspace organization",
    ]

    risk_level = "medium"

    requires_confirmation = True

    def run(
        self,
        source="",
        destination="",
        **kwargs,
    ):

        source = str(
            source or ""
        ).strip()

        destination = str(
            destination or ""
        ).strip()

        if not source:

            return {
                "ok": False,
                "error": "source_required",
            }

        if not destination:

            return {
                "ok": False,
                "error": "destination_required",
            }

        try:

            source_path = (
                Path(source)
                .expanduser()
            )

            destination_path = (
                Path(destination)
                .expanduser()
            )

            if not source_path.exists():

                return {
                    "ok": False,
                    "error": "source_not_found",
                    "source": str(source_path),
                }

            destination_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(source_path),
                str(destination_path),
            )

            return {
                "ok": True,
                "source": str(source_path),
                "destination": str(
                    destination_path
                ),
                "moved": True,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "source": source,
                "destination": destination,
            }
