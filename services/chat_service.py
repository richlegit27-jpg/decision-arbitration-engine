from __future__ import annotations

import json
import os
import re
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"

CHAT_SERVICE_VERSION = "real-model-artifact-memory-2026-03-30-003"
MODEL_STAGE_REAL = "real_model_path_restored"
MODEL_STAGE_FALLBACK = "real_model_path_failed_fallback"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS_PER_MESSAGE = 4000

MAX_MEMORY_ITEMS = 3
MAX_MEMORY_EXCERPT_CHARS = 700
MAX_MEMORY_BLOCK_CHARS = 2200


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


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


def tokenize(value: str) -> List[str]:
    text = normalize_space(value).lower()
    return re.findall(r"[a-z0-9_]{2,}", text)


def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


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
            "memory_used": False,
            "memory_selected_count": 0,
            "memory_pinned_count": 0,
            "memory_relevant_count": 0,
            "memory_titles": [],
            "artifact_recall_count": 0,
            "artifact_recall_titles": [],
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

    def _is_junk_artifact_text(self, text: str) -> bool:
        lowered = safe_text(text).lower()
        if not lowered:
            return True
        junk_markers = [
            "you said:",
            "nova fallback is active",
            "main model path is unavailable",
            "local fallback",
            "request failed:",
            "artifact skipped",
            "fallback reason:",
        ]
        marker_hits = sum(1 for marker in junk_markers if marker in lowered)
        if marker_hits >= 2:
            return True
        if len(lowered) < 20:
            return True
        return False

    def _artifact_title(self, artifact: Dict[str, Any]) -> str:
        return first_non_empty(
            artifact.get("title"),
            artifact.get("name"),
            artifact.get("label"),
            artifact.get("id"),
            "Untitled Artifact",
        )

    def _artifact_text(self, artifact: Dict[str, Any]) -> str:
        content = artifact.get("content")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, dict):
            possible = first_non_empty(
                content.get("content"),
                content.get("text"),
                content.get("body"),
                content.get("message"),
            )
            if possible:
                return possible

        return first_non_empty(
            artifact.get("text"),
            artifact.get("body"),
            artifact.get("message"),
            artifact.get("summary"),
            artifact.get("preview"),
        )

    def _artifact_is_pinned(self, artifact: Dict[str, Any]) -> bool:
        return bool(
            artifact.get("pinned") is True
            or artifact.get("is_pinned") is True
            or artifact.get("favorite") is True
            or artifact.get("starred") is True
        )

    def _artifact_updated_at(self, artifact: Dict[str, Any]) -> str:
        return first_non_empty(
            artifact.get("updated_at"),
            artifact.get("created_at"),
            artifact.get("timestamp"),
        )

    def _artifact_excerpt(self, text: str, query_terms: List[str]) -> str:
        clean = normalize_space(text)
        if len(clean) <= MAX_MEMORY_EXCERPT_CHARS:
            return clean

        lowered = clean.lower()
        for term in query_terms:
            idx = lowered.find(term.lower())
            if idx >= 0:
                start = max(0, idx - 180)
                end = min(len(clean), idx + MAX_MEMORY_EXCERPT_CHARS)
                excerpt = clean[start:end].strip()
                if start > 0:
                    excerpt = "… " + excerpt
                if end < len(clean):
                    excerpt = excerpt + " …"
                return excerpt

        excerpt = clean[:MAX_MEMORY_EXCERPT_CHARS].rstrip()
        if len(clean) > MAX_MEMORY_EXCERPT_CHARS:
            excerpt += " …"
        return excerpt

    def _artifact_score(self, artifact: Dict[str, Any], user_text: str) -> float:
        title = self._artifact_title(artifact)
        text = self._artifact_text(artifact)
        combined = f"{title}\n{text}".lower()

        query_terms = unique_preserve_order(tokenize(user_text))
        if not query_terms:
            return 0.0

        score = 0.0

        if self._artifact_is_pinned(artifact):
            score += 100.0

        for term in query_terms:
            if term in title.lower():
                score += 12.0
            elif term in combined:
                score += 4.0

        title_tokens = set(tokenize(title))
        body_tokens = set(tokenize(text))
        overlap = len(set(query_terms) & (title_tokens | body_tokens))
        score += overlap * 3.0

        updated = self._artifact_updated_at(artifact)
        if updated:
            score += 0.25

        return score

    def _load_candidate_artifacts(self, user_text: str) -> List[Dict[str, Any]]:
        artifacts = read_json_file(ARTIFACTS_FILE, [])
        if not isinstance(artifacts, list):
            return []

        candidates: List[Dict[str, Any]] = []

        for raw in artifacts:
            if not isinstance(raw, dict):
                continue

            title = self._artifact_title(raw)
            text = self._artifact_text(raw)

            if not title and not text:
                continue
            if self._is_junk_artifact_text(text):
                continue

            score = self._artifact_score(raw, user_text)
            if score <= 0 and not self._artifact_is_pinned(raw):
                continue

            candidates.append(
                {
                    "raw": raw,
                    "title": title,
                    "text": text,
                    "pinned": self._artifact_is_pinned(raw),
                    "updated_at": self._artifact_updated_at(raw),
                    "score": score,
                }
            )

        candidates.sort(
            key=lambda item: (
                0 if item["pinned"] else 1,
                -float(item["score"]),
                item["updated_at"] or "",
            )
        )
        return candidates

    def _select_memory_artifacts(self, user_text: str) -> Dict[str, Any]:
        candidates = self._load_candidate_artifacts(user_text)
        if not candidates:
            return {
                "memory_used": False,
                "items": [],
                "memory_selected_count": 0,
                "memory_pinned_count": 0,
                "memory_relevant_count": 0,
                "memory_titles": [],
                "artifact_recall_count": 0,
                "artifact_recall_titles": [],
                "memory_block": "",
            }

        selected: List[Dict[str, Any]] = []
        seen_titles = set()
        query_terms = unique_preserve_order(tokenize(user_text))

        for item in candidates:
            title_key = item["title"].strip().lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            selected.append(item)
            if len(selected) >= MAX_MEMORY_ITEMS:
                break

        pinned_count = sum(1 for item in selected if item["pinned"])
        relevant_count = sum(1 for item in selected if item["score"] > 0)

        memory_lines = [
            "Saved artifact memory that may be relevant to this reply:",
        ]
        used_chars = len(memory_lines[0])

        for index, item in enumerate(selected, start=1):
            excerpt = self._artifact_excerpt(item["text"], query_terms)
            line = f"[{index}] {item['title']}\n{excerpt}"
            projected = used_chars + len(line) + 2
            if projected > MAX_MEMORY_BLOCK_CHARS and index > 1:
                break
            memory_lines.append(line)
            used_chars = projected

        final_items_count = max(0, len(memory_lines) - 1)
        final_selected = selected[:final_items_count] if final_items_count < len(selected) else selected
        titles = [item["title"] for item in final_selected]

        return {
            "memory_used": bool(final_selected),
            "items": final_selected,
            "memory_selected_count": len(final_selected),
            "memory_pinned_count": sum(1 for item in final_selected if item["pinned"]),
            "memory_relevant_count": sum(1 for item in final_selected if item["score"] > 0),
            "memory_titles": titles,
            "artifact_recall_count": len(final_selected),
            "artifact_recall_titles": titles,
            "memory_block": "\n\n".join(memory_lines) if final_selected else "",
        }

    def _build_messages(
        self,
        user_text: str,
        history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
        memory_block: str = "",
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        system_text = safe_text(system_prompt)
        if not system_text:
            system_text = (
                "You are Nova, a sharp, helpful AI assistant. "
                "Use the conversation history and saved artifact memory when relevant. "
                "Be clear, direct, and useful."
            )

        messages.append({"role": "system", "content": system_text})

        if memory_block:
            messages.append(
                {
                    "role": "system",
                    "content": memory_block,
                }
            )

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

        memory_context = self._select_memory_artifacts(user_text)
        debug["memory_used"] = memory_context["memory_used"]
        debug["memory_selected_count"] = memory_context["memory_selected_count"]
        debug["memory_pinned_count"] = memory_context["memory_pinned_count"]
        debug["memory_relevant_count"] = memory_context["memory_relevant_count"]
        debug["memory_titles"] = memory_context["memory_titles"]
        debug["artifact_recall_count"] = memory_context["artifact_recall_count"]
        debug["artifact_recall_titles"] = memory_context["artifact_recall_titles"]

        reply_text = ""
        raw_error = ""

        if self.client is not None:
            try:
                messages = self._build_messages(
                    user_text=user_text,
                    history=normalized_history,
                    system_prompt=system_prompt or payload.get("system_prompt"),
                    memory_block=memory_context["memory_block"],
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
                "memory_used": debug["memory_used"],
                "memory_selected_count": debug["memory_selected_count"],
                "memory_pinned_count": debug["memory_pinned_count"],
                "artifact_recall_count": debug["artifact_recall_count"],
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