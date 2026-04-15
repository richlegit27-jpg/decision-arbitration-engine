from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _message_preview_from_message(message: Dict[str, Any]) -> str:
    text = _safe_text(message.get("text")).strip()
    if not text:
        return ""
    return text[:140]


def _session_title_from_messages(messages: List[Dict[str, Any]]) -> str:
    for msg in messages:
        if _safe_text(msg.get("role")) == "user":
            text = _safe_text(msg.get("text")).strip()
            if text:
                return text[:60]
    return "New Chat"


def _normalize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    now = iso_now()

    normalized = {
        "id": _safe_text(message.get("id")).strip() or f"msg_{uuid.uuid4().hex}",
        "role": _safe_text(message.get("role")).strip() or "assistant",
        "text": _safe_text(message.get("text")),
        "created_at": _safe_text(message.get("created_at")).strip() or now,
        "updated_at": _safe_text(message.get("updated_at")).strip() or now,
        "attachments": _safe_list(message.get("attachments")),
        "artifacts": _safe_list(message.get("artifacts")),
        "meta": message.get("meta") if isinstance(message.get("meta"), dict) else {},
    }

    if "pending" in message:
        normalized["pending"] = bool(message.get("pending"))
    if "streaming" in message:
        normalized["streaming"] = bool(message.get("streaming"))
    if "error" in message:
        normalized["error"] = bool(message.get("error"))

    return normalized


def _normalize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    now = iso_now()
    messages = [_normalize_message(m) for m in _safe_list(session.get("messages"))]

    normalized = {
        "id": _safe_text(session.get("id")).strip() or f"session_{uuid.uuid4().hex}",
        "title": _safe_text(session.get("title")).strip() or _session_title_from_messages(messages),
        "created_at": _safe_text(session.get("created_at")).strip() or now,
        "updated_at": _safe_text(session.get("updated_at")).strip() or now,
        "pinned": bool(session.get("pinned", False)),
        "messages": messages,
        "message_count": len(messages),
        "last_message_preview": _message_preview_from_message(messages[-1]) if messages else "",
    }
    return normalized


class SessionService:
    def __init__(self, sessions_file: str | Path):
        self.sessions_file = Path(sessions_file)
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap()

    # ==============================
    # COMPATIBILITY BRIDGE FOR APP.PY
    # ==============================

    @property
    def active_session_id(self) -> str:
        return self.get_active_session_id()

    def get_active(self) -> Optional[Dict[str, Any]]:
        return self.get_active_session()

    def create(self, title: str = "New Chat") -> Dict[str, Any]:
        return self.create_session(title)

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.get_session(session_id)

    def get_all(self) -> List[Dict[str, Any]]:
        return self.list_sessions()

    def list(self) -> List[Dict[str, Any]]:
        return self.list_sessions()

    def all(self) -> List[Dict[str, Any]]:
        return self.list_sessions()

    def set_active(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.set_active_session(session_id)

    def switch(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.set_active_session(session_id)

    def switch_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.set_active_session(session_id)

    def activate(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.set_active_session(session_id)

    def rename(self, session_id: str, title: str) -> Optional[Dict[str, Any]]:
        return self.rename_session(session_id, title)

    def delete(self, session_id: str) -> bool:
        return self.delete_session(session_id)

    def pin(self, session_id: str, pinned: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.pin_session(session_id, pinned)

    def unpin(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.pin_session(session_id, False)

    # ==============================
    # FILE IO
    # ==============================
    def _bootstrap(self) -> None:
        if not self.sessions_file.exists():
            self._write_store(
                {
                    "active_session_id": "",
                    "sessions": [],
                }
            )
            return

        try:
            store = self._read_store()
            changed = False

            if not isinstance(store, dict):
                store = {"active_session_id": "", "sessions": []}
                changed = True

            if "active_session_id" not in store:
                store["active_session_id"] = ""
                changed = True

            if "sessions" not in store or not isinstance(store["sessions"], list):
                store["sessions"] = []
                changed = True

            normalized_sessions = [_normalize_session(s) for s in store["sessions"]]
            if normalized_sessions != store["sessions"]:
                store["sessions"] = normalized_sessions
                changed = True

            if changed:
                self._write_store(store)

        except Exception:
            self._write_store(
                {
                    "active_session_id": "",
                    "sessions": [],
                }
            )

    def _read_store(self) -> Dict[str, Any]:
        try:
            raw = self.sessions_file.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                return {"active_session_id": "", "sessions": []}
            return data
        except Exception:
            return {"active_session_id": "", "sessions": []}

    def _write_store(self, store: Dict[str, Any]) -> None:
        self.sessions_file.write_text(
            json.dumps(store, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_sessions(self) -> List[Dict[str, Any]]:
        store = self._read_store()
        sessions = store.get("sessions", [])
        if not isinstance(sessions, list):
            return []
        return [_normalize_session(s) for s in sessions]

    def _save_sessions(self, sessions: List[Dict[str, Any]], active_session_id: Optional[str] = None) -> None:
        store = self._read_store()
        current_active = _safe_text(store.get("active_session_id")).strip()

        normalized_sessions = [_normalize_session(s) for s in sessions]

        if active_session_id is None:
            active_session_id = current_active

        self._write_store(
            {
                "active_session_id": _safe_text(active_session_id).strip(),
                "sessions": normalized_sessions,
            }
        )

    def _find_session_index(self, sessions: List[Dict[str, Any]], session_id: str) -> int:
        for i, session in enumerate(sessions):
            if _safe_text(session.get("id")).strip() == _safe_text(session_id).strip():
                return i
        return -1

    # ==============================
    # READ
    # ==============================
    def list_sessions(self) -> List[Dict[str, Any]]:
        store = self._read_store()
        sessions = [_normalize_session(s) for s in store.get("sessions", [])]

        sessions.sort(
            key=lambda s: (
                0 if s.get("pinned") else 1,
                -(self._iso_sort_key(s.get("updated_at"))),
            )
        )

        return deepcopy(sessions)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None
        return deepcopy(_normalize_session(sessions[idx]))

    def get_active_session_id(self) -> str:
        store = self._read_store()
        return _safe_text(store.get("active_session_id")).strip()

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        active_session_id = self.get_active_session_id()
        if not active_session_id:
            return None
        return self.get_session(active_session_id)

    # ==============================
    # COMPATIBILITY (APP.PY BRIDGE)
    # ==============================
    def get_active(self) -> Optional[Dict[str, Any]]:
        return self.get_active_session()

    def create(self, title: str = "New Chat") -> Dict[str, Any]:
        return self.create_session(title)

    # ==============================
    # CREATE / UPDATE
    # ==============================
    def create_session(self, title: str = "New Chat") -> Dict[str, Any]:
        sessions = self._load_sessions()
        now = iso_now()

        session = {
            "id": f"session_{uuid.uuid4().hex}",
            "title": _safe_text(title).strip() or "New Chat",
            "created_at": now,
            "updated_at": now,
            "pinned": False,
            "messages": [],
            "message_count": 0,
            "last_message_preview": "",
        }

        sessions.insert(0, _normalize_session(session))
        self._save_sessions(sessions, active_session_id=session["id"])
        return deepcopy(session)

    def set_active_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None

        self._save_sessions(sessions, active_session_id=session_id)
        return deepcopy(_normalize_session(sessions[idx]))

    def rename_session(self, session_id: str, title: str) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None

        sessions[idx]["title"] = _safe_text(title).strip() or sessions[idx].get("title") or "New Chat"
        sessions[idx]["updated_at"] = iso_now()

        self._save_sessions(sessions)
        return deepcopy(_normalize_session(sessions[idx]))

    def pin_session(self, session_id: str, pinned: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None

        current = bool(sessions[idx].get("pinned", False))
        sessions[idx]["pinned"] = (not current) if pinned is None else bool(pinned)
        sessions[idx]["updated_at"] = iso_now()

        self._save_sessions(sessions)
        return deepcopy(_normalize_session(sessions[idx]))

    def delete_session(self, session_id: str) -> bool:
        store = self._read_store()
        sessions = [_normalize_session(s) for s in store.get("sessions", [])]
        active_session_id = _safe_text(store.get("active_session_id")).strip()

        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return False

        sessions.pop(idx)

        if active_session_id == session_id:
            active_session_id = sessions[0]["id"] if sessions else ""

        self._save_sessions(sessions, active_session_id=active_session_id)
        return True

    # ==============================
    # MESSAGE WRITE
    # ==============================
    def append_message(self, session_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None

        normalized_message = _normalize_message(message)
        session = sessions[idx]

        session_messages = _safe_list(session.get("messages"))
        session_messages.append(normalized_message)

        session["messages"] = session_messages
        session["message_count"] = len(session_messages)
        session["last_message_preview"] = _message_preview_from_message(normalized_message)
        session["updated_at"] = iso_now()

        # Optional auto-title on first real user message
        if (_safe_text(session.get("title")).strip() in ("", "New Chat")) and normalized_message.get("role") == "user":
            candidate = _safe_text(normalized_message.get("text")).strip()
            if candidate:
                session["title"] = candidate[:60]

        sessions[idx] = _normalize_session(session)
        self._save_sessions(sessions, active_session_id=session_id)
        return deepcopy(sessions[idx])

    def add_message_to_session(self, session_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.append_message(session_id, message)

    def replace_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        sessions = self._load_sessions()
        idx = self._find_session_index(sessions, session_id)
        if idx < 0:
            return None

        normalized_messages = [_normalize_message(m) for m in _safe_list(messages)]
        sessions[idx]["messages"] = normalized_messages
        sessions[idx]["message_count"] = len(normalized_messages)
        sessions[idx]["last_message_preview"] = (
            _message_preview_from_message(normalized_messages[-1]) if normalized_messages else ""
        )
        sessions[idx]["updated_at"] = iso_now()

        if _safe_text(sessions[idx].get("title")).strip() in ("", "New Chat"):
            sessions[idx]["title"] = _session_title_from_messages(normalized_messages)

        sessions[idx] = _normalize_session(sessions[idx])
        self._save_sessions(sessions, active_session_id=session_id)
        return deepcopy(sessions[idx])

    # ==============================
    # HELPERS
    # ==============================
    def _iso_sort_key(self, value: Any) -> float:
        text = _safe_text(value).strip()
        if not text:
            return 0.0
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0