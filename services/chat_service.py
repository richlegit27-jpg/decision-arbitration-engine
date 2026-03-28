from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import requests
from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
DEFAULT_SYSTEM_PROMPT = (
    "You are Nova, a sharp, practical, high-agency assistant. "
    "Be direct, useful, and accurate. Prefer concrete action over vague advice.\n\n"
    "Use provided context when it is relevant. Do not claim to have used context that is "
    "empty or unavailable. If attached material is insufficient, say so plainly."
)

MAX_HISTORY_MESSAGES = 18
MAX_MESSAGE_CHARS = 12000
MAX_MEMORY_ITEMS = 12
MAX_ATTACHMENT_ITEMS = 8
MAX_ATTACHMENT_CHARS = 3000
MAX_WEB_PAGES = 3
MAX_WEB_CHARS_PER_PAGE = 3500
REQUEST_TIMEOUT = 12

URL_RE = re.compile(r"""https?://[^\s<>"')\]]+""", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b.*?</style>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class WebPageSummary:
    url: str
    final_url: str
    title: str
    content_type: str
    status_code: int
    ok: bool
    text: str
    preview: str
    truncated: bool
    error: str = ""


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\x00", " ")
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _truncate(text: str, limit: int) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)


def _extract_urls(text: str) -> List[str]:
    seen = set()
    urls: List[str] = []
    for match in URL_RE.findall(text or ""):
        url = match.rstrip(".,;:!?)]>}\"'")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = SCRIPT_RE.sub(" ", raw_html)
    text = STYLE_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return _clean_text(text)


def _extract_title(raw_html: str) -> str:
    if not raw_html:
        return ""
    match = TITLE_RE.search(raw_html)
    if not match:
        return ""
    return _clean_text(html.unescape(match.group(1)))


def _fetch_web_page(url: str) -> WebPageSummary:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Nova/1.0"
        )
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        body = response.text or ""

        if "html" in content_type:
            title = _extract_title(body)
            text = _strip_html(body)
        else:
            title = ""
            text = _clean_text(body)

        text = _truncate(text, MAX_WEB_CHARS_PER_PAGE)
        preview = _truncate(text, 500)

        return WebPageSummary(
            url=url,
            final_url=str(response.url),
            title=title or _clean_text(response.url),
            content_type=content_type or "unknown",
            status_code=response.status_code,
            ok=response.ok,
            text=text,
            preview=preview,
            truncated=len(_clean_text(_strip_html(body) if "html" in content_type else body)) > len(text),
        )
    except Exception as exc:
        return WebPageSummary(
            url=url,
            final_url=url,
            title="",
            content_type="",
            status_code=0,
            ok=False,
            text="",
            preview="",
            truncated=False,
            error=str(exc),
        )


def _summarize_web_from_text(text: str) -> Tuple[str, Dict[str, Any]]:
    urls = _extract_urls(text)
    if not urls:
        return "", {
            "enabled": True,
            "used": False,
            "urls": [],
            "pages": [],
            "summary": "",
        }

    pages: List[WebPageSummary] = []
    for url in urls[:MAX_WEB_PAGES]:
        pages.append(_fetch_web_page(url))

    usable_pages = [p for p in pages if p.ok and p.text]
    if not usable_pages:
        debug_payload = {
            "enabled": True,
            "used": False,
            "urls": urls[:MAX_WEB_PAGES],
            "pages": [
                {
                    "url": p.url,
                    "final_url": p.final_url,
                    "ok": p.ok,
                    "status_code": p.status_code,
                    "content_type": p.content_type,
                    "title": p.title,
                    "preview": p.preview,
                    "error": p.error,
                }
                for p in pages
            ],
            "summary": "",
        }
        return "", debug_payload

    blocks: List[str] = []
    for index, page in enumerate(usable_pages, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[Web Source {index}]",
                    f"Title: {page.title or 'Untitled'}",
                    f"URL: {page.final_url or page.url}",
                    f"Type: {page.content_type or 'unknown'}",
                    f"Preview: {_truncate(page.preview, 350)}",
                    f"Extracted Text: {_truncate(page.text, MAX_WEB_CHARS_PER_PAGE)}",
                ]
            )
        )

    summary = (
        "Web context was automatically fetched from URLs found in the user's latest message.\n"
        "Use it when relevant. If the fetched content is thin, noisy, or insufficient, say so plainly.\n\n"
        + "\n\n".join(blocks)
    )

    debug_payload = {
        "enabled": True,
        "used": True,
        "urls": urls[:MAX_WEB_PAGES],
        "pages": [
            {
                "url": p.url,
                "final_url": p.final_url,
                "ok": p.ok,
                "status_code": p.status_code,
                "content_type": p.content_type,
                "title": p.title,
                "preview": p.preview,
                "truncated": p.truncated,
                "error": p.error,
            }
            for p in pages
        ],
        "summary": summary,
    }
    return summary, debug_payload


def _coerce_message(item: Any) -> Optional[Dict[str, str]]:
    if not isinstance(item, dict):
        return None
    role = str(item.get("role") or "").strip().lower()
    content = item.get("content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        content = "\n".join(parts)
    content = _truncate(content, MAX_MESSAGE_CHARS)
    if not role or not content:
        return None
    if role not in {"system", "user", "assistant"}:
        role = "user"
    return {"role": role, "content": content}


def _normalize_history(history: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in history or []:
        msg = _coerce_message(item)
        if msg:
            normalized.append(msg)
    if len(normalized) > MAX_HISTORY_MESSAGES:
        normalized = normalized[-MAX_HISTORY_MESSAGES:]
    return normalized


def _normalize_memory(memory: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for raw in memory or []:
        if not isinstance(raw, dict):
            continue
        value = _clean_text(raw.get("value") or raw.get("text") or raw.get("content") or "")
        if not value:
            continue
        items.append(
            {
                "kind": _clean_text(raw.get("kind") or "note"),
                "value": value,
                "score": raw.get("score"),
                "source": raw.get("source"),
            }
        )
    return items[:MAX_MEMORY_ITEMS]


def _format_memory_block(memory: Optional[Sequence[Dict[str, Any]]]) -> str:
    items = _normalize_memory(memory)
    if not items:
        return ""
    lines = ["Saved user memory:"]
    for item in items:
        kind = item.get("kind") or "note"
        value = item.get("value") or ""
        lines.append(f"- [{kind}] {value}")
    return "\n".join(lines)


def _normalize_attachments(attachments: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for raw in attachments or []:
        if not isinstance(raw, dict):
            continue
        name = _clean_text(raw.get("name") or raw.get("filename") or raw.get("path") or "attachment")
        summary = _clean_text(
            raw.get("summary")
            or raw.get("preview")
            or raw.get("text")
            or raw.get("content")
            or ""
        )
        if not summary:
            continue
        normalized.append(
            {
                "name": name,
                "summary": _truncate(summary, MAX_ATTACHMENT_CHARS),
                "mime_type": _clean_text(raw.get("mime_type") or raw.get("content_type") or ""),
            }
        )
    return normalized[:MAX_ATTACHMENT_ITEMS]


def _format_attachments_block(attachments: Optional[Sequence[Dict[str, Any]]]) -> str:
    items = _normalize_attachments(attachments)
    if not items:
        return ""
    lines = ["Attachment context:"]
    for item in items:
        mime = f" ({item['mime_type']})" if item.get("mime_type") else ""
        lines.append(f"- {item['name']}{mime}: {item['summary']}")
    return "\n".join(lines)


def _build_messages(
    *,
    user_text: str,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    memory: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None,
    web_enabled: bool = True,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    final_system_prompt = _clean_text(system_prompt or DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT
    cleaned_user_text = _truncate(user_text, MAX_MESSAGE_CHARS)

    memory_block = _format_memory_block(memory)
    attachments_block = _format_attachments_block(attachments)
    web_block, web_debug = _summarize_web_from_text(cleaned_user_text) if web_enabled else (
        "",
        {"enabled": False, "used": False, "urls": [], "pages": [], "summary": ""},
    )

    system_parts = [final_system_prompt]
    if memory_block:
        system_parts.append(memory_block)
    if attachments_block:
        system_parts.append(attachments_block)
    if web_block:
        system_parts.append(web_block)

    messages: List[Dict[str, str]] = [{"role": "system", "content": "\n\n".join(system_parts)}]
    messages.extend(_normalize_history(history))
    messages.append({"role": "user", "content": cleaned_user_text})

    debug = {
        "model": DEFAULT_MODEL,
        "system_prompt_preview": _truncate(final_system_prompt, 500),
        "history_count": len(_normalize_history(history)),
        "memory": _normalize_memory(memory),
        "attachments": _normalize_attachments(attachments),
        "documents": _normalize_attachments(attachments),
        "images": [],
        "memory_update": None,
        "web": web_debug,
        "messages_preview": messages[-4:],
        "message_count": len(messages),
    }
    return messages, debug


def _make_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_reply(
    *,
    user_text: str = "",
    history: Optional[Sequence[Dict[str, Any]]] = None,
    memory: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Dict[str, Any]]] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    web_enabled: bool = True,
    temperature: float = 0.4,
    **_: Any,
) -> Tuple[str, Dict[str, Any]]:
    messages, debug = _build_messages(
        user_text=user_text,
        history=history,
        memory=memory,
        attachments=attachments,
        system_prompt=system_prompt,
        web_enabled=web_enabled,
    )

    chosen_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    debug["model"] = chosen_model

    client = _make_client()
    response = client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=temperature,
    )

    text = ""
    try:
        text = response.choices[0].message.content or ""
    except Exception:
        text = ""

    text = text.strip()
    if not text:
        text = "I couldn't produce a response from the model."

    return text, debug


def generate_reply_stream(
    *,
    user_text: str = "",
    history: Optional[Sequence[Dict[str, Any]]] = None,
    memory: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Dict[str, Any]]] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    web_enabled: bool = True,
    temperature: float = 0.4,
    **_: Any,
) -> Tuple[Iterator[Dict[str, Any]], Dict[str, Any]]:
    messages, debug = _build_messages(
        user_text=user_text,
        history=history,
        memory=memory,
        attachments=attachments,
        system_prompt=system_prompt,
        web_enabled=web_enabled,
    )

    chosen_model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    debug["model"] = chosen_model
    client = _make_client()

    stream = client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    def iterator() -> Iterator[Dict[str, Any]]:
        parts: List[str] = []
        try:
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None) or ""
                if not piece:
                    continue
                parts.append(piece)
                yield {"type": "delta", "delta": piece}
            final_text = "".join(parts).strip()
            yield {"type": "done", "text": final_text}
        except Exception as exc:
            yield {"type": "error", "error": str(exc)}

    return iterator(), debug


def preview_chat_context(
    *,
    user_text: str = "",
    history: Optional[Sequence[Dict[str, Any]]] = None,
    memory: Optional[Sequence[Dict[str, Any]]] = None,
    attachments: Optional[Sequence[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None,
    web_enabled: bool = True,
    **_: Any,
) -> Dict[str, Any]:
    messages, debug = _build_messages(
        user_text=user_text,
        history=history,
        memory=memory,
        attachments=attachments,
        system_prompt=system_prompt,
        web_enabled=web_enabled,
    )
    return {
        "messages": messages,
        "debug": debug,
    }