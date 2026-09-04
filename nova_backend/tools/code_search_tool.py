from __future__ import annotations

import os

from nova_backend.tools.base import NovaTool


class CodeSearchTool(NovaTool):

    name = "code_search"

    description = (
        "Searches source code and text files for matching text and "
        "returns the matching file paths, line numbers, and content."
    )

    category = "code"

    capabilities = [
        "code search",
        "source code search",
        "text search",
        "workspace code inspection",
        "recursive source search",
    ]

    risk_level = "low"

    requires_confirmation = False

    def run(
        self,
        query="",
        path="",
        max_results=100,
        **kwargs,
    ):

        query = str(
            query or ""
        ).strip()

        path = str(
            path or ""
        ).strip()

        if not query:

            return {
                "ok": False,
                "error": "query_required",
            }

        if not path:

            path = os.getcwd()

        path = os.path.abspath(path)

        if not os.path.exists(path):

            return {
                "ok": False,
                "error": "path_not_found",
                "path": path,
            }

        try:

            max_results = int(
                max_results
            )

        except (
            TypeError,
            ValueError,
        ):

            max_results = 100

        max_results = max(
            1,
            min(
                max_results,
                500,
            ),
        )

        results = []

        text_extensions = {
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".md",
            ".txt",
            ".yml",
            ".yaml",
        }

        for root, dirs, files in os.walk(
            path
        ):

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {
                    "__pycache__",
                    ".git",
                    "node_modules",
                    ".venv",
                    "venv",
                }
            ]

            for filename in files:

                extension = os.path.splitext(
                    filename
                )[1].lower()

                if extension not in text_extensions:
                    continue

                file_path = os.path.join(
                    root,
                    filename,
                )

                try:

                    with open(
                        file_path,
                        "r",
                        encoding="utf-8",
                        errors="ignore",
                    ) as handle:

                        for line_number, line in enumerate(
                            handle,
                            start=1,
                        ):

                            if (
                                query.lower()
                                in line.lower()
                            ):

                                results.append(
                                    {
                                        "path": file_path,
                                        "line": line_number,
                                        "content": line.rstrip(),
                                    }
                                )

                                if (
                                    len(results)
                                    >= max_results
                                ):

                                    return {
                                        "ok": True,
                                        "query": query,
                                        "path": path,
                                        "results": results,
                                        "count": len(results),
                                        "truncated": True,
                                    }

                except Exception:
                    continue

        return {
            "ok": True,
            "query": query,
            "path": path,
            "results": results,
            "count": len(results),
            "truncated": False,
        }
