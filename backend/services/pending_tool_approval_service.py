from __future__ import annotations

from threading import Lock
from typing import Any


class PendingToolApprovalService:

    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_pending(
        self,
        session_id: str,
        tool: str,
        risk: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        record = {
            "session_id": str(session_id),
            "tool": str(tool),
            "risk": str(risk).upper(),
            "payload": payload or {},
        }

        with self._lock:
            self._pending[str(session_id)] = record

        return record

    def get_pending(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:

        with self._lock:
            return self._pending.get(str(session_id))

    def clear_pending(
        self,
        session_id: str,
    ) -> None:

        with self._lock:
            self._pending.pop(str(session_id), None)

    def approve(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        pending = self.get_pending(session_id)

        if not pending:
            return {
                "ok": False,
                "error": "No pending tool approval.",
            }

        self.clear_pending(session_id)

        return {
            "ok": True,
            "approved": True,
            "tool": pending.get("tool"),
            "risk": pending.get("risk"),
            "payload": pending.get("payload") or {},
        }

    def deny(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        pending = self.get_pending(session_id)

        if not pending:
            return {
                "ok": False,
                "error": "No pending tool approval.",
            }

        self.clear_pending(session_id)

        return {
            "ok": True,
            "denied": True,
            "tool": pending.get("tool"),
        }


pending_tool_approval_service = (
    PendingToolApprovalService()
)
