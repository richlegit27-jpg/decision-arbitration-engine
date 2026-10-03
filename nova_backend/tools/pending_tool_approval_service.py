from __future__ import annotations

from typing import Any


class PendingToolApprovalService:
    """Process-local pending approvals, scoped to both session and owner."""

    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}

    def set_pending(self, session_id: str, tool_runtime: dict[str, Any], owner_id: str = "") -> dict[str, Any]:
        session_id = str(session_id or "").strip()
        owner_id = str(owner_id or "").strip()
        if not session_id or not owner_id:
            return {"ok": False, "error": "Missing session or authenticated owner."}
        plan = tool_runtime.get("plan") or {}
        pending = {
            "owner_id": owner_id,
            "tool": tool_runtime.get("tool"),
            "payload": tool_runtime.get("payload") or {},
            "risk": tool_runtime.get("risk"),
            "plan": plan,
        }
        for key in ("surface", "call_id", "model_response_id", "model"):
            value = tool_runtime.get(key)
            if isinstance(value, str) and value.strip():
                pending[key] = value.strip()
        self._pending[session_id] = pending
        return {"ok": True, "session_id": session_id, "pending": pending}

    def get_pending(self, session_id: str, owner_id: str = "") -> dict[str, Any] | None:
        session_id, owner_id = str(session_id or "").strip(), str(owner_id or "").strip()
        pending = self._pending.get(session_id) if session_id and owner_id else None
        if not pending or pending.get("owner_id") != owner_id:
            return None
        return dict(pending)

    def clear_pending(self, session_id: str, owner_id: str = "") -> None:
        session_id, owner_id = str(session_id or "").strip(), str(owner_id or "").strip()
        pending = self._pending.get(session_id) if session_id and owner_id else None
        if pending and pending.get("owner_id") == owner_id:
            self._pending.pop(session_id, None)

    def approve(self, session_id: str, owner_id: str = "") -> dict[str, Any]:
        pending = self.get_pending(session_id, owner_id)
        if not pending:
            return {"ok": False, "error": "No pending tool approval."}
        self.clear_pending(session_id, owner_id)
        return {"ok": True, "pending": pending}

    def deny(self, session_id: str, owner_id: str = "") -> dict[str, Any]:
        pending = self.get_pending(session_id, owner_id)
        if not pending:
            return {"ok": False, "error": "No pending tool approval."}
        self.clear_pending(session_id, owner_id)
        return {"ok": True, "denied": True, "tool": pending.get("tool")}


pending_tool_approval_service = PendingToolApprovalService()
