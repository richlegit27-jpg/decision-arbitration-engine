from __future__ import annotations

import os

from nova_backend.tools.base import NovaTool


class ProjectTreeTool(NovaTool):
    name = "project_tree"

    description = (
        "Returns a structured directory tree for a project."
    )

    def run(
        self,
        path="",
        max_depth=4,
        max_items=500,
        **kwargs,
    ):
        path = str(
            path or ""
        ).strip()

        if not path:
            return {
                "ok": False,
                "error": "path_required",
            }

        path = os.path.abspath(path)

        if not os.path.exists(path):
            return {
                "ok": False,
                "error": "path_not_found",
                "path": path,
            }

        if not os.path.isdir(path):
            return {
                "ok": False,
                "error": "path_not_directory",
                "path": path,
            }

        try:
            max_depth = int(max_depth)
        except (
            TypeError,
            ValueError,
        ):
            max_depth = 4

        try:
            max_items = int(max_items)
        except (
            TypeError,
            ValueError,
        ):
            max_items = 500

        max_depth = max(
            1,
            min(max_depth, 10),
        )

        max_items = max(
            1,
            min(max_items, 5000),
        )

        ignored_names = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
        }

        items = []
        truncated = False

        def walk(
            current_path,
            depth,
        ):
            nonlocal truncated

            if truncated:
                return

            if depth > max_depth:
                return

            try:
                entries = sorted(
                    os.scandir(current_path),
                    key=lambda entry: (
                        not entry.is_dir(),
                        entry.name.lower(),
                    ),
                )
            except OSError:
                return

            for entry in entries:

                if truncated:
                    return

                if entry.name in ignored_names:
                    continue

                relative_path = os.path.relpath(
                    entry.path,
                    path,
                )

                item = {
                    "name": entry.name,
                    "path": relative_path,
                    "type": (
                        "directory"
                        if entry.is_dir()
                        else "file"
                    ),
                    "depth": depth,
                }

                items.append(item)

                if len(items) >= max_items:
                    truncated = True
                    return

                if entry.is_dir(
                    follow_symlinks=False
                ):
                    walk(
                        entry.path,
                        depth + 1,
                    )

        walk(
            path,
            1,
        )

        return {
            "ok": True,
            "path": path,
            "items": items,
            "count": len(items),
            "max_depth": max_depth,
            "truncated": truncated,
        }