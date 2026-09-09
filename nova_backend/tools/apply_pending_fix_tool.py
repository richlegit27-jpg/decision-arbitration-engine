from __future__ import annotations

from typing import Any, Dict

from nova_backend.tools.base import NovaTool


class ApplyPendingFixTool(NovaTool):

    name = "apply_pending_fix"

    description = (
        "Applies the pending file fix stored in the active "
        "Nova chat session."
    )

    category = "development"

    capabilities = [
        "apply_pending_fix",
        "write_file",
        "backup_file",
    ]

    risk_level = "high"

    requires_confirmation = True


    def __init__(
        self,
        chat_service=None,
    ):
        self.chat_service = chat_service


    def run(
        self,
        session_id: str = "",
        **kwargs,
    ) -> Dict[str, Any]:

        if self.chat_service is None:
            return {
                "ok": False,
                "error": (
                    "chat_service_unavailable"
                ),
            }

        session_id = str(
            session_id or ""
        ).strip()

        if not session_id:
            return {
                "ok": False,
                "error": (
                    "session_id_required"
                ),
            }

        try:

            result = (
                self.chat_service._apply_pending_fix(
                    session_id=session_id,
                )
            )

            if not isinstance(result, dict):
                return {
                    "ok": False,
                    "error": (
                        "invalid_apply_pending_fix_result"
                    ),
                    "result": result,
                }

            return result

        except Exception as exc:

            return {
                "ok": False,
                "error": (
                    "apply_pending_fix_failed"
                ),
                "details": repr(exc),
            }
