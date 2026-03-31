from __future__ import annotations

import json
import mimetypes
import os
import re
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_SESSION_MESSAGES = 300
MAX_MEMORY_ITEMS = 5
MAX_ARTIFACT_MATCHES = 4
MAX_ATTACHMENT_PREVIEW = 8
MAX_PROMPT_CHARS = 12000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_trace(label: str, exc: Exception) -> str:
    tb = traceback.format_exc()
    print("\n" + "=" * 100)
    print(f"[{utc_now()}] CHAT SERVICE ERROR: {label}")
    print(f"{type(exc).__name__}: {exc}")
    print(tb)
    print("=" * 100 + "\n")
    return tb


def read_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clamp_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalize_whitespace(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def lower_tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]{3,}", str(value or "").lower()))


def guess_kind(filename: str = "", mime_type: str = "") -> str:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()

    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")):
        return "image"
    if mime.startswith("video/") or name.endswith((".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv")):
        return "video"
    if mime.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")):
        return "audio"
    return "file"


def build_upload_url(stored_name: str = "", filename: str = "") -> str:
    target = (stored_name or filename or "").strip()
    if not target:
        return ""
    return f"/api/uploads/{target}"


class ChatService:
    def __init__(self, sessions_file: str | Path, artifacts_file: str | Path, memory_file: str | Path) -> None:
        self.sessions_file = Path(sessions_file)
        self.artifacts_file = Path(artifacts_file)
        self.memory_file = Path(memory_file)

        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4")
        self._client = None

        if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            try:
                self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception:
                self._client = None

    # -------------------------------------------------------------------------
    # storage
    # -------------------------------------------------------------------------

    def _read_sessions(self) -> list[dict[str, Any]]:
        data = read_json_file(self.sessions_file, [])
        return data if isinstance(data, list) else []

    def _write_sessions(self, sessions: list[dict[str, Any]]) -> None:
        write_json_file(self.sessions_file, sessions)

    def _read_artifacts(self) -> list[dict[str, Any]]:
        data = read_json_file(self.artifacts_file, [])
        return data if isinstance(data, list) else []

    def _write_artifacts(self, artifacts: list[dict[str, Any]]) -> None:
        write_json_file(self.artifacts_file, artifacts)

    def _read_memory(self) -> list[dict[str, Any]]:
        data = read_json_file(self.memory_file, [])
        return data if isinstance(data, list) else []

    # -------------------------------------------------------------------------
    # sessions
    # -------------------------------------------------------------------------

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = self._read_sessions()
        sessions.sort(key=lambda s: (s.get("pinned", False), s.get("updated_at", "")), reverse=True)
        return [self._session_summary(s) for s in sessions]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for session in self._read_sessions():
            if session.get("id") == session_id:
                return session
        return None

    def create_session(self, title: str | None = None) -> dict[str, Any]:
        now = utc_now()
        new_session = {
            "id": str(uuid.uuid4()),
            "title": (title or "New Chat").strip() or "New Chat",
            "created_at": now,
            "updated_at": now,
            "pinned": False,
            "messages": [],
            "message_count": 0,
            "last_message_preview": "",
        }
        sessions = self._read_sessions()
        sessions.insert(0, new_session)
        self._write_sessions(sessions)
        return new_session

    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any] | None:
        sessions = self._read_sessions()
        updated = None
        for session in sessions:
            if session.get("id") != session_id:
                continue
            if "title" in changes:
                session["title"] = str(changes["title"] or "New Chat").strip() or "New Chat"
            if "pinned" in changes:
                session["pinned"] = bool(changes["pinned"])
            session["updated_at"] = utc_now()
            session["last_message_preview"] = clamp_text(
                session.get("last_message_preview") or session.get("title") or "",
                140,
            )
            updated = session
            break

        if updated is not None:
            self._write_sessions(sessions)
        return updated

    def delete_session(self, session_id: str) -> bool:
        sessions = self._read_sessions()
        new_sessions = [s for s in sessions if s.get("id") != session_id]
        if len(new_sessions) == len(sessions):
            return False
        self._write_sessions(new_sessions)
        return True

    def _session_summary(self, session: dict[str, Any]) -> dict[str, Any]:
        messages = session.get("messages") or []
        return {
            "id": session.get("id"),
            "title": session.get("title") or "New Chat",
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "pinned": bool(session.get("pinned", False)),
            "message_count": int(session.get("message_count", len(messages))),
            "last_message_preview": session.get("last_message_preview") or "",
        }

    def _ensure_session(self, session_id: str | None) -> dict[str, Any]:
        if session_id:
            found = self.get_session(session_id)
            if found:
                return found
        return self.create_session()

    # -------------------------------------------------------------------------
    # attachments normalization
    # -------------------------------------------------------------------------

    def _normalize_attachment(self, raw: Any, source: str = "unknown") -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        filename = (
            raw.get("filename")
            or raw.get("name")
            or raw.get("original_name")
            or raw.get("title")
            or ""
        )
        stored_name = raw.get("stored_name") or raw.get("stored_filename") or raw.get("path") or ""
        mime_type = raw.get("mime_type") or raw.get("content_type") or raw.get("mime") or ""
        url = raw.get("url") or raw.get("src") or raw.get("href") or ""

        if not mime_type and filename:
            guessed, _ = mimetypes.guess_type(filename)
            mime_type = guessed or ""

        kind = raw.get("type") or raw.get("kind") or guess_kind(filename, mime_type)
        if kind not in {"image", "video", "audio", "file"}:
            kind = guess_kind(filename, mime_type)

        if not url and stored_name and not str(stored_name).startswith(("http://", "https://", "/api/")):
            url = build_upload_url(str(stored_name), str(filename))
        elif stored_name and str(stored_name).startswith("/api/"):
            url = str(stored_name)
        elif stored_name and str(stored_name).startswith(("http://", "https://")):
            url = str(stored_name)
        elif not url and filename and str(filename).startswith("/api/"):
            url = str(filename)

        normalized = {
            "id": raw.get("id") or str(uuid.uuid4()),
            "type": kind,
            "filename": filename or "",
            "stored_name": str(stored_name or ""),
            "mime_type": str(mime_type or ""),
            "url": str(url or ""),
            "size": raw.get("size"),
            "source": source or raw.get("source") or "unknown",
            "title": raw.get("title") or filename or kind.title(),
            "alt": raw.get("alt") or raw.get("caption") or filename or kind.title(),
        }

        if not normalized["url"] and not normalized["filename"]:
            return None

        return normalized

    def _normalize_attachments(self, attachments: Any, source: str = "unknown") -> list[dict[str, Any]]:
        if not attachments:
            return []
        if isinstance(attachments, dict):
            attachments = [attachments]
        if not isinstance(attachments, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in attachments:
            entry = self._normalize_attachment(item, source=source)
            if entry:
                normalized.append(entry)

        return normalized[:MAX_ATTACHMENT_PREVIEW]

    def _collect_media_from_meta(self, meta: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(meta, dict):
            return []

        collected: list[dict[str, Any]] = []

        for key in ("attachments", "media", "images", "videos", "audio"):
            value = meta.get(key)
            if not value:
                continue

            inferred_source = "assistant"
            if key == "images":
                inferred_source = "assistant-image"
            elif key == "videos":
                inferred_source = "assistant-video"
            elif key == "audio":
                inferred_source = "assistant-audio"

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        collected.append(
                            {
                                "type": "file",
                                "url": item,
                                "title": item,
                                "source": inferred_source,
                            }
                        )
                    elif isinstance(item, dict):
                        merged = dict(item)
                        merged.setdefault("source", inferred_source)
                        collected.append(merged)
            elif isinstance(value, dict):
                merged = dict(value)
                merged.setdefault("source", inferred_source)
                collected.append(merged)

        web = meta.get("web") or {}
        if isinstance(web, dict):
            for item in web.get("media", []) or []:
                if isinstance(item, dict):
                    merged = dict(item)
                    merged.setdefault("source", "web")
                    collected.append(merged)

        return self._normalize_attachments(collected, source="meta")

    # -------------------------------------------------------------------------
    # memory + artifacts context
    # -------------------------------------------------------------------------

    def _select_memory_items(self, user_text: str) -> list[dict[str, Any]]:
        memory = self._read_memory()
        if not memory:
            return []

        user_terms = lower_tokens(user_text)

        scored: list[tuple[int, dict[str, Any]]] = []
        for item in memory:
            title = str(item.get("title") or "")
            content = str(item.get("content") or item.get("text") or "")
            haystack_terms = lower_tokens(title + " " + content)
            overlap = len(user_terms & haystack_terms)
            pinned_boost = 10 if item.get("pinned") else 0
            recent_boost = 2 if item.get("updated_at") else 0
            score = overlap + pinned_boost + recent_boost
            scored.append((score, item))

        scored.sort(key=lambda x: (x[0], str(x[1].get("updated_at") or "")), reverse=True)
        selected = [item for score, item in scored if score > 0][:MAX_MEMORY_ITEMS]

        if len(selected) < MAX_MEMORY_ITEMS:
            pinned = [item for item in memory if item.get("pinned")]
            for item in pinned:
                if item not in selected:
                    selected.append(item)
                if len(selected) >= MAX_MEMORY_ITEMS:
                    break

        return selected[:MAX_MEMORY_ITEMS]

    def _select_relevant_artifacts(self, user_text: str, session_id: str) -> list[dict[str, Any]]:
        artifacts = self._read_artifacts()
        if not artifacts:
            return []

        user_terms = lower_tokens(user_text)
        scored: list[tuple[int, dict[str, Any]]] = []

        for item in artifacts:
            title = str(item.get("title") or "")
            content = str(item.get("content") or "")
            item_session_id = str(item.get("session_id") or "")
            haystack_terms = lower_tokens(title + " " + content)
            overlap = len(user_terms & haystack_terms)
            same_session = 5 if item_session_id and item_session_id == session_id else 0
            pinned = 5 if item.get("pinned") else 0
            score = overlap + same_session + pinned
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: (x[0], str(x[1].get("updated_at") or x[1].get("created_at") or "")), reverse=True)
        return [item for score, item in scored[:MAX_ARTIFACT_MATCHES]]

    def _build_context_block(
        self,
        user_text: str,
        session: dict[str, Any],
        user_attachments: list[dict[str, Any]],
    ) -> tuple[str, dict[str, Any]]:
        memory_items = self._select_memory_items(user_text)
        artifact_items = self._select_relevant_artifacts(user_text, str(session.get("id") or ""))

        recent_messages = session.get("messages") or []
        recent_messages = recent_messages[-12:]

        lines: list[str] = []
        lines.append("SYSTEM CONTEXT")
        lines.append("- You are Nova, direct, useful, and concise.")
        lines.append("- Reply in plain markdown.")
        lines.append("- Preserve any media attachments you intentionally return in the attachments list.")
        lines.append("")

        if recent_messages:
            lines.append("RECENT SESSION HISTORY")
            for msg in recent_messages:
                role = (msg.get("role") or "user").upper()
                content = clamp_text(msg.get("content") or "", 1200)
                if content:
                    lines.append(f"{role}: {content}")
            lines.append("")

        if user_attachments:
            lines.append("USER ATTACHMENTS")
            for att in user_attachments:
                lines.append(
                    f"- {att.get('type', 'file')}: {att.get('filename') or att.get('title') or att.get('url')}"
                )
            lines.append("")

        if memory_items:
            lines.append("MEMORY")
            for item in memory_items:
                title = item.get("title") or "Memory"
                content = clamp_text(item.get("content") or item.get("text") or "", 500)
                lines.append(f"- {title}: {content}")
            lines.append("")

        if artifact_items:
            lines.append("RELEVANT ARTIFACTS")
            for item in artifact_items:
                title = item.get("title") or "Artifact"
                content = clamp_text(item.get("content") or "", 500)
                lines.append(f"- {title}: {content}")
            lines.append("")

        lines.append("LATEST USER MESSAGE")
        lines.append(user_text.strip())

        context_text = "\n".join(lines)
        if len(context_text) > MAX_PROMPT_CHARS:
            context_text = context_text[:MAX_PROMPT_CHARS]

        debug = {
            "memory_used": bool(memory_items),
            "memory_selected_count": len(memory_items),
            "memory_titles": [m.get("title") or "Memory" for m in memory_items],
            "artifact_used": bool(artifact_items),
            "artifact_count": len(artifact_items),
            "artifact_titles": [a.get("title") or "Artifact" for a in artifact_items],
            "history_count": len(recent_messages),
        }
        return context_text, debug

    # -------------------------------------------------------------------------
    # model path
    # -------------------------------------------------------------------------

    def _real_model_reply(
        self,
        prompt: str,
    ) -> tuple[str, dict[str, Any], str]:
        if self._client is None:
            raise RuntimeError("OpenAI client unavailable")

        response = self._client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=900,
        )

        text = ""
        meta: dict[str, Any] = {}

        if hasattr(response, "output_text") and response.output_text:
            text = response.output_text.strip()
        else:
            try:
                text = str(response).strip()
            except Exception:
                text = ""

        if not text:
            raise RuntimeError("Model returned empty text")

        meta["provider"] = "openai"
        meta["model"] = self.model
        return text, meta, self.model

    def _fallback_reply(
        self,
        user_text: str,
        user_attachments: list[dict[str, Any]],
        context_debug: dict[str, Any],
    ) -> tuple[str, dict[str, Any], str]:
        attachment_note = ""
        if user_attachments:
            names = [
                a.get("filename") or a.get("title") or a.get("type") or "file"
                for a in user_attachments[:4]
            ]
            attachment_note = f"\n\nAttachments received: {', '.join(names)}."

        text = (
            "Hey — I’m here. The main model is unavailable right now, so this is Nova’s local fallback answer.\n\n"
            f"You said: {user_text.strip() or '(empty message)'}"
            f"{attachment_note}"
        )

        meta = {
            "provider": "local",
            "model": "local-fallback",
            "fallback_reason": "local_contract_stable_reply",
            "memory_used": context_debug.get("memory_used", False),
            "artifact_used": context_debug.get("artifact_used", False),
        }
        return text, meta, "local-fallback"

    # -------------------------------------------------------------------------
    # artifacts
    # -------------------------------------------------------------------------

    def _save_reply_artifact(
        self,
        session_id: str,
        reply_message: dict[str, Any],
        debug: dict[str, Any],
    ) -> dict[str, Any]:
        artifacts = self._read_artifacts()

        content = str(reply_message.get("content") or "").strip()
        title = clamp_text(content.splitlines()[0] if content else "Chat Reply", 80) or "Chat Reply"
        artifact = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "title": f"Chat Reply - {title}",
            "kind": "chat_reply",
            "content": content,
            "attachments": reply_message.get("attachments") or [],
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "pinned": False,
            "meta": {
                "role": reply_message.get("role"),
                "message_id": reply_message.get("id"),
                "model": debug.get("model"),
                "fallback_reason": debug.get("fallback_reason"),
                "attachments_count": len(reply_message.get("attachments") or []),
                "artifact_source": "chat_service_autosave",
            },
        }
        artifacts.insert(0, artifact)
        self._write_artifacts(artifacts)
        return artifact

    # -------------------------------------------------------------------------
    # messages
    # -------------------------------------------------------------------------

    def _build_message(
        self,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": str(content or ""),
            "attachments": attachments or [],
            "created_at": utc_now(),
            "meta": meta or {},
        }

    def _append_message(self, session: dict[str, Any], message: dict[str, Any]) -> None:
        session.setdefault("messages", [])
        session["messages"].append(message)
        session["messages"] = session["messages"][-MAX_SESSION_MESSAGES:]
        session["updated_at"] = utc_now()
        session["message_count"] = len(session["messages"])
        preview_basis = message.get("content") or session.get("title") or ""
        session["last_message_preview"] = clamp_text(preview_basis, 140)

        if not session.get("title") or session.get("title") == "New Chat":
            if message.get("role") == "user" and str(message.get("content") or "").strip():
                session["title"] = clamp_text(message["content"], 48)

    def _persist_session(self, session: dict[str, Any]) -> None:
        sessions = self._read_sessions()
        replaced = False
        for idx, existing in enumerate(sessions):
            if existing.get("id") == session.get("id"):
                sessions[idx] = session
                replaced = True
                break
        if not replaced:
            sessions.insert(0, session)
        self._write_sessions(sessions)

    def send_message(
        self,
        content: str,
        session_id: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        route_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user_text = str(content or "").strip()
        session = self._ensure_session(session_id)

        incoming_attachments = self._normalize_attachments(attachments or [], source="upload")

        user_message = self._build_message(
            role="user",
            content=user_text,
            attachments=incoming_attachments,
            meta={"route_meta": route_meta or {}},
        )
        self._append_message(session, user_message)

        prompt, context_debug = self._build_context_block(
            user_text=user_text,
            session=session,
            user_attachments=incoming_attachments,
        )

        assistant_text = ""
        assistant_meta: dict[str, Any] = {}
        model_used = "local-fallback"
        fallback_reason = None
        trace = ""

        try:
            assistant_text, assistant_meta, model_used = self._real_model_reply(prompt)
        except Exception as exc:
            trace = safe_trace("real_model_reply", exc)
            fallback_reason = "real_model_exception"
            assistant_text, assistant_meta, model_used = self._fallback_reply(
                user_text=user_text,
                user_attachments=incoming_attachments,
                context_debug=context_debug,
            )

        assistant_attachments = self._collect_media_from_meta(assistant_meta)
        assistant_message = self._build_message(
            role="assistant",
            content=assistant_text,
            attachments=assistant_attachments,
            meta=assistant_meta,
        )
        self._append_message(session, assistant_message)
        self._persist_session(session)

        artifact = self._save_reply_artifact(
            session_id=str(session.get("id") or ""),
            reply_message=assistant_message,
            debug={
                "model": model_used,
                "fallback_reason": fallback_reason or assistant_meta.get("fallback_reason"),
            },
        )

        debug = {
            "ok": True,
            "model": model_used,
            "fallback_reason": fallback_reason or assistant_meta.get("fallback_reason"),
            "attachments_count": len(assistant_attachments),
            "attachments_types": [a.get("type") for a in assistant_attachments],
            "incoming_attachments_count": len(incoming_attachments),
            "incoming_attachments_types": [a.get("type") for a in incoming_attachments],
            "artifact_saved": True,
            "artifact_save_reason": "saved",
            "artifact_id": artifact.get("id"),
            "trace": trace,
            **context_debug,
        }

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "session": session,
            "debug": debug,
        }