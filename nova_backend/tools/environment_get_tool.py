from __future__ import annotations

import os

from nova_backend.tools.base import NovaTool


class EnvironmentGetTool(NovaTool):

    name = "environment_get"
    description = "Reads a local environment variable."
    category = "system"

    capabilities = [
        "environment inspection",
        "configuration lookup",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        name: str,
        default=None,
        **kwargs,
    ):

        if not name:

            return {
                "ok": False,
                "error": "name_required",
            }

        value = os.environ.get(
            str(name),
            default,
        )

        return {
            "ok": True,
            "name": str(name),
            "exists": value is not None,
            "value": value,
        }
