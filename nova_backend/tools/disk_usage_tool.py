from __future__ import annotations

import shutil
from pathlib import Path

from nova_backend.tools.base import NovaTool


class DiskUsageTool(NovaTool):

    name = "disk_usage"
    description = "Returns disk usage information for a path."
    category = "system"

    capabilities = [
        "disk inspection",
        "storage usage",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        path: str = ".",
        **kwargs,
    ):

        try:

            target = Path(path).resolve()

            usage = shutil.disk_usage(
                target
            )

            return {
                "ok": True,
                "path": str(target),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
