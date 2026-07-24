from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path


class ErrorReportingService:

    def __init__(
        self,
        path="data/nova_errors.json",
    ):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def report(
        self,
        error,
        service="",
        context=None,
    ):
        try:
            payload = {
                "timestamp": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "service": str(service or ""),
                "error_type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
                "context": (
                    context
                    if isinstance(context, dict)
                    else {}
                ),
            }

            existing = []

            if self.path.exists():
                try:
                    existing = json.loads(
                        self.path.read_text(
                            encoding="utf-8"
                        )
                    )
                except Exception:
                    existing = []

            if not isinstance(existing, list):
                existing = []

            existing.append(payload)

            self.path.write_text(
                json.dumps(
                    existing[-200:],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except Exception:
            pass

        return payload