from __future__ import annotations

from copy import deepcopy
from typing import Any

from nova_backend.core.json_store import read_json, write_json
from nova_backend.core.text_utils import safe_list
from nova_backend.paths import SESSIONS_FILE


DEFAULT_SESSIONS_PAYLOAD: dict[str, Any] = {
    "active_session_id": "",
    "sessions": [],
}


class SessionStore:
    def __init__(self, path=SESSIONS_FILE) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        data = read_json(self.path, DEFAULT_SESSIONS_PAYLOAD)
        if not isinstance(data, dict):
            data = deepcopy(DEFAULT_SESSIONS_PAYLOAD)

        data.setdefault("active_session_id", "")
        data["sessions"] = safe_list(data.get("sessions"))
        return data

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean = {
            "active_session_id": str(payload.get("active_session_id") or "").strip(),
            "sessions": safe_list(payload.get("sessions")),
        }
        write_json(self.path, clean)
        return clean

    def all_sessions(self) -> list[dict[str, Any]]:
        return safe_list(self.load().get("sessions"))

    def active_session_id(self) -> str:
        return str(self.load().get("active_session_id") or "").strip()

    def set_active_session_id(self, session_id: str) -> dict[str, Any]:
        data = self.load()
        data["active_session_id"] = str(session_id or "").strip()
        return self.save(data)