from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


class ChatService:
    def __init__(self, sessions_file: str | Path, artifacts_file: str | Path, memory_file: str | Path):
        self.sessions_file = Path(sessions_file)
        self.artifacts_file = Path(artifacts_file)
        self.memory_file = Path(memory_file)

        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_trace(label: str, exc: Exception) -> str:
        tb = traceback.format_exc()
        print("\n" + "=" * 100)
        print(f"[{datetime.now(timezone.utc).isoformat()}] CHAT SERVICE ERROR: {label}")
        print(f"{type(exc).__name__}: {exc}")
        print(tb)
        print("=" * 100 + "\n")
        return tb

    def _load_sessions(self) -> list[dict[str, Any]]:
        data = read_json_file(self.sessions_file, [])
        return data if isinstance(data, list) else []

    def _save_sessions(self, sessions: list[dict[str, Any]]) -> None:
        write_json_file(self.sessions_file, sessions)

    def _load_artifacts(self) -> list[dict[str, Any]]:
        data = read_json_file(self.artifacts_file, [])
        return data if isinstance(data, list) else []

    def _save_artifacts(self, artifacts: list[dict[str, Any]]) -> None:
        write_json_file(self.artifacts_file, artifacts)

    def _load_memory_items(self) -> list[dict[str, Any]]:
        data = read_json_file(self.memory_file, [])
        return data if isinstance(data, list) else []

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = self._load_sessions()
        ordered = sorted(
            sessions,
            key=lambda s: (
                0 if bool(s.get("pinned")) else 1,
                s.get("updated_at") or "",
            ),
            reverse=False,
        )
        ordered.reverse()
        return [self._session_summary(session) for session in ordered]

    def create_session(self, title: str = "New Session") -> dict[str, Any]:
        sessions = self._load_sessions()
        now = self.utc_now()
        session = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "New Session",
            "created_at": now,
            "updated_at": now,
            "pinned": False,
            "messages": [],
        }
        sessions.append(session)
        self._save_sessions(sessions)
        return session

    def get_session(self, session_id: str) -> dict[str, Any]:
        sessions = self._load_sessions()
        for session in sessions:
            if session.get("id") == session_id:
                session.setdefault("messages", [])
                session.setdefault("title", "Untitled")
                session.setdefault("pinned", False)
                session.setdefault("created_at", self.utc_now())
                session.setdefault("updated_at", self.utc_now())
                return session

        created = self.create_session(title="New Session")
        if session_id and created["id"] != session_id:
            sessions = self._load_sessions()
            for session in sessions:
                if session["id"] == created["id"]:
                    session["id"] = session_id
                    self._save_sessions(sessions)
                    return session
        return created

    def update_session(
        self,
        session_id: str,
        title: str | None = None,
        pinned: bool | None = None,
    ) -> dict[str, Any]:
        sessions = self._load_sessions()
        for session in sessions:
            if session.get("id") == session_id:
                if title is not None:
                    new_title = str(title).strip()
                    if new_title:
                        session["title"] = new_title
                if pinned is not None:
                    session["pinned"] = bool(pinned)
                session["updated_at"] = self.utc_now()
                self._save_sessions(sessions)
                return session
        raise ValueError(f"Session not found: {session_id}")

    def delete_session(self, session_id: str) -> bool:
        sessions = self._load_sessions()
        new_sessions = [s for s in sessions if s.get("id") != session_id]
        deleted = len(new_sessions) != len(sessions)
        if deleted:
            self._save_sessions(new_sessions)
        return deleted

    def _session_summary(self, session: dict[str, Any]) -> dict[str, Any]:
        messages = session.get("messages", [])
        last_preview = ""
        if messages:
            last_preview = str(messages[-1].get("content") or "").strip().replace("\n", " ")[:120]

        return {
            "id": session.get("id"),
            "title": session.get("title") or "Untitled",
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "pinned": bool(session.get("pinned")),
            "message_count": len(messages),
            "last_message_preview": last_preview,
        }

    def _append_message(
        self,
        session: dict[str, Any],
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "created_at": self.utc_now(),
            "attachments": attachments or [],
            "meta": meta or {},
        }
        session.setdefault("messages", []).append(message)
        session["updated_at"] = self.utc_now()
        return message

    def _upsert_session(self, session: dict[str, Any]) -> dict[str, Any]:
        sessions = self._load_sessions()
        found = False
        for idx, existing in enumerate(sessions):
            if existing.get("id") == session.get("id"):
                sessions[idx] = session
                found = True
                break
        if not found:
            sessions.append(session)
        self._save_sessions(sessions)
        return session

    def _save_assistant_artifact(
        self,
        session_id: str,
        assistant_message: dict[str, Any],
        debug_meta: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            content = str(assistant_message.get("content") or "").strip()
            if not content:
                return None

            artifacts = self._load_artifacts()
            artifact = {
                "id": str(uuid.uuid4()),
                "title": f"Chat Reply - {content[:60]}".strip(),
                "kind": "chat_reply",
                "created_at": self.utc_now(),
                "updated_at": self.utc_now(),
                "session_id": session_id,
                "content": content,
                "message_id": assistant_message.get("id"),
                "meta": {
                    "role": "assistant",
                    "artifact_source": "chat_service",
                    "debug": debug_meta,
                },
            }
            artifacts.insert(0, artifact)
            self._save_artifacts(artifacts)
            return artifact
        except Exception:
            return None

    def _select_memory_titles(self, limit: int = 5) -> list[str]:
        items = self._load_memory_items()
        titles: list[str] = []
        for item in items[:limit]:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("content") or "").strip()
                if title:
                    titles.append(title[:120])
            else:
                raw = str(item).strip()
                if raw:
                    titles.append(raw[:120])
        return titles

    def _recent_artifact_titles(self, limit: int = 3) -> list[str]:
        artifacts = self._load_artifacts()
        titles: list[str] = []
        for artifact in artifacts[:limit]:
            title = str(artifact.get("title") or "").strip()
            if title:
                titles.append(title[:120])
        return titles

    def _local_fallback_text(
        self,
        content: str,
        memory_titles: list[str],
        artifact_titles: list[str],
        fallback_reason: str,
    ) -> str:
        clean = (content or "").strip()
        if not clean:
            clean = "Say something to get started."

        lines = [
            f"You said: {clean}",
            "",
            f"Fallback reason: {fallback_reason}",
        ]

        if memory_titles:
            lines.extend(
                [
                    "",
                    "Saved memory matched:",
                    *[f"- {title}" for title in memory_titles],
                ]
            )

        if artifact_titles:
            lines.extend(
                [
                    "",
                    "Recent artifacts:",
                    *[f"- {title}" for title in artifact_titles],
                ]
            )

        return "\n".join(lines).strip()

    def _build_openai_reply(self, content: str, session: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError(f"OpenAI import failed: {exc}") from exc

        history = session.get("messages", [])[-12:]
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": "You are Nova, a direct helpful AI assistant inside a local app.",
            }
        ]

        for msg in history:
            role = str(msg.get("role") or "").strip()
            text = str(msg.get("content") or "").strip()
            if role in {"user", "assistant"} and text:
                messages.append({"role": role, "content": text})

        messages.append({"role": "user", "content": content})

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=500,
        )

        text = ""
        if response.choices:
            text = response.choices[0].message.content or ""

        text = str(text).strip()
        if not text:
            raise RuntimeError("Model returned empty content.")

        return text, {
            "model": model,
            "history_count": len(history),
            "history_included": len(history) > 0,
        }

    def build_route_fallback_result(
        self,
        content: str,
        session_id: str,
        reason: str,
        error: str,
    ) -> dict[str, Any]:
        try:
            session = self.get_session(session_id or str(uuid.uuid4()))
            if not session.get("messages"):
                session["title"] = (content.strip()[:40] or "New Session")

            user_message = self._append_message(
                session=session,
                role="user",
                content=content.strip() or "(empty message)",
                attachments=[],
                meta={"source": "route_fallback"},
            )

            memory_titles = self._select_memory_titles(limit=5)
            artifact_titles = self._recent_artifact_titles(limit=3)

            assistant_text = self._local_fallback_text(
                content=content,
                memory_titles=memory_titles,
                artifact_titles=artifact_titles,
                fallback_reason=reason,
            )

            assistant_message = self._append_message(
                session=session,
                role="assistant",
                content=assistant_text,
                attachments=[],
                meta={
                    "fallback": True,
                    "fallback_reason": reason,
                    "source": "route_fallback",
                },
            )

            self._upsert_session(session)
            artifact = self._save_assistant_artifact(
                session_id=session["id"],
                assistant_message=assistant_message,
                debug_meta={"fallback_reason": reason, "route_error": error},
            )

            return {
                "ok": True,
                "assistant_message": assistant_message,
                "session": session,
                "debug": {
                    "fallback": True,
                    "fallback_reason": reason,
                    "error": error,
                    "route_safe": True,
                    "artifact_saved": bool(artifact),
                    "message_count": len(session.get("messages", [])),
                    "session_id": session.get("id"),
                    "user_message_id": user_message.get("id"),
                    "assistant_message_id": assistant_message.get("id"),
                },
            }
        except Exception as exc:
            self._safe_trace("build_route_fallback_result", exc)

            now = self.utc_now()
            assistant_message = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": f"You said: {content.strip() or '(empty message)'}\n\nFallback reason: emergency_final_fallback",
                "created_at": now,
                "attachments": [],
                "meta": {
                    "fallback": True,
                    "fallback_reason": "emergency_final_fallback",
                },
            }

            return {
                "ok": True,
                "assistant_message": assistant_message,
                "session": {
                    "id": session_id or str(uuid.uuid4()),
                    "title": "Recovered Session",
                    "created_at": now,
                    "updated_at": now,
                    "pinned": False,
                    "messages": [assistant_message],
                },
                "debug": {
                    "fallback": True,
                    "fallback_reason": "emergency_final_fallback",
                    "original_reason": reason,
                    "original_error": error,
                    "secondary_error_type": type(exc).__name__,
                    "secondary_error": str(exc),
                },
            }

    def send_message(
        self,
        content: str,
        session_id: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        content = str(content or "").strip()
        attachments = attachments or []
        session_id = str(session_id or "").strip()

        try:
            session = self.get_session(session_id or str(uuid.uuid4()))

            if not session.get("messages"):
                session["title"] = content[:40] or "New Session"

            user_message = self._append_message(
                session=session,
                role="user",
                content=content or "(empty message)",
                attachments=attachments,
                meta={"source": "user"},
            )

            reply_debug: dict[str, Any] = {}
            fallback_reason = ""
            assistant_text = ""

            try:
                assistant_text, model_debug = self._build_openai_reply(content, session)
                reply_debug.update(model_debug)
                reply_debug["fallback"] = False
                reply_debug["fallback_reason"] = ""
            except Exception as model_exc:
                tb = self._safe_trace("model_reply", model_exc)
                fallback_reason = "local_contract_stable_reply"

                memory_titles = self._select_memory_titles(limit=5)
                artifact_titles = self._recent_artifact_titles(limit=3)
                assistant_text = self._local_fallback_text(
                    content=content,
                    memory_titles=memory_titles,
                    artifact_titles=artifact_titles,
                    fallback_reason=fallback_reason,
                )
                reply_debug.update(
                    {
                        "fallback": True,
                        "fallback_reason": fallback_reason,
                        "model_error_type": type(model_exc).__name__,
                        "model_error": str(model_exc),
                        "traceback": tb[-4000:],
                        "memory_used": bool(memory_titles),
                        "memory_titles": memory_titles,
                        "memory_selected_count": len(memory_titles),
                        "artifact_titles": artifact_titles,
                    }
                )

            assistant_message = self._append_message(
                session=session,
                role="assistant",
                content=assistant_text,
                attachments=[],
                meta={
                    "source": "assistant",
                    "fallback": bool(reply_debug.get("fallback")),
                    "fallback_reason": reply_debug.get("fallback_reason", ""),
                },
            )

            self._upsert_session(session)
            artifact = self._save_assistant_artifact(
                session_id=session["id"],
                assistant_message=assistant_message,
                debug_meta=reply_debug,
            )

            reply_debug.update(
                {
                    "route_safe": True,
                    "artifact_saved": bool(artifact),
                    "artifact_save_reason": "saved" if artifact else "skipped",
                    "session_id": session["id"],
                    "message_count": len(session.get("messages", [])),
                    "user_message_id": user_message["id"],
                    "assistant_message_id": assistant_message["id"],
                }
            )

            return {
                "ok": True,
                "assistant_message": assistant_message,
                "session": session,
                "debug": reply_debug,
            }

        except Exception as exc:
            tb = self._safe_trace("send_message", exc)
            return self.build_route_fallback_result(
                content=content,
                session_id=session_id or str(uuid.uuid4()),
                reason="send_message_exception",
                error=f"{type(exc).__name__}: {exc}\n{tb[-4000:]}",
            )