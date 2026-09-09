from __future__ import annotations

import py_compile
from pathlib import Path

from nova_backend.tools.base import NovaTool


class PythonCompileTool(NovaTool):

    name = "python_compile"
    description = "Compiles a Python file to check for syntax errors."
    category = "development"

    capabilities = [
        "python syntax validation",
        "python compilation checking",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        path: str,
        **kwargs,
    ):

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        try:

            target = Path(path)

            if not target.exists():

                return {
                    "ok": False,
                    "error": "file_not_found",
                    "path": str(target),
                }

            py_compile.compile(
                str(target),
                doraise=True,
            )

            return {
                "ok": True,
                "path": str(target),
                "compiled": True,
            }

        except py_compile.PyCompileError as exc:

            return {
                "ok": False,
                "path": path,
                "compiled": False,
                "error": str(exc),
            }

        except Exception as exc:

            return {
                "ok": False,
                "path": path,
                "error": str(exc),
            }
