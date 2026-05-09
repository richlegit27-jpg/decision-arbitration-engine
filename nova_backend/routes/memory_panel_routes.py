from __future__ import annotations

from typing import Any, Dict, List


def register_memory_panel_routes(app, memory_service):
    def _json_ok(**kwargs):
        payload = {"ok": True}
        payload.update(kwargs)
        return payload

    def _json_error(message: str, status_code: int = 400):
        return {"ok": False, "error": str(message)}, status_code

    def _coerce_memory_items(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("memory"), list):
                return payload["memory"]
            if isinstance(payload.get("items"), list):
                return payload["items"]
        return []

    def _build_memory_payload() -> List[Dict[str, Any]]:
        if hasattr(memory_service, "build_list_payload"):
            payload = memory_service.build_list_payload()
            return _coerce_memory_items(payload)

        if hasattr(memory_service, "list_memories"):
            payload = memory_service.list_memories()
            return _coerce_memory_items(payload)

        if hasattr(memory_service, "get_all"):
            payload = memory_service.get_all()
            return _coerce_memory_items(payload)

        return []

    @app.get("/api/memory")
    def api_memory():
        items = _build_memory_payload()
        return _json_ok(memory=items, items=items)

    @app.post("/api/memory/add")
    def api_memory_add():
        from flask import request

        data = request.get_json(silent=True) or {}
        text = str(data.get("text") or "").strip()
        kind = str(data.get("kind") or "general").strip() or "general"
        source = str(data.get("source") or "manual").strip() or "manual"
        session_id = str(data.get("session_id") or "").strip()

        if not text:
            return _json_error("Missing memory text")

        if hasattr(memory_service, "add_memory"):
            item = memory_service.add_memory(
                text=text,
                kind=kind,
                source=source,
                session_id=session_id,
            )
            return _json_ok(item=item)

        return _json_error("Memory service missing add_memory()", 500)

    @app.post("/api/memory/delete")
    def api_memory_delete():
        from flask import request

        data = request.get_json(silent=True) or {}
        memory_id = str(data.get("id") or "").strip()

        if not memory_id:
            return _json_error("Missing memory id")

        if hasattr(memory_service, "delete_memory"):
            deleted = memory_service.delete_memory(memory_id)
            return _json_ok(deleted=bool(deleted))

        if hasattr(memory_service, "remove_memory"):
            deleted = memory_service.remove_memory(memory_id)
            return _json_ok(deleted=bool(deleted))

        return _json_error("Memory service missing delete method", 500)