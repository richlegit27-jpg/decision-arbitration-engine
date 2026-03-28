from __future__ import annotations

import html
import io
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


REQUEST_TIMEOUT = 15
MAX_URLS = 3
MAX_HTML_CHARS = 120000
MAX_TEXT_CHARS = 12000
MAX_PREVIEW_CHARS = 800
MAX_TITLE_CHARS = 200
MAX_PDF_PAGES = 8
MAX_PDF_CHARS = 12000

URL_RE = re.compile(r"""https?://[^\s<>"')\]]+""", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b.*?</style>", re.IGNORECASE | re.DOTALL)
SVG_RE = re.compile(r"<svg\b.*?</svg>", re.IGNORECASE | re.DOTALL)
NOSCRIPT_RE = re.compile(r"<noscript\b.*?</noscript>", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
META_NAME_TITLE_RE = re.compile(
    r'<meta[^>]+name=["\']title["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.IGNORECASE | re.DOTALL)
ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.IGNORECASE | re.DOTALL)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\x00", " ")
    text = html.unescape(text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _truncate(text: str, limit: int) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def _extract_urls(text: str) -> List[str]:
    seen = set()
    urls: List[str] = []
    for match in URL_RE.findall(text or ""):
        url = match.rstrip(".,;:!?)]>}\"'")
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _domain_from_url(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _looks_like_binary(content_type: str) -> bool:
    ct = (content_type or "").lower()
    blocked_prefixes = (
        "image/",
        "audio/",
        "video/",
        "font/",
    )
    blocked_exact = {
        "application/zip",
        "application/octet-stream",
        "application/x-zip-compressed",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return ct.startswith(blocked_prefixes) or ct in blocked_exact


def _strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = COMMENT_RE.sub(" ", raw_html)
    text = SCRIPT_RE.sub(" ", text)
    text = STYLE_RE.sub(" ", text)
    text = SVG_RE.sub(" ", text)
    text = NOSCRIPT_RE.sub(" ", text)
    text = re.sub(r"</(p|div|section|article|main|li|h1|h2|h3|h4|h5|h6|br|tr)>", "\n", text, flags=re.IGNORECASE)
    text = TAG_RE.sub(" ", text)
    return _clean_text(text)


def _extract_title(raw_html: str, fallback_url: str = "") -> str:
    if raw_html:
        for regex in (META_OG_TITLE_RE, META_NAME_TITLE_RE, TITLE_RE):
            match = regex.search(raw_html)
            if match:
                title = _truncate(match.group(1), MAX_TITLE_CHARS)
                if title:
                    return title
    fallback = fallback_url or "Untitled page"
    return _truncate(fallback, MAX_TITLE_CHARS)


def _extract_primary_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""

    candidates: List[str] = []

    for regex in (ARTICLE_RE, MAIN_RE, BODY_RE):
        match = regex.search(raw_html)
        if match:
            stripped = _strip_html(match.group(1))
            if stripped:
                candidates.append(stripped)

    full_text = _strip_html(raw_html)
    if full_text:
        candidates.append(full_text)

    if not candidates:
        return ""

    candidates = sorted(candidates, key=lambda item: len(item), reverse=True)

    best = candidates[0]
    for candidate in candidates:
        if len(candidate) >= 500:
            best = candidate
            break

    return best


def _extract_pdf_text(content: bytes) -> str:
    if not content or PdfReader is None:
        return ""

    try:
        reader = PdfReader(io.BytesIO(content))
        parts: List[str] = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            page_text = _clean_text(page_text)
            if page_text:
                parts.append(page_text)
            joined = "\n\n".join(parts)
            if len(joined) >= MAX_PDF_CHARS:
                break

        return _truncate("\n\n".join(parts), MAX_PDF_CHARS)
    except Exception:
        return ""


def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Nova/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def fetch_url_preview(url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ok": False,
        "url": url,
        "final_url": url,
        "domain": _domain_from_url(url),
        "status_code": 0,
        "content_type": "",
        "title": "",
        "text": "",
        "preview": "",
        "truncated": False,
        "thin": False,
        "blocked": False,
        "error": "",
        "urls": [url] if url else [],
    }

    if not url:
        result["error"] = "Missing URL"
        return result

    try:
        response = requests.get(
            url,
            headers=_build_headers(),
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except Exception as exc:
        result["error"] = str(exc)
        return result

    result["final_url"] = str(response.url or url)
    result["domain"] = _domain_from_url(result["final_url"])
    result["status_code"] = int(response.status_code or 0)
    result["content_type"] = (response.headers.get("content-type") or "").split(";")[0].strip().lower()

    if response.status_code >= 400:
        result["error"] = f"HTTP {response.status_code}"
        return result

    content_type = result["content_type"]
    raw_bytes = response.content or b""
    raw_text = ""

    if _looks_like_binary(content_type):
        result["blocked"] = True
        result["error"] = f"Unsupported content type: {content_type or 'unknown'}"
        return result

    if content_type == "application/pdf":
        extracted = _extract_pdf_text(raw_bytes)
        result["title"] = _truncate(result["final_url"], MAX_TITLE_CHARS)
        result["text"] = extracted
        result["preview"] = _truncate(extracted, MAX_PREVIEW_CHARS)
        result["ok"] = bool(extracted)
        result["thin"] = len(extracted) < 280
        return result

    try:
        raw_text = response.text or ""
    except Exception:
        raw_text = ""

    if not raw_text:
        result["error"] = "Empty response body"
        return result

    raw_text = raw_text[:MAX_HTML_CHARS]

    if "html" in content_type or "<html" in raw_text.lower():
        title = _extract_title(raw_text, fallback_url=result["final_url"])
        extracted = _extract_primary_html_text(raw_text)
        result["title"] = title
        result["text"] = _truncate(extracted, MAX_TEXT_CHARS)
        result["preview"] = _truncate(result["text"], MAX_PREVIEW_CHARS)
        result["truncated"] = len(_clean_text(extracted)) > len(result["text"])
        result["thin"] = len(result["text"]) < 280
        result["ok"] = bool(result["text"])
        if not result["ok"]:
            result["error"] = "No usable text extracted from HTML"
        return result

    cleaned = _truncate(raw_text, MAX_TEXT_CHARS)
    result["title"] = _truncate(result["final_url"], MAX_TITLE_CHARS)
    result["text"] = cleaned
    result["preview"] = _truncate(cleaned, MAX_PREVIEW_CHARS)
    result["truncated"] = len(_clean_text(raw_text)) > len(cleaned)
    result["thin"] = len(cleaned) < 280
    result["ok"] = bool(cleaned)
    if not result["ok"]:
        result["error"] = "No usable text extracted"
    return result


def build_web_context_from_text(text: str, max_urls: int = MAX_URLS) -> Dict[str, Any]:
    urls = _extract_urls(text)
    selected_urls = urls[:max_urls]

    pages: List[Dict[str, Any]] = []
    for url in selected_urls:
        pages.append(fetch_url_preview(url))

    usable_pages = [page for page in pages if page.get("ok") and page.get("text")]

    blocks: List[str] = []
    for index, page in enumerate(usable_pages, start=1):
        block = "\n".join(
            [
                f"[Web Source {index}]",
                f"Title: {page.get('title') or 'Untitled'}",
                f"URL: {page.get('final_url') or page.get('url') or ''}",
                f"Domain: {page.get('domain') or ''}",
                f"Type: {page.get('content_type') or 'unknown'}",
                f"Preview: {_truncate(page.get('preview') or '', 350)}",
                f"Extracted Text: {_truncate(page.get('text') or '', MAX_TEXT_CHARS)}",
            ]
        )
        blocks.append(block)

    summary = ""
    if usable_pages:
        summary = (
            "Web context was automatically fetched from URLs in the user's message. "
            "Use it when relevant. If the content looks thin, blocked, or incomplete, say so plainly.\n\n"
            + "\n\n".join(blocks)
        )

    return {
        "enabled": True,
        "used": bool(usable_pages),
        "urls": selected_urls,
        "pages": pages,
        "summary": summary,
    }


def preview_web_text(text: str) -> Dict[str, Any]:
    urls = _extract_urls(text)
    if not urls:
        return {
            "ok": False,
            "url": "",
            "final_url": "",
            "content_type": "",
            "status_code": 0,
            "title": "",
            "preview": "",
            "text": "",
            "truncated": False,
            "urls": [],
            "error": "No URL found in text",
        }

    return fetch_url_preview(urls[0])


def summarize_web_text(text: str, max_urls: int = MAX_URLS) -> str:
    context = build_web_context_from_text(text, max_urls=max_urls)
    return context.get("summary", "")