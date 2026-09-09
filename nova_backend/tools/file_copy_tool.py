from __future__ import annotations

import shutil
from pathlib import Path

from nova_backend.tools.base import NovaTool


class FileCopyTool(NovaTool):

    name = "file_copy"
    description = "Copies a file to another location."
    category = "filesystem"

    capabilities = [
        "file copying",
        "file duplication",
    ]

    risk_level = "medium"
    requires_confirmation = False

    def run(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
        **kwargs,
    ):

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

            source_path = Path(source)
            destination_path = Path(destination)

            if not source_path.exists():

                return {
                    "ok": False,
                    "error": "source_not_found",
                    "source": str(source_path),
                }

            if not source_path.is_file():

                return {
                    "ok": False,
                    "error": "source_not_a_file",
                    "source": str(source_path),
                }

            if (
                destination_path.exists()
                and not overwrite
            ):

                return {
                    "ok": False,
                    "error": "destination_exists",
                    "destination": str(destination_path),
                }

            destination_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source_path,
                destination_path,
            )

            return {
                "ok": True,
                "source": str(source_path),
                "destination": str(destination_path),
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }
