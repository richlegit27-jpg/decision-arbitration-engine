from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List
import uuid

from nova_backend.utils.file_utils import load_json_file, save_json_file
from nova_backend.utils.time_utils import iso_now


WORKING_STATE_KEYS = (
    "active_task",
    "current_file",
    "current_bug",
    "last_success",
    "next_move",
    "checkpoint",
    "updated_at",
)


def _new_working_state() -> Dict[str, str]:
    return {
        "active_task": "",
        "current_file": "",
        "current_bug": "",
        "last_success": "",
        "next_move": "",
        "checkpoint": "",
        "updated_at": "",
    }


def _normalize_working_state(value: Any) -> Dict[str, str]:
    state = _new_working_state()
    if isinstance(value, dict):
        for key in WORKING_STATE_KEYS:
            if key in value:
                state[key] = str(value.get(key) or "")
    return state


def _session_sort_key(session: Dict[str, Any]) -> tuple:
    pinned = bool(session.get("pinned", False))
    updated_at = str(session.get("updated_at") or "")
    created_at = str(session.get("created_at") or "")
    stamp = updated_at or created_at
    return (0 if pinned else 1, stamp)


def _normalize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    msg = dict(message or {})
    msg.setdefault("id", f"msg_{uuid.uuid4().hex}")
    msg.setdefault("role", "assistant")
    msg.setdefault("text", "")
    msg.setdefault("attachments", [])
    msg.setdefault("meta", {})
    now = iso_now()
    msg.setdefault("created_at", now)
    msg.setdefault("updated_at", msg.get("created_at") or now)
    return msg


def _normalize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    now = iso_now()
    data = dict(session or {})
    data.setdefault("id", f"session_{uuid.uuid4().hex}")
    data["title"] = str(data.get("title") or "New Chat").strip() or "New Chat"
    data["messages"] = [
        _normalize_message(m) for m in (data.get("messages") or []) if isinstance(m, dict)
    ]
    data["pinned"] = bool(data.get("pinned", False))
    data["created_at"] = str(data.get("created_at") or now)
    data["updated_at"] = str(data.get("updated_at") or data["created_at"] or now)
    data["working_state"] = _normalize_working_state(data.get("working_state"))
    return data


def new_session(title: str = "New Chat") -> Dict[str, Any]:
    now = iso_now()
    return {
        "id": f"session_{uuid.uuid4().hex}",
        "title": str(title or "New Chat").strip() or "New Chat",
        "messages": [],
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "working_state": _new_working_state(),
    }


class SessionService:

    def __init__(self, sessions_file: str | Path):
        self.sessions_file = Path(sessions_file)
        self._bootstrap()

    @property
    def active_session_id(self):
        return self.get_active_session_id()

    # -----------------------
    # STORE
    # -----------------------

    def _bootstrap(self) -> None:
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.sessions_file.exists():
            first = new_session("New Chat")
            self._write_store(
                {
                    "active_session_id": first["id"],
                    "sessions": [first],
                }
            )
            return

        store = self._read_store()
        sessions = self._load_sessions()
        active = str(store.get("active_session_id") or "").strip()

        if not sessions:
            first = new_session("New Chat")
            sessions = [first]
            active = first["id"]

        if not any(str(s.get("id") or "") == active for s in sessions):
            active = str(sessions[0].get("id") or "").strip()

        self._save_sessions(sessions, active)

    def _read_store(self) -> Dict[str, Any]:
        data = load_json_file(
            self.sessions_file,
            {
                "active_session_id": "",
                "sessions": [],
            },
        )

        if isinstance(data, list):
            return {
                "active_session_id": str(data[0].get("id") or "").strip() if data else "",
                "sessions": data,
            }

        if not isinstance(data, dict):
            return {"active_session_id": "", "sessions": []}

        data.setdefault("active_session_id", "")
        data.setdefault("sessions", [])
        return data

    def _write_store(self, store: Dict[str, Any]) -> None:
        payload = {
            "active_session_id": str(store.get("active_session_id") or "").strip(),
            "sessions": [_normalize_session(s) for s in store.get("sessions", [])],
        }
        payload["sessions"] = sorted(payload["sessions"], key=_session_sort_key)
        save_json_file(self.sessions_file, payload)

    def _load_sessions(self) -> List[Dict[str, Any]]:
        store = self._read_store()
        sessions = [_normalize_session(s) for s in store.get("sessions", [])]
        sessions.sort(key=_session_sort_key)
        return sessions

    def _save_sessions(self, sessions, active_session_id=None):
        sessions = [_normalize_session(s) for s in sessions]
        sessions.sort(key=_session_sort_key)

        active = str(active_session_id or "").strip()
        if not active and sessions:
            active = str(sessions[0].get("id") or "").strip()

        self._write_store(
            {
                "active_session_id": active,
                "sessions": sessions,
            }
        )

    def _find(self, sessions, session_id):
        target = str(session_id or "").strip()
        for i, s in enumerate(sessions):
            if str(s.get("id") or "").strip() == target:
                return i
        return -1

    # -----------------------
    # SESSION CONTROL (FIXED)
    # -----------------------

    def set_active(self, session_id: str):
        data = self._read_store()

        sessions = data.get("sessions", [])
        found = None

        for s in sessions:
            if s.get("id") == session_id:
                found = s
                break

        if not found:
            return None

        data["active_session_id"] = session_id
        self._write_store(data)

        return found

    def delete(self, session_id: str):
        data = self._read_store()

        sessions = data.get("sessions", [])
        new_sessions = [s for s in sessions if s.get("id") != session_id]

        if len(new_sessions) == len(sessions):
            return False

        data["sessions"] = new_sessions

        if data.get("active_session_id") == session_id:
            data["active_session_id"] = new_sessions[0]["id"] if new_sessions else ""

        self._write_store(data)

        return True

    # -----------------------
    # WORKING STATE
    # -----------------------

    def get_working_state(self, session_id: str) -> Dict[str, str]:
        sessions = self._load_sessions()
        i = self._find(sessions, session_id)
        if i < 0:
            return _new_working_state()

        state = _normalize_working_state(sessions[i].get("working_state"))
        sessions[i]["working_state"] = state
        self._save_sessions(sessions, session_id)
        return state

    def update_working_state(self, session_id: str, patch: Dict[str, Any]):
        sessions = self._load_sessions()
        i = self._find(sessions, session_id)
        if i < 0:
            return _new_working_state()

        state = _normalize_working_state(sessions[i].get("working_state"))

        for key in WORKING_STATE_KEYS:
            if key == "updated_at":
                continue
            if key in patch:
                state[key] = str(patch[key] or "").strip()

        state["updated_at"] = iso_now()
        sessions[i]["working_state"] = state
        sessions[i]["updated_at"] = state["updated_at"]

        self._save_sessions(sessions, session_id)
        return deepcopy(state)

    def clear_working_state(self, session_id: str):
        sessions = self._load_sessions()
        i = self._find(sessions, session_id)
        if i < 0:
            return _new_working_state()

        state = _new_working_state()
        state["updated_at"] = iso_now()

        sessions[i]["working_state"] = state
        sessions[i]["updated_at"] = state["updated_at"]

        self._save_sessions(sessions, session_id)
        return deepcopy(state)

    # -----------------------
    # CORE METHODS
    # -----------------------

    def get_active_session_id(self):
        store = self._read_store()
        active = str(store.get("active_session_id") or "").strip()
        if active:
            return active

        sessions = self._load_sessions()
        if sessions:
            return str(sessions[0].get("id") or "").strip()
        return ""

    def get_session(self, session_id):
        sessions = self._load_sessions()
        i = self._find(sessions, session_id)
        return sessions[i] if i >= 0 else None

    def get_active_session(self):
        active_id = self.get_active_session_id()
        if not active_id:
            return None
        return self.get_session(active_id)

    def get_active(self):
        return self.get_active_session()

    def create_session(self, title="New Chat"):
        sessions = self._load_sessions()
        s = new_session(title)
        sessions.insert(0, s)
        self._save_sessions(sessions, s["id"])
        return s

    def append_message(self, session_id, message):
        sessions = self._load_sessions()
        i = self._find(sessions, session_id)
        if i < 0:
            return None

        sessions[i]["messages"].append(_normalize_message(message))
        sessions[i]["updated_at"] = iso_now()

        self._save_sessions(sessions, self.get_active_session_id())
        return sessions[i]

    # -----------------------
    # COMPATIBILITY
    # -----------------------

    def get_all(self):
        return self._load_sessions()

    def list_sessions(self):
        return self._load_sessions()

    def list(self):
        return self._load_sessions()

    def all(self):
        return self._load_sessions()

    def create(self, title="New Chat"):
        return self.create_session(title)

    def get(self, session_id):
        return self.get_session(session_id)

    def get_by_id(self, session_id):
        return self.get_session(session_id)