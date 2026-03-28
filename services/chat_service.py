# notepad C:\Users\Owner\nova\services\chat_service.py
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple


# =========================================================
# config
# =========================================================

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
DEFAULT_TEMPERATURE = float(os.getenv("NOVA_TEMPERATURE", "0.7"))
MAX_HISTORY_MESSAGES = int(os.getenv("NOVA_MAX_HISTORY_MESSAGES", "24"))
MAX_MESSAGE_CHARS = int(os.getenv("NOVA_MAX_MESSAGE_CHARS", "24000"))
MAX_SYSTEM_PROMPT_CHARS = int(os.getenv("NOVA_MAX_SYSTEM_PROMPT_CHARS", "12000"))
MAX_DEBUG_PREVIEW_CHARS = int(os.getenv("NOVA_MAX_DEBUG_PREVIEW_CHARS", "1800"))
STREAM_FAKE_CHUNK_SIZE = int(os.getenv("NOVA_STREAM_FAKE_CHUNK_SIZE", "120"))

DEFAULT_SYSTEM_PROMPT = """You are Nova, a sharp, practical, high-agency assistant. Be direct, useful, and accurate.
Prefer concrete action over vague advice.

Use provided context when it is relevant.
Do not claim to have used context that is empty or unavailable.
If attached material is insufficient, say so plainly.

When coding:
- prefer robust, production-minded code
- preserve existing contracts unless explicitly changing them
- avoid unnecessary rewrites
- return complete answers, not vague plans
""".strip()


# =========================================================
# optional imports
# =========================================================

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    from services.attachment_service import (
        attachments_to_prompt_text,
        build_attachment_context,
    )
except Exception:  # pragma: no cover
    attachments_to_prompt_text = None  # type: ignore
    build_attachment_context = None  # type: ignore

try:
    from services.web_service import build_web_prompt_context
except Exception:  # pragma: no cover
    build_web_prompt_context = None  # type: ignore

try:
    from services.memory_service import build_memory_prompt_context
except Exception:  # pragma: no cover
    build_memory_prompt_context = None  # type: ignore

try:
    from services.artifact_service import build_artifact_prompt_context
except Exception:  # pragma: no cover
    build_artifact_prompt_context = None  # type: ignore


# =========================================================
# helpers
# =========================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def make_id(prefix: str = "msg") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def compact_preview(value: Any, limit: int = MAX_DEBUG_PREVIEW_CHARS) -> str:
    text = clean_text(value)
    text = re.sub(r"\s+", " ", text)
    return truncate(text, limit)


# =========================================================
# request normalization
# =========================================================

def normalize_message(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item = safe_dict(item)
    role = clean_text(item.get("role")).lower() or "user"
    if role not in {"system", "user", "assistant", "developer", "tool"}:
        role = "user"

    content = clean_text(item.get("content"))
    if not content:
        return None

    return {
        "id": clean_text(item.get("id")) or make_id("msg"),
        "role": role,
        "content": truncate(content, MAX_MESSAGE_CHARS),
        "created_at": clean_text(item.get("created_at")) or utc_now_iso(),
        "metadata": safe_dict(item.get("metadata")),
    }


def normalize_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for raw in safe_list(messages):
        if not isinstance(raw, dict):
            continue
        msg = normalize_message(raw)
        if not msg:
            continue
        normalized.append(msg)

    return normalized[-MAX_HISTORY_MESSAGES:]


def normalize_chat_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)

    content = truncate(clean_text(payload.get("content")), MAX_MESSAGE_CHARS)
    session_id = clean_text(payload.get("session_id")) or None
    model = clean_text(payload.get("model")) or DEFAULT_MODEL
    system_prompt = truncate(
        clean_text(payload.get("system_prompt")) or DEFAULT_SYSTEM_PROMPT,
        MAX_SYSTEM_PROMPT_CHARS,
    )

    incoming_messages = normalize_history(payload.get("messages"))
    attachments = [safe_dict(x) for x in safe_list(payload.get("attachments")) if isinstance(x, dict)]
    artifacts = [safe_dict(x) for x in safe_list(payload.get("artifacts")) if isinstance(x, dict)]

    stream = safe_bool(payload.get("stream"), False)
    web_enabled = safe_bool(payload.get("web_enabled"), True)
    memory_enabled = safe_bool(payload.get("memory_enabled"), True)
    artifact_enabled = safe_bool(payload.get("artifact_enabled"), True)
    attachment_enabled = safe_bool(payload.get("attachment_enabled"), True)

    return {
        "session_id": session_id,
        "content": content,
        "model": model,
        "system_prompt": system_prompt,
        "messages": incoming_messages,
        "attachments": attachments,
        "artifacts": artifacts,
        "stream": stream,
        "web_enabled": web_enabled,
        "memory_enabled": memory_enabled,
        "artifact_enabled": artifact_enabled,
        "attachment_enabled": attachment_enabled,
        "metadata": safe_dict(payload.get("metadata")),
    }


# =========================================================
# context builders
# =========================================================

def _build_memory_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not payload.get("memory_enabled"):
        return {"prompt_text": "", "items": [], "error": None}

    if callable(build_memory_prompt_context):
        try:
            result = build_memory_prompt_context(
                {
                    "content": payload.get("content"),
                    "messages": payload.get("messages", []),
                    "session_id": payload.get("session_id"),
                    "metadata": payload.get("metadata", {}),
                }
            )
            result = safe_dict(result)
            return {
                "prompt_text": clean_text(result.get("prompt_text")),
                "items": safe_list(result.get("items") or result.get("memory")),
                "error": result.get("error"),
            }
        except Exception as exc:
            return {
                "prompt_text": "",
                "items": [],
                "error": {"code": "memory_context_failed", "message": str(exc)},
            }

    return {"prompt_text": "", "items": [], "error": None}


def _build_attachment_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    attachments = safe_list(payload.get("attachments"))
    if not payload.get("attachment_enabled") or not attachments:
        return {
            "prompt_text": "",
            "attachments": [],
            "documents": [],
            "images": [],
            "error": None,
        }

    prompt_text = ""
    structured: Dict[str, Any] = {}

    if callable(build_attachment_context):
        try:
            structured = safe_dict(build_attachment_context(attachments))
        except Exception as exc:
            return {
                "prompt_text": "",
                "attachments": [],
                "documents": [],
                "images": [],
                "error": {"code": "attachment_context_failed", "message": str(exc)},
            }

    if callable(attachments_to_prompt_text):
        try:
            prompt_text = clean_text(attachments_to_prompt_text(attachments))
        except Exception:
            prompt_text = ""

    return {
        "prompt_text": prompt_text,
        "attachments": safe_list(structured.get("attachments")),
        "documents": safe_list(structured.get("documents")),
        "images": safe_list(structured.get("images")),
        "error": None,
    }


def _build_web_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not payload.get("web_enabled"):
        return {"prompt_text": "", "results": [], "debug": [], "error": None}

    if callable(build_web_prompt_context):
        try:
            result = build_web_prompt_context(text=clean_text(payload.get("content")))
            result = safe_dict(result)
            return {
                "prompt_text": clean_text(result.get("prompt_text")),
                "results": safe_list(result.get("results")),
                "debug": safe_list(result.get("debug")),
                "error": result.get("error"),
            }
        except Exception as exc:
            return {
                "prompt_text": "",
                "results": [],
                "debug": [],
                "error": {"code": "web_context_failed", "message": str(exc)},
            }

    return {"prompt_text": "", "results": [], "debug": [], "error": None}


def _build_artifact_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = safe_list(payload.get("artifacts"))
    if not payload.get("artifact_enabled") or not artifacts:
        return {"prompt_text": "", "items": [], "error": None}

    if callable(build_artifact_prompt_context):
        try:
            result = build_artifact_prompt_context({"artifacts": artifacts})
            result = safe_dict(result)
            return {
                "prompt_text": clean_text(result.get("prompt_text")),
                "items": safe_list(result.get("items") or result.get("artifacts")),
                "error": result.get("error"),
            }
        except Exception as exc:
            return {
                "prompt_text": "",
                "items": [],
                "error": {"code": "artifact_context_failed", "message": str(exc)},
            }

    return {"prompt_text": "", "items": [], "error": None}


def build_context_bundle(payload: Dict[str, Any]) -> Dict[str, Any]:
    memory_context = _build_memory_context(payload)
    attachment_context = _build_attachment_context(payload)
    web_context = _build_web_context(payload)
    artifact_context = _build_artifact_context(payload)

    sections: List[str] = []

    memory_text = clean_text(memory_context.get("prompt_text"))
    if memory_text:
        sections.append(memory_text)

    attachment_text = clean_text(attachment_context.get("prompt_text"))
    if attachment_text:
        sections.append(attachment_text)

    web_text = clean_text(web_context.get("prompt_text"))
    if web_text:
        sections.append(web_text)

    artifact_text = clean_text(artifact_context.get("prompt_text"))
    if artifact_text:
        sections.append(artifact_text)

    return {
        "context_text": "\n\n".join([x for x in sections if x]).strip(),
        "memory": memory_context,
        "attachments": attachment_context,
        "web": web_context,
        "artifacts": artifact_context,
    }


# =========================================================
# input building
# =========================================================

def build_messages_for_model(payload: Dict[str, Any], bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []

    system_prompt = clean_text(payload.get("system_prompt")) or DEFAULT_SYSTEM_PROMPT
    context_text = clean_text(bundle.get("context_text"))

    if context_text:
        system_prompt = f"{system_prompt}\n\nContext:\n{context_text}".strip()

    messages.append(
        {
            "role": "system",
            "content": system_prompt,
        }
    )

    for item in safe_list(payload.get("messages")):
        msg = safe_dict(item)
        role = clean_text(msg.get("role")).lower()
        content = clean_text(msg.get("content"))
        if role not in {"user", "assistant", "system", "developer"}:
            continue
        if not content:
            continue
        messages.append({"role": role, "content": content})

    current_content = clean_text(payload.get("content"))
    if current_content:
        messages.append({"role": "user", "content": current_content})

    return messages


# =========================================================
# openai response handling
# =========================================================

def get_openai_client() -> Any:
    if OpenAI is None:
        return None

    api_key = clean_text(os.getenv("OPENAI_API_KEY"))
    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:
        try:
            return OpenAI()
        except Exception:
            return None


def extract_response_text(response: Any) -> str:
    try:
        text = clean_text(getattr(response, "output_text", ""))
        if text:
            return text
    except Exception:
        pass

    try:
        output = getattr(response, "output", None)
        if output:
            parts: List[str] = []
            for item in output:
                item_type = clean_text(getattr(item, "type", ""))
                if item_type == "message":
                    content_list = getattr(item, "content", []) or []
                    for content in content_list:
                        content_type = clean_text(getattr(content, "type", ""))
                        if content_type in {"output_text", "text"}:
                            chunk = clean_text(getattr(content, "text", ""))
                            if chunk:
                                parts.append(chunk)
                else:
                    text = clean_text(getattr(item, "text", ""))
                    if text:
                        parts.append(text)
            if parts:
                return clean_text("\n".join(parts))
    except Exception:
        pass

    try:
        as_dict = response.model_dump()  # type: ignore[attr-defined]
        if isinstance(as_dict, dict):
            if clean_text(as_dict.get("output_text")):
                return clean_text(as_dict.get("output_text"))
            output = safe_list(as_dict.get("output"))
            parts: List[str] = []
            for item in output:
                d = safe_dict(item)
                if clean_text(d.get("type")) == "message":
                    for content in safe_list(d.get("content")):
                        c = safe_dict(content)
                        ctype = clean_text(c.get("type"))
                        if ctype in {"output_text", "text"}:
                            text = clean_text(c.get("text"))
                            if text:
                                parts.append(text)
            if parts:
                return clean_text("\n".join(parts))
    except Exception:
        pass

    return ""


def call_model(messages: List[Dict[str, str]], model: str) -> Tuple[str, Dict[str, Any]]:
    client = get_openai_client()
    if client is None:
        return (
            "Nova backend is running, but the model client is not available. Check OPENAI_API_KEY and OpenAI SDK installation.",
            {
                "provider": "openai",
                "client_available": False,
                "model": model,
                "error": {
                    "code": "model_unavailable",
                    "message": "OpenAI client unavailable or OPENAI_API_KEY missing.",
                },
            },
        )

    try:
        response = client.responses.create(
            model=model,
            input=messages,
        )
        text = extract_response_text(response)
        if not text:
            text = "The model returned no text."
        return (
            text,
            {
                "provider": "openai",
                "client_available": True,
                "model": model,
                "response_id": clean_text(getattr(response, "id", "")),
                "error": None,
            },
        )
    except Exception as exc:
        return (
            "Nova hit a model error while generating a reply.",
            {
                "provider": "openai",
                "client_available": True,
                "model": model,
                "error": {
                    "code": "model_call_failed",
                    "message": str(exc),
                },
            },
        )


# =========================================================
# debug shaping
# =========================================================

def build_debug_brain(payload: Dict[str, Any], bundle: Dict[str, Any], messages: List[Dict[str, str]], model_meta: Dict[str, Any]) -> Dict[str, Any]:
    attachment_ctx = safe_dict(bundle.get("attachments"))
    web_ctx = safe_dict(bundle.get("web"))
    artifact_ctx = safe_dict(bundle.get("artifacts"))
    memory_ctx = safe_dict(bundle.get("memory"))

    messages_preview = []
    for item in messages[-8:]:
        msg = safe_dict(item)
        messages_preview.append(
            {
                "role": clean_text(msg.get("role")),
                "content": compact_preview(msg.get("content")),
            }
        )

    return {
        "model": clean_text(payload.get("model")) or DEFAULT_MODEL,
        "system_prompt_preview": compact_preview(messages[0]["content"] if messages else ""),
        "history_count": len(safe_list(payload.get("messages"))),
        "message_count": len(messages),
        "messages_preview": messages_preview,
        "memory": safe_list(memory_ctx.get("items")),
        "memory_update": "",
        "attachments": safe_list(attachment_ctx.get("attachments")),
        "documents": safe_list(attachment_ctx.get("documents")),
        "images": safe_list(attachment_ctx.get("images")),
        "web": safe_list(web_ctx.get("debug") or web_ctx.get("results")),
        "artifacts": safe_list(artifact_ctx.get("items")),
        "context_preview": compact_preview(bundle.get("context_text")),
        "model_meta": model_meta,
    }


# =========================================================
# output shaping
# =========================================================

def build_assistant_message(content: str, model: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": make_id("assistant"),
        "role": "assistant",
        "content": clean_text(content),
        "created_at": utc_now_iso(),
        "session_id": session_id,
        "metadata": {
            "model": model,
        },
    }


def build_chat_response(payload: Dict[str, Any], assistant_text: str, debug: Dict[str, Any], model_meta: Dict[str, Any]) -> Dict[str, Any]:
    assistant_message = build_assistant_message(
        content=assistant_text,
        model=clean_text(payload.get("model")) or DEFAULT_MODEL,
        session_id=payload.get("session_id"),
    )

    return {
        "ok": True,
        "message": assistant_message,
        "assistant_message": assistant_message,
        "session_id": payload.get("session_id"),
        "model": clean_text(payload.get("model")) or DEFAULT_MODEL,
        "debug": debug,
        "error": model_meta.get("error"),
    }


# =========================================================
# public service functions
# =========================================================

def generate_reply(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_chat_payload(payload)
    bundle = build_context_bundle(normalized)
    messages = build_messages_for_model(normalized, bundle)
    assistant_text, model_meta = call_model(messages, normalized.get("model") or DEFAULT_MODEL)
    debug = build_debug_brain(normalized, bundle, messages, model_meta)
    return build_chat_response(normalized, assistant_text, debug, model_meta)


def _chunk_text_for_stream(text: str, chunk_size: int = STREAM_FAKE_CHUNK_SIZE) -> Iterable[str]:
    text = clean_text(text)
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def generate_reply_stream(payload: Dict[str, Any]) -> Tuple[Generator[Dict[str, Any], None, None], Dict[str, Any]]:
    normalized = normalize_chat_payload({**safe_dict(payload), "stream": True})
    bundle = build_context_bundle(normalized)
    messages = build_messages_for_model(normalized, bundle)

    placeholder_model_meta = {
        "provider": "openai",
        "client_available": get_openai_client() is not None,
        "model": normalized.get("model") or DEFAULT_MODEL,
        "error": None,
    }
    debug = build_debug_brain(normalized, bundle, messages, placeholder_model_meta)

    def event_generator() -> Generator[Dict[str, Any], None, None]:
        assistant_text, model_meta = call_model(messages, normalized.get("model") or DEFAULT_MODEL)

        yield {
            "type": "start",
            "session_id": normalized.get("session_id"),
            "model": normalized.get("model") or DEFAULT_MODEL,
            "created_at": utc_now_iso(),
        }

        for chunk in _chunk_text_for_stream(assistant_text):
            yield {
                "type": "delta",
                "delta": chunk,
            }

        assistant_message = build_assistant_message(
            content=assistant_text,
            model=normalized.get("model") or DEFAULT_MODEL,
            session_id=normalized.get("session_id"),
        )

        yield {
            "type": "done",
            "message": assistant_message,
            "assistant_message": assistant_message,
            "session_id": normalized.get("session_id"),
            "model": normalized.get("model") or DEFAULT_MODEL,
            "debug": build_debug_brain(normalized, bundle, messages, model_meta),
            "error": model_meta.get("error"),
        }

    return event_generator(), debug


def preview_chat_brain(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_chat_payload(payload)
    bundle = build_context_bundle(normalized)
    messages = build_messages_for_model(normalized, bundle)
    model_meta = {
        "provider": "openai",
        "client_available": get_openai_client() is not None,
        "model": normalized.get("model") or DEFAULT_MODEL,
        "error": None,
    }

    return {
        "ok": True,
        "debug": build_debug_brain(normalized, bundle, messages, model_meta),
        "message_count": len(messages),
        "messages_preview": [
            {
                "role": clean_text(m.get("role")),
                "content": compact_preview(m.get("content")),
            }
            for m in messages
        ],
        "error": None,
    }


# =========================================================
# route helpers
# =========================================================

def coerce_stream_done_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = safe_dict(event)
    if clean_text(event.get("type")) != "done":
        return event

    message = safe_dict(event.get("message") or event.get("assistant_message"))
    return {
        "type": "done",
        "message": message,
        "assistant_message": message,
        "session_id": clean_text(event.get("session_id")) or message.get("session_id"),
        "model": clean_text(event.get("model")) or safe_dict(message.get("metadata")).get("model") or DEFAULT_MODEL,
        "debug": safe_dict(event.get("debug")),
        "error": event.get("error"),
    }


def service_status() -> Dict[str, Any]:
    client_available = get_openai_client() is not None
    api_key = clean_text(os.getenv("OPENAI_API_KEY"))

    return {
        "ok": True,
        "service": "chat_service",
        "model": DEFAULT_MODEL,
        "client_available": client_available,
        "key_present": bool(api_key),
        "key_prefix": api_key[:7] if api_key else "",
        "max_history_messages": MAX_HISTORY_MESSAGES,
        "max_message_chars": MAX_MESSAGE_CHARS,
        "stream_chunk_size": STREAM_FAKE_CHUNK_SIZE,
        "updated_at": utc_now_iso(),
        "error": None,
    }