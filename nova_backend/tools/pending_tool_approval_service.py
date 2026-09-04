from __future__ import annotations

from typing import Any, Dict


class PendingToolApprovalService:

    def __init__(self) -> None:
        self._pending: Dict[str, Dict[str, Any]] = {}

    def set_pending(
        self,
        session_id: str,
        tool_runtime: Dict[str, Any],
    ) -> Dict[str, Any]:

        session_id = str(session_id or "").strip()

        if not session_id:
            return {
                "ok": False,
                "error": "Missing session_id.",
            }

        plan = tool_runtime.get("plan") or {}

        pending = {
            "tool": tool_runtime.get("tool"),
            "payload": tool_runtime.get("payload") or {},
            "risk": tool_runtime.get("risk"),
            "plan": plan,
        }

        self._pending[session_id] = pending

        return {
            "ok": True,
            "session_id": session_id,
            "pending": pending,
        }

    def get_pending(
        self,
        session_id: str,
    ) -> Dict[str, Any] | None:

        session_id = str(session_id or "").strip()

        if not session_id:
            return None

        return self._pending.get(session_id)

    def clear_pending(
        self,
        session_id: str,
    ) -> None:

        session_id = str(session_id or "").strip()

        if session_id:
            self._pending.pop(session_id, None)

    def approve(
        self,
        session_id: str,
    ) -> Dict[str, Any]:

        pending = self.get_pending(session_id)

        if not pending:
            return {
                "ok": False,
                "error": "No pending tool approval.",
            }

        self.clear_pending(session_id)

        return {
            "ok": True,
            "pending": pending,
        }

    def deny(
        self,
        session_id: str,
    ) -> Dict[str, Any]:

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


pending_tool_approval_service = PendingToolApprovalService()