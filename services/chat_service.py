from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from services.artifact_service import ArtifactService


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatService:
    def __init__(
        self,
        data_dir: Optional[str] = None,
        artifact_service: Optional[ArtifactService] = None,
    ) -> None:
        base_dir = Path(data_dir or Path(__file__).resolve().parents[1] / "data")
        base_dir.mkdir(parents=True, exist_ok=True)

        self.data_dir = base_dir
        self.sessions_path = self.data_dir / "nova_sessions.json"
        self.artifact_service = artifact_service or ArtifactService(str(base_dir))
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

        self._ensure_sessions_file()

    def _ensure_sessions_file(self) -> None:
        if not self.sessions_path.exists():
            self._write_sessions({})

    def _read_sessions(self) -> Dict[str, Any]:
        self._ensure_sessions_file()
        try:
            with self.sessions_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_sessions(self, data: Dict[str, Any]) -> None:
        with self.sessions_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        sessions = self._read_sessions()
        session = sessions.get(session_id)

        if not isinstance(session, dict):
            session = {
                "id": session_id,
                "title": "New chat",
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "messages": [],
                "message_count": 0,
                "last_message_preview": "",
            }
            sessions[session_id] = session
            self._write_sessions(sessions)

        return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = list(self._read_sessions().values())
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self._get_or_create_session(session_id)

    def send_message(
        self,
        *,
        content: str,
        session_id: str = "default-session",
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        user_text = (content or "").strip()
        attachments = attachments or []

        if not user_text and not attachments:
            raise ValueError("Message content is required")

        session = self._get_or_create_session(session_id)
        sessions = self._read_sessions()
        session = sessions.get(session_id, session)

        artifact_retrieval = self.artifact_service.retrieve_for_prompt(
            user_text,
            session_id=session_id,
            limit=3,
            max_chars_per_artifact=1400,
        )

        attachment_context = self._build_attachment_context(attachments)
        message_history = session.get("messages") or []
        trimmed_history = message_history[-10:]

        system_prompt = self._build_system_prompt(
            artifact_context=artifact_retrieval.get("context_text", ""),
            attachment_context=attachment_context,
        )

        response_text = self._generate_reply(
            system_prompt=system_prompt,
            history=trimmed_history,
            user_text=user_text,
        )

        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": user_text,
            "attachments": attachments,
            "created_at": utc_now_iso(),
        }

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": response_text,
            "created_at": utc_now_iso(),
        }

        session_messages = list(message_history)
        session_messages.append(user_message)
        session_messages.append(assistant_message)

        session["messages"] = session_messages[-100:]
        session["updated_at"] = utc_now_iso()
        session["message_count"] = len(session["messages"])
        session["last_message_preview"] = response_text[:160]
        if session.get("title", "New chat") == "New chat" and user_text:
            session["title"] = user_text[:60]

        sessions[session_id] = session
        self._write_sessions(sessions)

        used_artifacts = artifact_retrieval.get("items", [])
        attachment_refs = self._build_attachment_refs(attachments)

        saved_reply_artifact = self.artifact_service.save_artifact(
            title=f"Chat reply • {user_text[:48] or 'untitled'}",
            content=response_text,
            kind="chat",
            session_id=session_id,
            tags=["chat", "reply", "memory" if used_artifacts else "fresh"],
            meta={
                "source": "chat_service",
                "user_prompt": user_text,
                "model": self.model,
                "source_summary": {
                    "artifact_retrieval_used": bool(used_artifacts),
                    "artifact_count": len(used_artifacts),
                    "attachment_count": len(attachments),
                    "history_count": len(trimmed_history),
                },
                "retrieved_artifacts": [
                    {
                        "id": x.get("id", ""),
                        "title": x.get("title", ""),
                        "kind": x.get("kind", ""),
                        "score": x.get("retrieval_score", 0),
                        "updated_at": x.get("updated_at", ""),
                    }
                    for x in used_artifacts
                ],
                "attachments": attachment_refs,
            },
        )

        debug = {
            "mode": "chat",
            "model": self.model,
            "artifact_used": bool(used_artifacts),
            "artifact_count": len(used_artifacts),
            "artifact_titles": [x.get("title", "") for x in used_artifacts],
            "artifact_ids": [x.get("id", "") for x in used_artifacts],
            "artifact_scores": [x.get("retrieval_score", 0) for x in used_artifacts],
            "attachment_count": len(attachments),
            "attachment_names": [x.get("name", "") for x in attachment_refs],
            "history_count": len(trimmed_history),
            "reply_chars": len(response_text),
            "saved_reply_artifact_id": saved_reply_artifact.get("id"),
        }

        return {
            "ok": True,
            "message": assistant_message,
            "session": {
                "id": session["id"],
                "title": session["title"],
                "updated_at": session["updated_at"],
                "message_count": session["message_count"],
                "last_message_preview": session["last_message_preview"],
            },
            "debug": debug,
        }

    def _build_system_prompt(self, *, artifact_context: str, attachment_context: str) -> str:
        parts = [
            (
                "You are Nova, a direct helpful assistant inside a local app. "
                "Use saved artifact context when it is relevant. "
                "When artifact context is helpful, continue from it instead of ignoring it. "
                "Be clear, practical, and concise."
            )
        ]

        if artifact_context.strip():
            parts.append("Saved artifact context:\n" + artifact_context.strip())

        if attachment_context.strip():
            parts.append("Attachment context:\n" + attachment_context.strip())

        return "\n\n".join(parts).strip()

    def _build_attachment_context(self, attachments: List[Dict[str, Any]]) -> str:
        if not attachments:
            return ""

        blocks: List[str] = []
        for idx, item in enumerate(attachments, start=1):
            name = str(item.get("name") or item.get("filename") or f"attachment-{idx}")
            content = str(item.get("content") or item.get("text") or item.get("preview") or "")
            file_type = str(item.get("type") or item.get("mime_type") or "")
            blocks.append(
                "\n".join(
                    [
                        f"[attachment {idx}]",
                        f"name: {name}",
                        f"type: {file_type}",
                        "content:",
                        content[:1600],
                    ]
                )
            )
        return "\n\n".join(blocks).strip()

    def _build_attachment_refs(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for item in attachments:
            refs.append(
                {
                    "name": str(item.get("name") or item.get("filename") or ""),
                    "type": str(item.get("type") or item.get("mime_type") or ""),
                    "url": str(item.get("url") or ""),
                    "size": item.get("size"),
                }
            )
        return refs

    def _generate_reply(
        self,
        *,
        system_prompt: str,
        history: List[Dict[str, Any]],
        user_text: str,
    ) -> str:
        if not self.client:
            return self._offline_reply(system_prompt=system_prompt, user_text=user_text)

        try:
            input_messages: List[Dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
            ]

            for msg in history:
                role = msg.get("role") or "user"
                content = str(msg.get("content") or "")
                if content.strip():
                    input_messages.append({"role": role, "content": content})

            input_messages.append({"role": "user", "content": user_text})

            response = self.client.responses.create(
                model=self.model,
                input=input_messages,
            )
            text = self._extract_response_text(response).strip()
            return text or "I’m here. I used what I could from the saved brain, but I didn’t get a full model response."
        except Exception as e:
            return f"[AI error: {e}]"

    def _extract_response_text(self, response: Any) -> str:
        if hasattr(response, "output_text") and response.output_text:
            return str(response.output_text)

        try:
            output = getattr(response, "output", None) or []
            parts: List[str] = []
            for item in output:
                content_list = getattr(item, "content", None) or []
                for content_item in content_list:
                    text_value = getattr(content_item, "text", None)
                    if text_value:
                        parts.append(str(text_value))
            return "\n".join(parts).strip()
        except Exception:
            return str(response)

    def _offline_reply(self, *, system_prompt: str, user_text: str) -> str:
        marker = "Saved artifact context:\n"
        if marker in system_prompt:
            artifact_section = system_prompt.split(marker, 1)[1].split("\n\nAttachment context:", 1)[0].strip()
            if artifact_section:
                return (
                    "No OpenAI API key is set, so Nova is running in local fallback mode.\n\n"
                    "I found relevant saved artifacts and would use them here:\n\n"
                    f"{artifact_section[:1800]}"
                )

        return (
            "No OpenAI API key is set, so Nova is running in local fallback mode.\n\n"
            f"You said: {user_text}"
        )