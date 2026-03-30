from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_load(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _safe_json_save(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _clip_text(value: str, limit: int) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[:limit]


class ChatService:
    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = _safe_json_load(SESSIONS_FILE, {})
        if not isinstance(self.sessions, dict):
            self.sessions = {}

    def _save(self) -> None:
        _safe_json_save(SESSIONS_FILE, self.sessions)

    def _ensure_session(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not isinstance(session, dict):
            session = {
                "id": session_id,
                "title": "New Chat",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "message_count": 0,
                "last_message_preview": "",
                "messages": [],
            }
            self.sessions[session_id] = session

        session.setdefault("id", session_id)
        session.setdefault("title", "New Chat")
        session.setdefault("created_at", _now_iso())
        session.setdefault("updated_at", _now_iso())
        session.setdefault("message_count", 0)
        session.setdefault("last_message_preview", "")
        session.setdefault("messages", [])

        if not isinstance(session["messages"], list):
            session["messages"] = []

        return session

    def get_sessions(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for session_id, session in self.sessions.items():
            if not isinstance(session, dict):
                continue
            rows.append({
                "id": session_id,
                "title": session.get("title", "New Chat"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "message_count": session.get("message_count", 0),
                "last_message_preview": session.get("last_message_preview", ""),
            })
        rows.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return rows

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self._ensure_session(session_id)

    def send_message(self, content: str, session_id: str) -> Dict[str, Any]:
        session = self._ensure_session(session_id)
        history = session["messages"]

        system_prompt = """
You are Nova, a sharp, practical, high-agency assistant.

Rules:
- Be direct, useful, and accurate.
- When the user provides page content, document content, pasted text, or extracted webpage text, treat that content as readable source material.
- Never claim you cannot browse, open links, access a page, or read the source if the source text is already included in the user's message.
- If the user asks about provided page text, answer from that text.
- If the text does not contain the answer, say that clearly.
- Do not make up source details that are not present.
- Keep answers clean and natural, not robotic.

Behavior:
- For normal chat, respond normally.
- For webpage/document questions, summarize or answer based on the provided content.
- Prefer concrete answers over generic disclaimers.
""".strip()

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        recent_history = history[-12:]
        for msg in recent_history:
            role = msg.get("role")
            text = msg.get("content")
            if role in {"user", "assistant"} and isinstance(text, str) and text.strip():
                messages.append({"role": role, "content": text})

        messages.append({"role": "user", "content": content})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_completion_tokens=900,
        )

        reply = (response.choices[0].message.content or "").strip()
        if not reply:
            reply = "I do not have a response."

        history.append({
            "role": "user",
            "content": content,
            "created_at": _now_iso(),
        })
        history.append({
            "role": "assistant",
            "content": reply,
            "created_at": _now_iso(),
        })

        if session["title"] == "New Chat":
            session["title"] = _clip_text(content.strip() or "New Chat", 60)

        session["updated_at"] = _now_iso()
        session["message_count"] = len(history)
        session["last_message_preview"] = _clip_text(reply, 140)

        self._save()

        return {
            "message": reply,
            "session": {
                "id": session["id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "message_count": session["message_count"],
                "last_message_preview": session["last_message_preview"],
            }
        }