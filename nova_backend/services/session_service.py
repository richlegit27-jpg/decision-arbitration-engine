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

    data["user_id"] = str(data.get("user_id") or "").strip()

    data["title"] = str(data.get("title") or "New Chat").strip() or "New Chat"
    data["messages"] = [
        _normalize_message(m) for m in (data.get("messages") or []) if isinstance(m, dict)
    ]
    data["pinned"] = bool(data.get("pinned", False))
    data["created_at"] = str(data.get("created_at") or now)
    data["updated_at"] = str(data.get("updated_at") or data["created_at"] or now)
    data["working_state"] = _normalize_working_state(data.get("working_state"))
    return data


def new_session(
    title: str = "New Chat",
    user_id: str = "",
) -> Dict[str, Any]:
    now = iso_now()
    return {
        "id": f"session_{uuid.uuid4().hex}",
        "title": str(title or "New Chat").strip() or "New Chat",
        "user_id": str(user_id or "").strip(),
        "messages": [],
        "pinned": False,
        "created_at": now,
        "updated_at": now,
        "working_state": _new_working_state(),
    }


# NOVA_SESSION_BAD_TITLE_AUTOFIX_HELPERS_20260624
NOVA_SESSION_BAD_AUTO_TITLES_20260624 = {
    "",
    "new chat",
    "untitled",
    "untitled session",
    "web fetch",
    "webfetch",
    "1",
}

def _nova_session_should_auto_title_20260624(title) -> bool:
    clean = str(title or "").strip()
    return clean.lower() in NOVA_SESSION_BAD_AUTO_TITLES_20260624

def _nova_session_title_from_message_20260624(message) -> str:
    if not isinstance(message, dict):
        return ""

    role = str(message.get("role") or message.get("sender") or "").strip().lower()
    if role and role not in {"user", "human"}:
        return ""

    text = (
        str(message.get("text") or "").strip()
        or str(message.get("content") or "").strip()
        or str(message.get("message") or "").strip()
        or str(message.get("user_text") or "").strip()
    )

    text = " ".join(text.split())
    if not text:
        return ""

    low = text.lower()
    if low in NOVA_SESSION_BAD_AUTO_TITLES_20260624:
        return ""
    if low.startswith("[nova"):
        return ""
    if low.startswith("http://") or low.startswith("https://"):
        return ""

    return text[:60].rstrip(" .,-_:;") or ""


class SessionService:
    MAX_SESSION_MESSAGES = 80
    MAX_TEXT_LEN = 20000
    MAX_META_STRING_LEN = 500
    ALLOWED_META_KEYS = {
    "route",
    "mode",
    "has_attachments",
    "artifact_ids",
    "artifact_id",
    "execution_id",
    "error",
    "status",
    "source",
    "model",

    # web/research persistence
    "sources",
    "source_urls",
    "query",
    "fresh",
}

    def _safe_str(self, value) -> str:
        if value is None:
            return ""
        try:
            return str(value)
        except Exception:
            return ""

    def _truncate_text(self, value: str, limit: int) -> str:
        text = self._safe_str(value)
        if len(text) <= limit:
            return text
        return text[:limit] + " â€¦[truncated]"

    def _sanitize_meta_for_storage(self, meta) -> dict:
        if not isinstance(meta, dict):
            return {}

        cleaned = {}

        for key in self.ALLOWED_META_KEYS:
            if key not in meta:
                continue

            value = meta.get(key)

            if key in {"artifact_ids"}:
                if isinstance(value, list):
                    cleaned[key] = [
                        self._truncate_text(item, 128)
                        for item in value
                        if self._safe_str(item).strip()
                    ][:20]
                continue

            if key in {"has_attachments"}:
                cleaned[key] = bool(value)
                continue

            if value is None:
                continue

            if key in {"sources"}:
                if isinstance(value, list):
                    cleaned[key] = value[:10]
                continue

            if key in {"source_urls"}:
                if isinstance(value, list):
                    cleaned[key] = [
                        self._truncate_text(v, 500)
                        for v in value
                        if self._safe_str(v).strip()
                    ][:20]
                continue

            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = (
                    self._truncate_text(value, self.MAX_META_STRING_LEN)
                    if isinstance(value, str)
                    else value
                )

        return cleaned

    def _sanitize_attachments_for_storage(self, attachments) -> list[dict]:
        if not isinstance(attachments, list):
            return []

        cleaned = []
        for item in attachments[:10]:
            if not isinstance(item, dict):
                continue

            cleaned_item = {
                "id": self._truncate_text(item.get("id", ""), 128),
                "filename": self._truncate_text(item.get("filename", ""), 256),
                "stored_name": self._truncate_text(item.get("stored_name", ""), 256),
                "url": self._truncate_text(item.get("url", ""), 512),
                "mime_type": self._truncate_text(item.get("mime_type", ""), 128),
                "size": item.get("size", 0) if isinstance(item.get("size"), (int, float)) else 0,
            }

            cleaned.append(cleaned_item)

        return cleaned

    def sanitize_message_for_storage(self, message: dict) -> dict:
        if not isinstance(message, dict):
            return {
                "role": "assistant",
                "text": "",
                "attachments": [],
                "meta": {},
            }

        role = self._safe_str(message.get("role")).strip().lower() or "assistant"
        if role not in {"user", "assistant", "system", "tool"}:
            role = "assistant"

        text = self._safe_str(
            message.get("text")
            or message.get("content")
            or message.get("body")
            or ""
        ).strip()

        message_id = self._safe_str(
            message.get("id")
        ).strip()

        if not message_id:
            message_id = f"msg_{uuid.uuid4().hex}"

        sanitized = {
            "id": self._truncate_text(message_id, 128),
            "role": role,
            "text": self._truncate_text(text, self.MAX_TEXT_LEN),
            "created_at": self._safe_str(message.get("created_at")).strip(),
            "updated_at": self._safe_str(message.get("updated_at")).strip(),
            "attachments": self._sanitize_attachments_for_storage(message.get("attachments")),
            "meta": self._sanitize_meta_for_storage(message.get("meta")),
        }

        # never persist bulky / duplicate / debug-heavy fields
        # drop anything like:
        # - debug
        # - execution
        # - working_state
        # - raw tool payloads
        # - artifacts embedded in message
        # by simply not copying them over

        return sanitized

    def trim_session_messages(self, messages: list[dict], max_messages: int | None = None) -> list[dict]:
        if not isinstance(messages, list):
            return []

        limit = max_messages or self.MAX_SESSION_MESSAGES
        sanitized = [self.sanitize_message_for_storage(m) for m in messages if isinstance(m, dict)]

        if len(sanitized) <= limit:
            return sanitized

        return sanitized[-limit:]

    def _sanitize_active_execution_for_storage(self, active_execution):
        if not isinstance(active_execution, dict):
            return None

        return {
            "id": self._truncate_text(active_execution.get("id", ""), 128),
            "goal": self._truncate_text(active_execution.get("goal", ""), 1000),
            "status": self._truncate_text(active_execution.get("status", ""), 64),
            "current_step_index": active_execution.get("current_step_index", 0)
            if isinstance(active_execution.get("current_step_index"), int)
            else 0,
            "updated_at": self._safe_str(active_execution.get("updated_at")).strip(),
            "steps": [
                {
                    "title": self._truncate_text(step.get("title", ""), 500),
                    "status": self._truncate_text(step.get("status", ""), 64),
                }
                for step in (active_execution.get("steps") or [])[:20]
                if isinstance(step, dict)
            ],
        }

    def sanitize_session_for_storage(self, session: dict) -> dict:
        if not isinstance(session, dict):
            return {}

        cleaned = dict(session)

        cleaned["id"] = self._truncate_text(session.get("id", ""), 128)
        cleaned["title"] = self._truncate_text(session.get("title", ""), 300)
        cleaned["created_at"] = self._safe_str(session.get("created_at")).strip()
        cleaned["updated_at"] = self._safe_str(session.get("updated_at")).strip()
        cleaned["pinned"] = bool(session.get("pinned", False))

        cleaned["messages"] = self.trim_session_messages(session.get("messages", []))

        # keep only one lean execution source of truth here
        cleaned["active_execution"] = self._sanitize_active_execution_for_storage(
            session.get("active_execution")
        )

        # keep working state tiny if present
        working_state = session.get("working_state")
        if isinstance(working_state, dict):
            cleaned["working_state"] = {
                "active_task": self._truncate_text(working_state.get("active_task", ""), 300),
                "current_file": self._truncate_text(working_state.get("current_file", ""), 500),
                "current_bug": self._truncate_text(working_state.get("current_bug", ""), 500),
                "last_success": self._truncate_text(working_state.get("last_success", ""), 500),
                "next_move": self._truncate_text(working_state.get("next_move", ""), 500),
                "checkpoint": self._truncate_text(working_state.get("checkpoint", ""), 300),
                "updated_at": self._safe_str(working_state.get("updated_at")).strip(),
            }
        else:
            cleaned["working_state"] = {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": "",
                "next_move": "",
                "checkpoint": "",
                "updated_at": "",
            }

        # explicitly kill known bloat keys if they leaked onto the session object
        cleaned.pop("debug", None)
        cleaned.pop("debug_log", None)
        cleaned.pop("tool_trace", None)
        cleaned.pop("raw_response", None)
        cleaned.pop("artifacts_full", None)

        return cleaned


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

    def _save_sessions(self, sessions, active):
        MAX_SESSIONS = 25

        safe_sessions = []

        for s in sessions[-MAX_SESSIONS:]:
            if not isinstance(s, dict):
                continue

            # ðŸ”¥ THIS IS THE CRITICAL LINE
            cleaned = self.sanitize_session_for_storage(s)

            # optional preview cap
            if cleaned.get("last_message_preview"):
                cleaned["last_message_preview"] = str(cleaned["last_message_preview"])[:200]

            safe_sessions.append(cleaned)

        payload = {
            "sessions": safe_sessions,
            "active_session_id": active,
        }

        self._write_store(payload)

    def _find(self, sessions, session_id):
        target = str(session_id or "").strip()
        for i, s in enumerate(sessions):
            if str(s.get("id") or "").strip() == target:
                return i
        return -1

    # SESSION_SERVICE_LOAD_SAVE_COMPAT_LOCK

    def _belongs_to_user(self, session, user_id=""):
        if not user_id:
            return False

        session_user_id = str(
            session.get("user_id") or ""
        ).strip()

        current_user_id = str(
            user_id or ""
        ).strip()

        if session_user_id == current_user_id:
            return True

        return False

    def load(self):
        """
        Compatibility bridge for older ChatService code that expects
        SessionService.load() to return the session list.
        """
        return self._load_sessions()

    def save(self, sessions, active=None):
        """
        Compatibility bridge for older ChatService code that expects
        SessionService.save(sessions). Current storage also tracks
        active_session_id, so preserve the current active id when one
        is not explicitly provided.
        """
        if active is None:
            active = self.get_active_session_id()
        return self._save_sessions(sessions, active)

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

    def rename(self, session_id: str, title: str, user_id=""):
        data = self._read_store()
        sessions = data.get("sessions", [])

        clean_title = str(title or "").strip() or "New Chat"

        for session in sessions:
            if str(session.get("id") or "") != str(session_id or ""):
                continue

            if user_id and not self._belongs_to_user(session, user_id):
                return None

            session["title"] = clean_title
            session["updated_at"] = iso_now()

            self._write_store(data)
            return session

        return None


    def pin(self, session_id: str, pinned: bool, user_id=""):
        data = self._read_store()
        sessions = data.get("sessions", [])

        for session in sessions:
            if str(session.get("id") or "") != str(session_id or ""):
                continue

            if user_id and not self._belongs_to_user(session, user_id):
                return None

            session["pinned"] = bool(pinned)
            session["updated_at"] = iso_now()

            self._write_store(data)
            return session

        return None
    def delete(self, session_id: str, user_id=""):
        data = self._read_store()
        sessions = data.get("sessions", [])

        remaining = []
        deleted = False

        for session in sessions:
            if str(session.get("id") or "") != str(session_id or ""):
                remaining.append(session)
                continue

            if user_id and not self._belongs_to_user(session, user_id):
                remaining.append(session)
                continue

            deleted = True

        if not deleted:
            return False

        data["sessions"] = remaining

        active_id = str(
            data.get("active_session_id") or ""
        ).strip()

        if active_id == str(session_id or "").strip():
            data["active_session_id"] = (
                remaining[0].get("id")
                if remaining
                else ""
            )

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

    def get_session(self, session_id, user_id=""):
        sessions = self._load_sessions()

        i = self._find(sessions, session_id)

        if i < 0:
            return None

        session = sessions[i]

        if not self._belongs_to_user(session, user_id):
            return None

        if (
            user_id
            and not str(session.get("user_id") or "").strip()
        ):
            session["user_id"] = str(user_id).strip()
            self._save_sessions(
                sessions,
                self.get_active_session_id(),
            )

        return session

    def get_active_session(self):
        active_id = self.get_active_session_id()
        if not active_id:
            return None
        return self.get_session(active_id)

    def get_active(self):
        return self.get_active_session()

    def get_active_session(self):
        active_id = self.get_active_session_id()
        if not active_id:
            return None
        return self.get_session(active_id)

    def get_active(self):
        return self.get_active_session()

    def create_session(
        self,
        title="New Chat",
        user_id="",
    ):
        sessions = self._load_sessions()
        s = new_session(
            title,
            user_id=user_id,
        )
        sessions.insert(0, s)
        self._save_sessions(sessions, s["id"])
        return s

    def get_active_session(self):
        active_id = self.get_active_session_id()
        if not active_id:
            return None
        return self.get_session(active_id)

    def get_active(self):
        return self.get_active_session()

    def create_session(
        self,
        title="New Chat",
        user_id="",
    ):
        sessions = self._load_sessions()
        s = new_session(
            title,
            user_id=user_id,
        )
        sessions.insert(0, s)
        self._save_sessions(sessions, s["id"])
        return s

    def append_message(self, session_id, message):
        sessions = self._load_sessions()

        i = self._find(sessions, session_id)

        if i < 0:
            return None

        normalized = _normalize_message(message)

        sessions[i]["messages"].append(normalized)

        sessions[i]["updated_at"] = iso_now()


        # NOVA_SESSION_BAD_TITLE_AUTOFIX_20260624
        try:
            if _nova_session_should_auto_title_20260624(session.get("title")):
                candidate = _nova_session_title_from_message_20260624(message)
                if candidate:
                    session["title"] = candidate
        except Exception:
            pass

        self._save_sessions(
            sessions,
            self.get_active_session_id(),
        )

        return normalized
    # -----------------------
    # COMPATIBILITY
    # -----------------------

    def get_all(self, user_id=""):
        return [
            s for s in self._load_sessions()
            if self._belongs_to_user(s, user_id)
        ]

    def list_sessions(self, user_id=""):
        return [
            s for s in self._load_sessions()
            if self._belongs_to_user(s, user_id)
        ]

    def list(self, user_id=""):
        return [
            s for s in self._load_sessions()
            if self._belongs_to_user(s, user_id)
        ]

    def all(self, user_id=""):
        return [
            s for s in self._load_sessions()
            if self._belongs_to_user(s, user_id)
        ]

    def create(self, title="New Chat", user_id=""):
        return self.create_session(
            title,
            user_id=user_id,
        )

    def get(self, session_id):
        return self.get_session(session_id)

    def get_by_id(self, session_id):
        return self.get_session(session_id)



