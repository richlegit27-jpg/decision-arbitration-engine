from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import uuid
import math

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from collections import defaultdict
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from helpers.web_utils import (
    should_route_to_web,
    normalize_url_input,
)

from helpers.video_utils import build_video_analysis_result


WEB_FETCH_TIMEOUT = 12
WEB_FETCH_TEXT_LIMIT = 6000
WEB_SEARCH_TIMEOUT = 12
WEB_SEARCH_MAX_RESULTS = 5
CURRENT_INFO_FETCH_LIMIT = 3

CURRENT_INFO_HINTS = {
    "latest", "today", "current", "recent", "recently", "updated", "update",
    "news", "headlines", "record", "score", "scores", "standing", "standings",
    "schedule", "weather", "forecast", "temperature", "stock", "stocks",
    "price", "prices", "market", "rankings", "ranking", "who won", "who is winning",
    "what happened", "breaking", "live",
}

def clean_web_input(value: Any) -> str:
    value = normalize_text(value).strip()

    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        value = value[1:-1].strip()

    if value.lower().startswith("/web "):
        value = value[5:].strip()

    return value

def _looks_like_current_info_query(text: str) -> bool:
    text = normalize_text(text).strip().lower()
    if not text:
        return False

    if text.startswith("/web ") or text.startswith("/image "):
        return False

    if extract_url(text):
        return False

    for hint in CURRENT_INFO_HINTS:
        if hint in text:
            return True

    sports_patterns = [
        r"\b(record|score|standing|standings|schedule)\b",
        r"\b(latest|current|today|recent)\b",
        r"\b(news|headline|headlines|breaking)\b",
        r"\b(weather|forecast|temperature)\b",
        r"\b(stock|stocks|market|price|prices)\b",
    ]

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in sports_patterns)

def detect_tool_intent(text: str) -> str:
    text = normalize_text(text).strip()
    lowered = text.lower()

    if lowered.startswith("/web "):
        return "web"

    if extract_url(text):
        return "web"

    if _looks_like_current_info_query(text):
        return "current_info"

    if lowered.startswith("/image "):
        return "image"

    return "none"

def _clean_search_result_url(url: str) -> str:
    url = normalize_text(url).strip()
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        uddg = query.get("uddg")
        if uddg and uddg[0]:
            return unquote(uddg[0]).strip()
    except Exception:
        pass

    return url

def search_web(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> dict[str, Any]:
    query = normalize_text(query).strip()
    if not query:
        return {
            "ok": False,
            "error": "Empty search query.",
            "query": "",
            "results": [],
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nova/2026",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=WEB_SEARCH_TIMEOUT,
            headers=headers,
            allow_redirects=True,
        )
        response.raise_for_status()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc) or "Search request failed.",
            "query": query,
            "results": [],
        }

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for node in soup.select(".result"):
        link = node.select_one(".result__title a") or node.select_one("a.result__a")
        snippet_node = node.select_one(".result__snippet")
        if not link:
            continue

        title = normalize_text(link.get_text(" ", strip=True)).strip()
        href = _clean_search_result_url(link.get("href") or "")
        snippet = normalize_text(snippet_node.get_text(" ", strip=True) if snippet_node else "").strip()

        if not href or not title:
            continue

        key = href.lower().strip()
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "title": title,
                "url": href,
                "snippet": snippet,
                "domain": _domain_from_url(href),
            }
        )

        if len(results) >= max_results:
            break

    return {
        "ok": True,
        "query": query,
        "results": results,
    }

def build_current_info_context(query: str) -> dict[str, Any]:
    search_result = search_web(query, max_results=WEB_SEARCH_MAX_RESULTS)
    if not search_result.get("ok"):
        return {
            "ok": False,
            "error": search_result.get("error") or "Search failed.",
            "query": query,
            "results": [],
            "sources": [],
            "source_text": "",
        }

    results = safe_list(search_result.get("results"))
    sources: list[dict[str, Any]] = []
    blocks: list[str] = []

    for item in results[:CURRENT_INFO_FETCH_LIMIT]:
        if not isinstance(item, dict):
            continue

        url = normalize_text(item.get("url") or "").strip()
        if not url:
            continue

        fetched = fetch_web(url)
        if not fetched.get("ok"):
            continue

        title = normalize_text(fetched.get("title") or item.get("title") or "").strip()
        description = normalize_text(fetched.get("description") or item.get("snippet") or "").strip()
        content = normalize_text(fetched.get("content") or "").strip()
        domain = normalize_text(fetched.get("domain") or item.get("domain") or "").strip()

        sources.append(
            {
                "title": title,
                "url": url,
                "domain": domain,
                "description": description,
                "content": content[:1800],
                "status_code": int(fetched.get("status_code") or 0),
            }
        )

        block_parts = [
            f"TITLE: {title}" if title else "",
            f"URL: {url}" if url else "",
            f"DOMAIN: {domain}" if domain else "",
            f"DESCRIPTION: {description}" if description else "",
            f"CONTENT: {content[:1800]}" if content else "",
        ]
        block = "\n".join(part for part in block_parts if part)
        if block:
            blocks.append(block)

    return {
        "ok": True,
        "query": query,
        "results": results,
        "sources": sources,
        "source_text": "\n\n---\n\n".join(blocks).strip(),
    }

def answer_current_info_query(query: str) -> dict[str, Any]:
    context = build_current_info_context(query)
    if not context.get("ok"):
        return {
            "ok": False,
            "error": context.get("error") or "Current-info search failed.",
            "query": query,
            "results": [],
            "sources": [],
            "text": "",
        }

    sources = safe_list(context.get("sources"))
    if not sources:
        return {
            "ok": False,
            "error": "No useful search sources found.",
            "query": query,
            "results": safe_list(context.get("results")),
            "sources": [],
            "text": "",
        }

    if OPENAI_CLIENT is None:
        lines = [f"Search results for: {query}", ""]
        for source in sources[:3]:
            title = normalize_text(source.get("title") or "").strip()
            url = normalize_text(source.get("url") or "").strip()
            description = normalize_text(source.get("description") or "").strip()

            if title:
                lines.append(f"- {title}")
            if description:
                lines.append(f"  {description}")
            if url:
                lines.append(f"  {url}")

        return {
            "ok": True,
            "query": query,
            "results": safe_list(context.get("results")),
            "sources": sources,
            "text": "\n".join(lines).strip(),
        }

    source_text = normalize_text(context.get("source_text") or "").strip()
    system_prompt = (
        "You are Nova, a sharp current-info web assistant.\n"
        "Answer only from the provided search/fetch evidence.\n"
        "Be concise, direct, and useful.\n"
        "If the evidence is weak or conflicting, say that clearly.\n"
        "Prefer the freshest and most clearly relevant evidence.\n"
        "Do not claim certainty beyond the provided sources.\n"
    )

    user_prompt = (
        f"User query: {query}\n\n"
        f"Current UTC time: {now_iso()}\n\n"
        "Evidence from live web search and fetched pages:\n\n"
        f"{source_text}\n\n"
        "Write a direct answer first, then a short Sources section with title + domain only."
    )

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
        )
        text = normalize_text(response.choices[0].message.content or "").strip()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc) or "Model synthesis failed.",
            "query": query,
            "results": safe_list(context.get("results")),
            "sources": sources,
            "text": "",
        }

    return {
        "ok": True,
        "query": query,
        "results": safe_list(context.get("results")),
        "sources": sources,
        "text": text,
    }

def build_current_info_meta(result: dict[str, Any]) -> dict[str, Any]:
    sources = safe_list(result.get("sources"))
    first_url = ""
    if sources and isinstance(sources[0], dict):
        first_url = normalize_text(sources[0].get("url") or "").strip()

    bullets: list[str] = []
    for item in sources[:3]:
        if not isinstance(item, dict):
            continue
        title = summarize_text(normalize_text(item.get("title") or "").strip(), 100)
        domain = normalize_text(item.get("domain") or "").strip()
        if title and domain:
            bullets.append(f"{title} ({domain})")
        elif title:
            bullets.append(title)

    return {
        "source_url": first_url,
        "search_query": normalize_text(result.get("query") or "").strip(),
        "analysis_text": summarize_text(normalize_text(result.get("text") or "").strip(), 240),
        "bullets": bullets[:5],
        "sources": sources[:5],
    }

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
ARTIFACTS_FILE = DATA_DIR / "nova_artifacts.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# APP
# =========================================================

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"

OPENAI_CLIENT = None
if OPENAI_API_KEY and OpenAI is not None:
    try:
        OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        OPENAI_CLIENT = None


# =========================================================
# HELPERS
# =========================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        write_json(path, default)
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        write_json(path, default)
        return deepcopy(default)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def summarize_text(value: str, limit: int = 120) -> str:
    text = normalize_text(value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def ensure_store_files() -> None:
    if not SESSIONS_FILE.exists():
        write_json(
            SESSIONS_FILE,
            {
                "active_session_id": "",
                "sessions": [],
            },
        )
    if not ARTIFACTS_FILE.exists():
        write_json(ARTIFACTS_FILE, [])
    if not MEMORY_FILE.exists():
        write_json(MEMORY_FILE, [])


def load_sessions_store() -> dict[str, Any]:
    ensure_store_files()
    store = read_json(
        SESSIONS_FILE,
        {
            "active_session_id": "",
            "sessions": [],
        },
    )
    if not isinstance(store, dict):
        store = {"active_session_id": "", "sessions": []}
    store["active_session_id"] = str(store.get("active_session_id") or "")
    store["sessions"] = safe_list(store.get("sessions"))
    return store


def save_sessions_store(store: dict[str, Any]) -> None:
    write_json(SESSIONS_FILE, store)


def load_artifacts() -> list[dict[str, Any]]:
    ensure_store_files()
    items = read_json(ARTIFACTS_FILE, [])
    return items if isinstance(items, list) else []


def save_artifacts(items: list[dict[str, Any]]) -> None:
    write_json(ARTIFACTS_FILE, items)

def build_artifact_viewer(artifact: dict[str, Any]) -> dict[str, Any]:
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}

    kind = str(artifact.get("kind") or "")
    body = str(artifact.get("body") or artifact.get("content") or "")
    title = str(artifact.get("title") or "Artifact")

    image_url = meta.get("image_url") or artifact.get("image_url") or ""
    source_url = meta.get("source_url") or artifact.get("source_url") or ""
    video_url = meta.get("video_url") or ""
    audio_url = meta.get("audio_url") or ""

    analysis_text = meta.get("analysis_text") or ""
    bullets = meta.get("bullets") if isinstance(meta.get("bullets"), list) else []

    return {
        "kind": kind,
        "title": title,
        "body": body,
        "image_url": image_url,
        "video_url": video_url,
        "audio_url": audio_url,
        "source_url": source_url,
        "analysis_text": analysis_text,
        "bullets": bullets,
    }


def load_memory() -> list[dict[str, Any]]:
    ensure_store_files()
    items = read_json(MEMORY_FILE, [])
    return items if isinstance(items, list) else []


def find_session(store: dict[str, Any], session_id: str) -> dict[str, Any] | None:
    for session in safe_list(store.get("sessions")):
        if str(session.get("id") or "") == str(session_id or ""):
            return session
    return None


def make_session(title: str = "New chat") -> dict[str, Any]:
    session_id = make_id("session")
    now = now_iso()
    return {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "pinned": False,
        "last_message_preview": "",
        "message_count": 0,
        "messages": [],
    }


def ensure_active_session(store: dict[str, Any]) -> dict[str, Any]:
    active_session_id = str(store.get("active_session_id") or "")
    session = find_session(store, active_session_id)
    if session:
        return session

    sessions = safe_list(store.get("sessions"))
    if sessions:
        store["active_session_id"] = sessions[0]["id"]
        save_sessions_store(store)
        return sessions[0]

    session = make_session("New chat")
    store["sessions"].append(session)
    store["active_session_id"] = session["id"]
    save_sessions_store(store)
    return session


def message_text(message: dict[str, Any]) -> str:
    return normalize_text(
        message.get("text")
        or message.get("content")
        or message.get("body")
        or message.get("message")
        or ""
    )


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(message.get("id") or make_id("msg")),
        "role": str(message.get("role") or "assistant"),
        "text": message_text(message),
        "created_at": str(message.get("created_at") or now_iso()),
        "pending": bool(message.get("pending", False)),
        "streaming": bool(message.get("streaming", False)),
        "stopped": bool(message.get("stopped", False)),
        "error": bool(message.get("error", False)),
        "source": str(message.get("source") or ""),
        "meta": message.get("meta") if isinstance(message.get("meta"), dict) else {},
        "attachments": safe_list(message.get("attachments")),
    }


def session_messages(session: dict[str, Any]) -> list[dict[str, Any]]:
    messages = safe_list(session.get("messages"))
    session["messages"] = messages
    return messages


def recalc_session(session: dict[str, Any]) -> None:
    messages = session_messages(session)
    session["message_count"] = len(messages)
    session["updated_at"] = now_iso()
    preview = ""
    if messages:
        preview = summarize_text(message_text(messages[-1]), 100)
    session["last_message_preview"] = preview


def append_message(session: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    msg = normalize_message(message)
    session_messages(session).append(msg)
    recalc_session(session)
    return msg


def replace_message(session: dict[str, Any], message_id: str, new_message: dict[str, Any]) -> dict[str, Any] | None:
    messages = session_messages(session)
    for index, item in enumerate(messages):
        if str(item.get("id") or "") == str(message_id or ""):
            msg = normalize_message(new_message)
            messages[index] = msg
            recalc_session(session)
            return msg
    return None


def find_message(session: dict[str, Any], message_id: str) -> dict[str, Any] | None:
    for item in session_messages(session):
        if str(item.get("id") or "") == str(message_id or ""):
            return item
    return None


def sanitize_filename(filename: str) -> str:
    raw = Path(str(filename or "upload.bin")).name
    raw = re.sub(r"[^A-Za-z0-9._ -]+", "_", raw).strip()
    return raw or "upload.bin"


def file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0

def normalize_attachment(item: dict[str, Any]) -> dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    attachment_id = str(item.get("id") or item.get("attachment_id") or make_id("att"))
    filename = sanitize_filename(
        str(item.get("filename") or item.get("name") or item.get("title") or "upload.bin")
    )
    stored_name = sanitize_filename(
        str(item.get("stored_name") or item.get("stored_filename") or filename)
    )
    url = str(item.get("url") or item.get("file_url") or item.get("source_url") or "").strip()
    mime_type = str(
        item.get("mime_type")
        or item.get("type")
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    ).strip()
    size = int(item.get("size") or 0) if str(item.get("size") or "").strip() else 0

    return {
        "id": attachment_id,
        "name": filename,
        "filename": filename,
        "stored_name": stored_name,
        "url": url,
        "mime_type": mime_type or "application/octet-stream",
        "size": size,
    }


def normalize_attachments(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in safe_list(items):
        normalized = normalize_attachment(item if isinstance(item, dict) else {})
        out.append(normalized)
    return out

def make_user_message(text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return normalize_message(
        {
            "id": make_id("user"),
            "role": "user",
            "text": normalize_text(text),
            "created_at": now_iso(),
            "attachments": normalize_attachments(attachments),
        }
    )

def make_assistant_message(
    text: str,
    *,
    message_id: str | None = None,
    source: str = "",
    pending: bool = False,
    streaming: bool = False,
    stopped: bool = False,
    error: bool = False,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return normalize_message(
        {
            "id": message_id or make_id("assistant"),
            "role": "assistant",
            "text": normalize_text(text),
            "created_at": now_iso(),
            "pending": pending,
            "streaming": streaming,
            "stopped": stopped,
            "error": error,
            "source": source,
            "meta": meta or {},
        }
    )

# =========================================================
# ARTIFACT INTELLIGENCE (TITLE + KIND ROUTING)
# =========================================================

def _detect_artifact_kind(text: str) -> str:
    t = _textish(text).lower()

    if any(k in t for k in ["traceback", "error", "exception", "fix", "bug"]):
        return "debug"

    if any(k in t for k in ["def ", "class ", "import ", "function", "javascript", "python"]):
        return "code"

    if any(k in t for k in ["plan", "steps", "roadmap", "phase"]):
        return "plan"

    if any(k in t for k in ["story", "paragraph", "write", "rewrite", "email"]):
        return "writing"

    if any(k in t for k in ["http://", "https://", "www."]):
        return "web"

    return "chat_reply"

def _build_artifact_title(text: str, kind: str) -> str:
    text = normalize_text(text).strip()

    if not text:
        return "Artifact"

    first_line = text.split("\n")[0][:80]

    if kind == "debug":
        return f"Debug Fix: {first_line}"

    if kind == "code":
        return f"Code: {first_line}"

    if kind == "plan":
        return f"Plan: {first_line}"

    if kind == "writing":
        return f"Writing: {first_line}"

    if kind == "web":
        return f"Web: {first_line}"

    return f"Response: {first_line}"

# =========================================================
# ARTIFACT METADATA ENRICHMENT
# =========================================================

ARTIFACT_BULLET_MAX_ITEMS = 5
ARTIFACT_BULLET_MAX_LEN = 140
ARTIFACT_SUMMARY_MAX_LEN = 240

def _clean_artifact_line(line: str) -> str:
    line = normalize_text(line).strip()
    line = re.sub(r"\s+", " ", line)
    return line.strip("-*• \t")

def _split_artifact_lines(text: str) -> list[str]:
    raw_lines = normalize_text(text).split("\n")
    lines: list[str] = []

    for raw in raw_lines:
        cleaned = _clean_artifact_line(raw)
        if not cleaned:
            continue
        lines.append(cleaned)

    return lines

def _summarize_artifact_text(text: str, kind: str) -> str:
    lines = _split_artifact_lines(text)
    if not lines:
        return ""

    first = lines[0]

    if kind == "debug":
        return summarize_text(f"Debug outcome: {first}", ARTIFACT_SUMMARY_MAX_LEN)

    if kind == "code":
        return summarize_text(f"Code result: {first}", ARTIFACT_SUMMARY_MAX_LEN)

    if kind == "plan":
        return summarize_text(f"Plan summary: {first}", ARTIFACT_SUMMARY_MAX_LEN)

    if kind == "writing":
        return summarize_text(f"Writing summary: {first}", ARTIFACT_SUMMARY_MAX_LEN)

    if kind == "web":
        return summarize_text(f"Web result: {first}", ARTIFACT_SUMMARY_MAX_LEN)

    return summarize_text(first, ARTIFACT_SUMMARY_MAX_LEN)

def _extract_artifact_bullets(text: str, kind: str) -> list[str]:
    lines = _split_artifact_lines(text)
    if not lines:
        return []

    bullets: list[str] = []
    seen: set[str] = set()

    for line in lines:
        lowered = line.lower()

        if lowered in seen:
            continue

        if kind == "code":
            if not any(token in line for token in ["def ", "class ", "import ", "return ", "if ", "="]):
                if len(bullets) > 0:
                    continue

        if kind == "debug":
            if not any(token in lowered for token in [
                "root cause", "fix", "test", "error", "exception", "cause"
            ]):
                if len(bullets) > 0:
                    continue

        if kind == "plan":
            if not re.match(r"^(\d+[\).\:]|\bphase\b|\bstep\b|\bnext\b)", lowered):
                if len(bullets) > 0:
                    continue

        clean = summarize_text(line, ARTIFACT_BULLET_MAX_LEN)
        if not clean:
            continue

        bullets.append(clean)
        seen.add(lowered)

        if len(bullets) >= ARTIFACT_BULLET_MAX_ITEMS:
            break

    if bullets:
        return bullets

    fallback: list[str] = []
    for line in lines[:ARTIFACT_BULLET_MAX_ITEMS]:
        clean = summarize_text(line, ARTIFACT_BULLET_MAX_LEN)
        if clean:
            fallback.append(clean)

    return fallback

def _build_artifact_meta(text: str, kind: str, message: dict[str, Any]) -> dict[str, Any]:
    existing_meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}

    source_url = str(
        existing_meta.get("source_url")
        or message.get("source_url")
        or ""
    ).strip()

    analysis_text = _summarize_artifact_text(text, kind)
    bullets = _extract_artifact_bullets(text, kind)

    return {
        "source": str(message.get("source") or "send"),
        "source_url": source_url,
        "analysis_text": analysis_text,
        "bullets": bullets,
    }

# =========================================================
# ARTIFACT DUPLICATE SUPPRESSION + SMART UPDATE LOCK
# =========================================================

ARTIFACT_DUPLICATE_WINDOW = 8

def _artifact_text_fingerprint(text: str) -> str:
    cleaned = normalize_text(text).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned

def _artifact_meta_fingerprint(meta: dict[str, Any] | None) -> str:
    meta = meta if isinstance(meta, dict) else {}
    source = str(meta.get("source") or "").strip().lower()
    source_url = str(meta.get("source_url") or "").strip().lower()
    analysis_text = str(meta.get("analysis_text") or "").strip().lower()
    bullets = meta.get("bullets") if isinstance(meta.get("bullets"), list) else []
    bullet_text = " | ".join(str(x).strip().lower() for x in bullets if str(x).strip())
    return f"{source}||{source_url}||{analysis_text}||{bullet_text}"

def _artifacts_equivalent(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False

    a_kind = str(a.get("kind") or "").strip().lower()
    b_kind = str(b.get("kind") or "").strip().lower()
    if a_kind != b_kind:
        return False

    a_session = str(a.get("session_id") or "").strip()
    b_session = str(b.get("session_id") or "").strip()
    if a_session != b_session:
        return False

    a_body = _artifact_text_fingerprint(a.get("body") or a.get("content") or "")
    b_body = _artifact_text_fingerprint(b.get("body") or b.get("content") or "")
    if not a_body or not b_body:
        return False

    if a_body != b_body:
        return False

    a_meta_fp = _artifact_meta_fingerprint(a.get("meta"))
    b_meta_fp = _artifact_meta_fingerprint(b.get("meta"))
    return a_meta_fp == b_meta_fp

def _choose_better_artifact(existing_artifact: dict[str, Any], new_artifact: dict[str, Any]) -> dict[str, Any]:
    existing_meta = existing_artifact.get("meta") if isinstance(existing_artifact.get("meta"), dict) else {}
    new_meta = new_artifact.get("meta") if isinstance(new_artifact.get("meta"), dict) else {}

    existing_bullets = existing_meta.get("bullets") if isinstance(existing_meta.get("bullets"), list) else []
    new_bullets = new_meta.get("bullets") if isinstance(new_meta.get("bullets"), list) else []

    existing_analysis = str(existing_meta.get("analysis_text") or "").strip()
    new_analysis = str(new_meta.get("analysis_text") or "").strip()

    existing_preview = str(existing_artifact.get("preview") or "").strip()
    new_preview = str(new_artifact.get("preview") or "").strip()

    score_existing = 0
    score_new = 0

    if existing_analysis:
        score_existing += 2
    if new_analysis:
        score_new += 2

    score_existing += len(existing_bullets)
    score_new += len(new_bullets)

    if len(existing_preview) >= 40:
        score_existing += 1
    if len(new_preview) >= 40:
        score_new += 1

    if score_new > score_existing:
        merged = dict(new_artifact)
        merged["id"] = str(existing_artifact.get("id") or new_artifact.get("id") or make_id("artifact"))
        merged["created_at"] = str(existing_artifact.get("created_at") or new_artifact.get("created_at") or now_iso())
        return merged

    merged = dict(existing_artifact)
    merged["updated_at"] = str(new_artifact.get("updated_at") or now_iso())
    if not str(merged.get("preview") or "").strip() and new_preview:
        merged["preview"] = new_preview

    merged_meta = dict(existing_meta)
    if not existing_analysis and new_analysis:
        merged_meta["analysis_text"] = new_analysis
    if not existing_bullets and new_bullets:
        merged_meta["bullets"] = new_bullets
    if not str(merged_meta.get("source_url") or "").strip():
        merged_meta["source_url"] = str(new_meta.get("source_url") or "").strip()
    if not str(merged_meta.get("source") or "").strip():
        merged_meta["source"] = str(new_meta.get("source") or "").strip()

    merged["meta"] = merged_meta
    return merged

# =========================================================
# WEB / IMAGE ARTIFACT ROUTING LOCK
# =========================================================

def _first_attachment_url(message: dict[str, Any]) -> str:
    attachments = safe_list(message.get("attachments"))
    for item in attachments:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url:
            return url
    return ""

def _first_attachment_mime(message: dict[str, Any]) -> str:
    attachments = safe_list(message.get("attachments"))
    for item in attachments:
        if not isinstance(item, dict):
            continue
        mime_type = str(item.get("mime_type") or "").strip().lower()
        if mime_type:
            return mime_type
    return ""

def _detect_routed_artifact_kind(message: dict[str, Any], text: str) -> str:
    meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}
    source = str(message.get("source") or "").strip().lower()
    source_url = str(meta.get("source_url") or message.get("source_url") or "").strip()
    image_url = str(meta.get("image_url") or message.get("image_url") or "").strip()
    video_url = str(meta.get("video_url") or message.get("video_url") or "").strip()

    if source == "video_analysis":
        return "video_analysis"

    attachment_url = _first_attachment_url(message)
    attachment_mime = _first_attachment_mime(message)

    if video_url:
        return "video_analysis"

    if image_url:
        return "image_generation"

    if attachment_url and attachment_mime.startswith("image/"):
        return "image_generation"

    if "![generated image]" in text.lower():
        return "image_generation"

    if source_url:
        return "web_result"

    if source in {"web", "web_fetch"}:
        return "web_result"

    return _detect_artifact_kind(text)

def _build_routed_artifact_title(message: dict[str, Any], text: str, kind: str) -> str:
    meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}
    source_url = str(meta.get("source_url") or message.get("source_url") or "").strip()

    if kind == "image_generation":
        clean = normalize_text(text).strip()
        if clean.startswith("!["):
            clean = "Generated image"
        if not clean:
            clean = "Generated image"
        return f"Image: {summarize_text(clean, 70)}"

    if kind == "web_result":
        if source_url:
            return f"Web: {summarize_text(source_url, 70)}"
        return f"Web: {summarize_text(text, 70)}"

    return _build_artifact_title(text, kind)

def _build_routed_artifact_meta(text: str, kind: str, message: dict[str, Any]) -> dict[str, Any]:
    base = _build_artifact_meta(text, kind, message)
    meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}

    image_url = str(meta.get("image_url") or message.get("image_url") or "").strip()
    video_url = str(meta.get("video_url") or message.get("video_url") or "").strip()

    if not image_url:
        attachment_url = _first_attachment_url(message)
        attachment_mime = _first_attachment_mime(message)
        if attachment_url and attachment_mime.startswith("image/"):
            image_url = attachment_url

    source_url = str(meta.get("source_url") or message.get("source_url") or "").strip()

    if image_url:
        base["image_url"] = image_url
    if video_url:
        base["video_url"] = video_url
    if source_url:
        base["source_url"] = source_url

    if kind == "image_generation":
        base["analysis_text"] = summarize_text("Generated image artifact.", 240)
        if not base.get("bullets"):
            base["bullets"] = ["Generated image saved to artifacts."]

    elif kind == "video_analysis":
        if not base.get("analysis_text"):
            base["analysis_text"] = summarize_text("Video analysis artifact.", 240)
        if not base.get("bullets"):
            base["bullets"] = ["Video saved to artifacts."]

    elif kind == "web_result":
        if source_url:
            base["analysis_text"] = summarize_text(f"Web result captured from {source_url}", 240)
        else:
            base["analysis_text"] = summarize_text("Web result captured.", 240)
        if not base.get("bullets"):
            bullets: list[str] = []
            if source_url:
                bullets.append(summarize_text(source_url, 140))
            first_line = normalize_text(text).strip().split("\n")[0].strip() if normalize_text(text).strip() else ""
            if first_line:
                bullets.append(summarize_text(first_line, 140))
            base["bullets"] = bullets[:5]

    return base

def save_artifact_from_assistant(message: dict[str, Any], session_id: str) -> None:
    if not isinstance(message, dict):
        return

    text = normalize_text(message.get("text") or "").strip()
    if not text:
        return

    message_id = str(message.get("id") or "").strip()
    if not message_id:
        return

    session_id = str(session_id or "").strip()
    if not session_id:
        return

    artifacts = load_artifacts()

    existing_index = -1
    existing_artifact: dict[str, Any] | None = None

    for idx, item in enumerate(artifacts):
        if str(item.get("message_id") or "").strip() == message_id:
            existing_index = idx
            existing_artifact = item
            break

    created_at = str(message.get("created_at") or now_iso())
    updated_at = now_iso()

    detected_kind = _detect_routed_artifact_kind(message, text)
    detected_title = _build_routed_artifact_title(message, text, detected_kind)
    artifact_meta = _build_routed_artifact_meta(text, detected_kind, message)
    routed_image_url = str(artifact_meta.get("image_url") or "").strip()
    routed_source_url = str(artifact_meta.get("source_url") or "").strip()

    new_artifact = {
        "id": (
            str(existing_artifact.get("id") or "")
            if existing_artifact
            else make_id("artifact")
        ),
	"session_id": session_id,
        "message_id": message_id,
        "kind": detected_kind,
        "title": detected_title,
        "body": text,
        "preview": summarize_text(text, 120),
        "image_url": routed_image_url,
        "source_url": routed_source_url,
        "created_at": (
            str(existing_artifact.get("created_at") or created_at)
            if existing_artifact
            else created_at
        ),
        "updated_at": updated_at,
        "meta": artifact_meta,
    }

    if existing_index >= 0 and existing_artifact:
        artifacts[existing_index] = _choose_better_artifact(existing_artifact, new_artifact)
        save_artifacts(artifacts)
        return

    for idx, item in enumerate(artifacts[:ARTIFACT_DUPLICATE_WINDOW]):
        if _artifacts_equivalent(item, new_artifact):
            artifacts[idx] = _choose_better_artifact(item, new_artifact)
            save_artifacts(artifacts)
            return

    artifacts.insert(0, new_artifact)
    save_artifacts(artifacts)

def session_contract_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "session": {
            "id": session.get("id") or "",
            "title": session.get("title") or "Untitled chat",
            "created_at": session.get("created_at") or "",
            "updated_at": session.get("updated_at") or "",
            "pinned": bool(session.get("pinned", False)),
            "last_message_preview": session.get("last_message_preview") or "",
            "message_count": int(session.get("message_count") or 0),
            "messages": session_messages(session),
        },
        "active_session_id": session.get("id") or "",
    }

def session_delete_contract_payload(
    deleted_session_id: str,
    active_session: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "deleted_session_id": deleted_session_id,
        "session": {
            "id": active_session.get("id") or "",
            "title": active_session.get("title") or "Untitled chat",
            "created_at": active_session.get("created_at") or "",
            "updated_at": active_session.get("updated_at") or "",
            "pinned": bool(active_session.get("pinned", False)),
            "last_message_preview": active_session.get("last_message_preview") or "",
            "message_count": int(active_session.get("message_count") or 0),
            "messages": session_messages(active_session),
        },
        "active_session_id": active_session.get("id") or "",
    }


def session_error_payload(
    *,
    error: str,
    active_session_id: str = "",
    deleted_session_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": error,
        "session": None,
        "active_session_id": active_session_id or "",
    }
    if deleted_session_id is not None:
        payload["deleted_session_id"] = deleted_session_id
    return payload


def resolve_session_id_from_request(data: dict[str, Any]) -> str:
    return str(
        data.get("session_id")
        or data.get("id")
        or data.get("active_session_id")
        or ""
    ).strip()


def state_payload(session: dict[str, Any] | None = None) -> dict[str, Any]:
    store = load_sessions_store()
    active = session or ensure_active_session(store)

    raw_artifacts = load_artifacts()
    artifacts: list[dict[str, Any]] = []
    for item in raw_artifacts:
        enriched = dict(item)
        enriched["viewer"] = build_artifact_viewer(item)
        artifacts.append(enriched)

    memory = load_memory()

    sessions_summary: list[dict[str, Any]] = []
    for item in safe_list(store.get("sessions")):
        sessions_summary.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "Untitled chat",
                "created_at": item.get("created_at") or "",
                "updated_at": item.get("updated_at") or "",
                "pinned": bool(item.get("pinned", False)),
                "last_message_preview": item.get("last_message_preview") or "",
                "message_count": int(item.get("message_count") or 0),
                "messages": safe_list(item.get("messages")),
            }
        )

    return {
        "ok": True,
        "session_id": active.get("id") or "",
        "active_session_id": active.get("id") or "",
        "session": {
            "id": active.get("id") or "",
            "title": active.get("title") or "Untitled chat",
            "created_at": active.get("created_at") or "",
            "updated_at": active.get("updated_at") or "",
            "pinned": bool(active.get("pinned", False)),
            "last_message_preview": active.get("last_message_preview") or "",
            "message_count": int(active.get("message_count") or 0),
            "messages": session_messages(active),
        },
        "messages": session_messages(active),
        "sessions": sessions_summary,
        "artifacts": artifacts,
        "memory": memory,
        "debug": {
            "route_build": "attachment-pipeline-polish-2026-04-07-001",
            "has_openai_api_key": bool(OPENAI_API_KEY),
            "openai_configured": OPENAI_CLIENT is not None,
            "chat_model": OPENAI_MODEL,
            "timestamp": now_iso(),
        },
    }

# =========================================================
# MEMORY + ATTACHMENT INJECTION LOCK
# =========================================================

MEMORY_MAX_ITEMS = 8
MEMORY_MAX_CHARS = 2400
MODEL_HISTORY_LIMIT = 16
ATTACHMENT_CONTEXT_MAX_ITEMS = 6

# =========================================================
# PHASE D.3 — MEMORY CONFLICT + PRIORITY WEIGHTING
# =========================================================

def _memory_bucket_key(item: dict[str, Any]) -> str:
    text = _textish(item.get("text") or "").lower()

    if any(w in text for w in {"short", "brief", "concise", "tight"}):
        return "length"
    if any(w in text for w in {"long", "detailed", "in depth", "deep dive", "verbose"}):
        return "length"

    if "direct" in text:
        return "tone"
    if any(w in text for w in {"gentle", "soft"}):
        return "tone"

    if "powershell" in text:
        return "shell"

    if any(w in text for w in {"full file", "full-file", "smff"}):
        return "format"

    if any(w in text for w in {"steps", "step by step"}):
        return "workflow"

    return f"raw:{text}"


def _memory_route_bonus(item: dict[str, Any], route_result: dict[str, Any] | None) -> int:
    route = _textish(
        (route_result or {}).get("primary")
        or (route_result or {}).get("mode")
        or ""
    ).lower()

    kind = _textish(item.get("kind") or "").lower()
    text = _textish(item.get("text") or "").lower()

    bonus = 0

    if kind == "preference":
        bonus += 2

    if route in {"coding", "code"} and any(w in text for w in {"powershell", "full file", "smff"}):
        bonus += 4

    if route in {"planning", "plan"} and any(w in text for w in {"phase", "steps", "next move"}):
        bonus += 3

    if route in {"debug", "fix", "error"} and any(w in text for w in {"direct", "concise", "root cause"}):
        bonus += 3

    return bonus


def _memory_time_score(item: dict[str, Any]) -> int:
    stamp = _textish(item.get("updated_at") or item.get("created_at") or "")
    if not stamp:
        return 0

    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        age_seconds = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return 0

    age_days = age_seconds / 86400.0

    if age_days <= 7:
        return 4
    if age_days <= 30:
        return 3
    if age_days <= 90:
        return 2
    if age_days <= 180:
        return 1
    return 0


def resolve_memory_conflicts(
    selected: list[dict[str, Any]],
    route_result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not selected:
        return []

    ranked: list[dict[str, Any]] = []

    for item in selected:
        row = dict(item)
        base_score = int(row.get("score") or 0)
        route_bonus = _memory_route_bonus(row, route_result)
        time_score = _memory_time_score(row)
        final_score = base_score + route_bonus + time_score

        reasons = row.get("reasons") if isinstance(row.get("reasons"), list) else []
        reasons = list(reasons)
        if route_bonus:
            reasons.append(f"route_bonus:{route_bonus}")
        if time_score:
            reasons.append(f"time_bonus:{time_score}")

        row["final_score"] = final_score
        row["reasons"] = reasons
        row["_bucket"] = _memory_bucket_key(row)
        ranked.append(row)

    ranked.sort(
        key=lambda x: (
            int(x.get("final_score") or 0),
            _textish(x.get("updated_at") or x.get("created_at") or ""),
        ),
        reverse=True,
    )

    winners: dict[str, dict[str, Any]] = {}
    for item in ranked:
        bucket = str(item.get("_bucket") or "")
        if bucket not in winners:
            winners[bucket] = item

    final = list(winners.values())
    final.sort(
        key=lambda x: (
            int(x.get("final_score") or 0),
            _textish(x.get("updated_at") or x.get("created_at") or ""),
        ),
        reverse=True,
    )

    return final[:MEMORY_MAX_ITEMS]

# =========================================================
# MODE DETECTION + SYSTEM PROMPT LOCK
# =========================================================

def detect_request_mode(user_text: str) -> str:
    text = _textish(user_text).lower()

    if any(k in text for k in [
        "error", "traceback", "bug", "fix", "crash", "not working", "exception"
    ]):
        return "debug"

    if any(k in text for k in [
        "code", "function", "script", "python", "javascript", "api", "app.py", "route", "endpoint"
    ]):
        return "coding"

    if any(k in text for k in [
        "plan", "roadmap", "steps", "strategy", "next move", "phase", "priority"
    ]):
        return "planning"

    if any(k in text for k in [
        "write", "rewrite", "story", "book", "paragraph", "email", "message"
    ]):
        return "writing"

    return "general"

def build_route_debug_payload(
    *,
    user_text: str,
    session: dict[str, Any] | None,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> dict[str, Any]:
    mode = detect_request_mode(user_text)
    attachment_items = normalize_attachments(attachments)
    attachment_names = [str(item.get("name") or item.get("filename") or "") for item in attachment_items]

    session_id = ""
    session_title = ""
    if isinstance(session, dict):
        session_id = str(session.get("id") or "")
        session_title = str(session.get("title") or "")

    lowered = _textish(user_text).lower()

    signals: list[str] = []
    if any(k in lowered for k in ["error", "traceback", "bug", "fix", "crash", "exception"]):
        signals.append("debug_terms")
    if any(k in lowered for k in ["code", "python", "javascript", "api", "app.py", "route", "endpoint"]):
        signals.append("coding_terms")
    if any(k in lowered for k in ["plan", "roadmap", "steps", "phase", "priority"]):
        signals.append("planning_terms")
    if any(k in lowered for k in ["write", "rewrite", "story", "book", "email", "message"]):
        signals.append("writing_terms")
    if regenerate_of:
        signals.append("regenerate")
    if attachment_items:
        signals.append("attachments_present")

    return {
        "mode": mode,
        "signals": signals,
        "user_text_preview": summarize_text(_textish(user_text), 160),
        "session_id": session_id,
        "session_title": session_title,
        "attachments_count": len(attachment_items),
        "attachment_names": attachment_names[:6],
        "regenerate_of": str(regenerate_of or ""),
        "timestamp": now_iso(),
    }

def build_mode_system_prompt(mode: str) -> str:
    if mode == "debug":
        return (
            "You are in DEBUG MODE.\n"
            "- Start with the root cause immediately.\n"
            "- Then give the exact fix.\n"
            "- No fluff. No theory unless needed.\n"
            "- Show concrete corrections.\n"
        )

    if mode == "coding":
        return (
            "You are in CODING MODE.\n"
            "- Be implementation-first.\n"
            "- Give full working code when possible.\n"
            "- Avoid explanations unless necessary.\n"
            "- Match user's stack and file structure.\n"
        )

    if mode == "planning":
        return (
            "You are in PLANNING MODE.\n"
            "- Be structured and step-based.\n"
            "- Focus on execution order.\n"
            "- Avoid over-explaining.\n"
        )

    if mode == "writing":
        return (
            "You are in WRITING MODE.\n"
            "- Focus on tone, clarity, and flow.\n"
            "- Match user's voice.\n"
            "- Avoid robotic phrasing.\n"
        )

    return (
        "You are in GENERAL MODE.\n"
        "- Be direct, helpful, and concise.\n"
    )

# =========================================================
# PHASE D.2 — RESPONSE DOMINANCE LOCK
# =========================================================

def enforce_response_dominance(text: str, route: str) -> str:
    t = normalize_text(text).strip()

    if not t:
        return t

    # kill fluff phrases
    fluff = [
        "here's what you can do",
        "it seems like",
        "you might want to",
        "in conclusion",
        "overall,",
    ]

    lowered = t.lower()
    for f in fluff:
        if lowered.startswith(f):
            t = t[len(f):].lstrip(" ,:-")

    # enforce structure for certain routes
    if route == "planning":
        if not re.search(r"\d+\.", t):
            lines = [l.strip() for l in t.split("\n") if l.strip()]
            if len(lines) > 1:
                t = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))

    if route == "debug":
        if "fix" not in lowered:
            t += "\n\nFix:\n- Identify root cause\n- Apply correction\n- Verify outcome"

    # tighten spacing
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()

# =========================================================
# MEMORY EXTRACTION + DURABLE WRITE LOCK
# =========================================================

MEMORY_WRITE_MAX_ITEMS = 200
MEMORY_TEXT_MAX = 300

def _textish(value: Any) -> str:
    return str(value or "").strip()


def _tokenize(value: str) -> list[str]:
    raw = _textish(value).lower()
    parts: list[str] = []
    current: list[str] = []
    for ch in raw:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                parts.append("".join(current))
                current = []
    if current:
        parts.append("".join(current))
    return parts


def _clean_memory_text(text: str) -> str:
    text = normalize_text(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:MEMORY_TEXT_MAX].strip(" -:\t")


def _is_meaningful_memory(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower().strip()

    if len(lowered) < 8:
        return False

    if any(x in lowered for x in ["http://", "https://", "<html", "{", "}"]):
        return False

    junk_exact = {
        "fine", "good", "okay", "ok",
        "tired", "sad", "happy",
        "here", "ready",
    }
    if lowered in junk_exact:
        return False

    return True


def extract_memory_candidates(user_text: str) -> list[dict[str, str]]:
    text = normalize_text(user_text)
    candidates: list[dict[str, str]] = []

    patterns = [
        (r"(?:remember that|note that|from now on)\s+(.*)", "instruction"),
        (r"(?:my name is)\s+(.*)", "profile"),
        (r"(?:i prefer)\s+(.*)", "preference"),
        (r"(?:i want)\s+(.*)", "preference"),
        (r"(?:i am working on|my project is)\s+(.*)", "project"),
    ]

    for pattern, kind in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            cleaned = _clean_memory_text(match)
            if _is_meaningful_memory(cleaned):
                candidates.append({"text": cleaned, "kind": kind})

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in candidates:
        key = _textish(item.get("text")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique

def _memory_kind_priority(kind: str) -> int:
    kind = _textish(kind).lower()
    if kind == "instruction":
        return 5
    if kind == "preference":
        return 4
    if kind == "project":
        return 3
    if kind == "profile":
        return 2
    return 1

def _memory_conflict_key(text: str, kind: str) -> str:
    lowered = _clean_memory_text(text).lower()
    kind = _textish(kind).lower()

    if kind == "preference":
        if any(word in lowered for word in {"concise", "brief", "short"}):
            return "preference:reply_length"
        if any(word in lowered for word in {"detailed", "detail", "longer", "verbose"}):
            return "preference:reply_length"
        if "dark" in lowered and "ui" in lowered:
            return "preference:ui_theme"
        if "light" in lowered and "ui" in lowered:
            return "preference:ui_theme"

    if kind == "instruction":
        if lowered.startswith("always "):
            return "instruction:always"
        if lowered.startswith("never "):
            return "instruction:never"
        if "from now on" in lowered:
            return "instruction:from_now_on"

    if kind == "project":
        if "working on" in lowered or "my project is" in lowered or "nova" in lowered:
            return "project:current_focus"

    return f"{kind}:{lowered}"

def save_memory_items(candidates: list[dict[str, str]], session_id: str) -> None:
    if not candidates:
        return

    existing = safe_list(load_memory())
    now = now_iso()

    ordered_existing = []
    for item in existing:
        if isinstance(item, dict):
            ordered_existing.append(item)

    existing_texts = {
        _clean_memory_text(item.get("text") or "").lower()
        for item in ordered_existing
        if _clean_memory_text(item.get("text") or "")
    }

    conflict_index: dict[str, int] = {}
    for idx, item in enumerate(ordered_existing):
        text = _textish(item.get("text") or "")
        kind = _textish(item.get("kind") or "note")
        key = _memory_conflict_key(text, kind)
        if key:
            conflict_index[key] = idx

    for candidate in candidates:
        text = _clean_memory_text(candidate.get("text") or "")
        kind = _textish(candidate.get("kind") or "note").lower() or "note"

        if not text:
            continue

        lowered = text.lower()
        if lowered in existing_texts:
            continue

        key = _memory_conflict_key(text, kind)

        new_item = {
            "id": make_id("memory"),
            "kind": kind,
            "text": text,
            "source": "assistant",
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
        }

        if key in conflict_index:
            old_idx = conflict_index[key]
            old_item = ordered_existing[old_idx]

            new_item["id"] = old_item.get("id") or new_item["id"]
            new_item["created_at"] = old_item.get("created_at") or now
            ordered_existing[old_idx] = new_item
        else:
            ordered_existing.insert(0, new_item)
            conflict_index[key] = 0

        existing_texts.add(lowered)

    ordered_existing.sort(
        key=lambda item: _textish(item.get("updated_at") or item.get("created_at")),
        reverse=True,
    )

    ordered_existing = ordered_existing[:MEMORY_WRITE_MAX_ITEMS]
    write_json(MEMORY_FILE, ordered_existing)

def _session_keyword_text(session: dict[str, Any]) -> str:
    bits: list[str] = []
    bits.append(_textish(session.get("title")))
    for msg in safe_list(session.get("messages"))[-12:]:
        role = _textish(msg.get("role")).lower()
        if role in {"user", "assistant"}:
            bits.append(_textish(msg.get("content") or msg.get("text")))
    return " ".join(bit for bit in bits if bit)


def _memory_score(
    item: dict[str, Any],
    query_terms: set[str],
    intent_terms: set[str] | None = None,
) -> int:
    text = _textish(item.get("text") or item.get("content") or item.get("body"))
    if not text:
        return -1

    intent_terms = intent_terms or set()

    kind = _textish(item.get("kind")).lower()
    source = _textish(item.get("source")).lower()
    hay_terms = set(_tokenize(text))

    overlap = len(query_terms.intersection(hay_terms))
    intent_overlap = len(intent_terms.intersection({kind} | hay_terms))

    score = overlap * 5
    score += intent_overlap * 10
    score += _memory_kind_priority(kind) * 4

    if source in {"manual", "memory"}:
        score += 3
    elif source == "assistant":
        score += 1

    updated_at = _textish(item.get("updated_at") or item.get("created_at"))
    if updated_at:
        score += 2

    uses = int(item.get("uses") or 1)
    score += min(uses, 8)

    return score


def _detect_memory_intent_terms(user_text: str) -> set[str]:
    lowered = _textish(user_text).lower()

    buckets = {
        "preference": {
            "prefer", "preference", "style", "tone", "voice", "like",
            "want", "settings", "ui", "theme", "dark", "light",
            "concise", "direct", "detailed", "brief",
        },
        "project": {
            "project", "working", "build", "building", "nova", "app",
            "backend", "frontend", "memory", "feature", "roadmap",
        },
        "instruction": {
            "remember", "from now on", "always", "never", "do not",
            "dont", "instruction", "rule",
        },
        "profile": {
            "name", "who am i", "about me", "profile",
        },
    }

    found: set[str] = set()

    for kind, terms in buckets.items():
        if any(term in lowered for term in terms):
            found.add(kind)

    return found


def _reinforce_memory_from_user_text(user_text: str) -> None:
    lowered = _textish(user_text).lower()
    if not lowered:
        return

    memory_items = safe_list(load_memory())
    changed = False

    for item in memory_items:
        if not isinstance(item, dict):
            continue

        text = _textish(item.get("text")).lower()
        if not text:
            continue

        if text in lowered:
            item["uses"] = int(item.get("uses") or 1) + 1
            item["updated_at"] = now_iso()
            changed = True
            continue

        conflict_key = _memory_conflict_key(text, _textish(item.get("kind")))
        if conflict_key == "preference:reply_length":
            if any(word in lowered for word in {"concise", "brief", "short", "detailed", "verbose", "longer"}):
                item["updated_at"] = item.get("updated_at") or item.get("created_at") or now_iso()
                changed = True

    if changed:
        write_json(MEMORY_FILE, memory_items[:MEMORY_WRITE_MAX_ITEMS])


def build_memory_context_block(
    *,
    user_text: str,
    session: dict[str, Any] | None,
) -> str:
    memory_items = safe_list(load_memory())
    if not memory_items:
        return ""

    session = session or {}
    session_text = _session_keyword_text(session)

    query_terms = set(_tokenize(user_text)) | set(_tokenize(session_text))
    intent_terms = _detect_memory_intent_terms(user_text)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in memory_items:
        score = _memory_score(
            item,
            query_terms=query_terms,
            intent_terms=intent_terms,
        )
        if score >= 0:
            ranked.append((score, item))

    ranked.sort(
        key=lambda pair: (
            -pair[0],
            _textish(pair[1].get("updated_at") or pair[1].get("created_at")),
        )
    )

    selected: list[str] = []
    total_chars = 0
    seen_conflict_keys: set[str] = set()

    for score, item in ranked:
        text = _textish(item.get("text") or item.get("content") or item.get("body"))
        if not text:
            continue

        kind = _textish(item.get("kind") or "note").lower()
        conflict_key = _memory_conflict_key(text, kind)
        if conflict_key in seen_conflict_keys:
            continue
        seen_conflict_keys.add(conflict_key)

        prefix = {
            "preference": "[Preference]",
            "project": "[Project]",
            "instruction": "[Instruction]",
            "profile": "[Profile]",
        }.get(kind, "[Note]")

        line = f"- {prefix} {text}"
        next_len = total_chars + len(line) + 1

        if selected and next_len > MEMORY_MAX_CHARS:
            break
        if len(selected) >= MEMORY_MAX_ITEMS:
            break

        selected.append(line)
        total_chars = next_len

    if not selected:
        return ""

    return "Relevant memory for this request:\n" + "\n".join(selected)


def build_attachment_context_block(attachments: list[dict[str, Any]] | None) -> str:
    normalized = normalize_attachments(attachments)
    if not normalized:
        return ""

    selected = normalized[:ATTACHMENT_CONTEXT_MAX_ITEMS]
    lines: list[str] = []

    for item in selected:
        label = _textish(item.get("filename") or item.get("name") or "Attachment")
        mime_type = _textish(item.get("mime_type") or "application/octet-stream")
        size = int(item.get("size") or 0)
        size_text = f"{size} bytes" if size > 0 else "size unknown"
        lines.append(f"- {label} ({mime_type}, {size_text})")

    return "Attachments for this request:\n" + "\n".join(lines)

# =========================================================
# RESPONSE FORMATTING LOCK
# =========================================================

def _detect_response_format_mode(user_text: str) -> str:
    text = _textish(user_text).lower()

    if any(k in text for k in {
        "error", "traceback", "bug", "fix", "debug", "crash", "exception"
    }):
        return "debug"

    if any(k in text for k in {
        "code", "app.py", "python", "javascript", "function", "class", "api", "file"
    }):
        return "coding"

    if any(k in text for k in {
        "plan", "roadmap", "phase", "steps", "strategy", "next move"
    }):
        return "planning"

    if any(k in text for k in {
        "write", "rewrite", "story", "book", "paragraph", "email", "message"
    }):
        return "writing"

    return "general"

def build_response_formatting_block(
    *,
    user_text: str,
    session: dict[str, Any] | None,
) -> str:
    mode = _detect_response_format_mode(user_text)
    lowered = _textish(user_text).lower()

    wants_tldr = "tldr" in lowered or "tl;dr" in lowered
    wants_full_file = "full file" in lowered or "smff" in lowered
    wants_steps = "steps" in lowered or "step by step" in lowered
    wants_short = any(term in lowered for term in {"short", "brief", "quick", "concise", "direct"})
    wants_detail = any(term in lowered for term in {"detailed", "in depth", "deep dive", "full breakdown"})

    lines: list[str] = [
        "- Match the user's stored style preferences when relevant.",
        "- Prefer clean formatting over long walls of text.",
        "- Lead with the answer, action, or fix first.",
        "- Do not waste space repeating the user's question.",
        "- Do not sound robotic, corporate, or over-polished.",
        "- Use only enough structure to make execution faster and clearer.",
    ]

    if mode == "debug":
        lines.extend(
            [
                "- Debug format:",
                "  1. Root cause",
                "  2. Exact fix",
                "  3. What to test next",
                "- Be diagnosis-first.",
                "- Name the broken area clearly.",
                "- If code is needed, give the corrected block directly.",
            ]
        )
    elif mode == "coding":
        lines.extend(
            [
                "- Coding format:",
                "  1. TLDR",
                "  2. File path",
                "  3. Full code or exact replacement",
                "- Prefer implementation-first output.",
                "- Avoid long theory unless the user explicitly asks.",
            ]
        )
    elif mode == "planning":
        lines.extend(
            [
                "- Planning format:",
                "  1. TLDR",
                "  2. Phase / priority",
                "  3. Ordered next moves",
                "- Keep the plan tight and executable.",
            ]
        )
    elif mode == "writing":
        lines.extend(
            [
                "- Writing format:",
                "- Optimize for clarity, flow, and voice.",
                "- Keep tone natural and non-generic.",
                "- Do not over-structure unless the user asks.",
            ]
        )
    else:
        lines.extend(
            [
                "- General format:",
                "- Be direct, clean, and concise.",
                "- Use light structure only when it improves speed and clarity.",
            ]
        )

    if wants_tldr:
        lines.append("- Include a short TLDR at the top.")

    if wants_full_file:
        lines.append("- The user wants a real full-file style answer, not partial snippets.")

    if wants_steps:
        lines.append("- Use numbered steps where that makes execution easier.")

    if wants_short and not wants_detail:
        lines.append("- Keep the answer tight. Trim filler and optional explanation.")

    if wants_detail:
        lines.append("- The user asked for more depth. Expand, but stay structured and useful.")

    return "Response formatting rules for this request:\n" + "\n".join(lines)

# =========================================================
# RESPONSE QUALITY CONTROL LOCK
# =========================================================

def _canonical_response_route(route: str) -> str:
    route = _textish(route).lower()

    if route in {"debug", "fix", "error"}:
        return "debug"

    if route in {"code", "coding", "implementation", "dev"}:
        return "code"

    if route in {"plan", "planning", "roadmap", "strategy"}:
        return "plan"

    if route in {"write", "writing", "rewrite"}:
        return "write"

    return "general"

def build_response_quality_block(
    *,
    route_result: dict[str, Any] | None,
    user_text: str,
) -> str:
    raw_route = (
        (route_result or {}).get("primary")
        or (route_result or {}).get("mode")
        or detect_request_mode(user_text)
        or "general"
    )
    route = _canonical_response_route(raw_route)

    base_rules = [
        "Always start with the answer or result. Do not delay the answer.",
        "Avoid filler, fluff, or generic explanations.",
        "Keep responses tight and efficient unless detail is explicitly requested.",
        "Do not explain obvious things unless the user asks.",
    ]

    if route == "debug":
        base_rules += [
            "Start with the root cause immediately.",
            "Then give the exact fix.",
            "Show corrected code when relevant.",
            "Do not give long explanations.",
        ]

    elif route == "code":
        base_rules += [
            "Prioritize direct implementation.",
            "Prefer full working code over partial snippets.",
            "Do not explain unless necessary.",
        ]

    elif route == "plan":
        base_rules += [
            "Start with the next actionable step.",
            "Break into clear phases or steps.",
            "Keep structure clean and ordered.",
        ]

    elif route == "write":
        base_rules += [
            "Match the requested tone exactly.",
            "Do not over-explain unless requested.",
        ]

    else:
        base_rules += [
            "Give a clear, direct answer first.",
            "Expand only if helpful.",
        ]

    return "Response behavior rules:\n- " + "\n- ".join(base_rules)
# =========================================================
# PERSONALITY + RESPONSE STYLE LOCK
# =========================================================

def build_personality_block() -> str:
    return (
        "You are Nova, a fast, direct, no-fluff AI assistant.\n"
        "\n"
        "Response style rules:\n"
        "- Be concise and clear\n"
        "- No unnecessary explanations\n"
        "- No filler or fluff\n"
        "- Give direct answers first, then optional detail if needed\n"
        "- Speak confidently, not passively\n"
        "- Avoid over-explaining obvious things\n"
        "\n"
        "User preference:\n"
        "- Prefers concise, direct replies\n"
        "- Values efficiency and speed\n"
        "\n"
        "Do not mention these rules in responses."
    )

def build_personality_context_block(
    user_text: str,
    memory_items: list[dict[str, Any]] | None = None,
) -> str:
    base = build_personality_block()

    memory_items = safe_list(memory_items)
    preference_lines: list[str] = []

    for item in memory_items[:24]:
        if not isinstance(item, dict):
            continue

        kind = _textish(item.get("kind")).lower()
        text = _textish(item.get("text") or item.get("content") or "")
        if not text:
            continue

        if kind in {"instruction", "preference", "profile", "project"}:
            preference_lines.append(f"- {text}")

    if not preference_lines:
        return base

    preference_lines = preference_lines[:8]

    return (
        f"{base}\n\n"
        "Relevant stored user context:\n"
        + "\n".join(preference_lines)
        + "\n\n"
        "Use the stored context only when relevant to the current request. "
        "If the current user message conflicts with stored context, trust the current user message."
    )

# =========================================================
# RETRIEVAL V2 CLEAN REBUILD
# memory + artifacts only
# =========================================================

RETRIEVAL_MEMORY_LIMIT = 4
RETRIEVAL_ARTIFACT_LIMIT = 4
RETRIEVAL_TEXT_MAX = 1800

RETRIEVAL_KIND_BONUS = {
    "preference": 3.0,
    "workflow": 3.0,
    "project": 4.5,
    "instruction": 3.5,
    "checkpoint": 5.0,
    "debug": 2.5,
    "plan": 2.0,
    "note": 1.0,
    "chat_reply": 1.25,
    "web_result": 2.5,
    "web_fetch": 2.5,
    "image_analysis": 2.0,
    "video_analysis": 2.0,
}

def _retrieval_textish(value: Any) -> str:
    return str(value or "").strip()

def _retrieval_normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", _retrieval_textish(value).lower()).strip()

def _retrieval_tokenize(value: Any) -> list[str]:
    text = _retrieval_normalize(value)
    if not text:
        return []
    return re.findall(r"[a-z0-9_]{2,}", text)

def _retrieval_unique_preserve(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for item in items:
        cleaned = _retrieval_textish(item)
        key = _retrieval_normalize(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(cleaned)

    return out

def _retrieval_query_terms(user_text: str) -> list[str]:
    base = _retrieval_tokenize(user_text)
    boosted: list[str] = list(base)

    phrase_hints = [
        "web fetch",
        "video support",
        "video analysis",
        "memory",
        "artifacts",
        "retrieval",
        "checkpoint",
        "session",
        "brain",
        "router",
        "nova",
    ]

    lowered = _retrieval_normalize(user_text)
    for phrase in phrase_hints:
        if phrase in lowered:
            boosted.extend(_retrieval_tokenize(phrase))

    return _retrieval_unique_preserve(boosted)

def _retrieval_keyword_overlap_score(query_terms: list[str], text: str) -> float:
    query_set = set(_retrieval_tokenize(" ".join(query_terms)))
    text_set = set(_retrieval_tokenize(text))
    if not query_set or not text_set:
        return 0.0
    return float(len(query_set.intersection(text_set)))

def _retrieval_exact_phrase_bonus(user_text: str, text: str) -> float:
    query = _retrieval_normalize(user_text)
    body = _retrieval_normalize(text)
    if not query or not body:
        return 0.0

    bonus = 0.0

    if query in body:
        bonus += 8.0

    for phrase in re.findall(r'"([^"]+)"', user_text or ""):
        normalized_phrase = _retrieval_normalize(phrase)
        if normalized_phrase and normalized_phrase in body:
            bonus += 8.0

    common_phrases = [
        "web fetch",
        "video support",
        "video analysis",
        "memory",
        "artifacts",
        "retrieval",
        "checkpoint",
        "brain",
        "nova",
    ]

    for phrase in common_phrases:
        if phrase in query and phrase in body:
            bonus += 4.0

    return bonus

def _retrieval_same_session_bonus(item: dict[str, Any], session_id: str | None) -> float:
    item_session_id = str(item.get("session_id") or "").strip()
    target_session_id = str(session_id or "").strip()
    if item_session_id and target_session_id and item_session_id == target_session_id:
        return 3.0
    return 0.0

def _retrieval_query_intent_bonus(user_text: str, text: str, kind: str) -> float:
    q = _retrieval_normalize(user_text)
    t = _retrieval_normalize(text)
    k = _retrieval_normalize(kind)

    bonus = 0.0

    debug_words = ["bug", "error", "traceback", "fix", "broken", "crash", "issue"]
    project_words = ["nova", "memory", "retrieval", "web fetch", "router", "checkpoint", "phase"]
    preference_words = ["prefer", "style", "reply style", "tone", "short answers", "concise"]
    web_words = ["url", "website", "web", "fetch", "link", "page"]

    if any(word in q for word in debug_words):
        if k in {"debug", "checkpoint"}:
            bonus += 4.0
        if any(word in t for word in debug_words):
            bonus += 2.0

    if any(word in q for word in project_words):
        if k in {"project", "checkpoint", "plan", "debug"}:
            bonus += 3.5
        if any(word in t for word in project_words):
            bonus += 1.5

    if any(word in q for word in preference_words):
        if k in {"preference", "instruction"}:
            bonus += 4.0

    if any(word in q for word in web_words):
        if k in {"web_result", "web_fetch"}:
            bonus += 3.0

    return bonus

def _retrieval_text_quality_bonus(text: str, kind: str) -> float:
    body = _retrieval_textish(text)
    k = _retrieval_normalize(kind)

    if not body:
        return 0.0

    bonus = 0.0
    length = len(body)

    if 80 <= length <= 1400:
        bonus += 1.5
    elif 25 <= length < 80:
        bonus += 0.5
    elif length > 1400:
        bonus += 0.25

    if "\n" in body:
        bonus += 0.5

    if k in {"project", "checkpoint", "preference", "instruction", "web_result"}:
        bonus += 0.75

    return bonus

def _retrieval_recency_bonus(item: dict[str, Any]) -> float:
    stamp = _retrieval_textish(item.get("updated_at") or item.get("created_at"))
    if not stamp:
        return 0.0

    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_seconds = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return 0.0

    age_days = age_seconds / 86400.0

    if age_days <= 1:
        return 3.0
    if age_days <= 7:
        return 2.0
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.35
    return 0.0

def _retrieval_kind_bonus(kind: str) -> float:
    return float(RETRIEVAL_KIND_BONUS.get(_retrieval_normalize(kind), 0.0))

def _retrieval_memory_text(item: dict[str, Any]) -> str:
    parts = [
        _retrieval_textish(item.get("text")),
        _retrieval_textish(item.get("summary")),
        _retrieval_textish(item.get("preview")),
        _retrieval_textish(item.get("title")),
    ]
    return " | ".join([p for p in parts if p])

def _retrieval_artifact_text(item: dict[str, Any]) -> str:
    viewer = item.get("viewer") if isinstance(item.get("viewer"), dict) else {}
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}

    parts = [
        _retrieval_textish(item.get("title")),
        _retrieval_textish(item.get("kind")),
        _retrieval_textish(item.get("preview")),
        _retrieval_textish(item.get("body")),
        _retrieval_textish(item.get("content")),
        _retrieval_textish(item.get("summary")),
        _retrieval_textish(item.get("analysis_text")),
        _retrieval_textish(viewer.get("title")),
        _retrieval_textish(viewer.get("body")),
        _retrieval_textish(viewer.get("analysis_text")),
        _retrieval_textish(meta.get("source_url")),
        _retrieval_textish(meta.get("url")),
    ]
    return " | ".join([p for p in parts if p])

def _retrieval_trim_line(text: str, max_len: int = 220) -> str:
    value = re.sub(r"\s+", " ", _retrieval_textish(text)).strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 3].rstrip() + "..."

def _render_retrieved_memory_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""

    lines = ["RETRIEVED MEMORY"]
    for item in items:
        text = _retrieval_memory_text(item)
        line = _retrieval_trim_line(text, 200)
        if not line:
            continue
        lines.append(f"- {line}")

    return "\n".join(lines) if len(lines) > 1 else ""

def _render_retrieved_artifacts_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""

    lines = ["RETRIEVED ARTIFACTS"]
    for item in items:
        kind = _retrieval_textish(item.get("kind")) or "artifact"
        when = _retrieval_textish(item.get("updated_at") or item.get("created_at"))
        text = _retrieval_artifact_text(item)
        line = _retrieval_trim_line(text, 220)
        if not line:
            continue

        prefix = "- "
        if when:
            prefix += f"{when} "
        if kind:
            prefix += f"[{kind}] "

        lines.append(prefix + line)

    return "\n".join(lines) if len(lines) > 1 else ""

def _retrieval_limit_text(text: str, max_len: int = RETRIEVAL_TEXT_MAX) -> str:
    value = _retrieval_textish(text)
    if len(value) <= max_len:
        return value
    return value[:max_len].rstrip() + "\n..."

def build_retrieval_context(user_text: str, session_id: str | None) -> dict[str, Any]:
    query_terms = _retrieval_query_terms(user_text)

    all_memory = [
        item for item in safe_list(load_memory())
        if isinstance(item, dict)
    ]
    all_artifacts = [
        item for item in safe_list(load_artifacts())
        if isinstance(item, dict)
    ]

    scored_memory: list[dict[str, Any]] = []
    for item in all_memory:
        text = _retrieval_memory_text(item)
        kind = _retrieval_textish(item.get("kind"))

        if not text:
            continue

        keyword_overlap = _retrieval_keyword_overlap_score(query_terms, text)
        exact_phrase = _retrieval_exact_phrase_bonus(user_text, text)
        same_session = _retrieval_same_session_bonus(item, session_id)
        recency_bonus = _retrieval_recency_bonus(item)
        kind_bonus = _retrieval_kind_bonus(kind)
        intent_bonus = _retrieval_query_intent_bonus(user_text, text, kind)
        quality_bonus = _retrieval_text_quality_bonus(text, kind)

        score = (
            (keyword_overlap * 4.0)
            + exact_phrase
            + (same_session * 1.5)
            + (recency_bonus * 1.5)
            + (kind_bonus * 1.75)
            + intent_bonus
            + quality_bonus
        )

        if score <= 0:
            continue

        scored_memory.append(
            {
                "item": item,
                "score": float(score),
                "text": text,
                "kind": kind,
                "components": {
                    "keyword_overlap": keyword_overlap,
                    "exact_phrase_bonus": exact_phrase,
                    "same_session_bonus": same_session,
                    "recency_bonus": recency_bonus,
                    "kind_bonus": kind_bonus,
                    "intent_bonus": intent_bonus,
                    "quality_bonus": quality_bonus,
                },
            }
        )

    scored_artifacts: list[dict[str, Any]] = []
    for item in all_artifacts:
        text = _retrieval_artifact_text(item)
        kind = _retrieval_textish(
            item.get("kind")
            or ((item.get("viewer") or {}).get("kind") if isinstance(item.get("viewer"), dict) else "")
        )

        if not text:
            continue

        keyword_overlap = _retrieval_keyword_overlap_score(query_terms, text)
        exact_phrase = _retrieval_exact_phrase_bonus(user_text, text)
        same_session = _retrieval_same_session_bonus(item, session_id)
        recency_bonus = _retrieval_recency_bonus(item)
        kind_bonus = _retrieval_kind_bonus(kind)
        intent_bonus = _retrieval_query_intent_bonus(user_text, text, kind)
        quality_bonus = _retrieval_text_quality_bonus(text, kind)

        score = (
            (keyword_overlap * 4.0)
            + exact_phrase
            + (same_session * 1.5)
            + (recency_bonus * 1.5)
            + (kind_bonus * 1.75)
            + intent_bonus
            + quality_bonus
        )

        if score <= 0:
            continue

        scored_artifacts.append(
            {
                "item": item,
                "score": float(score),
                "text": text,
                "kind": kind,
                "components": {
                    "keyword_overlap": keyword_overlap,
                    "exact_phrase_bonus": exact_phrase,
                    "same_session_bonus": same_session,
                    "recency_bonus": recency_bonus,
                    "kind_bonus": kind_bonus,
                    "intent_bonus": intent_bonus,
                    "quality_bonus": quality_bonus,
                },
            }
        )

    scored_memory.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    scored_artifacts.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)

    selected_memory: list[dict[str, Any]] = []
    selected_artifacts: list[dict[str, Any]] = []
    selected_texts: list[str] = []

    for entry in scored_memory[:RETRIEVAL_MEMORY_LIMIT]:
        text_key = _retrieval_normalize(entry["text"])
        if text_key and text_key not in selected_texts:
            selected_memory.append(entry["item"])
            selected_texts.append(text_key)

    for entry in scored_artifacts[:RETRIEVAL_ARTIFACT_LIMIT]:
        text_key = _retrieval_normalize(entry["text"])
        if text_key and text_key not in selected_texts:
            selected_artifacts.append(entry["item"])
            selected_texts.append(text_key)

    memory_text = _render_retrieved_memory_block(selected_memory)
    artifact_text = _render_retrieved_artifacts_block(selected_artifacts)

    combined_parts = [part for part in [memory_text, artifact_text] if _retrieval_textish(part)]
    combined_text = _retrieval_limit_text("\n\n".join(combined_parts))

    return {
        "memory_items": selected_memory,
        "artifact_items": selected_artifacts,
        "memory_text": memory_text,
        "artifact_text": artifact_text,
        "combined_text": combined_text,
        "debug": {
            "query_terms": query_terms,
            "memory_selected_count": len(selected_memory),
            "artifact_selected_count": len(selected_artifacts),
            "memory_ids": [str(item.get("id") or "") for item in selected_memory],
            "artifact_ids": [str(item.get("id") or "") for item in selected_artifacts],
            "memory_scores": [
                {
                    "id": str(x["item"].get("id") or ""),
                    "kind": x["kind"],
                    "score": round(float(x["score"]), 3),
                    "components": x["components"],
                }
                for x in scored_memory[:RETRIEVAL_MEMORY_LIMIT]
            ],
            "artifact_scores": [
                {
                    "id": str(x["item"].get("id") or ""),
                    "kind": x["kind"],
                    "score": round(float(x["score"]), 3),
                    "components": x["components"],
                }
                for x in scored_artifacts[:RETRIEVAL_ARTIFACT_LIMIT]
            ],
        },
    }

def build_retrieval_debug(session: dict[str, Any], user_text: str) -> dict[str, Any]:
    try:
        ctx = build_retrieval_context(
            user_text=user_text,
            session_id=str((session or {}).get("id") or ""),
        )
        return ctx.get("debug") if isinstance(ctx.get("debug"), dict) else {}
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc) or "retrieval_debug_failed",
        }

def build_messages_for_model(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
    memory_block: str = "",
    route_result: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    model_messages: list[dict[str, str]] = []

    mode = str((route_result or {}).get("primary") or "general").strip().lower()
    mode_prompt = build_mode_system_prompt(mode)
    if mode_prompt:
        model_messages.append(
            {
                "role": "system",
                "content": mode_prompt,
            }
        )

    quality_block = build_response_style_block(
        route_result=route_result,
        user_text=user_text,
    )
    if quality_block:
        model_messages.append(
            {
                "role": "system",
                "content": quality_block,
            }
        )

    retrieval = build_retrieval_context(
        user_text=user_text,
        session_id=str(session.get("id") or ""),
    )

    injected_retrieval = _retrieval_textish(retrieval.get("combined_text"))
    injected_memory = _retrieval_textish(memory_block)

    if injected_memory and injected_retrieval:
        injected_context = injected_memory + "\n\n" + injected_retrieval
    elif injected_memory:
        injected_context = injected_memory
    else:
        injected_context = injected_retrieval

    if injected_context:
        model_messages.append(
            {
                "role": "system",
                "content": (
                    "Use the following durable context only when relevant. "
                    "Prefer relevance over volume. "
                    "Do not mention retrieval explicitly unless the user asks.\n\n"
                    f"{injected_context}"
                ),
            }
        )

    attachment_block = build_attachment_context_block(attachments)
    if attachment_block:
        model_messages.append(
            {
                "role": "system",
                "content": attachment_block,
            }
        )

    recent_messages = session_messages(session)
    for msg in recent_messages[-12:]:
        role = "assistant" if str(msg.get("role")) == "assistant" else "user"
        text = _retrieval_textish(msg.get("text"))
        if not text:
            continue
        model_messages.append(
            {
                "role": role,
                "content": text,
            }
        )

    current_user_parts: list[str] = []
    if _retrieval_textish(user_text):
        current_user_parts.append(_retrieval_textish(user_text))

    attachment_user_block = build_attachment_user_block(attachments)
    if attachment_user_block:
        current_user_parts.append(attachment_user_block)

    final_user_text = "\n\n".join([part for part in current_user_parts if part.strip()]).strip()
    if not final_user_text:
        final_user_text = "(no user text provided)"

    model_messages.append(
        {
            "role": "user",
            "content": final_user_text,
        }
    )

    return model_messages

def build_retrieval_debug(
    session: dict[str, Any],
    user_text: str,
) -> dict[str, Any]:
    retrieval = build_retrieval_context(
        user_text=user_text,
        session_id=str(session.get("id") or ""),
    )
    return retrieval.get("debug") or {}

def _extract_style_preferences(memory_items: list[dict[str, Any]]) -> list[str]:
    if not memory_items:
        return []

    def _normalize(text: str) -> str:
        return _textish(text).strip()

    def _key(text: str) -> str:
        t = _textish(text).lower()

        # 🔥 length conflict
        if any(w in t for w in {"short", "brief", "concise", "tight"}):
            return "length"
        if any(w in t for w in {"long", "detailed", "in depth", "deep dive", "verbose"}):
            return "length"

        # 🔥 tone
        if "direct" in t:
            return "tone"
        if any(w in t for w in {"gentle", "soft"}):
            return "tone"

        # 🔥 format
        if "powershell" in t:
            return "shell"
        if any(w in t for w in {"full file", "full-file", "smff"}):
            return "format"
        if any(w in t for w in {"steps", "step by step"}):
            return "format"

        # 🔥 fallback
        return f"raw:{t}"

    ordered = sorted(
        safe_list(memory_items),
        key=lambda x: _textish(x.get("updated_at") or x.get("created_at")),
        reverse=True,
    )

    winners: dict[str, str] = {}

    for item in ordered:
        if _textish(item.get("kind")).lower() != "preference":
            continue

        text = _normalize(item.get("text") or "")
        if not text:
            continue

        k = _key(text)

        # newest wins
        if k not in winners:
            winners[k] = text

    return list(winners.values())

def local_fallback_response(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> str:
    if regenerate_of:
        target = find_message(session, regenerate_of)
        target_text = message_text(target or {})
        return (
            "Regenerated response.\n\n"
            f"Target message preview:\n{target_text[:500]}\n\n"
            "No live model is configured, so this is the local fallback path."
        )

    attachment_block = build_attachment_context_block(attachments)
    attachment_suffix = f"\n\n{attachment_block}" if attachment_block else ""
    previous_user_count = sum(1 for m in session_messages(session) if str(m.get("role")) == "user")

    if normalize_text(user_text).strip():
        return (
            f"You said:\n{normalize_text(user_text)}"
            f"{attachment_suffix}\n\n"
            f"This is local fallback reply #{previous_user_count} because no live model is configured."
        )

    return (
        "You sent attachments without text."
        f"{attachment_suffix}\n\n"
        f"This is local fallback reply #{previous_user_count} because no live model is configured."
    )


def build_personality_context_block(user_text: str, memory_items: list[dict[str, Any]]) -> str:
    lines = [
        "- Be concise and direct",
        "- No fluff",
        "- Solution first",
        "- Match user's tone",
    ]

    for item in memory_items:
        text = str(item.get("text") or "").lower()
        if "prefer" in text or "style" in text:
            lines.append(f"- {item.get('text')}")

    return "Assistant behavior:\n" + "\n".join(lines)

def stream_model_text(
    session: dict[str, Any],
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
    memory_block: str = "",
    route_result: dict[str, Any] | None = None,
) -> Generator[str, None, None]:

    # =========================================================
    # 🔥 D5 — ONE SOURCE OF TRUTH
    # =========================================================

    payload = build_model_payload(
        session=session,
        user_text=user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
    )

    route_result = payload["route_result"]
    route = payload["route"]
    memory_selection = payload["memory_selection"]
    memory_block = payload["memory_block"]
    execution = payload["execution"]
    execution_context = payload["execution_context"]
    model_messages = payload["model_messages"]

    if OPENAI_CLIENT is None:
        fallback_text = local_fallback_response(
            user_text=user_text,
            attachments=attachments,
        )
        yield fallback_text
        return

    stream = OPENAI_CLIENT.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        messages=model_messages,
        stream=True,
    )

    for chunk in stream:
        try:
            delta = chunk.choices[0].delta
            token = getattr(delta, "content", None)
        except Exception:
            token = None

        if not token:
            continue

        yield token


# =========================================================
# STREAM CONTRACT LOCK
# =========================================================

def build_video_analysis_result(
    *,
    attachments: list[dict[str, Any]] | None,
    user_text: str,
) -> dict[str, Any]:
    videos = []

    for item in safe_list(attachments):
        if not isinstance(item, dict):
            continue

        mime_type = str(item.get("mime_type") or item.get("mime") or "").strip()
        name = str(item.get("name") or item.get("filename") or "").strip()
        url = str(item.get("url") or item.get("path") or "").strip()
        kind = str(item.get("kind") or item.get("type") or "").lower().strip()

        is_video = False
        if "video" in kind:
            is_video = True
        elif mime_type.startswith("video/"):
            is_video = True
        elif name.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".avi")):
            is_video = True
        elif url.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".avi")):
            is_video = True

        if not is_video:
            continue

        if url and not url.startswith("/api/uploads/"):
            safe_name = Path(url).name.strip()
            if safe_name:
                url = f"/api/uploads/{safe_name}"

        try:
            size_int = int(item.get("size") or 0)
        except Exception:
            size_int = 0

        videos.append(
            {
                "url": url,
                "name": name or Path(url).name.strip() or "video",
                "mime_type": mime_type or "video/mp4",
                "size": size_int,
            }
        )

    if not videos:
        return {
            "ok": False,
            "error": "No video attachment found.",
            "summary": "",
            "analysis_text": "",
            "videos": [],
            "bullets": [],
        }

    prompt = normalize_text(user_text).strip()
    first_video = videos[0]
    video_name = str(first_video.get("name") or "video").strip()

    bullets = [
        f"Video file received: {video_name}",
        f"Detected {len(videos)} video attachment(s)",
    ]

    if prompt:
        analysis_text = (
            f"Video received for analysis.\n\n"
            f"User request: {prompt}\n\n"
            f"I can confirm the upload and preserve the video in chat and artifacts. "
            f"Deeper frame-level understanding can be layered in later without breaking this pipeline."
        )
    else:
        analysis_text = (
            "Video received for analysis.\n\n"
            "The upload has been preserved and attached to this session."
        )

    summary = normalize_text(analysis_text).strip()
    if not summary:
        summary = "Video received and analyzed."

    return {
        "ok": True,
        "summary": summary,
        "analysis_text": analysis_text,
        "videos": videos,
        "bullets": bullets,
    }

def chat_stream_generator(

    *,
    session_id: str,
    user_text: str,
    attachments: list[dict[str, Any]] | None,
    regenerate_of: str | None,
) -> Generator[str, None, None]:

    store = load_sessions_store()
    session = find_session(store, session_id)
    if not session:
        session = ensure_active_session(store)

    locked_session_id = str(session.get("id") or session_id or "")
    attachments = normalize_attachments(attachments)

    target_message = find_message(session, regenerate_of) if regenerate_of else None
    assistant_message_id = (target_message or {}).get("id") if target_message else make_id("assistant")
    assistant_created_at = now_iso()

    started = False
    refined_text = ""

    if not regenerate_of and (normalize_text(user_text).strip() or attachments):
        append_message(session, make_user_message(user_text, attachments))

    try:
        candidates = extract_memory_candidates(user_text)
        save_memory_items(candidates, locked_session_id)
    except Exception:
        pass

    # =========================================================
    # 🌍 CURRENT INFO AUTO ROUTE
    # =========================================================
    if detect_tool_intent(user_text) == "current_info":
        try:
            current_info = answer_current_info_query(user_text)

            if not current_info.get("ok"):
                yield sse({
                    "type": "error",
                    "ok": False,
                    "session_id": locked_session_id,
                    "message_id": assistant_message_id,
                    "assistant_message_id": assistant_message_id,
                    "error": current_info.get("error") or "Current-info lookup failed.",
                    "debug": {
                        "tool": "current_info",
                        "query": user_text,
                    },
                })
                return

            msg = make_assistant_message(
                normalize_text(current_info.get("text") or "").strip() or "No live answer generated.",
                message_id=assistant_message_id,
                source="web_fetch",
                meta=build_current_info_meta(current_info),
            )

            append_message(session, msg)

            try:
                save_artifact_from_assistant(msg, session["id"])
            except Exception:
                pass

            yield sse({
                "type": "final",
                "ok": True,
                "session_id": locked_session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "message": msg,
                "messages": session_messages(session),
                "artifacts": load_artifacts(),
                "memory": load_memory(),
                "debug": {
                    "tool": "current_info",
                    "query": current_info.get("query") or user_text,
                    "source_count": len(safe_list(current_info.get("sources"))),
                },
            })
            return

        except Exception as exc:
            yield sse({
                "type": "error",
                "ok": False,
                "session_id": locked_session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "error": str(exc) or "Current-info route failed.",
                "debug": {
                    "tool": "current_info",
                    "query": user_text,
                },
            })
            return

    # =========================================================
    # 🌐 WEB AUTO ROUTE (PASS LOCK)
    # =========================================================

    if should_route_to_web(user_text):
        try:
            url = normalize_url_input(user_text)

            if not url:
                yield sse({
                    "type": "error",
                    "ok": False,
                    "session_id": locked_session_id,
                    "error": "Invalid URL",
                })
                return

            result = fetch_web(url)

            if not result.get("ok"):
                yield sse({
                    "type": "error",
                    "ok": False,
                    "session_id": locked_session_id,
                    "error": result.get("error") or "Web fetch failed.",
                    "debug": {
                        "tool": "web",
                        "url": result.get("url") or url,
                    },
                })
                return

            text = build_web_result_text(result)
            meta = build_web_result_meta(result)

            msg = make_assistant_message(
                text,
                message_id=assistant_message_id,
                source="web_fetch",
                meta=meta,
            )

            append_message(session, msg)

            try:
                save_artifact_from_assistant(msg, session["id"])
            except Exception:
                pass

            yield sse({
                "type": "final",
                "ok": True,
                "session_id": locked_session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "message": msg,
                "messages": session_messages(session),
                "artifacts": load_artifacts(),
                "memory": load_memory(),
                "debug": {
                    "tool": "web",
                    "url": result.get("url") or url,
                    "status_code": int(result.get("status_code") or 0),
                    "ssl_verified": bool(result.get("ssl_verified")),
                },
            })
            return

        except Exception as exc:
            yield sse({
                "type": "error",
                "ok": False,
                "session_id": locked_session_id,
                "error": str(exc) or "Web fetch failed.",
                "debug": {"tool": "web"},
            })
            return

    started = False
    refined_text = ""

    # -------------------------
    # VIDEO TOOL (STREAM)
    # -------------------------
    if has_video(attachments):
        try:
            video_result = build_video_analysis_result(
                attachments=attachments,
                user_text=user_text,
            )

            if not video_result.get("ok"):
                yield sse(
                    {
                        "type": "error",
                        "ok": False,
                        "session_id": locked_session_id,
                        "message_id": assistant_message_id,
                        "assistant_message_id": assistant_message_id,
                        "error": video_result.get("error") or "Video analysis failed.",
                        "debug": {"tool": "video"},
                    }
                )
                return

            videos = safe_list(video_result.get("videos"))
            summary = normalize_text(video_result.get("summary") or "").strip()
            analysis_text = normalize_text(video_result.get("analysis_text") or "").strip()
            bullets = safe_list(video_result.get("bullets"))

            video_url = ""
            if videos:
                first_video = videos[0] if isinstance(videos[0], dict) else {}
                raw_url = normalize_text(first_video.get("url") or "").strip()
                raw_name = normalize_text(
                    first_video.get("stored_name")
                    or first_video.get("stored_filename")
                    or first_video.get("filename")
                    or first_video.get("name")
                    or ""
                ).strip()

                if raw_url.startswith("/api/uploads/"):
                    video_url = raw_url
                else:
                    safe_name = Path(raw_url).name.strip() if raw_url else ""
                    chosen_name = raw_name or safe_name
                    if chosen_name:
                        video_url = f"/api/uploads/{chosen_name}"

            msg = make_assistant_message(
                summary or analysis_text or "Video received.",
                message_id=assistant_message_id,
                source="video_analysis",
                meta={
                    "analysis_text": analysis_text,
                    "bullets": bullets,
                    "videos": videos,
                    "video_url": video_url,
                },
            )

            append_message(session, msg)

            try:
                save_artifact_from_assistant(msg, session["id"])
            except Exception:
                pass

            yield sse(
                {
                    "type": "final",
                    "ok": True,
                    "session_id": locked_session_id,
                    "message_id": assistant_message_id,
                    "assistant_message_id": assistant_message_id,
                    "message": msg,
                    "messages": session_messages(session),
                    "artifacts": load_artifacts(),
                    "memory": load_memory(),
                    "debug": {"tool": "video"},
                }
            )
            return

        except Exception as exc:
            yield sse(
                {
                    "type": "error",
                    "ok": False,
                    "session_id": locked_session_id,
                    "message_id": assistant_message_id,
                    "assistant_message_id": assistant_message_id,
                    "error": str(exc),
                    "debug": {"tool": "video"},
                }
            )
            return

    # NORMAL CHAT CONTINUES BELOW HERE

    try:

        # =========================================================
        # 🔥 D5 — ONE SOURCE OF TRUTH
        # =========================================================
        payload = build_model_payload(
            session=session,
            user_text=user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
        )

        route_result = payload["route_result"]
        route = payload["route"]
        memory_selection = payload["memory_selection"]
        memory_block = payload["memory_block"]

        for token in stream_model_text(
            session=session,
            user_text=user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
            memory_block=memory_block,
            route_result=route_result,
        ):
            if not started:
                started = True
                yield sse(
                    {
                        "type": "start",
                        "ok": True,
                        "session_id": locked_session_id,
                        "message_id": assistant_message_id,
                        "assistant_message_id": assistant_message_id,
                        "debug": {
                            "route_build": "phase-d5-one-source-of-truth-prompt-builder-2026-04-08-001",
                            "route_result": route_result,
                            "route": route,
                            "memory_selected_count": len(memory_selection.get("selected") or []),
                        },
                    }
                )

            token = str(token or "")
            if not token:
                continue

            refined_text += token

            yield sse(
                {
                    "type": "token",
                    "ok": True,
                    "session_id": locked_session_id,
                    "message_id": assistant_message_id,
                    "assistant_message_id": assistant_message_id,
                    "token": token,
                }
            )

        final_message = make_assistant_message(
            refined_text.strip(),
            message_id=assistant_message_id,
            source="send",
            pending=False,
            streaming=False,
            stopped=False,
            error=False,
        )

        append_message(session, final_message)

        try:
            save_artifact_from_assistant(final_message, session["id"])
        except Exception:
            pass

        yield sse(
            {
                "type": "final",
                "ok": True,
                "session_id": locked_session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "message": final_message,
                "messages": session_messages(session),
                "artifacts": load_artifacts(),
                "memory": load_memory(),
                "debug": {
                    "route_result": route_result,
                    "memory_selected_count": len(memory_selection.get("selected") or []),
                },
            }
        )
        return

    except Exception as exc:
        yield sse(
            {
                "type": "error",
                "ok": False,
                "session_id": locked_session_id,
                "message_id": assistant_message_id,
                "assistant_message_id": assistant_message_id,
                "error": str(exc) or "Stream failed",
            }
        )
        return

def run_non_stream_chat(
    session_id: str,
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
    route_result: dict[str, Any] | None = None,
    memory_selection: dict[str, Any] | None = None,
    memory_block: str = "",
) -> dict[str, Any]:
    store = load_sessions_store()
    session = find_session(store, session_id) or ensure_active_session(store)

    attachments = normalize_attachments(attachments)
    route_result = route_result if isinstance(route_result, dict) else {}
    memory_selection = memory_selection if isinstance(memory_selection, dict) else {}

    parts: list[str] = []
    for token in stream_model_text(
        session,
        user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
    ):
        parts.append(str(token or ""))

    final_text = "".join(parts).strip()
    if not final_text:
        final_text = "No response generated."

    assistant_message = make_assistant_message(
        final_text,
        message_id=assistant_message_id,
        source="send",
        pending=False,
        streaming=False,
        stopped=False,
        error=False,
        meta={
            "regenerate_of": regenerate_of or "",
        },
    )

    if target_message:
        replace_message(session, assistant_message_id, assistant_message)
    else:
        append_message(session, assistant_message)

    recalc_session(session)
    save_sessions_store(store)

    try:
        save_artifact_from_assistant(assistant_message, session["id"])
    except Exception:
        pass

    return {
        "ok": True,
        "assistant_message": assistant_message,
        "session": session_contract_payload(session)["session"],
        "session_id": session["id"],
        "active_session_id": session["id"],
        "debug": {
            "route_result": route_result,
            "memory_selected_count": len(memory_selection.get("selected") or []),
        },
    }

# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def index() -> Any:
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>Nova</h1>", 200


@app.get("/api/health")
def api_health() -> Any:
    return jsonify(
        {
            "ok": True,
            "route_build": "attachment-pipeline-polish-2026-04-07-001",
            "has_openai_api_key": bool(OPENAI_API_KEY),
            "openai_configured": OPENAI_CLIENT is not None,
            "chat_model": OPENAI_MODEL,
            "timestamp": now_iso(),
        }
    )


@app.get("/api/state")
def api_state() -> Any:
    return jsonify(state_payload())


@app.post("/api/upload")
def api_upload() -> Any:
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"ok": False, "error": "file is required"}), 400

    original_name = sanitize_filename(uploaded.filename or "upload.bin")
    attachment_id = make_id("att")
    stored_name = f"{attachment_id}_{original_name}"
    target_path = UPLOADS_DIR / stored_name

    try:
        uploaded.save(target_path)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc) or "upload failed"}), 500

    mime_type = (
        str(uploaded.mimetype or "").strip()
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )

    attachment = normalize_attachment(
        {
            "id": attachment_id,
            "name": original_name,
            "filename": original_name,
            "stored_name": stored_name,
            "url": f"/api/uploads/{stored_name}",
            "mime_type": mime_type,
            "size": file_size(target_path),
        }
    )

    return jsonify(
        {
            "ok": True,
            "attachment": attachment,
            "id": attachment["id"],
            "name": attachment["name"],
            "filename": attachment["filename"],
            "url": attachment["url"],
            "mime_type": attachment["mime_type"],
            "size": attachment["size"],
        }
    )


@app.post("/api/sessions/new")
def api_sessions_new() -> Any:
    store = load_sessions_store()
    session = make_session("New chat")
    store["sessions"].insert(0, session)
    store["active_session_id"] = session["id"]
    save_sessions_store(store)
    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/open")
def api_sessions_open() -> Any:
    data = request.get_json(silent=True) or {}
    session_id = resolve_session_id_from_request(data)

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
            )
        ), 400

    session = find_session(store, session_id)
    if not session:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
            )
        ), 404

    store["active_session_id"] = session["id"]
    save_sessions_store(store)

    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/rename")
def api_sessions_rename() -> Any:
    data = request.get_json(silent=True) or {}

    session_id = resolve_session_id_from_request(data)
    title = str(data.get("title") or "").strip()

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
            )
        ), 400

    if not title:
        return jsonify(
            session_error_payload(
                error="title is required.",
                active_session_id=current_active,
            )
        ), 400

    session = find_session(store, session_id)
    if not session:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
            )
        ), 404

    session["title"] = title
    session["updated_at"] = now_iso()
    save_sessions_store(store)

    return jsonify(session_contract_payload(session))


@app.post("/api/sessions/delete")
def api_sessions_delete() -> Any:
    data = request.get_json(silent=True) or {}

    session_id = resolve_session_id_from_request(data)

    store = load_sessions_store()
    current_active = str(store.get("active_session_id") or "")
    sessions = safe_list(store.get("sessions"))

    if not session_id:
        return jsonify(
            session_error_payload(
                error="session_id is required.",
                active_session_id=current_active,
                deleted_session_id=None,
            )
        ), 400

    delete_index = -1

    for index, session in enumerate(sessions):
        if str(session.get("id") or "") == session_id:
            delete_index = index
            break

    if delete_index < 0:
        return jsonify(
            session_error_payload(
                error="Session not found.",
                active_session_id=current_active,
                deleted_session_id=None,
            )
        ), 404

    deleted_session = sessions.pop(delete_index)
    store["sessions"] = sessions

    active_session: dict[str, Any] | None = None

    if not sessions:
        replacement = make_session("New chat")
        sessions.append(replacement)
        store["sessions"] = sessions
        store["active_session_id"] = replacement["id"]
        active_session = replacement
    else:
        if current_active == session_id:
            store["active_session_id"] = str(sessions[0].get("id") or "")

        active_session = find_session(store, store.get("active_session_id") or "")
        if not active_session:
            active_session = sessions[0]
            store["active_session_id"] = str(active_session.get("id") or "")

    save_sessions_store(store)

    return jsonify(
        session_delete_contract_payload(
            deleted_session.get("id") or "",
            active_session,
        )
    )

# =========================================================
# MEMORY RELEVANCE SELECTION LOCK
# =========================================================

MEMORY_RELEVANCE_BUILD = "memory-relevance-lock-2026-04-08-001"
MEMORY_MAX_INJECT = 6
MEMORY_TEXT_SOFT_MAX = 220

MEMORY_KIND_BASE_WEIGHTS = {
    "preference": 4.0,
    "personality": 3.5,
    "project": 3.0,
    "identity": 2.0,
    "workflow": 3.5,
    "goal": 2.5,
    "summary": 1.8,
    "note": 1.2,
    "temporary": 0.6,
}

ROUTE_MEMORY_KIND_BONUS = {
    "code": {"workflow": 2.0, "project": 1.5, "preference": 1.2},
    "debug": {"workflow": 1.8, "project": 1.4, "summary": 0.8},
    "plan": {"goal": 1.8, "project": 1.6, "workflow": 1.0},
    "write": {"preference": 1.6, "personality": 1.8, "summary": 1.0},
    "analysis": {"summary": 1.4, "project": 1.2, "goal": 1.0},
    "general": {"preference": 1.0, "project": 0.8},
    "attachment_analysis": {"project": 1.0, "workflow": 0.8},
    "web": {"project": 0.8, "goal": 0.6},
    "image": {"preference": 0.8, "project": 0.6},
}

TEMPORARY_MEMORY_HINTS = [
    "today",
    "tonight",
    "this week",
    "this month",
    "for now",
    "currently",
    "temporary",
    "tmp",
    "draft",
    "test",
    "trying",
]

DURABLE_MEMORY_HINTS = [
    "prefer",
    "always",
    "never",
    "from now on",
    "going forward",
    "i want",
    "my project",
    "my app",
    "my workflow",
]

CONFLICT_HINT_GROUPS = [
    ["prefer concise", "prefer detailed"],
    ["always send full file", "partial edits are fine"],
    ["powershell", "bash"],
]


def _memory_textish(value: Any) -> str:
    return str(value or "").strip()


def _memory_normalize_text(value: Any) -> str:
    text = _memory_textish(value).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _memory_tokenize(value: Any) -> list[str]:
    text = _memory_normalize_text(value)
    return re.findall(r"[a-z0-9_./:\\-]+", text)


def _memory_overlap_score(a: Any, b: Any) -> float:
    ta = set(_memory_tokenize(a))
    tb = set(_memory_tokenize(b))
    if not ta or not tb:
        return 0.0
    overlap = ta & tb
    if not overlap:
        return 0.0
    return min(4.0, float(len(overlap)) * 0.7)


def _memory_kind_of(item: dict[str, Any]) -> str:
    kind = _memory_normalize_text(item.get("kind") or "")
    if kind:
        return kind
    text = _memory_normalize_text(item.get("text") or "")
    if any(h in text for h in DURABLE_MEMORY_HINTS):
        return "preference"
    if any(h in text for h in TEMPORARY_MEMORY_HINTS):
        return "temporary"
    return "note"


def _memory_age_days(item: dict[str, Any]) -> float:
    raw = (
        item.get("updated_at")
        or item.get("created_at")
        or item.get("timestamp")
        or ""
    )
    raw = _memory_textish(raw)
    if not raw:
        return 9999.0
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 86400.0)
    except Exception:
        return 9999.0


def _memory_recency_score(kind: str, age_days: float) -> float:
    if age_days >= 9999:
        return 0.0

    if kind in {"preference", "workflow", "project", "personality"}:
        if age_days <= 365:
            return 1.6
        if age_days <= 730:
            return 1.0
        return 0.2

    if kind in {"temporary", "note"}:
        if age_days <= 3:
            return 1.6
        if age_days <= 14:
            return 0.8
        if age_days <= 45:
            return 0.2
        return -1.2

    if age_days <= 30:
        return 1.0
    if age_days <= 120:
        return 0.4
    return 0.0


def _memory_is_temporary(item: dict[str, Any]) -> bool:
    text = _memory_normalize_text(item.get("text") or "")
    kind = _memory_kind_of(item)
    return kind == "temporary" or any(h in text for h in TEMPORARY_MEMORY_HINTS)


def _memory_is_durable(item: dict[str, Any]) -> bool:
    text = _memory_normalize_text(item.get("text") or "")
    kind = _memory_kind_of(item)
    return kind in {"preference", "workflow", "project", "personality"} or any(
        h in text for h in DURABLE_MEMORY_HINTS
    )


def _memory_trim_text(text: Any, limit: int = MEMORY_TEXT_SOFT_MAX) -> str:
    value = _memory_textish(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _memory_route_bonus(route_name: str, kind: str) -> float:
    route_map = ROUTE_MEMORY_KIND_BONUS.get(route_name or "", {})
    return float(route_map.get(kind, 0.0))


def _memory_conflict_key(text: str, kind: str = "") -> str:
    normalized = _memory_normalize_text(text)
    normalized_kind = _textish(kind).strip().lower()

    for group in CONFLICT_HINT_GROUPS:
        for hint in group:
            if hint in normalized:
                base = "group:" + "|".join(group)
                return f"{normalized_kind}::{base}" if normalized_kind else base

    return f"{normalized_kind}::{normalized}" if normalized_kind else normalized

def _score_memory_item(
    item: dict[str, Any],
    user_text: str,
    route_result: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    text = _memory_textish(item.get("text") or "")
    if not text:
        return {
            "id": item.get("id") or "",
            "score": -999.0,
            "reasons": ["empty-text"],
            "kind": _memory_kind_of(item),
            "text": "",
            "age_days": 9999.0,
        }

    route_result = route_result or {}
    primary = route_result.get("primary") or "general"
    secondary = route_result.get("secondary") or ""
    kind = _memory_kind_of(item)
    age_days = _memory_age_days(item)

    score = 0.0
    reasons: list[str] = []

    base = float(MEMORY_KIND_BASE_WEIGHTS.get(kind, 1.0))
    score += base
    reasons.append(f"kind:{kind}+{base}")

    overlap = _memory_overlap_score(text, user_text)
    if overlap:
        score += overlap
        reasons.append(f"overlap+{round(overlap, 2)}")

    primary_bonus = _memory_route_bonus(primary, kind)
    if primary_bonus:
        score += primary_bonus
        reasons.append(f"route:{primary}+{primary_bonus}")

    if secondary:
        secondary_bonus = _memory_route_bonus(secondary, kind) * 0.45
        if secondary_bonus:
            score += secondary_bonus
            reasons.append(f"secondary:{secondary}+{round(secondary_bonus, 2)}")

    recency = _memory_recency_score(kind, age_days)
    if recency:
        score += recency
        reasons.append(f"recency+{round(recency, 2)}")

    item_session_id = _memory_textish(item.get("session_id") or "")
    if session_id and item_session_id and item_session_id == session_id:
        score += 0.9
        reasons.append("same-session+0.9")

    if _memory_is_durable(item):
        score += 0.8
        reasons.append("durable+0.8")

    if _memory_is_temporary(item):
        score -= 0.8
        reasons.append("temporary-0.8")

    normalized = _memory_normalize_text(text)
    if "prefer concise" in normalized and primary in {"code", "debug", "plan"}:
        score += 0.8
        reasons.append("concise-fit+0.8")

    return {
        "id": item.get("id") or "",
        "score": round(score, 3),
        "reasons": reasons[:12],
        "kind": kind,
        "text": _memory_trim_text(text),
        "age_days": round(age_days, 2) if age_days < 9999 else 9999.0,
        "session_id": item_session_id,
        "source": item.get("source") or "",
        "updated_at": item.get("updated_at") or item.get("created_at") or "",
        "item": item,
    }


def select_relevant_memories(
    memories: list[dict[str, Any]],
    user_text: str,
    route_result: dict[str, Any] | None = None,
    session_id: str | None = None,
    limit: int = MEMORY_MAX_INJECT,
) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    for item in memories or []:
        scored.append(
            _score_memory_item(
                item=item,
                user_text=user_text,
                route_result=route_result,
                session_id=session_id,
            )
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected: list[dict[str, Any]] = []
    seen_conflicts: set[str] = set()

    for entry in scored:
        if len(selected) >= limit:
            break
        if entry["score"] <= 0:
            continue

        conflict_key = _memory_conflict_key(entry["text"])
        if conflict_key in seen_conflicts:
            continue

        seen_conflicts.add(conflict_key)
        selected.append(entry)

    return {
        "build": MEMORY_RELEVANCE_BUILD,
        "selected": selected,
        "top_candidates": scored[:10],
    }

def render_memory_injection_block(selected_entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in selected_entries or []:
        kind = _memory_textish(entry.get("kind") or "note")
        text = _memory_textish(entry.get("text") or "")
        if not text:
            continue
        lines.append(f"- [{kind}] {text}")
    return "\n".join(lines).strip()

# =========================================================
# ROUTE SCORING + CONFIDENCE LOCK
# =========================================================

ROUTE_BUILD = "route-scoring-confidence-lock-2026-04-08-001"

ROUTE_FAMILIES = [
    "debug",
    "code",
    "plan",
    "write",
    "analysis",
    "general",
    "web",
    "image",
    "attachment_analysis",
]

ROUTE_HIGH_CONFIDENCE = 0.80
ROUTE_MEDIUM_CONFIDENCE = 0.55

ROUTE_SCORE_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "debug": [
        {"pattern": r"\btraceback\b", "weight": 6.0, "reason": "traceback"},
        {"pattern": r"\bsyntaxerror\b", "weight": 6.0, "reason": "syntaxerror"},
        {"pattern": r"\bindentationerror\b", "weight": 6.0, "reason": "indentationerror"},
        {"pattern": r"\bnameerror\b", "weight": 5.0, "reason": "nameerror"},
        {"pattern": r"\btypeerror\b", "weight": 5.0, "reason": "typeerror"},
        {"pattern": r"\bvalueerror\b", "weight": 5.0, "reason": "valueerror"},
        {"pattern": r"\bexception\b", "weight": 4.0, "reason": "exception"},
        {"pattern": r"\berror\b", "weight": 3.5, "reason": "error"},
        {"pattern": r"\bcrash(?:ed|ing)?\b", "weight": 4.0, "reason": "crash"},
        {"pattern": r"\bfailing\b", "weight": 3.0, "reason": "failing"},
        {"pattern": r"\bline\s+\d+\b", "weight": 3.5, "reason": "line-number"},
        {"pattern": r"\blogs?\b", "weight": 2.5, "reason": "logs"},
        {"pattern": r"\bdebug\b", "weight": 4.0, "reason": "debug"},
        {"pattern": r"\bwhy is this breaking\b", "weight": 5.0, "reason": "breaking"},
        {"pattern": r"\bunexpected end of input\b", "weight": 6.0, "reason": "unexpected-end-of-input"},
    ],
    "code": [
        {"pattern": r"\bsmff\b", "weight": 8.0, "reason": "smff"},
        {"pattern": r"\bfull file\b", "weight": 6.0, "reason": "full-file"},
        {"pattern": r"[A-Za-z]:\\[^ \n\r\t]+", "weight": 5.5, "reason": "windows-file-path"},
        {"pattern": r"\bapp\.py\b", "weight": 4.5, "reason": "app-py"},
        {"pattern": r"\bindex\.html\b", "weight": 4.5, "reason": "index-html"},
        {"pattern": r"\bnova-main\.css\b", "weight": 4.5, "reason": "css-file"},
        {"pattern": r"\bnova-composer-bundle\.js\b", "weight": 4.5, "reason": "js-file"},
        {"pattern": r"```", "weight": 3.0, "reason": "code-fence"},
        {"pattern": r"\bdef\b", "weight": 2.5, "reason": "def-keyword"},
        {"pattern": r"\bclass\b", "weight": 2.5, "reason": "class-keyword"},
        {"pattern": r"\breturn\b", "weight": 1.5, "reason": "return-keyword"},
        {"pattern": r"\bimport\b", "weight": 1.5, "reason": "import-keyword"},
        {"pattern": r"\bfix\b", "weight": 2.5, "reason": "fix"},
        {"pattern": r"\breplace\b", "weight": 2.0, "reason": "replace"},
        {"pattern": r"\bedit\b", "weight": 2.0, "reason": "edit"},
        {"pattern": r"\bfunction\b", "weight": 2.0, "reason": "function"},
        {"pattern": r"\broute\b", "weight": 2.0, "reason": "route"},
    ],
    "plan": [
        {"pattern": r"\bnext\b", "weight": 2.5, "reason": "next"},
        {"pattern": r"\bnext move\b", "weight": 5.0, "reason": "next-move"},
        {"pattern": r"\bplan\b", "weight": 4.0, "reason": "plan"},
        {"pattern": r"\broadmap\b", "weight": 5.0, "reason": "roadmap"},
        {"pattern": r"\bphase\b", "weight": 4.0, "reason": "phase"},
        {"pattern": r"\bsequence\b", "weight": 3.0, "reason": "sequence"},
        {"pattern": r"\bpriority\b", "weight": 3.0, "reason": "priority"},
        {"pattern": r"\barchitecture\b", "weight": 3.5, "reason": "architecture"},
        {"pattern": r"\bwhat should we do next\b", "weight": 6.0, "reason": "what-next"},
        {"pattern": r"\bbest next\b", "weight": 5.0, "reason": "best-next"},
    ],
    "write": [
        {"pattern": r"\brewrite\b", "weight": 5.0, "reason": "rewrite"},
        {"pattern": r"\bpolish\b", "weight": 3.5, "reason": "polish"},
        {"pattern": r"\bmake this sound better\b", "weight": 6.0, "reason": "sound-better"},
        {"pattern": r"\bemail\b", "weight": 4.0, "reason": "email"},
        {"pattern": r"\bpost\b", "weight": 2.5, "reason": "post"},
        {"pattern": r"\bsummary\b", "weight": 2.5, "reason": "summary"},
        {"pattern": r"\btone\b", "weight": 2.5, "reason": "tone"},
    ],
    "analysis": [
        {"pattern": r"\banaly[sz]e\b", "weight": 5.0, "reason": "analyze"},
        {"pattern": r"\bcompare\b", "weight": 4.0, "reason": "compare"},
        {"pattern": r"\btrade[\-\s]?off\b", "weight": 4.0, "reason": "tradeoff"},
        {"pattern": r"\bpros?\b", "weight": 2.0, "reason": "pros"},
        {"pattern": r"\bcons?\b", "weight": 2.0, "reason": "cons"},
        {"pattern": r"\bwhy\b", "weight": 1.5, "reason": "why"},
        {"pattern": r"\broot cause\b", "weight": 5.0, "reason": "root-cause"},
        {"pattern": r"\bevaluate\b", "weight": 4.0, "reason": "evaluate"},
        {"pattern": r"\binspect\b", "weight": 3.0, "reason": "inspect"},
    ],
    "web": [
        {"pattern": r"(?i)\b/web\b", "weight": 9.0, "reason": "slash-web"},
        {"pattern": r"https?://", "weight": 8.0, "reason": "http-url"},
        {"pattern": r"\bwww\.[^\s]+\b", "weight": 7.0, "reason": "www-url"},
        {"pattern": r"\bfetch\b", "weight": 2.0, "reason": "fetch"},
        {"pattern": r"\bwebsite\b", "weight": 2.5, "reason": "website"},
        {"pattern": r"\burl\b", "weight": 2.5, "reason": "url"},
    ],
    "image": [
        {"pattern": r"(?i)\b/image\b", "weight": 9.0, "reason": "slash-image"},
        {"pattern": r"\bgenerate image\b", "weight": 6.0, "reason": "generate-image"},
        {"pattern": r"\bmake an image\b", "weight": 6.0, "reason": "make-image"},
        {"pattern": r"\bcreate an image\b", "weight": 6.0, "reason": "create-image"},
        {"pattern": r"\bimage prompt\b", "weight": 5.0, "reason": "image-prompt"},
    ],
    "general": [
        {"pattern": r".+", "weight": 1.0, "reason": "general-fallback"},
    ],
}

ATTACHMENT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
ATTACHMENT_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ATTACHMENT_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
ATTACHMENT_DOC_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".json", ".log", ".py", ".js", ".html", ".css"
}


def _router_textish(value: Any) -> str:
    return str(value or "").strip()


def _normalize_router_text(value: Any) -> str:
    text = _router_textish(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip().lower()

def _route_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _route_primary(route_result: dict[str, Any] | None) -> str:
    if not isinstance(route_result, dict):
        return "general"

    primary = (
        route_result.get("primary")
        or route_result.get("route")
        or route_result.get("mode")
        or "general"
    )
    primary = _route_text(primary)

    alias_map = {
        "coding": "code",
        "planning": "plan",
        "writing": "write",
        "image_analysis": "attachment_analysis",
    }
    return alias_map.get(primary, primary or "general")


def _route_confidence(route_result: dict[str, Any] | None) -> float:
    if not isinstance(route_result, dict):
        return 0.0

    raw = route_result.get("confidence", 0.0)
    try:
        return max(0.0, min(float(raw), 1.0))
    except Exception:
        return 0.0


def _route_signals(route_result: dict[str, Any] | None) -> list[str]:
    if not isinstance(route_result, dict):
        return []

    signals = route_result.get("signals")
    if not isinstance(signals, list):
        return []

    out: list[str] = []
    for item in signals:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out[:24]


def build_tool_use_brain(
    *,
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    route_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attachments = normalize_attachments(attachments)
    primary = _route_primary(route_result)
    confidence = _route_confidence(route_result)
    signals = _route_signals(route_result)

    lowered = normalize_text(user_text).strip().lower()

    has_url = (
        "http://" in lowered
        or "https://" in lowered
        or "www." in lowered
        or lowered.startswith("/web ")
    )

    has_image_attachment = any(
        str(item.get("mime_type") or "").lower().startswith("image/")
        for item in attachments
    )

    has_any_attachment = bool(attachments)

    should_use_web = primary == "web" or has_url
    should_use_attachments = has_any_attachment
    should_use_attachment_analysis = primary == "attachment_analysis" or has_image_attachment
    should_use_memory = primary in {"debug", "code", "plan", "write", "analysis", "general"}

    response_mode_map = {
        "debug": "root-cause-first",
        "code": "implementation-first",
        "plan": "next-step-first",
        "write": "tone-match",
        "analysis": "reasoned-summary",
        "web": "source-aware-summary",
        "image": "generation-directive",
        "attachment_analysis": "attachment-aware-analysis",
        "general": "direct-answer",
    }

    return {
        "build": "phase-c-tool-brain-lock-2026-04-08-001",
        "primary": primary,
        "confidence": confidence,
        "signals": signals,
        "should_use_memory": should_use_memory,
        "should_use_web": should_use_web,
        "should_use_attachments": should_use_attachments,
        "should_use_attachment_analysis": should_use_attachment_analysis,
        "response_mode": response_mode_map.get(primary, "direct-answer"),
    }


def build_tool_use_block(tool_brain: dict[str, Any] | None) -> str:
    if not isinstance(tool_brain, dict):
        return ""

    primary = _route_text(tool_brain.get("primary") or "general")
    confidence = tool_brain.get("confidence", 0.0)
    response_mode = str(tool_brain.get("response_mode") or "direct-answer")
    signals = tool_brain.get("signals") if isinstance(tool_brain.get("signals"), list) else []

    rules: list[str] = [
        f"Primary operating route: {primary}",
        f"Confidence: {confidence}",
        f"Response mode: {response_mode}",
    ]

    if tool_brain.get("should_use_memory"):
        rules.append("Use relevant memory when it helps answer correctly.")
    else:
        rules.append("Do not force memory if it is not useful.")

    if tool_brain.get("should_use_web"):
        rules.append("A web-oriented request is likely. Prefer web-aware behavior when available.")

    if tool_brain.get("should_use_attachments"):
        rules.append("The user included attachments. Use attachment metadata when relevant.")

    if tool_brain.get("should_use_attachment_analysis"):
        rules.append("Attachment/image analysis is likely relevant.")

    if primary == "debug":
        rules += [
            "Start with the root cause.",
            "Then give the exact fix.",
            "Prefer concrete corrections over theory.",
        ]
    elif primary == "code":
        rules += [
            "Prioritize implementation.",
            "Prefer full working code when the user wants file work.",
        ]
    elif primary == "plan":
        rules += [
            "Start with the next move.",
            "Keep steps ordered and actionable.",
        ]
    elif primary == "write":
        rules += [
            "Match requested tone and voice.",
            "Optimize wording, not explanation.",
        ]
    elif primary == "web":
        rules += [
            "Summarize source-backed content cleanly.",
            "Do not pretend to have fetched anything that has not been fetched.",
        ]
    elif primary == "attachment_analysis":
        rules += [
            "Ground the answer in available attachment context.",
            "Do not claim full file understanding unless content is actually available.",
        ]
    else:
        rules += [
            "Answer directly first.",
            "Expand only when useful.",
        ]

    if signals:
        rules.append("Signals: " + ", ".join(str(x) for x in signals[:10]))

    return "Tool-use and routing rules:\n- " + "\n- ".join(rules)

def _attachment_name(att: dict[str, Any]) -> str:
    return str(
        att.get("filename")
        or att.get("name")
        or att.get("path")
        or att.get("url")
        or ""
    ).strip()


def _attachment_ext(name: str) -> str:
    try:
        return Path(name).suffix.lower()
    except Exception:
        return ""


def _classify_attachment_kind(att: dict[str, Any]) -> str:
    mime = str(att.get("mime_type") or att.get("content_type") or "").lower()
    name = _attachment_name(att)
    ext = _attachment_ext(name)

    if mime.startswith("image/") or ext in ATTACHMENT_IMAGE_EXTENSIONS:
        return "image"
    if mime.startswith("video/") or ext in ATTACHMENT_VIDEO_EXTENSIONS:
        return "video"
    if mime.startswith("audio/") or ext in ATTACHMENT_AUDIO_EXTENSIONS:
        return "audio"
    if (
        mime.startswith("text/")
        or "json" in mime
        or "pdf" in mime
        or ext in ATTACHMENT_DOC_EXTENSIONS
    ):
        return "document"
    return "unknown"


def _summarize_attachment_signals(attachments: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "total": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
        "document": 0,
        "unknown": 0,
    }
    names: list[str] = []

    for att in attachments or []:
        kind = _classify_attachment_kind(att)
        counts["total"] += 1
        counts[kind] = counts.get(kind, 0) + 1
        name = _attachment_name(att)
        if name:
            names.append(name)

    return {
        "counts": counts,
        "names": names[:8],
    }


def _score_patterns(route_name: str, normalized_text: str) -> tuple[float, list[str]]:
    total = 0.0
    reasons: list[str] = []

    for spec in ROUTE_SCORE_PATTERNS.get(route_name, []):
        pattern = str(spec.get("pattern") or "")
        weight = float(spec.get("weight") or 0.0)
        reason = str(spec.get("reason") or pattern)

        try:
            if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                total += weight
                reasons.append(reason)
        except Exception:
            continue

    return total, reasons


def _apply_attachment_route_bias(
    scores: dict[str, float],
    reasons: dict[str, list[str]],
    attachments: list[dict[str, Any]],
) -> dict[str, Any]:
    info = _summarize_attachment_signals(attachments)
    counts = info["counts"]

    if counts["total"] <= 0:
        return info

    scores["attachment_analysis"] += 5.0
    reasons["attachment_analysis"].append("has-attachments")

    if counts["image"] > 0:
        scores["attachment_analysis"] += 2.5
        reasons["attachment_analysis"].append("image-attachment")
        scores["image"] += 1.0
        reasons["image"].append("image-attachment-present")

    if counts["document"] > 0:
        scores["analysis"] += 1.5
        reasons["analysis"].append("document-attachment")
        scores["code"] += 1.0
        reasons["code"].append("document-attachment-present")

    if counts["video"] > 0 or counts["audio"] > 0:
        scores["attachment_analysis"] += 1.5
        reasons["attachment_analysis"].append("media-attachment")

    return info


def _route_softmax_confidence(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0

    ordered = sorted(scores.values(), reverse=True)
    if not ordered:
        return 0.0

    top = ordered[0]
    shifted = [math.exp(v - top) for v in ordered]
    denom = sum(shifted) or 1.0
    probs = [v / denom for v in shifted]
    return float(max(probs) if probs else 0.0)


def _route_confidence_band(confidence: float) -> str:
    if confidence >= ROUTE_HIGH_CONFIDENCE:
        return "high"
    if confidence >= ROUTE_MEDIUM_CONFIDENCE:
        return "medium"
    return "low"


def _choose_primary_secondary(scores: dict[str, float]) -> tuple[str, str | None, float, float]:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        return "general", None, 0.0, 0.0

    primary, primary_score = ranked[0]
    secondary = ranked[1][0] if len(ranked) > 1 else None
    secondary_score = ranked[1][1] if len(ranked) > 1 else 0.0
    return primary, secondary, float(primary_score), float(secondary_score)


def _route_mixed_intent(primary_score: float, secondary_score: float) -> bool:
    if primary_score <= 0:
        return False
    gap = primary_score - secondary_score
    ratio = (secondary_score / primary_score) if primary_score else 0.0
    return ratio >= 0.68 or gap <= 2.5


def choose_route(
    user_text: Any,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: Any = None,
) -> dict[str, Any]:
    attachments = list(attachments or [])
    raw_text = _router_textish(user_text)
    normalized_text = _normalize_router_text(raw_text)

    scores: dict[str, float] = {name: 0.0 for name in ROUTE_FAMILIES}
    reasons: dict[str, list[str]] = defaultdict(list)

    for route_name in ROUTE_FAMILIES:
        route_score, route_reasons = _score_patterns(route_name, normalized_text)
        scores[route_name] += route_score
        reasons[route_name].extend(route_reasons)

    attachment_info = _apply_attachment_route_bias(scores, reasons, attachments)

    if regenerate_of:
        scores["debug"] += 0.5
        reasons["debug"].append("regenerate-context")
        scores["code"] += 0.5
        reasons["code"].append("regenerate-context")

    primary, secondary, primary_score, secondary_score = _choose_primary_secondary(scores)
    mixed_intent = _route_mixed_intent(primary_score, secondary_score)
    confidence = _route_softmax_confidence(scores)
    confidence_band = _route_confidence_band(confidence)

    fallback_used = False
    effective_primary = primary
    effective_secondary = secondary

    if confidence_band == "low":
        fallback_used = True
        effective_secondary = primary
        effective_primary = "general"

    return {
        "primary": effective_primary,
        "secondary": effective_secondary,
        "raw_primary": primary,
        "confidence": round(confidence, 4),
        "confidence_band": confidence_band,
        "mixed_intent": mixed_intent,
        "fallback_used": fallback_used,
        "scores": {k: round(v, 3) for k, v in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)},
        "reasons": {k: list(dict.fromkeys(v))[:10] for k, v in reasons.items() if v},
        "attachments": attachment_info,
        "raw_user_text": raw_text,
        "normalized_user_text": normalized_text,
        "regenerate_of": regenerate_of,
        "route_build": ROUTE_BUILD,
    }


# =========================================================
# PHASE D.5 — ONE-SOURCE-OF-TRUTH PROMPT BUILDER LOCK
# =========================================================

from copy import deepcopy


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _clip_text(value: Any, limit: int = 4000) -> str:
    text = _safe_str(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " ...[truncated]"


def _normalize_attachment_prompt_block(attachments: list[dict]) -> str:
    if not attachments:
        return ""

    lines: list[str] = []
    for idx, att in enumerate(attachments, start=1):
        if not isinstance(att, dict):
            continue

        name = _safe_str(att.get("name") or att.get("filename") or f"attachment_{idx}")
        kind = _safe_str(att.get("kind") or att.get("type") or "file")
        mime = _safe_str(att.get("mime_type") or att.get("mime") or "")
        notes = _safe_str(att.get("analysis_text") or att.get("summary") or att.get("notes") or "")
        url = _safe_str(att.get("url") or att.get("path") or att.get("src") or "")

        chunk = [f"{idx}. {name} [{kind}]"]
        if mime:
            chunk.append(f"mime={mime}")
        if url:
            chunk.append(f"source={url}")
        if notes:
            chunk.append(f"notes={_clip_text(notes, 500)}")

        lines.append(" | ".join(chunk))

    if not lines:
        return ""

    return "ATTACHMENT CONTEXT:\n" + "\n".join(lines)


def _normalize_execution_context_block(execution: dict | None) -> str:
    execution = execution or {}
    if not isinstance(execution, dict):
        return ""

    summary = _safe_str(execution.get("summary"))
    instructions = _safe_str(execution.get("instructions"))
    constraints = _safe_list(execution.get("constraints"))
    steps = _safe_list(execution.get("steps"))
    tools = _safe_list(execution.get("tools"))
    warnings = _safe_list(execution.get("warnings"))

    lines: list[str] = []

    if summary:
        lines.append(f"EXECUTION SUMMARY:\n{_clip_text(summary, 1200)}")

    if instructions:
        lines.append(f"EXECUTION INSTRUCTIONS:\n{_clip_text(instructions, 1200)}")

    if constraints:
        lines.append(
            "EXECUTION CONSTRAINTS:\n" +
            "\n".join(f"- {_clip_text(item, 240)}" for item in constraints if _safe_str(item))
        )

    if steps:
        lines.append(
            "EXECUTION STEPS:\n" +
            "\n".join(f"- {_clip_text(item, 240)}" for item in steps if _safe_str(item))
        )

    if tools:
        lines.append(
            "SUGGESTED TOOLS:\n" +
            "\n".join(f"- {_clip_text(item, 120)}" for item in tools if _safe_str(item))
        )

    if warnings:
        lines.append(
            "WARNINGS:\n" +
            "\n".join(f"- {_clip_text(item, 240)}" for item in warnings if _safe_str(item))
        )

    return "\n\n".join(part for part in lines if part).strip()


def _build_route_context_block(route_result: dict | None) -> str:
    route_result = route_result or {}
    if not isinstance(route_result, dict):
        return ""

    route = _safe_str(route_result.get("route") or route_result.get("mode") or "general")
    intent = _safe_str(route_result.get("intent"))
    reason = _safe_str(route_result.get("reason"))
    goals = _safe_list(route_result.get("goals"))
    constraints = _safe_list(route_result.get("constraints"))

    lines = [f"ROUTE MODE: {route}"]
    if intent:
        lines.append(f"ROUTE INTENT: {intent}")
    if reason:
        lines.append(f"ROUTE REASON: {_clip_text(reason, 500)}")
    if goals:
        lines.append("ROUTE GOALS:\n" + "\n".join(f"- {_clip_text(x, 160)}" for x in goals if _safe_str(x)))
    if constraints:
        lines.append("ROUTE CONSTRAINTS:\n" + "\n".join(f"- {_clip_text(x, 160)}" for x in constraints if _safe_str(x)))

    return "\n".join(lines).strip()


def _build_memory_block(memory_selection: dict | None) -> str:
    memory_selection = memory_selection or {}
    if not isinstance(memory_selection, dict):
        return ""

    items = _safe_list(memory_selection.get("items"))
    if not items:
        return ""

    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        kind = _safe_str(item.get("kind") or "memory")
        text = _safe_str(item.get("text"))
        source = _safe_str(item.get("source"))
        if not text:
            continue

        line = f"{idx}. ({kind}) {_clip_text(text, 240)}"
        if source:
            line += f" [source={source}]"
        lines.append(line)

    if not lines:
        return ""

    return "MEMORY CONTEXT:\n" + "\n".join(lines)


def _build_system_prompt_unified(
    *,
    user_text: str,
    route_result: dict | None,
    memory_block: str,
    attachment_block: str,
    execution_context: str,
) -> str:
    base_sections: list[str] = []

    # Use your existing system/personality builder if present.
    base_builder = globals().get("build_dynamic_system_prompt") or globals().get("build_system_prompt")
    if callable(base_builder):
        try:
            base_text = base_builder(user_text=user_text, route_result=route_result)
        except TypeError:
            base_text = base_builder(user_text)
        except Exception:
            base_text = ""
        if _safe_str(base_text):
            base_sections.append(_safe_str(base_text))

    if not base_sections:
        base_sections.append(
            "\n".join(
                [
                    "You are Nova.",
                    "Be accurate, direct, useful, and consistent.",
                    "Follow the user's intent tightly.",
                    "Prefer action over filler.",
                    "Do not contradict remembered user preferences unless the current request overrides them.",
                ]
            )
        )

    route_block = _build_route_context_block(route_result)
    if route_block:
        base_sections.append(route_block)

    if memory_block:
        base_sections.append(memory_block)

    if attachment_block:
        base_sections.append(attachment_block)

    if execution_context:
        base_sections.append(execution_context)

    return "\n\n".join(section.strip() for section in base_sections if _safe_str(section)).strip()


def build_prompt_context(
    *,
    user_text: str,
    session: dict,
    attachments: list[dict] | None = None,
    regenerate_of: str | None = None,
) -> dict:
    attachments = _safe_list(attachments)

    # ROUTE
    route_result: dict = {}
    route = "general"
    router_fn = globals().get("route_user_input") or globals().get("route_message") or globals().get("detect_route")
    if callable(router_fn):
        try:
            route_result = router_fn(
                user_text=user_text,
                session=session,
                attachments=attachments,
                regenerate_of=regenerate_of,
            )
        except TypeError:
            try:
                route_result = router_fn(user_text, session)
            except Exception:
                route_result = {}
        except Exception:
            route_result = {}

    if not isinstance(route_result, dict):
        route_result = {}

    route = _safe_str(route_result.get("route") or route_result.get("mode") or "general") or "general"

    # MEMORY
    memory_selection: dict = {}
    memory_fn = globals().get("select_relevant_memory") or globals().get("build_memory_selection")
    if callable(memory_fn):
        try:
            memory_selection = memory_fn(
                user_text=user_text,
                session=session,
                route_result=route_result,
            )
        except TypeError:
            try:
                memory_selection = memory_fn(user_text, session)
            except Exception:
                memory_selection = {}
        except Exception:
            memory_selection = {}

    if not isinstance(memory_selection, dict):
        memory_selection = {}

    memory_block = _build_memory_block(memory_selection)

    # EXECUTION
    execution: dict = {}
    execution_fn = globals().get("build_execution_plan") or globals().get("prepare_execution_context")
    if callable(execution_fn):
        try:
            execution = execution_fn(
                user_text=user_text,
                session=session,
                route_result=route_result,
                attachments=attachments,
            )
        except TypeError:
            try:
                execution = execution_fn(user_text, route_result)
            except Exception:
                execution = {}
        except Exception:
            execution = {}

    if not isinstance(execution, dict):
        execution = {}

    execution_context = _normalize_execution_context_block(execution)
    attachment_block = _normalize_attachment_prompt_block(attachments)

    system_prompt = _build_system_prompt_unified(
        user_text=user_text,
        route_result=route_result,
        memory_block=memory_block,
        attachment_block=attachment_block,
        execution_context=execution_context,
    )

    return {
        "route_result": route_result,
        "route": route,
        "memory_selection": memory_selection,
        "memory_block": memory_block,
        "execution": execution,
        "execution_context": execution_context,
        "attachment_block": attachment_block,
        "system_prompt": system_prompt,
    }


def build_model_messages_from_context(
    *,
    session: dict,
    user_text: str,
    prompt_context: dict,
    attachments: list[dict] | None = None,
) -> list[dict]:
    attachments = _safe_list(attachments)
    prompt_context = prompt_context or {}

    # Use your existing message builder if present.
    existing_builder = globals().get("build_messages_for_model")
    if callable(existing_builder):
        try:
            messages = existing_builder(
                session=session,
                user_text=user_text,
                system_prompt=prompt_context.get("system_prompt", ""),
                attachments=attachments,
            )
            if isinstance(messages, list) and messages:
                return messages
        except TypeError:
            pass
        except Exception:
            pass

    messages: list[dict] = []

    system_prompt = _safe_str(prompt_context.get("system_prompt"))
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    history = _safe_list(session.get("messages"))
    for msg in history[-20:]:
        if not isinstance(msg, dict):
            continue
        role = _safe_str(msg.get("role") or "user")
        text = _safe_str(msg.get("text") or msg.get("content"))
        if not text:
            continue
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        messages.append({"role": role, "content": text})

    user_payload = user_text.strip()
    attachment_block = _safe_str(prompt_context.get("attachment_block"))
    if attachment_block:
        user_payload = f"{user_payload}\n\n{attachment_block}".strip()

    messages.append({"role": "user", "content": user_payload})
    return messages


def build_model_payload(
    *,
    session: dict,
    user_text: str,
    attachments: list[dict] | None = None,
    regenerate_of: str | None = None,
) -> dict:
    prompt_context = build_prompt_context(
        user_text=user_text,
        session=session,
        attachments=attachments,
        regenerate_of=regenerate_of,
    )

    model_messages = build_model_messages_from_context(
        session=session,
        user_text=user_text,
        prompt_context=prompt_context,
        attachments=attachments,
    )

    payload = deepcopy(prompt_context)
    payload["model_messages"] = model_messages
    return payload

# =========================================================
# PHASE G — AGENT PLAN + ACT LOOP
# =========================================================

def detect_agent_mode(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(x in t for x in [
        "analyze and fix",
        "go through",
        "step by step",
        "check and repair",
        "inspect and solve",
        "debug this fully",
        "handle this for me",
        "find the problem and fix it",
    ])


def build_agent_steps(user_text: str) -> list[str]:
    t = (user_text or "").strip()
    steps: list[str] = []

    if re.search(r"https?://|www\.", t.lower()):
        steps.append("Extract the URL from the request")
        steps.append("Fetch the web content")
        steps.append("Summarize the important result")
        return steps

    if any(x in t.lower() for x in ["generate image", "create image", "draw", "image of"]):
        steps.append("Extract the image prompt")
        steps.append("Generate the image")
        steps.append("Return the generated result")
        return steps

    steps.append("Inspect the request carefully")
    steps.append("Choose the best route")
    steps.append("Produce the final result")
    return steps


def stream_agent_plan(
    *,
    assistant_id: str,
    session: dict[str, Any],
    user_text: str,
) -> Generator[str, None, str]:
    steps = build_agent_steps(user_text)
    built = ""

    for idx, step in enumerate(steps, start=1):
        token = f"[step {idx}/{len(steps)}] {step}\n"
        built += token
        yield sse({
            "type": "token",
            "message_id": assistant_id,
            "token": token,
        })

    return built

# =========================================================
# PHASE H — AGENT MEMORY + EXECUTION UPGRADE
# =========================================================

def build_agent_context(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = (user_text or "").lower()

    recent_messages = safe_list(session.get("messages"))[-8:]
    recent_text = "\n".join(
        normalize_text(m.get("text") or "")
        for m in recent_messages
        if isinstance(m, dict)
    ).strip()

    matched_memory = select_agent_memory(
        user_text=user_text,
        limit=5,
    )

    return {
        "recent_text": recent_text,
        "matched_memory": matched_memory,
    }

def build_agent_system_prompt(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    ctx = build_agent_context(user_text=user_text, session=session)

    mem_lines = []
    for item in ctx["matched_memory"]:
        txt = normalize_text(item.get("text") or "").strip()
        if txt:
            mem_lines.append(f"- {txt}")

    memory_block = "\n".join(mem_lines).strip()
    recent_block = (ctx["recent_text"] or "").strip()

    parts = [
        "You are Nova.",
        "Follow the user's style hard.",
        "Be direct.",
        "Be solution-first.",
        "Prefer full working output over explanation.",
        "Do not waste motion.",
    ]

    if memory_block:
        parts.append("\nRelevant user memory:\n" + memory_block)

    if recent_block:
        parts.append("\nRecent conversation context:\n" + recent_block)

    return "\n".join(parts).strip()

# =========================================================
# PHASE I — AGENT PLAN + ACTION MODE LOCK
# =========================================================

def build_agent_plan(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    action_mode = "respond"
    plan_steps: list[str] = []
    intent = "general"

    if re.search(r"https?://|www\.", lower):
        action_mode = "tool"
        intent = "web"
        plan_steps = [
            "Detected URL in user input.",
            "Route to web handling.",
            "Return result with minimal extra explanation.",
        ]
    elif lower.startswith("/image") or any(x in lower for x in [
        "generate image",
        "create image",
        "make image",
        "draw",
        "image of",
        "picture of",
    ]):
        action_mode = "tool"
        intent = "image"
        plan_steps = [
            "Detected image-generation intent.",
            "Route to image handling.",
            "Return generated result cleanly.",
        ]
    elif any(x in lower for x in [
        "fix",
        "patch",
        "replace",
        "rewrite",
        "refactor",
        "smff",
        "full file",
    ]):
        action_mode = "execute"
        intent = "code"
        plan_steps = [
            "User wants direct execution-style help.",
            "Prefer full working code over discussion.",
            "Return concrete implementation.",
        ]
    elif any(x in lower for x in [
        "plan",
        "phase",
        "next",
        "roadmap",
        "what now",
    ]):
        action_mode = "plan"
        intent = "planning"
        plan_steps = [
            "User wants next-step guidance.",
            "Keep sequence tight and actionable.",
            "Return the next exact move.",
        ]
    else:
        plan_steps = [
            "Answer directly.",
            "Keep response concise and useful.",
            "Avoid wasted motion.",
        ]

    recent_messages = safe_list(session.get("messages"))[-6:]
    recent_user_texts: list[str] = []

    for msg in recent_messages:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "") != "user":
            continue
        txt = normalize_text(msg.get("text") or "").strip()
        if txt:
            recent_user_texts.append(txt)

    return {
        "action_mode": action_mode,
        "intent": intent,
        "plan_steps": plan_steps[:4],
        "recent_user_texts": recent_user_texts[-3:],
    }


def build_agent_execution_header(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    plan = build_agent_plan(user_text=user_text, session=session)

    lines = [
        "Execution mode rules:",
        f"- action_mode: {plan['action_mode']}",
        f"- intent: {plan['intent']}",
        "- prioritize direct completion",
        "- prefer concrete output over explanation",
        "- keep wording tight",
        "- do not drift away from user style",
    ]

    for step in safe_list(plan.get("plan_steps")):
        step_text = normalize_text(step).strip()
        if step_text:
            lines.append(f"- plan: {step_text}")

    for item in safe_list(plan.get("recent_user_texts")):
        item_text = normalize_text(item).strip()
        if item_text:
            lines.append(f"- recent_user: {item_text}")

    return "\n".join(lines).strip()

# =========================================================
# PHASE J — AGENT TOOL DECISION + RESPONSE SHAPE LOCK
# =========================================================

def decide_agent_response_shape(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    shape = "default"
    tone = "direct"
    requires_full_output = False
    should_minimize_explanation = True
    preferred_format = "plain"

    if any(x in lower for x in [
        "smff",
        "full file",
        "whole file",
        "entire file",
        "send the file",
    ]):
        shape = "full_file"
        requires_full_output = True
        preferred_format = "code"
    elif any(x in lower for x in [
        "step by step",
        "walk me through",
        "teach me",
        "explain",
        "why",
    ]):
        shape = "guided"
        tone = "clear"
        should_minimize_explanation = False
        preferred_format = "structured"
    elif any(x in lower for x in [
        "phase",
        "next",
        "what now",
        "roadmap",
        "plan",
    ]):
        shape = "next_move"
        preferred_format = "tight"
    elif any(x in lower for x in [
        "fix",
        "patch",
        "replace",
        "rewrite",
        "refactor",
    ]):
        shape = "implementation"
        requires_full_output = True
        preferred_format = "code"

    recent_messages = safe_list(session.get("messages"))[-8:]
    recent_assistant_texts: list[str] = []

    for msg in recent_messages:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "") != "assistant":
            continue
        txt = normalize_text(msg.get("text") or "").strip()
        if txt:
            recent_assistant_texts.append(txt[:240])

    return {
        "shape": shape,
        "tone": tone,
        "requires_full_output": requires_full_output,
        "should_minimize_explanation": should_minimize_explanation,
        "preferred_format": preferred_format,
        "recent_assistant_texts": recent_assistant_texts[-2:],
    }


def decide_agent_tool_choice(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    suggested_tool = "none"
    reason = "direct_response"

    if re.search(r"https?://|www\.", lower):
        suggested_tool = "web"
        reason = "url_detected"
    elif lower.startswith("/image") or any(x in lower for x in [
        "generate image",
        "create image",
        "make image",
        "draw",
        "image of",
        "picture of",
    ]):
        suggested_tool = "image"
        reason = "image_intent_detected"
    elif any(x in lower for x in [
        "analyze attachment",
        "look at this image",
        "what is in this image",
        "read this screenshot",
    ]):
        suggested_tool = "vision"
        reason = "vision_intent_detected"

    shape_data = decide_agent_response_shape(
        user_text=user_text,
        session=session,
    )

    return {
        "suggested_tool": suggested_tool,
        "reason": reason,
        "response_shape": shape_data,
    }


def build_agent_decision_header(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    tool_choice = decide_agent_tool_choice(
        user_text=user_text,
        session=session,
    )
    response_shape = tool_choice.get("response_shape") or {}

    lines = [
        "Decision rules:",
        f"- suggested_tool: {tool_choice.get('suggested_tool') or 'none'}",
        f"- tool_reason: {tool_choice.get('reason') or 'direct_response'}",
        f"- response_shape: {response_shape.get('shape') or 'default'}",
        f"- tone: {response_shape.get('tone') or 'direct'}",
        f"- preferred_format: {response_shape.get('preferred_format') or 'plain'}",
    ]

    if bool(response_shape.get("requires_full_output")):
        lines.append("- full_output_required: yes")

    if bool(response_shape.get("should_minimize_explanation")):
        lines.append("- minimize_explanation: yes")
    else:
        lines.append("- minimize_explanation: no")

    for item in safe_list(response_shape.get("recent_assistant_texts")):
        item_text = normalize_text(item).strip()
        if item_text:
            lines.append(f"- recent_assistant: {item_text}")

    return "\n".join(lines).strip()

# =========================================================
# PHASE K — AGENT AUTONOMY + TASK LOOP LOCK
# =========================================================

def build_agent_task_loop(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    mode = "single_pass"
    max_steps = 1
    allow_recheck = False
    completion_style = "direct"

    if any(x in lower for x in [
        "phase",
        "plan",
        "roadmap",
        "what now",
        "next",
    ]):
        mode = "planner"
        max_steps = 3
        allow_recheck = True
        completion_style = "tight_plan"
    elif any(x in lower for x in [
        "fix",
        "patch",
        "replace",
        "rewrite",
        "refactor",
        "smff",
        "full file",
    ]):
        mode = "executor"
        max_steps = 3
        allow_recheck = True
        completion_style = "deliver_work"
    elif re.search(r"https?://|www\.", lower):
        mode = "tool_route"
        max_steps = 2
        allow_recheck = False
        completion_style = "route_clean"
    elif any(x in lower for x in [
        "compare",
        "analyze",
        "review",
        "check",
        "audit",
    ]):
        mode = "analysis"
        max_steps = 2
        allow_recheck = True
        completion_style = "concise_analysis"

    tasks: list[str] = []

    if mode == "planner":
        tasks = [
            "Infer the exact next move.",
            "Keep sequence tight.",
            "Return only the move that matters now.",
        ]
    elif mode == "executor":
        tasks = [
            "Identify the concrete deliverable.",
            "Prefer working implementation.",
            "Minimize discussion and ship the result.",
        ]
    elif mode == "tool_route":
        tasks = [
            "Detect the correct route.",
            "Do not over-explain.",
            "Return the routed result cleanly.",
        ]
    elif mode == "analysis":
        tasks = [
            "Inspect the request.",
            "Summarize only the important outcome.",
            "Keep wording tight.",
        ]
    else:
        tasks = [
            "Answer directly.",
            "Do not waste motion.",
            "Finish in one pass.",
        ]

    return {
        "mode": mode,
        "max_steps": max_steps,
        "allow_recheck": allow_recheck,
        "completion_style": completion_style,
        "tasks": tasks[:4],
    }


def build_agent_autonomy_header(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    loop_data = build_agent_task_loop(
        user_text=user_text,
        session=session,
    )

    lines = [
        "Autonomy rules:",
        f"- mode: {loop_data.get('mode') or 'single_pass'}",
        f"- max_steps: {int(loop_data.get('max_steps') or 1)}",
        f"- allow_recheck: {'yes' if bool(loop_data.get('allow_recheck')) else 'no'}",
        f"- completion_style: {loop_data.get('completion_style') or 'direct'}",
        "- complete the task with minimum wasted motion",
        "- do not stall",
        "- do not drift",
    ]

    for task in safe_list(loop_data.get("tasks")):
        task_text = normalize_text(task).strip()
        if task_text:
            lines.append(f"- task: {task_text}")

    return "\n".join(lines).strip()

# =========================================================
# PHASE L — AGENT SELF-CHECK + FINAL ANSWER CONTRACT LOCK
# =========================================================

def build_agent_self_check(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    must_return_code = False
    must_return_next_move = False
    must_be_concise = True
    should_verify_fit = True
    contract = "direct_answer"

    if any(x in lower for x in [
        "smff",
        "full file",
        "whole file",
        "entire file",
        "send the file",
        "replace this",
    ]):
        must_return_code = True
        contract = "full_file_delivery"
    elif any(x in lower for x in [
        "phase",
        "next",
        "what now",
        "roadmap",
        "plan",
    ]):
        must_return_next_move = True
        contract = "next_move_only"
    elif any(x in lower for x in [
        "explain",
        "why",
        "teach me",
        "walk me through",
        "step by step",
    ]):
        must_be_concise = False
        contract = "guided_answer"

    checks: list[str] = [
        "Match the user's style.",
        "Do the answer shape that fits the request.",
        "Avoid wasting motion.",
    ]

    if must_return_code:
        checks.extend([
            "Return working code, not partial theory.",
            "Prefer full output when requested.",
        ])

    if must_return_next_move:
        checks.extend([
            "Return the exact next move.",
            "Do not branch into side quests.",
        ])

    if must_be_concise:
        checks.extend([
            "Keep it tight.",
            "Cut filler.",
        ])

    return {
        "must_return_code": must_return_code,
        "must_return_next_move": must_return_next_move,
        "must_be_concise": must_be_concise,
        "should_verify_fit": should_verify_fit,
        "contract": contract,
        "checks": checks[:6],
    }


def build_agent_final_answer_header(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    self_check = build_agent_self_check(
        user_text=user_text,
        session=session,
    )

    lines = [
        "Final answer contract:",
        f"- contract: {self_check.get('contract') or 'direct_answer'}",
        f"- must_return_code: {'yes' if bool(self_check.get('must_return_code')) else 'no'}",
        f"- must_return_next_move: {'yes' if bool(self_check.get('must_return_next_move')) else 'no'}",
        f"- must_be_concise: {'yes' if bool(self_check.get('must_be_concise')) else 'no'}",
        f"- should_verify_fit: {'yes' if bool(self_check.get('should_verify_fit')) else 'no'}",
        "- before answering, self-check output against the request",
        "- if the answer drifts, tighten it",
    ]

    for item in safe_list(self_check.get("checks")):
        item_text = normalize_text(item).strip()
        if item_text:
            lines.append(f"- check: {item_text}")

    return "\n".join(lines).strip()

# =========================================================
# PHASE M — AGENT MEMORY WEIGHTING + PRIORITY SELECTION LOCK
# =========================================================

def score_agent_memory_item(
    *,
    item: dict[str, Any],
    user_text: str,
) -> int:
    if not isinstance(item, dict):
        return 0

    text = normalize_text(user_text or "").lower()
    mem_text = normalize_text(item.get("text") or "").lower()

    if not mem_text:
        return 0

    score = 0

    user_tokens = set(re.findall(r"[a-zA-Z0-9_]+", text))
    mem_tokens = set(re.findall(r"[a-zA-Z0-9_]+", mem_text))
    overlap = len(user_tokens & mem_tokens)
    score += overlap * 5

    priority_terms = [
        "smff",
        "full file",
        "direct",
        "solution-first",
        "powershell",
        "no explanations",
        "endgame",
        "full code",
        "file path",
    ]

    for term in priority_terms:
        if term in mem_text:
            score += 8
        if term in text and term in mem_text:
            score += 12

    kind = str(item.get("kind") or "").strip().lower()
    source = str(item.get("source") or "").strip().lower()

    if kind in {"preference", "rule", "workflow"}:
        score += 10

    if source in {"assistant", "manual", "system"}:
        score += 4

    created_at = normalize_text(item.get("created_at") or "")
    updated_at = normalize_text(item.get("updated_at") or "")

    if updated_at:
        score += 3
    elif created_at:
        score += 1

    return score


def select_agent_memory(
    *,
    user_text: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    memory_items = safe_list(load_memory())
    scored: list[dict[str, Any]] = []

    for item in memory_items:
        if not isinstance(item, dict):
            continue

        item_score = score_agent_memory_item(
            item=item,
            user_text=user_text,
        )

        if item_score <= 0:
            continue

        enriched = dict(item)
        enriched["_agent_score"] = item_score
        scored.append(enriched)

    scored.sort(
        key=lambda x: (
            int(x.get("_agent_score") or 0),
            normalize_text(x.get("updated_at") or x.get("created_at") or ""),
        ),
        reverse=True,
    )

    return scored[: max(1, int(limit or 6))]


def build_agent_memory_priority_header(
    *,
    user_text: str,
) -> str:
    selected = select_agent_memory(user_text=user_text, limit=6)

    lines = [
        "Memory priority rules:",
        "- favor the user's stable preferences",
        "- favor recent useful memory when relevance is close",
        "- prioritize execution preferences over general style notes",
        "- do not overload the answer with too much memory",
    ]

    for item in selected:
        txt = normalize_text(item.get("text") or "").strip()
        score = int(item.get("_agent_score") or 0)
        if txt:
            lines.append(f"- memory[{score}]: {txt}")

    return "\n".join(lines).strip()

# =========================================================
# PHASE N — AGENT CONFLICT RESOLUTION + INSTRUCTION HIERARCHY LOCK
# =========================================================

def build_agent_instruction_hierarchy(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    live_user_priority = 100
    recent_context_priority = 80
    stable_memory_priority = 60
    default_behavior_priority = 20

    live_rules: list[str] = []
    memory_rules: list[str] = []
    override_reason = "default"

    if any(x in lower for x in [
        "smff",
        "full file",
        "whole file",
        "entire file",
        "send the file",
    ]):
        live_rules.append("Return full working file output.")
        override_reason = "full_file_requested"

    if any(x in lower for x in [
        "no explanations",
        "no explanation",
        "just do it",
        "go now",
        "endgame",
    ]):
        live_rules.append("Minimize explanation hard.")
        override_reason = "user_requested_minimal_explanation"

    if any(x in lower for x in [
        "phase",
        "what now",
        "next",
        "roadmap",
        "plan",
    ]):
        live_rules.append("Return the next move only.")
        override_reason = "next_move_requested"

    selected_memory = select_agent_memory(
        user_text=user_text,
        limit=5,
    )

    for item in selected_memory:
        mem_text = normalize_text(item.get("text") or "").strip()
        if mem_text:
            memory_rules.append(mem_text)

    recent_messages = safe_list(session.get("messages"))[-6:]
    recent_rules: list[str] = []

    for msg in recent_messages:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "") != "user":
            continue
        msg_text = normalize_text(msg.get("text") or "").strip()
        if not msg_text:
            continue
        recent_rules.append(msg_text[:220])

    return {
        "live_user_priority": live_user_priority,
        "recent_context_priority": recent_context_priority,
        "stable_memory_priority": stable_memory_priority,
        "default_behavior_priority": default_behavior_priority,
        "live_rules": live_rules[:4],
        "memory_rules": memory_rules[:5],
        "recent_rules": recent_rules[-3:],
        "override_reason": override_reason,
    }


def build_agent_conflict_resolution(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    hierarchy = build_agent_instruction_hierarchy(
        user_text=user_text,
        session=session,
    )

    live_rules = safe_list(hierarchy.get("live_rules"))
    memory_rules = safe_list(hierarchy.get("memory_rules"))

    final_rules: list[str] = []
    conflict_notes: list[str] = []

    for rule in live_rules:
        rule_text = normalize_text(rule).strip()
        if rule_text and rule_text not in final_rules:
            final_rules.append(rule_text)

    for rule in memory_rules:
        rule_text = normalize_text(rule).strip()
        if not rule_text:
            continue
        if rule_text in final_rules:
            continue
        final_rules.append(rule_text)

    if live_rules and memory_rules:
        conflict_notes.append("Live user request overrides stored memory when they conflict.")

    if not live_rules:
        conflict_notes.append("No strong live override detected. Use best-fit memory and defaults.")

    if any("full working file" in normalize_text(x).lower() for x in final_rules):
        conflict_notes.append("Prefer complete implementation over partial snippets.")

    if any("minimize explanation" in normalize_text(x).lower() for x in final_rules):
        conflict_notes.append("Keep wording tight unless the user explicitly asks for teaching.")

    return {
        "final_rules": final_rules[:8],
        "conflict_notes": conflict_notes[:4],
        "override_reason": hierarchy.get("override_reason") or "default",
    }


def build_agent_conflict_header(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    hierarchy = build_agent_instruction_hierarchy(
        user_text=user_text,
        session=session,
    )
    resolution = build_agent_conflict_resolution(
        user_text=user_text,
        session=session,
    )

    lines = [
        "Conflict resolution rules:",
        f"- live_user_priority: {int(hierarchy.get('live_user_priority') or 100)}",
        f"- recent_context_priority: {int(hierarchy.get('recent_context_priority') or 80)}",
        f"- stable_memory_priority: {int(hierarchy.get('stable_memory_priority') or 60)}",
        f"- default_behavior_priority: {int(hierarchy.get('default_behavior_priority') or 20)}",
        f"- override_reason: {resolution.get('override_reason') or 'default'}",
        "- when conflict exists, obey the current user request first",
        "- use memory to reinforce style, not to fight the current request",
    ]

    for item in safe_list(resolution.get("final_rules")):
        item_text = normalize_text(item).strip()
        if item_text:
            lines.append(f"- final_rule: {item_text}")

    for item in safe_list(resolution.get("conflict_notes")):
        item_text = normalize_text(item).strip()
        if item_text:
            lines.append(f"- note: {item_text}")

    return "\n".join(lines).strip()

# =========================================================
# ULTIMATE ENDGAME MOVE — AGENT BRAIN CONSOLIDATION LOCK
# =========================================================

AGENT_PRIORITY_TERMS = [
    "smff",
    "full file",
    "whole file",
    "entire file",
    "send the file",
    "full code",
    "file path",
    "powershell",
    "direct",
    "solution-first",
    "endgame",
    "no explanations",
]

def agent_tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", normalize_text(value or "").lower()))


def score_agent_memory_item(
    *,
    item: dict[str, Any],
    user_text: str,
) -> int:
    if not isinstance(item, dict):
        return 0

    text = normalize_text(user_text or "").lower()
    mem_text = normalize_text(item.get("text") or "").lower()
    if not mem_text:
        return 0

    score = 0

    user_tok = agent_tokens(text)
    mem_tok = agent_tokens(mem_text)
    overlap = len(user_tok & mem_tok)
    score += overlap * 5

    for term in AGENT_PRIORITY_TERMS:
        if term in mem_text:
            score += 8
        if term in text and term in mem_text:
            score += 12

    kind = normalize_text(item.get("kind") or "").lower()
    source = normalize_text(item.get("source") or "").lower()

    if kind in {"preference", "rule", "workflow"}:
        score += 10
    if source in {"assistant", "manual", "system"}:
        score += 4

    if normalize_text(item.get("updated_at") or ""):
        score += 3
    elif normalize_text(item.get("created_at") or ""):
        score += 1

    return score


def select_agent_memory(
    *,
    user_text: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    memory_items = safe_list(load_memory())
    scored: list[dict[str, Any]] = []

    for item in memory_items:
        if not isinstance(item, dict):
            continue

        item_score = score_agent_memory_item(
            item=item,
            user_text=user_text,
        )
        if item_score <= 0:
            continue

        enriched = dict(item)
        enriched["_agent_score"] = item_score
        scored.append(enriched)

    scored.sort(
        key=lambda x: (
            int(x.get("_agent_score") or 0),
            normalize_text(x.get("updated_at") or x.get("created_at") or ""),
        ),
        reverse=True,
    )

    return scored[: max(1, int(limit or 5))]


def build_agent_context(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    recent_messages = safe_list(session.get("messages"))[-8:]
    recent_text = "\n".join(
        normalize_text(m.get("text") or "")
        for m in recent_messages
        if isinstance(m, dict)
    ).strip()

    matched_memory = select_agent_memory(
        user_text=user_text,
        limit=5,
    )

    return {
        "recent_text": recent_text,
        "matched_memory": matched_memory,
    }


def build_agent_plan(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()

    action_mode = "respond"
    intent = "general"
    plan_steps: list[str] = []

    if re.search(r"https?://|www\.", lower):
        action_mode = "tool"
        intent = "web"
        plan_steps = [
            "Detected URL in user input.",
            "Route to web handling.",
            "Return result with minimal extra explanation.",
        ]
    elif lower.startswith("/image") or any(x in lower for x in [
        "generate image", "create image", "make image", "draw", "image of", "picture of",
    ]):
        action_mode = "tool"
        intent = "image"
        plan_steps = [
            "Detected image-generation intent.",
            "Route to image handling.",
            "Return generated result cleanly.",
        ]
    elif any(x in lower for x in [
        "fix", "patch", "replace", "rewrite", "refactor", "smff", "full file",
    ]):
        action_mode = "execute"
        intent = "code"
        plan_steps = [
            "User wants direct execution-style help.",
            "Prefer full working code over discussion.",
            "Return concrete implementation.",
        ]
    elif any(x in lower for x in [
        "plan", "phase", "next", "roadmap", "what now",
    ]):
        action_mode = "plan"
        intent = "planning"
        plan_steps = [
            "User wants next-step guidance.",
            "Keep sequence tight and actionable.",
            "Return the next exact move.",
        ]
    else:
        plan_steps = [
            "Answer directly.",
            "Keep response concise and useful.",
            "Avoid wasted motion.",
        ]

    recent_messages = safe_list(session.get("messages"))[-6:]
    recent_user_texts: list[str] = []

    for msg in recent_messages:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "") != "user":
            continue
        txt = normalize_text(msg.get("text") or "").strip()
        if txt:
            recent_user_texts.append(txt)

    return {
        "action_mode": action_mode,
        "intent": intent,
        "plan_steps": plan_steps[:4],
        "recent_user_texts": recent_user_texts[-3:],
    }


def decide_agent_response_shape(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    lower = normalize_text(user_text or "").lower()

    shape = "default"
    tone = "direct"
    requires_full_output = False
    should_minimize_explanation = True
    preferred_format = "plain"

    if any(x in lower for x in [
        "smff", "full file", "whole file", "entire file", "send the file",
    ]):
        shape = "full_file"
        requires_full_output = True
        preferred_format = "code"
    elif any(x in lower for x in [
        "step by step", "walk me through", "teach me", "explain", "why",
    ]):
        shape = "guided"
        tone = "clear"
        should_minimize_explanation = False
        preferred_format = "structured"
    elif any(x in lower for x in [
        "phase", "next", "what now", "roadmap", "plan",
    ]):
        shape = "next_move"
        preferred_format = "tight"
    elif any(x in lower for x in [
        "fix", "patch", "replace", "rewrite", "refactor",
    ]):
        shape = "implementation"
        requires_full_output = True
        preferred_format = "code"

    return {
        "shape": shape,
        "tone": tone,
        "requires_full_output": requires_full_output,
        "should_minimize_explanation": should_minimize_explanation,
        "preferred_format": preferred_format,
    }


def decide_agent_tool_choice(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    lower = normalize_text(user_text or "").lower()

    suggested_tool = "none"
    reason = "direct_response"

    if re.search(r"https?://|www\.", lower):
        suggested_tool = "web"
        reason = "url_detected"
    elif lower.startswith("/image") or any(x in lower for x in [
        "generate image", "create image", "make image", "draw", "image of", "picture of",
    ]):
        suggested_tool = "image"
        reason = "image_intent_detected"
    elif any(x in lower for x in [
        "analyze attachment", "look at this image", "what is in this image", "read this screenshot",
    ]):
        suggested_tool = "vision"
        reason = "vision_intent_detected"

    return {
        "suggested_tool": suggested_tool,
        "reason": reason,
        "response_shape": decide_agent_response_shape(
            user_text=user_text,
            session=session,
        ),
    }


def build_agent_task_loop(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    lower = normalize_text(user_text or "").lower()

    mode = "single_pass"
    max_steps = 1
    allow_recheck = False
    completion_style = "direct"

    if any(x in lower for x in ["phase", "plan", "roadmap", "what now", "next"]):
        mode = "planner"
        max_steps = 3
        allow_recheck = True
        completion_style = "tight_plan"
    elif any(x in lower for x in [
        "fix", "patch", "replace", "rewrite", "refactor", "smff", "full file",
    ]):
        mode = "executor"
        max_steps = 3
        allow_recheck = True
        completion_style = "deliver_work"
    elif re.search(r"https?://|www\.", lower):
        mode = "tool_route"
        max_steps = 2
        allow_recheck = False
        completion_style = "route_clean"
    elif any(x in lower for x in ["compare", "analyze", "review", "check", "audit"]):
        mode = "analysis"
        max_steps = 2
        allow_recheck = True
        completion_style = "concise_analysis"

    tasks: list[str] = []

    if mode == "planner":
        tasks = [
            "Infer the exact next move.",
            "Keep sequence tight.",
            "Return only the move that matters now.",
        ]
    elif mode == "executor":
        tasks = [
            "Identify the concrete deliverable.",
            "Prefer working implementation.",
            "Minimize discussion and ship the result.",
        ]
    elif mode == "tool_route":
        tasks = [
            "Detect the correct route.",
            "Do not over-explain.",
            "Return the routed result cleanly.",
        ]
    elif mode == "analysis":
        tasks = [
            "Inspect the request.",
            "Summarize only the important outcome.",
            "Keep wording tight.",
        ]
    else:
        tasks = [
            "Answer directly.",
            "Do not waste motion.",
            "Finish in one pass.",
        ]

    return {
        "mode": mode,
        "max_steps": max_steps,
        "allow_recheck": allow_recheck,
        "completion_style": completion_style,
        "tasks": tasks[:4],
    }


def build_agent_self_check(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    lower = normalize_text(user_text or "").lower()

    must_return_code = False
    must_return_next_move = False
    must_be_concise = True
    should_verify_fit = True
    contract = "direct_answer"

    if any(x in lower for x in [
        "smff", "full file", "whole file", "entire file", "send the file", "replace this",
    ]):
        must_return_code = True
        contract = "full_file_delivery"
    elif any(x in lower for x in [
        "phase", "next", "what now", "roadmap", "plan",
    ]):
        must_return_next_move = True
        contract = "next_move_only"
    elif any(x in lower for x in [
        "explain", "why", "teach me", "walk me through", "step by step",
    ]):
        must_be_concise = False
        contract = "guided_answer"

    checks: list[str] = [
        "Match the user's style.",
        "Do the answer shape that fits the request.",
        "Avoid wasting motion.",
    ]

    if must_return_code:
        checks.extend([
            "Return working code, not partial theory.",
            "Prefer full output when requested.",
        ])

    if must_return_next_move:
        checks.extend([
            "Return the exact next move.",
            "Do not branch into side quests.",
        ])

    if must_be_concise:
        checks.extend([
            "Keep it tight.",
            "Cut filler.",
        ])

    return {
        "must_return_code": must_return_code,
        "must_return_next_move": must_return_next_move,
        "must_be_concise": must_be_concise,
        "should_verify_fit": should_verify_fit,
        "contract": contract,
        "checks": checks[:6],
    }


def build_agent_instruction_hierarchy(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    lower = normalize_text(user_text or "").lower()

    live_user_priority = 100
    recent_context_priority = 80
    stable_memory_priority = 60
    default_behavior_priority = 20

    live_rules: list[str] = []
    override_reason = "default"

    if any(x in lower for x in [
        "smff", "full file", "whole file", "entire file", "send the file",
    ]):
        live_rules.append("Return full working file output.")
        override_reason = "full_file_requested"

    if any(x in lower for x in [
        "no explanations", "no explanation", "just do it", "go now", "endgame",
    ]):
        live_rules.append("Minimize explanation hard.")
        override_reason = "user_requested_minimal_explanation"

    if any(x in lower for x in [
        "phase", "what now", "next", "roadmap", "plan",
    ]):
        live_rules.append("Return the next move only.")
        override_reason = "next_move_requested"

    memory_rules: list[str] = []
    for item in select_agent_memory(user_text=user_text, limit=5):
        mem_text = normalize_text(item.get("text") or "").strip()
        if mem_text:
            memory_rules.append(mem_text)

    recent_rules: list[str] = []
    for msg in safe_list(session.get("messages"))[-6:]:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "") != "user":
            continue
        msg_text = normalize_text(msg.get("text") or "").strip()
        if msg_text:
            recent_rules.append(msg_text[:220])

    return {
        "live_user_priority": live_user_priority,
        "recent_context_priority": recent_context_priority,
        "stable_memory_priority": stable_memory_priority,
        "default_behavior_priority": default_behavior_priority,
        "live_rules": live_rules[:4],
        "memory_rules": memory_rules[:5],
        "recent_rules": recent_rules[-3:],
        "override_reason": override_reason,
    }


def build_agent_conflict_resolution(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    hierarchy = build_agent_instruction_hierarchy(
        user_text=user_text,
        session=session,
    )

    final_rules: list[str] = []
    conflict_notes: list[str] = []

    for rule in safe_list(hierarchy.get("live_rules")):
        rule_text = normalize_text(rule).strip()
        if rule_text and rule_text not in final_rules:
            final_rules.append(rule_text)

    for rule in safe_list(hierarchy.get("memory_rules")):
        rule_text = normalize_text(rule).strip()
        if rule_text and rule_text not in final_rules:
            final_rules.append(rule_text)

    if hierarchy.get("live_rules") and hierarchy.get("memory_rules"):
        conflict_notes.append("Live user request overrides stored memory when they conflict.")
    if not hierarchy.get("live_rules"):
        conflict_notes.append("No strong live override detected. Use best-fit memory and defaults.")
    if any("full working file" in normalize_text(x).lower() for x in final_rules):
        conflict_notes.append("Prefer complete implementation over partial snippets.")
    if any("minimize explanation" in normalize_text(x).lower() for x in final_rules):
        conflict_notes.append("Keep wording tight unless the user explicitly asks for teaching.")

    return {
        "final_rules": final_rules[:8],
        "conflict_notes": conflict_notes[:4],
        "override_reason": hierarchy.get("override_reason") or "default",
    }


def build_agent_brain_bundle(
    *,
    user_text: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    ctx = build_agent_context(user_text=user_text, session=session)
    plan = build_agent_plan(user_text=user_text, session=session)
    tool_choice = decide_agent_tool_choice(user_text=user_text, session=session)
    task_loop = build_agent_task_loop(user_text=user_text, session=session)
    self_check = build_agent_self_check(user_text=user_text, session=session)
    hierarchy = build_agent_instruction_hierarchy(user_text=user_text, session=session)
    conflict = build_agent_conflict_resolution(user_text=user_text, session=session)

    return {
        "context": ctx,
        "plan": plan,
        "tool_choice": tool_choice,
        "task_loop": task_loop,
        "self_check": self_check,
        "hierarchy": hierarchy,
        "conflict": conflict,
        "selected_memory": select_agent_memory(user_text=user_text, limit=5),
    }


def build_agent_system_prompt(
    *,
    user_text: str,
    session: dict[str, Any],
) -> str:
    bundle = build_agent_brain_bundle(
        user_text=user_text,
        session=session,
    )

    ctx = bundle["context"]
    plan = bundle["plan"]
    tool_choice = bundle["tool_choice"]
    response_shape = tool_choice.get("response_shape") or {}
    task_loop = bundle["task_loop"]
    self_check = bundle["self_check"]
    conflict = bundle["conflict"]

    mem_lines: list[str] = []
    for item in safe_list(ctx.get("matched_memory")):
        txt = normalize_text(item.get("text") or "").strip()
        score = int(item.get("_agent_score") or 0)
        if txt:
            mem_lines.append(f"- [{score}] {txt}")

    recent_block = normalize_text(ctx.get("recent_text") or "").strip()

    parts = [
        "You are Nova.",
        "Follow the user's style hard.",
        "Be direct.",
        "Be solution-first.",
        "Prefer full working output over explanation.",
        "Do not waste motion.",
        "",
        "Execution:",
        f"- action_mode: {plan.get('action_mode') or 'respond'}",
        f"- intent: {plan.get('intent') or 'general'}",
        f"- suggested_tool: {tool_choice.get('suggested_tool') or 'none'}",
        f"- tool_reason: {tool_choice.get('reason') or 'direct_response'}",
        f"- response_shape: {response_shape.get('shape') or 'default'}",
        f"- tone: {response_shape.get('tone') or 'direct'}",
        f"- preferred_format: {response_shape.get('preferred_format') or 'plain'}",
        f"- completion_style: {task_loop.get('completion_style') or 'direct'}",
        f"- max_steps: {int(task_loop.get('max_steps') or 1)}",
        f"- allow_recheck: {'yes' if bool(task_loop.get('allow_recheck')) else 'no'}",
        "",
        "Final answer contract:",
        f"- contract: {self_check.get('contract') or 'direct_answer'}",
        f"- must_return_code: {'yes' if bool(self_check.get('must_return_code')) else 'no'}",
        f"- must_return_next_move: {'yes' if bool(self_check.get('must_return_next_move')) else 'no'}",
        f"- must_be_concise: {'yes' if bool(self_check.get('must_be_concise')) else 'no'}",
        "- self-check answer against request before finishing",
        "- if drifting, tighten and finish",
        "",
        "Conflict rules:",
        f"- override_reason: {conflict.get('override_reason') or 'default'}",
        "- current user request overrides stored memory when they conflict",
        "- use memory to reinforce style, not fight live instructions",
    ]

    for item in safe_list(plan.get("plan_steps")):
        item_text = normalize_text(item).strip()
        if item_text:
            parts.append(f"- plan: {item_text}")

    for item in safe_list(task_loop.get("tasks")):
        item_text = normalize_text(item).strip()
        if item_text:
            parts.append(f"- task: {item_text}")

    for item in safe_list(self_check.get("checks")):
        item_text = normalize_text(item).strip()
        if item_text:
            parts.append(f"- check: {item_text}")

    for item in safe_list(conflict.get("final_rules")):
        item_text = normalize_text(item).strip()
        if item_text:
            parts.append(f"- final_rule: {item_text}")

    if mem_lines:
        parts.append("")
        parts.append("Relevant user memory:")
        parts.extend(mem_lines)

    if recent_block:
        parts.append("")
        parts.append("Recent conversation context:")
        parts.append(recent_block)

    return "\n".join(parts).strip()

# =========================================================
# POST-RESPONSE CLEANUP + ANTI-WAFFLE LOCK
# =========================================================

ANTI_WAFFLE_OPENERS = [
    "sure,",
    "absolutely,",
    "of course,",
    "certainly,",
    "here's",
    "here is",
    "no problem,",
    "got it,",
]

ANTI_WAFFLE_FILLER_LINES = {
    "let me know if you want me to keep going.",
    "let me know if you'd like me to continue.",
    "if you want, i can keep going.",
    "if you'd like, i can continue.",
    "i can help with that.",
    "hope that helps.",
}

def cleanup_agent_response(text: Any) -> str:
    value = str(text or "")
    if not value.strip():
        return ""

    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines: list[str] = []

    blank_run = 0
    for raw_line in lines:
        line = raw_line.rstrip()

        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            cleaned_lines.append("")
            continue

        blank_run = 0
        low = line.strip().lower()

        if low in ANTI_WAFFLE_FILLER_LINES:
            continue

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()

    lower = cleaned.lower()
    for opener in ANTI_WAFFLE_OPENERS:
        if lower.startswith(opener):
            cleaned = cleaned[len(opener):].lstrip(" \t\n-:,.")
            lower = cleaned.lower()
            break

    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned


def enforce_agent_response_contract(
    *,
    text: Any,
    user_text: str,
    session: dict[str, Any],
) -> str:
    cleaned = cleanup_agent_response(text)

    self_check = build_agent_self_check(
        user_text=user_text,
        session=session,
    )
    response_shape = decide_agent_response_shape(
        user_text=user_text,
        session=session,
    )
    conflict = build_agent_conflict_resolution(
        user_text=user_text,
        session=session,
    )

    must_be_concise = bool(self_check.get("must_be_concise"))
    requires_full_output = bool(response_shape.get("requires_full_output"))
    should_minimize_explanation = bool(response_shape.get("should_minimize_explanation"))

    if must_be_concise or should_minimize_explanation:
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    final_rules = [
        normalize_text(x).strip().lower()
        for x in safe_list(conflict.get("final_rules"))
        if normalize_text(x).strip()
    ]

    if any("minimize explanation" in rule for rule in final_rules):
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        if len(paragraphs) > 5:
            cleaned = "\n\n".join(paragraphs[:5]).strip()

    if not requires_full_output and len(cleaned) > 4000:
        cleaned = cleaned[:4000].rstrip() + "\n\n[trimmed for brevity]"

    return cleaned.strip()


def finalize_agent_response(
    *,
    text: Any,
    user_text: str,
    session: dict[str, Any],
) -> str:
    cleaned = enforce_agent_response_contract(
        text=text,
        user_text=user_text,
        session=session,
    )

    if not cleaned:
        fallback = "Done."
        self_check = build_agent_self_check(
            user_text=user_text,
            session=session,
        )
        if bool(self_check.get("must_return_next_move")):
            fallback = "Next move ready."
        elif bool(self_check.get("must_return_code")):
            fallback = "# No output generated."
        return fallback

    return cleaned

# =========================================================
# PHASE TOOL FOLLOW-THROUGH LOCK
# =========================================================

def detect_agent_tool_route(
    *,
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = normalize_text(user_text or "")
    lower = text.lower()
    items = safe_list(attachments)

    has_url = bool(re.search(r"https?://|www\.", lower))
    has_image_attachment = False
    has_video_attachment = False
    has_other_attachment = False

    for item in items:
        if not isinstance(item, dict):
            continue
        mime = normalize_text(
            item.get("mime_type")
            or item.get("content_type")
            or item.get("type")
            or ""
        ).lower()
        name = normalize_text(item.get("name") or item.get("filename") or "").lower()

        probe = f"{mime} {name}".strip()

        if "image/" in mime or any(name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]):
            has_image_attachment = True
        elif "video/" in mime or any(name.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]):
            has_video_attachment = True
        elif probe:
            has_other_attachment = True

    route = "chat"
    reason = "default_chat"
    should_force_tool = False

    image_terms = [
        "generate image",
        "create image",
        "make image",
        "draw",
        "image of",
        "picture of",
        "/image",
    ]

    vision_terms = [
        "look at this image",
        "what is in this image",
        "analyze this image",
        "read this screenshot",
        "describe this image",
        "what do you see",
        "analyze attachment",
    ]

    web_terms = [
        "/web",
        "open this link",
        "check this site",
        "summarize this page",
        "read this url",
        "visit this link",
    ]

    if has_url or any(term in lower for term in web_terms):
        route = "web"
        reason = "url_or_web_intent"
        should_force_tool = True
    elif lower.startswith("/image") or any(term in lower for term in image_terms):
        route = "image"
        reason = "image_generation_intent"
        should_force_tool = True
    elif has_image_attachment and any(term in lower for term in vision_terms):
        route = "vision"
        reason = "image_attachment_analysis_intent"
        should_force_tool = True
    elif has_image_attachment and not text.strip():
        route = "vision"
        reason = "image_attachment_present"
        should_force_tool = True
    elif has_video_attachment:
        route = "video"
        reason = "video_attachment_present"
        should_force_tool = True
    elif has_other_attachment and "analyze" in lower:
        route = "attachment"
        reason = "generic_attachment_analysis_intent"
        should_force_tool = True

    return {
        "route": route,
        "reason": reason,
        "has_url": has_url,
        "has_image_attachment": has_image_attachment,
        "has_video_attachment": has_video_attachment,
        "has_other_attachment": has_other_attachment,
        "should_force_tool": should_force_tool,
    }


def build_agent_tool_follow_through_header(
    *,
    user_text: str,
    session: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    route_data = detect_agent_tool_route(
        user_text=user_text,
        attachments=attachments,
    )

    lines = [
        "Tool follow-through rules:",
        f"- forced_route: {route_data.get('route') or 'chat'}",
        f"- route_reason: {route_data.get('reason') or 'default_chat'}",
        f"- should_force_tool: {'yes' if bool(route_data.get('should_force_tool')) else 'no'}",
        "- if a tool route is clearly detected, do not drift into generic chat",
        "- complete the detected route cleanly",
        "- when tool route is not applicable, fall back to direct chat cleanly",
        "- keep final output aligned with the selected route",
    ]

    return "\n".join(lines).strip()


def finalize_tool_route_output(
    *,
    route_data: dict[str, Any],
    text: Any,
) -> str:
    value = normalize_text(text or "").strip()
    route = normalize_text(route_data.get("route") or "chat").lower()

    if value:
        return value

    if route == "web":
        return "Web route selected."
    if route == "image":
        return "Image route selected."
    if route == "vision":
        return "Image analysis route selected."
    if route == "video":
        return "Video analysis route selected."
    if route == "attachment":
        return "Attachment analysis route selected."
    return "Done."

# =========================================================
# PHASE UI POLISH — RESPONSE SHAPE + DISPLAY CONTRACT LOCK
# =========================================================

def build_ui_message_payload(
    *,
    text: str,
    route_data: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, Any]:
    clean_text = normalize_text(text or "").strip()
    route = normalize_text(route_data.get("route") or "chat").lower()

    payload: dict[str, Any] = {
        "text": clean_text,
        "kind": "chat",
        "badges": [],
        "meta": {},
    }

    if route == "web":
        payload["kind"] = "web"
        payload["badges"].append("web")
        payload["meta"]["source"] = "web_fetch"

    elif route == "image":
        payload["kind"] = "image_generation"
        payload["badges"].append("image")

    elif route == "vision":
        payload["kind"] = "image_analysis"
        payload["badges"].append("vision")

    elif route == "video":
        payload["kind"] = "video_analysis"
        payload["badges"].append("video")

    elif route == "attachment":
        payload["kind"] = "attachment_analysis"
        payload["badges"].append("attachment")

    # tighten preview
    preview = clean_text[:180].strip()
    payload["preview"] = preview

    # add lightweight formatting hints
    if len(clean_text) > 1200:
        payload["meta"]["long"] = True

    if "\n" in clean_text:
        payload["meta"]["multiline"] = True

    return payload


def build_ui_status_meta(
    *,
    route_data: dict[str, Any],
) -> dict[str, Any]:
    route = normalize_text(route_data.get("route") or "chat").lower()

    status = "ready"
    label = "Ready"

    if route == "web":
        label = "Web"
    elif route == "image":
        label = "Image"
    elif route == "vision":
        label = "Vision"
    elif route == "video":
        label = "Video"
    elif route == "attachment":
        label = "Attachment"

    return {
        "status": status,
        "label": label,
    }

def attach_ui_envelope(
    *,
    final_message: dict[str, Any],
    refined_text: str,
    route_data: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(final_message, dict):
        return final_message

    ui_payload = build_ui_message_payload(
        text=refined_text,
        route_data=route_data,
        session=session,
    )

    ui_meta = build_ui_status_meta(
        route_data=route_data,
    )

    enriched = dict(final_message)
    enriched["ui"] = {
        "message": ui_payload,
        "status": ui_meta,
    }

    return enriched








# =========================================================
# FETCH WEB HARDENING + VIDEO PIPELINE LOCK
# =========================================================

WEB_FETCH_TIMEOUT = 20


def normalize_web_url(value: Any) -> str:
    url = normalize_text(value or "").strip()
    if not url:
        return ""

    if url.startswith("www."):
        url = "https://" + url

    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = "https://" + url

    return url.strip()

def extract_first_url_from_text(value: Any) -> str:
    text = normalize_text(value or "")
    match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return normalize_web_url(match.group(1))


def build_web_fetch_result(
    *,
    url: str,
    ok: bool,
    status_code: int | None = None,
    title: str = "",
    description: str = "",
    content: str = "",
    error: str = "",
    ssl_verified: bool = True,
    final_url: str = "",
) -> dict[str, Any]:
    clean_url = normalize_web_url(final_url or url)

    preview = normalize_text(description or content or "").strip()
    if len(preview) > 240:
        preview = preview[:240].rstrip() + "..."

    return {
        "ok": bool(ok),
        "url": clean_url,
        "final_url": clean_url,
        "status_code": status_code,
        "title": normalize_text(title or "").strip(),
        "description": normalize_text(description or "").strip(),
        "content": normalize_text(content or "").strip(),
        "preview": preview,
        "error": normalize_text(error or "").strip(),
        "ssl_verified": bool(ssl_verified),
        "fetched_at": now_iso(),
    }


def fetch_web_page_hardened(url: str) -> dict[str, Any]:
    clean_url = normalize_web_url(url)
    if not clean_url:
        return build_web_fetch_result(
            url=url,
            ok=False,
            error="No valid URL found.",
            ssl_verified=True,
        )

    try:
        response = requests.get(
            clean_url,
            timeout=WEB_FETCH_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Nova Local Fetch)",
            },
            allow_redirects=True,
            verify=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title = ""
        if soup.title and soup.title.string:
            title = normalize_text(soup.title.string).strip()

        description = ""
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta and desc_meta.get("content"):
            description = normalize_text(desc_meta.get("content")).strip()

        body_text = soup.get_text("\n", strip=True)
        if len(body_text) > 8000:
            body_text = body_text[:8000].rstrip()

        return build_web_fetch_result(
            url=clean_url,
            ok=True,
            status_code=int(response.status_code),
            title=title,
            description=description,
            content=body_text,
            ssl_verified=True,
            final_url=str(response.url or clean_url),
        )

    except requests.exceptions.SSLError:
        try:
            response = requests.get(
                clean_url,
                timeout=WEB_FETCH_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (Nova Local Fetch)",
                },
                allow_redirects=True,
                verify=False,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title = ""
            if soup.title and soup.title.string:
                title = normalize_text(soup.title.string).strip()

            description = ""
            desc_meta = soup.find("meta", attrs={"name": "description"})
            if desc_meta and desc_meta.get("content"):
                description = normalize_text(desc_meta.get("content")).strip()

            body_text = soup.get_text("\n", strip=True)
            if len(body_text) > 8000:
                body_text = body_text[:8000].rstrip()

            return build_web_fetch_result(
                url=clean_url,
                ok=True,
                status_code=int(response.status_code),
                title=title,
                description=description,
                content=body_text,
                ssl_verified=False,
                final_url=str(response.url or clean_url),
            )
        except Exception as exc:
            return build_web_fetch_result(
                url=clean_url,
                ok=False,
                error=str(exc) or "Web fetch failed after SSL retry.",
                ssl_verified=False,
            )
    except Exception as exc:
        return build_web_fetch_result(
            url=clean_url,
            ok=False,
            error=str(exc) or "Web fetch failed.",
            ssl_verified=True,
        )


def build_web_artifact_from_fetch_result(
    fetch_result: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    title = normalize_text(fetch_result.get("title") or "").strip() or "Web Result"
    description = normalize_text(fetch_result.get("description") or "").strip()
    content = normalize_text(fetch_result.get("content") or "").strip()
    preview = normalize_text(fetch_result.get("preview") or "").strip()

    body_parts = []
    if description:
        body_parts.append(description)
    if content:
        body_parts.append(content[:3000].rstrip())

    return {
        "title": title,
        "kind": "web_result",
        "body": "\n\n".join(body_parts).strip() or preview or "Fetched web content.",
        "session_id": session_id,
        "meta": {
            "source_url": normalize_text(fetch_result.get("final_url") or fetch_result.get("url") or "").strip(),
            "status_code": fetch_result.get("status_code"),
            "ssl_verified": bool(fetch_result.get("ssl_verified")),
            "fetched_at": normalize_text(fetch_result.get("fetched_at") or "").strip(),
            "preview": preview,
        },
    }


def detect_video_attachments(
    attachments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for item in safe_list(attachments):
        if not isinstance(item, dict):
            continue

        mime = normalize_text(
            item.get("mime_type")
            or item.get("content_type")
            or item.get("type")
            or ""
        ).lower()

        name = normalize_text(item.get("name") or item.get("filename") or "").lower()

        is_video = (
            mime.startswith("video/")
            or name.endswith(".mp4")
            or name.endswith(".mov")
            or name.endswith(".avi")
            or name.endswith(".mkv")
            or name.endswith(".webm")
        )

        if is_video:
            results.append(item)

    return results

# =========================================================
# WEB FETCH NORMALIZATION + AUTO ROUTE (LOCK)
# =========================================================


def build_video_artifact_from_result(
    video_result: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    first_video = safe_list(video_result.get("videos"))[:1]
    first_video = first_video[0] if first_video else {}

    return {
        "title": normalize_text((first_video or {}).get("filename") or "Video Analysis").strip(),
        "kind": "video_analysis",
        "body": normalize_text(video_result.get("summary") or "").strip() or "Video analysis ready.",
        "session_id": session_id,
        "meta": {
            "video_url": normalize_text((first_video or {}).get("url") or "").strip(),
            "mime_type": normalize_text((first_video or {}).get("mime_type") or "").strip(),
        },
    }


# =========================================================
# WEB FETCH HARDEN + VIDEO PIPELINE LOCK
# =========================================================

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

WEB_FETCH_TIMEOUT = 20
WEB_FETCH_TEXT_LIMIT = 4000


def normalize_url(url: str) -> str:
    value = normalize_text(url).strip()
    if not value:
        return ""

    if value.startswith("www."):
        value = "https://" + value

    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value

    return value.rstrip("/")


def extract_url(text: str) -> str:
    match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", text or "", re.IGNORECASE)
    if not match:
        return ""

    raw = match.group(1).strip().rstrip(").,!?]}>\"'")
    if raw.startswith("www."):
        raw = "https://" + raw
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "https://" + raw

    return raw

def clean_web_input(text: str) -> str:
    value = normalize_text(text).strip()

    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1].strip()

    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        value = value[1:-1].strip()

    if value.lower().startswith("/web "):
        value = value[5:].strip()

    return value

def detect_tool_intent(text: str) -> str:
    text = normalize_text(text).strip()
    lowered = text.lower()

    if lowered.startswith("/web "):
        return "web"

    if extract_url(text):
        return "web"

    if _looks_like_current_info_query(text):
        return "current_info"

    if lowered.startswith("/image "):
        return "image"

    return "none"


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def fetch_web(url: str) -> dict[str, Any]:
    normalized = normalize_url(url)
    if not normalized:
        return {
            "ok": False,
            "error": "No valid URL found.",
            "url": "",
            "normalized_url": "",
            "ssl_verified": True,
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Nova/2026",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    ssl_verified = True

    try:
        response = requests.get(
            normalized,
            timeout=WEB_FETCH_TIMEOUT,
            headers=headers,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.exceptions.SSLError:
        ssl_verified = False
        response = requests.get(
            normalized,
            timeout=WEB_FETCH_TIMEOUT,
            headers=headers,
            allow_redirects=True,
            verify=False,
        )
        response.raise_for_status()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "url": normalized,
            "normalized_url": normalized,
            "ssl_verified": ssl_verified,
        }

    final_url = str(response.url or normalized).strip()
    content_type = str(response.headers.get("Content-Type") or "").strip()

    soup = BeautifulSoup(response.text, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string).strip()

    description = ""
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if desc_tag and desc_tag.get("content"):
        description = normalize_text(desc_tag.get("content")).strip()

    site_name = ""
    site_tag = soup.find("meta", attrs={"property": re.compile("^og:site_name$", re.I)})
    if site_tag and site_tag.get("content"):
        site_name = normalize_text(site_tag.get("content")).strip()

    body_text = normalize_text(soup.get_text("\n", strip=True)).strip()
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)
    content = body_text[:WEB_FETCH_TEXT_LIMIT]
    preview = summarize_text(description or content or title or final_url, 240)

    return {
        "ok": True,
        "url": final_url,
        "normalized_url": final_url,
        "domain": _domain_from_url(final_url),
        "title": title,
        "description": description,
        "site_name": site_name,
        "content": content,
        "preview": preview,
        "status_code": int(response.status_code),
        "content_type": content_type,
        "ssl_verified": ssl_verified,
        "fetched_at": now_iso(),
    }


def build_web_result_text(result: dict[str, Any]) -> str:
    lines: list[str] = []

    title = normalize_text(result.get("title") or "").strip()
    description = normalize_text(result.get("description") or "").strip()
    site_name = normalize_text(result.get("site_name") or "").strip()
    domain = normalize_text(result.get("domain") or "").strip()
    url = normalize_text(result.get("url") or "").strip()
    content = normalize_text(result.get("content") or "").strip()

    if title:
        lines.append(title)
    if description:
        lines.append(description)
    if site_name or domain:
        lines.append("Source: " + " · ".join([x for x in [site_name, domain] if x]))
    if url:
        lines.append("URL: " + url)
    if content:
        lines.append(content)

    text = "\n\n".join([x for x in lines if x]).strip()
    return text or "Web result"


def build_web_result_meta(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "web_fetch",
        "source_url": normalize_text(result.get("url") or "").strip(),
        "site_name": normalize_text(result.get("site_name") or "").strip(),
        "domain": normalize_text(result.get("domain") or "").strip(),
        "description": normalize_text(result.get("description") or "").strip(),
        "preview": normalize_text(result.get("preview") or "").strip(),
        "ssl_verified": bool(result.get("ssl_verified")),
        "status_code": int(result.get("status_code") or 0),
        "content_type": normalize_text(result.get("content_type") or "").strip(),
        "fetched_at": normalize_text(result.get("fetched_at") or now_iso()).strip(),
    }


def detect_video_attachments(
    attachments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for item in safe_list(attachments):
        if not isinstance(item, dict):
            continue

        mime = normalize_text(
            item.get("mime_type")
            or item.get("content_type")
            or item.get("type")
            or ""
        ).lower()

        name = normalize_text(
            item.get("name")
            or item.get("filename")
            or ""
        ).lower()

        is_video = (
            mime.startswith("video/")
            or name.endswith(".mp4")
            or name.endswith(".mov")
            or name.endswith(".avi")
            or name.endswith(".mkv")
            or name.endswith(".webm")
        )

        if is_video:
            results.append(item)

    return results


def has_video(attachments: list[dict[str, Any]] | None = None) -> bool:
    return len(detect_video_attachments(attachments)) > 0


def build_video_analysis_result(
    *,
    attachments: list[dict[str, Any]] | None = None,
    user_text: str,
) -> dict[str, Any]:
    videos = detect_video_attachments(attachments)
    if not videos:
        return {
            "ok": False,
            "kind": "video_analysis",
            "summary": "",
            "videos": [],
            "error": "No video attachment found.",
        }

    first_video = videos[0]
    filename = normalize_text(
        first_video.get("filename")
        or first_video.get("name")
        or "video"
    ).strip()

    url = normalize_text(
        first_video.get("url")
        or first_video.get("file_url")
        or first_video.get("source_url")
        or ""
    ).strip()

    prompt_hint = normalize_text(user_text or "").strip()

    summary = (
        f"Video received: {filename}.\n"
        f"Route locked for video analysis."
    )

    if prompt_hint:
        summary += f"\nUser request: {prompt_hint}"

    return {
        "ok": True,
        "kind": "video_analysis",
        "summary": summary.strip(),
        "videos": [
            {
                "filename": filename,
                "url": url,
                "mime_type": normalize_text(
                    first_video.get("mime_type")
                    or first_video.get("content_type")
                    or ""
                ).strip(),
            }
        ],
        "error": "",
    }

# =========================================================
# VIDEO PIPELINE REAL ARTIFACT + VIEWER LOCK
# =========================================================

def detect_video_attachments(
    attachments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for item in safe_list(attachments):
        if not isinstance(item, dict):
            continue

        mime = normalize_text(
            item.get("mime_type")
            or item.get("content_type")
            or item.get("type")
            or ""
        ).lower()

        name = normalize_text(
            item.get("name")
            or item.get("filename")
            or ""
        ).lower()

        is_video = (
            mime.startswith("video/")
            or name.endswith(".mp4")
            or name.endswith(".mov")
            or name.endswith(".avi")
            or name.endswith(".mkv")
            or name.endswith(".webm")
        )

        if is_video:
            results.append(normalize_attachment(item))

    return results


def has_video(attachments: list[dict[str, Any]] | None = None) -> bool:
    return len(detect_video_attachments(attachments)) > 0


def build_video_analysis_result(
    *,
    attachments: list[dict[str, Any]] | None = None,
    user_text: str,
) -> dict[str, Any]:
    videos = detect_video_attachments(attachments)
    if not videos:
        return {
            "ok": False,
            "kind": "video_analysis",
            "summary": "",
            "videos": [],
            "error": "No video attachment found.",
        }

    first_video = videos[0]

    filename = normalize_text(
        first_video.get("filename")
        or first_video.get("name")
        or "video"
    ).strip()

    stored_name = normalize_text(
        first_video.get("stored_name")
        or first_video.get("stored_filename")
        or first_video.get("filename")
        or first_video.get("name")
        or ""
    ).strip()

    raw_video_url = normalize_text(
        first_video.get("url")
        or first_video.get("file_url")
        or first_video.get("source_url")
        or ""
    ).strip()

    if stored_name:
        video_url = f"/api/uploads/{stored_name}"
    else:
        video_url = raw_video_url

    mime_type = normalize_text(
        first_video.get("mime_type")
        or first_video.get("content_type")
        or ""
    ).strip()

    prompt_hint = normalize_text(user_text or "").strip()

    summary_lines = [
        f"Video received: {filename}.",
        "Video artifact saved and ready in the viewer.",
    ]

    if prompt_hint:
        summary_lines.append(f"User request: {prompt_hint}")

    return {
        "ok": True,
        "kind": "video_analysis",
        "summary": "\n".join(summary_lines).strip(),
        "videos": [
            {
                "filename": filename,
                "url": video_url,
                "mime_type": mime_type,
            }
        ],
        "error": "",
    }


def build_video_message_meta(video_result: dict[str, Any]) -> dict[str, Any]:
    videos = safe_list(video_result.get("videos"))
    first_video = videos[0] if videos else {}

    filename = normalize_text(
        first_video.get("filename")
        or "video"
    ).strip()

    video_url = normalize_text(
        first_video.get("url")
        or ""
    ).strip()

    mime_type = normalize_text(
        first_video.get("mime_type")
        or ""
    ).strip()

    summary = normalize_text(video_result.get("summary") or "").strip()

    return {
        "video_url": video_url,
        "mime_type": mime_type,
        "analysis_text": summary,
        "bullets": [
            f"Video: {filename}",
            "Saved as video artifact.",
        ],
    }

# =========================================================
# API CHAT — THIN WRAPPER LOCK (FINAL)
# =========================================================

def chat_single_response(
    session_id: str,
    user_text: str,
    attachments: list[dict[str, Any]] | None = None,
    regenerate_of: str | None = None,
) -> dict[str, Any]:
    store = load_sessions_store()
    session = find_session(store, session_id) or ensure_active_session(store)

    attachments = normalize_attachments(attachments)
    locked_session_id = str(session.get("id") or session_id or "")

    target_message = find_message(session, regenerate_of) if regenerate_of else None
    assistant_message_id = (
        str((target_message or {}).get("id") or "").strip()
        if target_message
        else make_id("assistant")
    )

    if not regenerate_of and (normalize_text(user_text).strip() or attachments):
        append_message(session, make_user_message(user_text, attachments))
        save_sessions_store(store)

    try:
        candidates = extract_memory_candidates(user_text)
        save_memory_items(candidates, locked_session_id)
    except Exception:
        pass

    # -------------------------
    # CURRENT INFO AUTO ROUTE
    # -------------------------
    if detect_tool_intent(user_text) == "current_info":
        current_info = answer_current_info_query(user_text)

        if not current_info.get("ok"):
            return {
                "ok": False,
                "error": current_info.get("error") or "Current-info lookup failed.",
                "session_id": locked_session_id,
                "active_session_id": locked_session_id,
                "debug": {
                    "tool": "current_info",
                    "query": user_text,
                },
            }

        assistant_message = make_assistant_message(
            normalize_text(current_info.get("text") or "").strip() or "No live answer generated.",
            message_id=assistant_message_id,
            source="web_fetch",
            pending=False,
            streaming=False,
            stopped=False,
            error=False,
            meta=build_current_info_meta(current_info),
        )

        if target_message:
            replace_message(session, assistant_message_id, assistant_message)
        else:
            append_message(session, assistant_message)

        recalc_session(session)
        save_sessions_store(store)

        try:
            save_artifact_from_assistant(assistant_message, session["id"])
        except Exception:
            pass

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "session": session_contract_payload(session)["session"],
            "session_id": session["id"],
            "active_session_id": session["id"],
            "artifacts": load_artifacts(),
            "memory": load_memory(),
            "debug": {
                "tool": "current_info",
                "query": current_info.get("query") or user_text,
                "source_count": len(safe_list(current_info.get("sources"))),
            },
        }

    # -------------------------
    # WEB AUTO ROUTE
    # -------------------------
    if should_route_to_web(user_text):
        url = normalize_url_input(user_text)
        if not url:
            return {
                "ok": False,
                "error": "Invalid URL",
                "session_id": locked_session_id,
                "active_session_id": locked_session_id,
            }

        result = fetch_web(url)
        if not result.get("ok"):
            return {
                "ok": False,
                "error": result.get("error") or "Web fetch failed.",
                "session_id": locked_session_id,
                "active_session_id": locked_session_id,
                "debug": {
                    "tool": "web",
                    "url": result.get("url") or url,
                },
            }

        text = build_web_result_text(result)
        meta = build_web_result_meta(result)

        assistant_message = make_assistant_message(
            text,
            message_id=assistant_message_id,
            source="web_fetch",
            pending=False,
            streaming=False,
            stopped=False,
            error=False,
            meta=meta,
        )

        if target_message:
            replace_message(session, assistant_message_id, assistant_message)
        else:
            append_message(session, assistant_message)

        recalc_session(session)
        save_sessions_store(store)

        try:
            save_artifact_from_assistant(assistant_message, session["id"])
        except Exception:
            pass

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "session": session_contract_payload(session)["session"],
            "session_id": session["id"],
            "active_session_id": session["id"],
            "artifacts": load_artifacts(),
            "memory": load_memory(),
            "debug": {
                "tool": "web",
                "url": result.get("url") or url,
                "status_code": int(result.get("status_code") or 0),
                "ssl_verified": bool(result.get("ssl_verified")),
            },
        }

    # -------------------------
    # VIDEO TOOL
    # -------------------------
    if has_video(attachments):
        video_result = build_video_analysis_result(
            attachments=attachments,
            user_text=user_text,
        )

        if not video_result.get("ok"):
            return {
                "ok": False,
                "error": video_result.get("error") or "Video analysis failed.",
                "session_id": locked_session_id,
                "active_session_id": locked_session_id,
                "debug": {"tool": "video"},
            }

        videos = safe_list(video_result.get("videos"))
        summary = normalize_text(video_result.get("summary") or "").strip()
        analysis_text = normalize_text(video_result.get("analysis_text") or "").strip()
        bullets = safe_list(video_result.get("bullets"))

        video_url = ""
        if videos:
            first_video = videos[0] if isinstance(videos[0], dict) else {}
            raw_url = normalize_text(first_video.get("url") or "").strip()
            raw_name = normalize_text(
                first_video.get("stored_name")
                or first_video.get("stored_filename")
                or first_video.get("filename")
                or first_video.get("name")
                or ""
            ).strip()

            if raw_url.startswith("/api/uploads/"):
                video_url = raw_url
            else:
                safe_name = Path(raw_url).name.strip() if raw_url else ""
                chosen_name = raw_name or safe_name
                if chosen_name:
                    video_url = f"/api/uploads/{chosen_name}"

        assistant_message = make_assistant_message(
            summary or analysis_text or "Video received.",
            message_id=assistant_message_id,
            source="video_analysis",
            pending=False,
            streaming=False,
            stopped=False,
            error=False,
            meta={
                "analysis_text": analysis_text or summary,
                "bullets": bullets,
                "videos": videos,
                "video_url": video_url,
            },
        )

        if target_message:
            replace_message(session, assistant_message_id, assistant_message)
        else:
            append_message(session, assistant_message)

        recalc_session(session)
        save_sessions_store(store)

        try:
            save_artifact_from_assistant(assistant_message, session["id"])
        except Exception:
            pass

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "session": session_contract_payload(session)["session"],
            "session_id": session["id"],
            "active_session_id": session["id"],
            "artifacts": load_artifacts(),
            "memory": load_memory(),
            "debug": {"tool": "video"},
        }

    # -------------------------
    # NORMAL CHAT
    # -------------------------
    payload = build_model_payload(
        session=session,
        user_text=user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
    )

    route_result = payload["route_result"]
    memory_selection = payload["memory_selection"]
    memory_block = payload["memory_block"]

    parts: list[str] = []
    for token in stream_model_text(
        session=session,
        user_text=user_text,
        attachments=attachments,
        regenerate_of=regenerate_of,
        memory_block=memory_block,
        route_result=route_result,
    ):
        parts.append(str(token or ""))

    final_text = "".join(parts).strip()
    if not final_text:
        final_text = "No response generated."

    assistant_message = make_assistant_message(
        final_text,
        message_id=assistant_message_id,
        source="send",
        pending=False,
        streaming=False,
        stopped=False,
        error=False,
        meta={
            "regenerate_of": regenerate_of or "",
        },
    )

    if target_message:
        replace_message(session, assistant_message_id, assistant_message)
    else:
        append_message(session, assistant_message)

    recalc_session(session)
    save_sessions_store(store)

    try:
        save_artifact_from_assistant(assistant_message, session["id"])
    except Exception:
        pass

    return {
        "ok": True,
        "assistant_message": assistant_message,
        "session": session_contract_payload(session)["session"],
        "session_id": session["id"],
        "active_session_id": session["id"],
        "artifacts": load_artifacts(),
        "memory": load_memory(),
        "debug": {
            "route_result": route_result,
            "memory_selected_count": len(memory_selection.get("selected") or []),
        },
    }

@app.post("/api/chat")
def api_chat() -> Any:
    try:
        data = request.get_json(silent=True) or {}

        requested_session_id = str(data.get("session_id") or "").strip()
        user_text = normalize_text(data.get("user_text") or "")
        attachments = normalize_attachments(safe_list(data.get("attachments")))
        regenerate_of = str(data.get("regenerate_of") or "").strip() or None
        wants_stream = bool(data.get("stream", True))

        # -------------------------
        # SESSION RESOLVE (KEEP THIS)
        # -------------------------
        store = load_sessions_store()
        session = find_session(store, requested_session_id) if requested_session_id else None
        if not session:
            session = ensure_active_session(store)

        store["active_session_id"] = session["id"]
        save_sessions_store(store)

        if not regenerate_of and not user_text.strip() and not attachments:
            return jsonify({"ok": False, "error": "user_text or attachments required"}), 400

        # -------------------------
        # STREAM PATH (ONLY DELEGATION)
        # -------------------------
        if wants_stream:
            return Response(
                chat_stream_generator(
                    session_id=session["id"],
                    user_text=user_text,
                    attachments=attachments,
                    regenerate_of=regenerate_of,
                ),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # -------------------------
        # NON-STREAM PATH (DELEGATE)
        # -------------------------
        result = chat_single_response(
            session_id=session["id"],
            user_text=user_text,
            attachments=attachments,
            regenerate_of=regenerate_of,
        )

        return jsonify(result)

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc) or "api_chat failed",
        }), 500

@app.post("/api/web/fetch")
def api_web_fetch() -> Any:
    data = request.get_json(silent=True) or {}

    requested_session_id = str(data.get("session_id") or "").strip()
    raw_url = clean_web_input(data.get("url") or data.get("user_text") or "")
    url = extract_url(raw_url) or normalize_url(raw_url)
    if not url:
        return jsonify({
            "ok": False,
            "error": "A valid URL is required.",
        }), 400

    store = load_sessions_store()
    session = find_session(store, requested_session_id) if requested_session_id else None
    if not session:
        session = ensure_active_session(store)

    store["active_session_id"] = session["id"]
    save_sessions_store(store)

    result = fetch_web(url)
    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "error": result.get("error") or "Web fetch failed.",
            "debug": {
                "tool": "web",
                "url": result.get("url") or url,
            },
        }), 500

    text = build_web_result_text(result)
    meta = build_web_result_meta(result)

    user_msg = make_user_message(url, [])
    assistant_msg = make_assistant_message(
        text,
        source="web_fetch",
        meta=meta,
    )

    append_message(session, user_msg)
    append_message(session, assistant_msg)

    try:
        save_artifact_from_assistant(assistant_msg, session["id"])
    except Exception:
        pass

    retrieval_debug = build_retrieval_debug(session, raw_url)

    return jsonify({
        "ok": True,
        "session_id": session["id"],
        "message": assistant_msg,
        "messages": session_messages(session),
        "artifacts": load_artifacts(),
        "memory": load_memory(),
        "debug": {
            "tool": "web",
            "url": result.get("url") or "",
            "ssl_verified": bool(result.get("ssl_verified")),
            "status_code": int(result.get("status_code") or 0),
            "retrieval": retrieval_debug,
        },
    })

@app.route("/api/uploads/<path:filename>")
def serve_upload(filename: str):
    return send_from_directory(str(UPLOADS_DIR), filename)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    ensure_store_files()
    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=False)