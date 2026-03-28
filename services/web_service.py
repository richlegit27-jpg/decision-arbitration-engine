# notepad C:\Users\Owner\nova\services\web_service.py
from __future__ import annotations

import json
import re
import socket
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


# =========================================================
# config
# =========================================================

MAX_URLS_PER_REQUEST = 5
MAX_FETCH_BYTES = 2_500_000
MAX_TEXT_CHARS = 24_000
MAX_SUMMARY_CHARS = 1_000
MAX_PREVIEW_CHARS = 320
MAX_CHUNKS = 10
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 180
REQUEST_TIMEOUT = 12

DEFAULT_HEADERS = {
    "User-Agent": "NovaWebService/1.0 (+https://local.nova)",
    "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# =========================================================
# helpers
# =========================================================

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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def preview_text(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    return truncate(compact_whitespace(text), limit)


def summarize_text(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    parts = [clean_text(x) for x in parts if clean_text(x)]

    kept: List[str] = []
    total = 0
    for part in parts:
        if total + len(part) > limit:
            break
        kept.append(part)
        total += len(part) + 1
        if len(kept) >= 6:
            break

    if not kept:
        return truncate(text, limit)
    return truncate(" ".join(kept), limit)


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = clean_text(text)
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length and len(chunks) < MAX_CHUNKS:
        end = min(length, start + chunk_size)
        piece = text[start:end]

        if end < length:
            split_at = max(piece.rfind("\n\n"), piece.rfind(". "), piece.rfind("\n"), piece.rfind(" "))
            if split_at > max(200, chunk_size // 3):
                piece = piece[: split_at + 1]
                end = start + len(piece)

        piece = clean_text(piece)
        if piece:
            chunks.append(piece)

        if end >= length:
            break

        start = max(end - overlap, start + 1)

    return chunks


# =========================================================
# url parsing + safety
# =========================================================

URL_RE = re.compile(
    r"""(?ix)
    \b
    (?:
        https?://
        |
        www\.
    )
    [^\s<>"'`]+
    """
)


def extract_urls_from_text(text: str) -> List[str]:
    text = clean_text(text)
    if not text:
        return []

    found = URL_RE.findall(text)
    urls: List[str] = []
    seen = set()

    for raw in found:
        url = normalize_url(raw)
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= MAX_URLS_PER_REQUEST:
            break

    return urls


def normalize_url(value: str) -> str:
    value = clean_text(value).strip("()[]{}<>,. ")
    if not value:
        return ""
    if value.startswith("www."):
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if not parsed.netloc:
        return ""
    return parsed.geturl()


def is_private_hostname(hostname: str) -> bool:
    hostname = clean_text(hostname).lower()
    if not hostname:
        return True

    blocked = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    }
    if hostname in blocked:
        return True

    if hostname.endswith(".local"):
        return True

    try:
        infos = socket.getaddrinfo(hostname, None)
    except Exception:
        return False

    for info in infos:
        ip = info[4][0]
        if ip.startswith("10."):
            return True
        if ip.startswith("127."):
            return True
        if ip.startswith("192.168."):
            return True
        if ip.startswith("169.254."):
            return True
        if ip == "::1":
            return True
        if ip.lower().startswith("fe80:"):
            return True
        if ip.lower().startswith("fc") or ip.lower().startswith("fd"):
            return True
        if "." in ip:
            parts = ip.split(".")
            if len(parts) == 4:
                try:
                    if int(parts[0]) == 172 and 16 <= int(parts[1]) <= 31:
                        return True
                except Exception:
                    pass

    return False


def validate_url(url: str) -> Dict[str, Any]:
    normalized = normalize_url(url)
    if not normalized:
        return {
            "ok": False,
            "url": clean_text(url),
            "error": {"code": "invalid_url", "message": "URL is invalid or unsupported."},
        }

    parsed = urlparse(normalized)
    hostname = clean_text(parsed.hostname)

    if is_private_hostname(hostname):
        return {
            "ok": False,
            "url": normalized,
            "error": {"code": "blocked_host", "message": "Private or local network hosts are blocked."},
        }

    return {
        "ok": True,
        "url": normalized,
        "hostname": hostname,
        "scheme": parsed.scheme,
        "error": None,
    }


# =========================================================
# html/json/text extraction
# =========================================================

TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
META_DESC_RE = re.compile(
    r'(?is)<meta[^>]+(?:name|property)\s*=\s*["\'](?:description|og:description|twitter:description)["\'][^>]+content\s*=\s*["\'](.*?)["\']'
)
H1_RE = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")


def strip_html(html: str) -> str:
    if not html:
        return ""
    html = unescape(html)
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p\s*>", "\n\n", html)
    html = re.sub(r"(?i)</div\s*>", "\n", html)
    html = re.sub(r"(?i)</section\s*>", "\n", html)
    html = re.sub(r"(?i)</article\s*>", "\n", html)
    html = re.sub(r"(?i)</li\s*>", "\n", html)
    html = re.sub(r"(?i)<li[^>]*>", "- ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return clean_text(html)


def extract_html_title(html: str) -> str:
    for regex in (TITLE_RE, H1_RE):
        match = regex.search(html or "")
        if match:
            return truncate(strip_html(match.group(1)), 200)
    return ""


def extract_html_description(html: str) -> str:
    match = META_DESC_RE.search(html or "")
    if not match:
        return ""
    return truncate(strip_html(match.group(1)), 320)


def normalize_json_content(text: str) -> str:
    try:
        parsed = json.loads(text)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        return truncate(pretty, MAX_TEXT_CHARS)
    except Exception:
        return truncate(text, MAX_TEXT_CHARS)


def classify_content_type(content_type: str, url: str = "") -> str:
    content_type = clean_text(content_type).lower()
    path = clean_text(urlparse(url).path).lower()

    if "application/json" in content_type or path.endswith(".json"):
        return "json"
    if "text/html" in content_type or "application/xhtml+xml" in content_type or path.endswith(".html") or path.endswith(".htm"):
        return "html"
    if content_type.startswith("text/"):
        return "text"
    return "other"


# =========================================================
# fetching
# =========================================================

def _requests_available() -> bool:
    return requests is not None


def fetch_url(url: str, timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
    validated = validate_url(url)
    if not validated.get("ok"):
        return {
            "ok": False,
            "url": clean_text(url),
            "status_code": None,
            "content_type": "",
            "final_url": "",
            "headers": {},
            "text": "",
            "raw_text": "",
            "title": "",
            "summary": "",
            "preview": "",
            "chunks": [],
            "links": [],
            "metadata": {},
            "error": validated.get("error"),
        }

    if not _requests_available():
        return {
            "ok": False,
            "url": validated["url"],
            "status_code": None,
            "content_type": "",
            "final_url": "",
            "headers": {},
            "text": "",
            "raw_text": "",
            "title": "",
            "summary": "",
            "preview": "",
            "chunks": [],
            "links": [],
            "metadata": {},
            "error": {"code": "requests_unavailable", "message": "requests library is unavailable."},
        }

    try:
        response = requests.get(
            validated["url"],
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
    except Exception as exc:
        return {
            "ok": False,
            "url": validated["url"],
            "status_code": None,
            "content_type": "",
            "final_url": "",
            "headers": {},
            "text": "",
            "raw_text": "",
            "title": "",
            "summary": "",
            "preview": "",
            "chunks": [],
            "links": [],
            "metadata": {},
            "error": {"code": "fetch_failed", "message": str(exc)},
        }

    try:
        raw_bytes = b""
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            raw_bytes += chunk
            if len(raw_bytes) >= MAX_FETCH_BYTES:
                raw_bytes = raw_bytes[:MAX_FETCH_BYTES]
                break

        content_type = clean_text(response.headers.get("Content-Type")).lower()
        final_url = clean_text(response.url)
        status_code = safe_int(response.status_code, 0)

        encoding = response.encoding or response.apparent_encoding or "utf-8"
        try:
            raw_text = raw_bytes.decode(encoding, errors="replace")
        except Exception:
            raw_text = raw_bytes.decode("utf-8", errors="replace")

        content_kind = classify_content_type(content_type, final_url)
        title = ""
        extracted_text = ""
        description = ""

        if content_kind == "html":
            title = extract_html_title(raw_text)
            description = extract_html_description(raw_text)
            extracted_text = strip_html(raw_text)
        elif content_kind == "json":
            extracted_text = normalize_json_content(raw_text)
        elif content_kind == "text":
            extracted_text = clean_text(raw_text)
        else:
            extracted_text = ""

        extracted_text = truncate(extracted_text, MAX_TEXT_CHARS)
        summary_source = description or extracted_text or title
        summary = summarize_text(summary_source)
        preview = preview_text(summary_source or title)
        chunks = split_into_chunks(extracted_text)

        links = extract_links_from_html(raw_text, base_url=final_url) if content_kind == "html" else []

        ok = 200 <= status_code < 400 and bool(extracted_text or title or description)

        return {
            "ok": ok,
            "url": validated["url"],
            "status_code": status_code,
            "content_type": content_type,
            "final_url": final_url,
            "headers": dict(response.headers),
            "text": extracted_text,
            "raw_text": truncate(clean_text(raw_text), MAX_TEXT_CHARS),
            "title": title,
            "summary": truncate(summary, MAX_SUMMARY_CHARS),
            "preview": truncate(preview, MAX_PREVIEW_CHARS),
            "chunks": chunks,
            "links": links[:20],
            "metadata": {
                "hostname": validated.get("hostname"),
                "scheme": validated.get("scheme"),
                "content_kind": content_kind,
                "bytes_read": len(raw_bytes),
                "characters": len(extracted_text),
                "chunk_count": len(chunks),
                "link_count": len(links),
            },
            "error": None if ok else {
                "code": "unusable_response",
                "message": f"HTTP {status_code} or empty extractable content.",
            },
        }
    finally:
        try:
            response.close()
        except Exception:
            pass


# =========================================================
# html links
# =========================================================

LINK_RE = re.compile(r'(?is)<a[^>]+href\s*=\s*["\'](.*?)["\']')


def extract_links_from_html(html: str, base_url: str) -> List[Dict[str, Any]]:
    if not html:
        return []

    links: List[Dict[str, Any]] = []
    seen = set()

    for match in LINK_RE.finditer(html):
        href = clean_text(match.group(1))
        if not href:
            continue
        if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue

        absolute = urljoin(base_url, href)
        normalized = normalize_url(absolute)
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        links.append({"url": normalized})

        if len(links) >= 20:
            break

    return links


# =========================================================
# higher-level analysis
# =========================================================

def analyze_web_content(url: str) -> Dict[str, Any]:
    fetched = fetch_url(url)

    return {
        "ok": bool(fetched.get("ok")),
        "url": fetched.get("url"),
        "final_url": fetched.get("final_url"),
        "title": clean_text(fetched.get("title")),
        "summary": clean_text(fetched.get("summary")),
        "preview": clean_text(fetched.get("preview")),
        "text": clean_text(fetched.get("text")),
        "chunks": safe_list(fetched.get("chunks")),
        "links": safe_list(fetched.get("links")),
        "status_code": fetched.get("status_code"),
        "content_type": clean_text(fetched.get("content_type")),
        "metadata": safe_dict(fetched.get("metadata")),
        "error": fetched.get("error"),
    }


def analyze_many_urls(urls: List[str]) -> Dict[str, Any]:
    normalized_urls: List[str] = []
    seen = set()

    for raw in safe_list(urls):
        url = normalize_url(raw)
        if not url or url in seen:
            continue
        seen.add(url)
        normalized_urls.append(url)
        if len(normalized_urls) >= MAX_URLS_PER_REQUEST:
            break

    results = [analyze_web_content(url) for url in normalized_urls]

    return {
        "ok": True,
        "count": len(results),
        "results": results,
    }


def analyze_text_for_web_context(text: str) -> Dict[str, Any]:
    urls = extract_urls_from_text(text)
    analyzed = analyze_many_urls(urls)

    return {
        "ok": True,
        "urls": urls,
        "count": safe_int(analyzed.get("count"), 0),
        "results": safe_list(analyzed.get("results")),
    }


# =========================================================
# prompt shaping
# =========================================================

def build_web_prompt_context(text: str = "", urls: Optional[List[str]] = None) -> Dict[str, Any]:
    if urls is None:
        urls = extract_urls_from_text(text)

    analyzed = analyze_many_urls(urls)
    results = safe_list(analyzed.get("results"))

    lines: List[str] = []
    debug_items: List[Dict[str, Any]] = []

    if results:
        lines.append("Web context:")

    for item in results[:MAX_URLS_PER_REQUEST]:
        data = safe_dict(item)
        url = clean_text(data.get("final_url") or data.get("url"))
        title = clean_text(data.get("title"))
        summary = clean_text(data.get("summary"))
        preview = clean_text(data.get("preview"))
        chunks = [clean_text(x) for x in safe_list(data.get("chunks")) if clean_text(x)]

        label = title or url or "web page"
        lines.append(f"- {label}")
        if url and url != label:
            lines.append(f"  URL: {url}")
        if summary:
            lines.append(f"  Summary: {truncate(summary, MAX_SUMMARY_CHARS)}")
        elif preview:
            lines.append(f"  Preview: {truncate(preview, MAX_PREVIEW_CHARS)}")

        for idx, chunk in enumerate(chunks[:3], 1):
            lines.append(f"  [Chunk {idx}] {truncate(chunk, 700)}")

        debug_items.append(
            {
                "url": url,
                "title": title,
                "summary": summary,
                "preview": preview,
                "status_code": data.get("status_code"),
                "content_type": data.get("content_type"),
                "metadata": safe_dict(data.get("metadata")),
                "error": data.get("error"),
            }
        )

    prompt_text = "\n".join(lines).strip()

    return {
        "ok": True,
        "urls": [clean_text(x) for x in urls if clean_text(x)],
        "results": results,
        "debug": debug_items,
        "prompt_text": prompt_text,
    }


def web_results_to_prompt_text(results: List[Dict[str, Any]]) -> str:
    lines: List[str] = []

    if results:
        lines.append("Web context:")

    for raw in safe_list(results)[:MAX_URLS_PER_REQUEST]:
        item = safe_dict(raw)
        title = clean_text(item.get("title"))
        url = clean_text(item.get("final_url") or item.get("url"))
        summary = clean_text(item.get("summary"))
        lines.append(f"- {title or url or 'web page'}")
        if url:
            lines.append(f"  URL: {url}")
        if summary:
            lines.append(f"  Summary: {truncate(summary, MAX_SUMMARY_CHARS)}")

        chunks = [clean_text(x) for x in safe_list(item.get("chunks")) if clean_text(x)]
        for idx, chunk in enumerate(chunks[:2], 1):
            lines.append(f"  [Chunk {idx}] {truncate(chunk, 700)}")

    return "\n".join(lines).strip()


# =========================================================
# api-friendly helpers
# =========================================================

def web_preview_from_text(text: str) -> Dict[str, Any]:
    context = build_web_prompt_context(text=text)
    return {
        "ok": True,
        "urls": context.get("urls", []),
        "count": len(safe_list(context.get("results"))),
        "results": context.get("results", []),
        "prompt_text": context.get("prompt_text", ""),
        "debug": context.get("debug", []),
    }


def fetch_single_url(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    url = clean_text(payload.get("url"))
    if not url:
        return {
            "ok": False,
            "error": {"code": "invalid_request", "message": "url is required."},
        }
    return analyze_web_content(url)


def fetch_urls(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = safe_dict(payload)
    urls = [clean_text(x) for x in safe_list(payload.get("urls")) if clean_text(x)]

    if not urls:
        text = clean_text(payload.get("text"))
        urls = extract_urls_from_text(text)

    return analyze_many_urls(urls)


# =========================================================
# diagnostics
# =========================================================

def web_service_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "requests_available": _requests_available(),
        "max_urls_per_request": MAX_URLS_PER_REQUEST,
        "max_fetch_bytes": MAX_FETCH_BYTES,
        "max_text_chars": MAX_TEXT_CHARS,
        "timeout_seconds": REQUEST_TIMEOUT,
    }