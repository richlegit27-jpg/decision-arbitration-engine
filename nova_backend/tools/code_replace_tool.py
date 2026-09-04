from __future__ import annotations

import os

from nova_backend.tools.base import NovaTool


class CodeReplaceTool(NovaTool):

    name = "code_replace"

    description = (
        "Safely replaces one exact and unique block of text in a source "
        "file with new text."
    )

    category = "code"

    capabilities = [
        "code replacement",
        "source code editing",
        "exact text replacement",
        "safe code modification",
    ]

    risk_level = "medium"

    requires_confirmation = True

    def run(
        self,
        path="",
        old_text="",
        new_text="",
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

        if not old_text:

            return {
                "ok": False,
                "error": "old_text_required",
            }

        path = os.path.abspath(path)

        if not os.path.exists(path):

            return {
                "ok": False,
                "error": "file_not_found",
                "path": path,
            }

        if not os.path.isfile(path):

            return {
                "ok": False,
                "error": "not_a_file",
                "path": path,
            }

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="strict",
            ) as handle:

                content = handle.read()

        except UnicodeDecodeError:

            return {
                "ok": False,
                "error": "file_not_utf8",
                "path": path,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }

        occurrences = content.count(
            old_text
        )

        if occurrences == 0:

            return {
                "ok": False,
                "error": "old_text_not_found",
                "path": path,
            }

        if occurrences > 1:

            return {
                "ok": False,
                "error": "old_text_not_unique",
                "path": path,
                "occurrences": occurrences,
            }

        updated_content = content.replace(
            old_text,
            new_text,
            1,
        )

        try:

            with open(
                path,
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:

                handle.write(
                    updated_content
                )

            return {
                "ok": True,
                "path": path,
                "replaced": True,
                "occurrences": 1,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
                "path": path,
            }
