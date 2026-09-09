from __future__ import annotations

import json

from nova_backend.tools.base import NovaTool


class JsonValidateTool(NovaTool):

    name = "json_validate"
    description = "Validates JSON text and returns parsing details."
    category = "development"

    capabilities = [
        "json validation",
        "json parsing",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        text: str,
        **kwargs,
    ):

        if not text:
            return {
                "ok": False,
                "error": "text_required",
            }

        try:

            parsed = json.loads(text)

            return {
                "ok": True,
                "valid": True,
                "type": type(parsed).__name__,
            }

        except json.JSONDecodeError as exc:

            return {
                "ok": False,
                "valid": False,
                "error": str(exc),
                "line": exc.lineno,
                "column": exc.colno,
            }
