from __future__ import annotations

from typing import Any, Dict, List, Optional

from nova_backend.utils.file_utils import (
    read_json_file,
    atomic_write_json,
    safe_list,
)
from nova_backend.utils.time_utils import iso_now
from nova_backend.models.session import (
    new_session,
    normalize_session,
    normalize_message,
)


class SessionService:
    def __init__(self, sessions_file: str):
        self.sessions_file = sessions_file
        self.sessions: List[dict] = []
        self.active_session_id: Optional[str] = None

        self._load()

    # -----------------------
    # LOAD / SAVE
    # -----------------------

    def _load(self) -> None:
        data = read_json_file(self.sessions_file, default=[])

        raw_sessions = safe_list(data)
        self.sessions = [normalize_session(s) for s in raw_sessions]

        if self.sessions:
            self.active_session_id = self.sessions[0]["id"]

    def _save(self) -> None:
        atomic_write_json(self.sessions_file, self.sessions)

    # -----------------------
    # GETTERS
    # -----------------------

    def get_all(self) -> List[dict]:
        return self.sessions

    def get_active(self) -> Optional[dict]:
        return self.get_by_id(self.active_session_id)

    def get_by_id(self, session_id: str | None) -> Optional[dict]:
        if not session_id:
            return None

        for s in self.sessions:
            if s["id"] == session_id:
                return s

        return None

    # -----------------------
    # SESSION CONTROL
    # -----------------------

    def create(self, title: str = "New Chat") -> dict:
        session = new_session(title)
        self.sessions.insert(0, session)
        self.active_session_id = session["id"]
        self._save()
        return session

    def set_active(self, session_id: str) -> Optional[dict]:
        session = self.get_by_id(session_id)
        if not session:
            return None

        self.active_session_id = session_id
        return session

    def delete(self, session_id: str) -> bool:
        before = len(self.sessions)
        self.sessions = [s for s in self.sessions if s["id"] != session_id]

        if len(self.sessions) == before:
            return False

        if self.active_session_id == session_id:
            self.active_session_id = self.sessions[0]["id"] if self.sessions else None

        self._save()
        return True

    def rename(self, session_id: str, title: str) -> bool:
        session = self.get_by_id(session_id)
        if not session:
            return False

        session["title"] = str(title or "New Chat")
        session["updated_at"] = iso_now()
        self._save()
        return True

    def pin(self, session_id: str) -> bool:
        session = self.get_by_id(session_id)
        if not session:
            return False

        session["pinned"] = not session.get("pinned", False)
        session["updated_at"] = iso_now()

        # keep pinned at top
        self.sessions.sort(key=lambda s: (not s.get("pinned", False), s["updated_at"]), reverse=False)

        self._save()
        return True

    # -----------------------
    # MESSAGES
    # -----------------------

    def append_message(self, session_id: str, message: Dict[str, Any]) -> Optional[dict]:
        session = self.get_by_id(session_id)
        if not session:
            return None

        msg = normalize_message(message)

        session["messages"].append(msg)
        session["updated_at"] = iso_now()

        self._save()
        return msg

    def replace_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> bool:
        session = self.get_by_id(session_id)
        if not session:
            return False

        session["messages"] = [normalize_message(m) for m in messages]
        session["updated_at"] = iso_now()

        self._save()
        return True

    # -----------------------
    # STATE PAYLOAD
    # -----------------------

    def build_state(self) -> dict:
        return {
            "sessions": self.sessions,
            "active_session_id": self.active_session_id,
            "session": self.get_active(),
        }