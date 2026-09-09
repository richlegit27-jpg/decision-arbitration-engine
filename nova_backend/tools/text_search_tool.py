from __future__ import annotations

from pathlib import Path

from nova_backend.tools.base import NovaTool


class TextSearchTool(NovaTool):

    name = "text_search"
    description = "Searches for text inside a local file."
    category = "development"

    capabilities = [
        "text searching",
        "file content search",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        path: str,
        query: str,
        case_sensitive: bool = False,
        max_results: int = 100,
        **kwargs,
    ):

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        if not query:
            return {
                "ok": False,
                "error": "query_required",
            }

        try:

            target = Path(path)

            if not target.exists():

                return {
                    "ok": False,
                    "error": "file_not_found",
                    "path": str(target),
                }

            if not target.is_file():

                return {
                    "ok": False,
                    "error": "not_a_file",
                    "path": str(target),
                }

            content = target.read_text(
                encoding="utf-8",
                errors="replace",
            )

            search_query = query
            search_content = content

            if not case_sensitive:

                search_query = query.lower()
                search_content = content.lower()

            results = []

            for line_number, line in enumerate(
                content.splitlines(),
                start=1,
            ):

                comparison = (
                    line
                    if case_sensitive
                    else line.lower()
                )

                if search_query in comparison:

                    results.append(
                        {
                            "line": line_number,
                            "text": line,
                        }
                    )

                    if len(results) >= int(max_results):
                        break

            return {
                "ok": True,
                "path": str(target),
                "query": query,
                "count": len(results),
                "results": results,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
