from __future__ import annotations

import os
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


CHAT_SERVICE_VERSION = "real-model-history-2026-03-30-002"
MODEL_STAGE_REAL = "real_model_path_restored"
MODEL_STAGE_FALLBACK = "real_model_path_failed_fallback"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
MAX_HISTORY_MESSAGES = 16
MAX_HISTORY_CHARS_PER_MESSAGE = 4000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = safe_text(value)
        if text:
            return text
    return ""


class ChatService:
    def __init__(self) -> None:
        self.api_key = safe_text(os.getenv("OPENAI_API_KEY"))
        self.model = safe_text(os.getenv("OPENAI_MODEL")) or DEFAULT_MODEL
        self.client = None

        if self.api_key and OpenAI is not None:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    def _base_debug(self) -> Dict[str, Any]:
        return {
            "chat_service_version": CHAT_SERVICE_VERSION,
            "route_build": os.getenv("NOVA_ROUTE_BUILD", "clean-chat-pipeline-2026-03-30-004"),
            "api_key_present": bool(self.api_key),
            "openai_import_ok": OpenAI is not None,
            "client_ready": self.client is not None,
            "model": self.model if self.client else "local-fallback",
            "used_fallback": False,
            "fallback_reason": "",
            "model_stage": MODEL_STAGE_REAL if self.client else MODEL_STAGE_FALLBACK,
        }

    def _extract_user_text(
        self,
        content: Optional[str] = None,
        message: Optional[str] = None,
        text: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload = payload or {}
        return first_non_empty(
            content,
            message,
            text,
            payload.get("content"),
            payload.get("message"),
            payload.get("text"),
        )

    def _normalize_history_item(self, item: Any) -> Optional[Dict[str, str]]:
        if not isinstance(item, dict):
            return None

        role = safe_text(item.get("role")).lower()
        content = first_non_empty(
            item.get("content"),
            item.get("message"),
            item.get("text"),
        )

        if role not in {"system", "user", "assistant"}:
            return None
        if not content:
            return None

        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE].rstrip()

        return {
            "role": role,
            "content": content,
        }

    def _normalize_history(self, history: Any) -> List[Dict[str, str]]:
        if not isinstance(history, list):
            return []

        normalized: List[Dict[str, str]] = []

        for item in history:
            fixed = self._normalize_history_item(item)
            if fixed:
                normalized.append(fixed)

        if len(normalized) > MAX_HISTORY_MESSAGES:
            normalized = normalized[-MAX_HISTORY_MESSAGES:]

        return normalized

    def _build_messages(
        self,
        user_text: str,
        history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        system_text = safe_text(system_prompt)
        if not system_text:
            system_text = (
                "You are Nova, a sharp, helpful AI assistant. "
                "Use the conversation history when relevant. "
                "Be clear, direct, and useful."
            )

        messages.append({"role": "system", "content": system_text})

        normalized_history = self._normalize_history(history or [])
        messages.extend(normalized_history)

        messages.append({"role": "user", "content": user_text})
        return messages

    def _fallback_reply(self, user_text: str, reason: str) -> str:
        clean_reason = safe_text(reason) or "unknown_failure"

        if not user_text:
            return (
                "Hey — I’m here. The main model path is unavailable right now, "
                f"so Nova is using fallback mode. Failure cause: {clean_reason}."
            )

        return (
            f"You said: {user_text}\n\n"
            "Nova fallback is active because the real model path is unavailable right now.\n"
            f"Failure cause: {clean_reason}"
        )

    def _extract_response_text(self, response: Any) -> str:
        try:
            output_text = safe_text(getattr(response, "output_text", ""))
            if output_text:
                return output_text
        except Exception:
            pass

        try:
            choices = getattr(response, "choices", None)
            if choices:
                first_choice = choices[0]
                message = getattr(first_choice, "message", None)
                if message is not None:
                    content = getattr(message, "content", None)
                    if isinstance(content, str) and content.strip():
                        return content.strip()
        except Exception:
            pass

        try:
            data = response.model_dump() if hasattr(response, "model_dump") else {}
            text = safe_text(data.get("output_text"))
            if text:
                return text
        except Exception:
            pass

        return ""

    def send_message(
        self,
        content: Optional[str] = None,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        payload: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        text: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload = payload or {}
        debug = self._base_debug()

        user_text = self._extract_user_text(
            content=content,
            message=message,
            text=text,
            payload=payload,
        )

        final_session_id = first_non_empty(
            session_id,
            payload.get("session_id"),
            kwargs.get("session_id"),
            "default-session",
        )

        raw_history = history
        if raw_history is None:
            raw_history = payload.get("history")
        if raw_history is None:
            raw_history = kwargs.get("history")

        normalized_history = self._normalize_history(raw_history)

        attachments = attachments or payload.get("attachments") or kwargs.get("attachments") or []

        debug["session_id"] = final_session_id
        debug["history_count"] = len(normalized_history)
        debug["history_included"] = bool(normalized_history)
        debug["history_roles"] = [item["role"] for item in normalized_history]
        debug["attachments_count"] = len(attachments) if isinstance(attachments, list) else 0
        debug["latest_user_text"] = user_text[:500]

        reply_text = ""
        raw_error = ""

        if self.client is not None:
            try:
                messages = self._build_messages(
                    user_text=user_text,
                    history=normalized_history,
                    system_prompt=system_prompt or payload.get("system_prompt"),
                )

                debug["request_message_count"] = len(messages)

                response = self.client.responses.create(
                    model=self.model,
                    input=messages,
                )

                reply_text = self._extract_response_text(response)

                if not reply_text:
                    raise RuntimeError("empty_model_response")

                debug["model"] = self.model
                debug["model_stage"] = MODEL_STAGE_REAL
                debug["used_fallback"] = False
                debug["fallback_reason"] = ""
            except Exception as exc:
                raw_error = f"{type(exc).__name__}: {exc}"
                debug["used_fallback"] = True
                debug["fallback_reason"] = raw_error
                debug["model_stage"] = MODEL_STAGE_FALLBACK
                debug["model"] = "local-fallback"
                debug["traceback"] = traceback.format_exc(limit=3)
                reply_text = self._fallback_reply(user_text=user_text, reason=raw_error)
        else:
            if not debug["api_key_present"]:
                raw_error = "missing_openai_api_key"
            elif OpenAI is None:
                raw_error = "openai_package_not_installed"
            else:
                raw_error = "openai_client_not_initialized"

            debug["used_fallback"] = True
            debug["fallback_reason"] = raw_error
            debug["model_stage"] = MODEL_STAGE_FALLBACK
            debug["model"] = "local-fallback"
            reply_text = self._fallback_reply(user_text=user_text, reason=raw_error)

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": reply_text,
            "created_at": utc_now(),
            "attachments": [],
            "meta": {
                "used_fallback": debug["used_fallback"],
                "fallback_reason": debug["fallback_reason"],
                "chat_service_version": CHAT_SERVICE_VERSION,
                "model_stage": debug["model_stage"],
                "model": debug["model"],
                "history_count": debug["history_count"],
                "history_included": debug["history_included"],
            },
        }

        return {
            "ok": True,
            "message": reply_text,
            "session_id": final_session_id,
            "assistant_message": assistant_message,
            "debug": debug,
        }


chat_service = ChatService()


def send_message(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return chat_service.send_message(*args, **kwargs)