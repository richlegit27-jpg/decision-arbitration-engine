# notepad C:\Users\Owner\nova\services\web_service.py
from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None  # type: ignore


# =========================================================
# config
# =========================================================

MAX_URLS = 5
MAX_FETCH_BYTES = 750000
MAX_RESPONSE_CHARS = 30000
MAX_PREVIEW_CHARS = 5000
MAX_SUMMARY_CHARS = 600
MAX_TEXT_BLOCK_CHARS = 12000
REQUEST_TIMEOUT = 12

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 Nova/1.0"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "text/plain;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# =========================================================
# helpers
# =========================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _collapse_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value)).strip()


def _truncate(value: Any, limit: int) -> str:
    text = _clean_text(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _collapse_ws(value).lower()
    return text in {"1", "true", "yes", "on"}


def _unique_preserve(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _is_probable_url(value: str) -> bool:
    value = value.strip()
    return value.startswith("http://") or value.startswith("https://")


def _normalize_url(value: str) -> str:
    value = _clean_text(value).strip()
    if not value:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", value):
        return value
    if "." in value and " " not in value:
        return "https://" + value
    return value


def extract_urls_from_text(text: str) -> List[str]:
    raw_text = _clean_text(text)
    found = re.findall(r"https?://[^\s<>()\"']+", raw_text, flags=re.IGNORECASE)

    normalized = []
    for url in found:
        cleaned = url.strip().rstrip(".,);!?]}>")
        if _is_probable_url(cleaned):
            normalized.append(cleaned)

    return _unique_preserve(normalized)[:MAX_URLS]


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _looks_like_html(content_type: str, text: str) -> bool:
    ctype = _collapse_ws(content_type).lower()
    if "html" in ctype or "xhtml" in ctype:
        return True
    probe = text[:500].lower()
    return "<html" in probe or "<body" in probe or "<title" in probe


def _strip_html_tags(html_text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)</div\s*>", "\n", text)
    text = re.sub(r"(?is)</h[1-6]\s*>", "\n\n", text)
    text = re.sub(r"(?is)<li\s*>", "• ", text)
    text = re.sub(r"(?is)<.*?>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_html_fields_with_bs4(html_text: str) -> Dict[str, Any]:
    result = {
        "title": "",
        "description": "",
        "content": "",
    }

    if not BeautifulSoup:
        return result

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return result

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        try:
            tag.decompose()
        except Exception:
            pass

    title = ""
    if soup.title and soup.title.string:
        title = _collapse_ws(soup.title.string)

    description = ""
    meta_description = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta_description and meta_description.get("content"):
        description = _collapse_ws(meta_description.get("content"))

    if not description:
        og_description = soup.find("meta", attrs={"property": re.compile("^og:description$", re.I)})
        if og_description and og_description.get("content"):
            description = _collapse_ws(og_description.get("content"))

    main_node = (
        soup.find("main")
        or soup.find("article")
        or soup.find("section")
        or soup.body
        or soup
    )

    content = _collapse_ws(main_node.get_text("\n", strip=True)) if main_node else ""
    content = _truncate(content, MAX_TEXT_BLOCK_CHARS)

    result["title"] = title
    result["description"] = description
    result["content"] = content
    return result


def _extract_html_fields_fallback(html_text: str) -> Dict[str, Any]:
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text)
    title = _collapse_ws(title_match.group(1)) if title_match else ""

    description = ""
    meta_match = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html_text,
    )
    if meta_match:
        description = _collapse_ws(meta_match.group(1))

    content = _strip_html_tags(html_text)
    content = _truncate(content, MAX_TEXT_BLOCK_CHARS)

    return {
        "title": title,
        "description": description,
        "content": content,
    }


def _extract_html_fields(html_text: str) -> Dict[str, Any]:
    if BeautifulSoup:
        parsed = _extract_html_fields_with_bs4(html_text)
        if parsed.get("title") or parsed.get("description") or parsed.get("content"):
            return parsed
    return _extract_html_fields_fallback(html_text)


def _build_summary(title: str, description: str, content: str, domain: str) -> str:
    if description:
        return _truncate(description, MAX_SUMMARY_CHARS)

    if title and content:
        return _truncate(f"{title} — {content}", MAX_SUMMARY_CHARS)

    if content:
        return _truncate(content, MAX_SUMMARY_CHARS)

    if title:
        return _truncate(f"Web page fetched from {domain}: {title}", MAX_SUMMARY_CHARS)

    return _truncate(f"Web page fetched from {domain}.", MAX_SUMMARY_CHARS)


def _build_preview(title: str, description: str, content: str) -> str:
    parts: List[str] = []
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if content:
        parts.append("Content Preview:")
        parts.append(content)
    return _truncate("\n".join(parts).strip(), MAX_PREVIEW_CHARS)


def _build_prompt_text(url: str, title: str, description: str, content: str) -> str:
    parts = [f"Fetched URL: {url}"]
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if content:
        parts.append("Extracted content:")
        parts.append(content)
    return _truncate("\n".join(parts), MAX_TEXT_BLOCK_CHARS)


# =========================================================
# network
# =========================================================

def _requests_available() -> bool:
    return requests is not None


def fetch_url_preview(url: str) -> Dict[str, Any]:
    normalized_url = _normalize_url(url)
    domain = _domain_from_url(normalized_url)

    base = {
        "url": normalized_url,
        "domain": domain,
        "title": "",
        "summary": "",
        "preview": "",
        "prompt_text": "",
        "status": "error",
        "status_code": None,
        "content_type": "",
        "meta": {},
    }

    if not normalized_url or not _is_probable_url(normalized_url):
        base["summary"] = "Invalid URL."
        base["meta"] = {"reason": "invalid_url"}
        return base

    if not _requests_available():
        base["summary"] = "Web fetching is unavailable because the requests package is not installed."
        base["meta"] = {"reason": "requests_unavailable"}
        return base

    try:
        response = requests.get(  # type: ignore[union-attr]
            normalized_url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )

        content_chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            content_chunks.append(chunk)
            total += len(chunk)
            if total >= MAX_FETCH_BYTES:
                break

        raw_bytes = b"".join(content_chunks)
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        text = raw_bytes.decode(encoding, errors="ignore")
        text = _truncate(text, MAX_RESPONSE_CHARS)

        content_type = _clean_text(response.headers.get("Content-Type"))
        final_url = _clean_text(response.url) or normalized_url
        final_domain = _domain_from_url(final_url)

        base["url"] = final_url
        base["domain"] = final_domain
        base["status_code"] = response.status_code
        base["content_type"] = content_type

        if response.status_code >= 400:
            base["summary"] = f"Fetch failed with status {response.status_code}."
            base["meta"] = {
                "reason": "http_error",
                "status_code": response.status_code,
            }
            return base

        if _looks_like_html(content_type, text):
            extracted = _extract_html_fields(text)
            title = _truncate(extracted.get("title", ""), 300)
            description = _truncate(extracted.get("description", ""), 800)
            content = _truncate(extracted.get("content", ""), MAX_TEXT_BLOCK_CHARS)

            base["title"] = title
            base["summary"] = _build_summary(title, description, content, final_domain)
            base["preview"] = _build_preview(title, description, content)
            base["prompt_text"] = _build_prompt_text(final_url, title, description, content)
            base["status"] = "ready"
            base["meta"] = {
                "mode": "html",
                "bytes_read": len(raw_bytes),
                "final_url": final_url,
                "status_code": response.status_code,
            }
            return base

        plain_text = _collapse_ws(text)
        plain_text = _truncate(plain_text, MAX_TEXT_BLOCK_CHARS)

        base["summary"] = _build_summary("", "", plain_text, final_domain)
        base["preview"] = _truncate(plain_text, MAX_PREVIEW_CHARS)
        base["prompt_text"] = _truncate(f"Fetched URL: {final_url}\n\n{plain_text}", MAX_TEXT_BLOCK_CHARS)
        base["status"] = "ready"
        base["meta"] = {
            "mode": "text",
            "bytes_read": len(raw_bytes),
            "final_url": final_url,
            "status_code": response.status_code,
        }
        return base

    except Exception as exc:
        base["summary"] = _truncate(f"Fetch failed: {exc}", MAX_SUMMARY_CHARS)
        base["meta"] = {"reason": "exception", "error": _truncate(str(exc), 300)}
        return base


# =========================================================
# public workflow
# =========================================================

def analyze_web_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = _coerce_dict(payload)

    text = _clean_text(payload.get("text") or payload.get("content"))
    explicit_urls = [_normalize_url(_clean_text(x)) for x in _coerce_list(payload.get("urls"))]
    discovered_urls = extract_urls_from_text(text)

    urls = _unique_preserve(
        [url for url in explicit_urls + discovered_urls if _is_probable_url(url)]
    )[:MAX_URLS]

    results: List[Dict[str, Any]] = []
    for url in urls:
        results.append(fetch_url_preview(url))

    ready_results = [item for item in results if _clean_text(item.get("status")) == "ready"]
    failed_results = [item for item in results if _clean_text(item.get("status")) != "ready"]

    combined_prompt_parts: List[str] = []
    for item in ready_results:
        prompt_text = _clean_text(item.get("prompt_text"))
        if prompt_text:
            combined_prompt_parts.append(prompt_text)

    combined_prompt = _truncate("\n\n---\n\n".join(combined_prompt_parts), MAX_TEXT_BLOCK_CHARS)

    return {
        "ok": True,
        "urls": urls,
        "count": len(results),
        "ready_count": len(ready_results),
        "failed_count": len(failed_results),
        "results": results,
        "prompt_text": combined_prompt,
        "summary": _truncate(
            f"Resolved {len(ready_results)} web preview(s)"
            + (f"; {len(failed_results)} failed." if failed_results else "."),
            MAX_SUMMARY_CHARS,
        ),
    }


def analyze_web_text(text: str) -> Dict[str, Any]:
    return analyze_web_request({"text": text})


def build_web_debug_payload(text: str) -> Dict[str, Any]:
    analyzed = analyze_web_text(text)

    previews = []
    for item in analyzed.get("results", []):
        item = _coerce_dict(item)
        previews.append(
            {
                "url": _clean_text(item.get("url")),
                "domain": _clean_text(item.get("domain")),
                "title": _clean_text(item.get("title")),
                "summary": _clean_text(item.get("summary")),
                "preview": _clean_text(item.get("preview")),
                "status": _clean_text(item.get("status")),
                "status_code": item.get("status_code"),
                "content_type": _clean_text(item.get("content_type")),
                "meta": _coerce_dict(item.get("meta")),
            }
        )

    return {
        "enabled": True,
        "input": _truncate(text, 2000),
        "urls": analyzed.get("urls", []),
        "summary": _clean_text(analyzed.get("summary")),
        "prompt_text": _clean_text(analyzed.get("prompt_text")),
        "previews": previews,
        "meta": {
            "count": analyzed.get("count", 0),
            "ready_count": analyzed.get("ready_count", 0),
            "failed_count": analyzed.get("failed_count", 0),
        },
    }


def merge_web_prompt_into_message_context(
    text: str,
    existing_context_blocks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    existing_context_blocks = existing_context_blocks or []
    web = analyze_web_text(text)
    merged_blocks = list(existing_context_blocks)

    prompt_text = _clean_text(web.get("prompt_text"))
    if prompt_text:
        merged_blocks.append(prompt_text)

    return {
        "web": web,
        "context_blocks": merged_blocks,
    }


def extract_first_url(text: str) -> str:
    urls = extract_urls_from_text(text)
    return urls[0] if urls else ""


def summarize_web_results(results: List[Dict[str, Any]]) -> str:
    summaries: List[str] = []
    for item in results[:MAX_URLS]:
        item = _coerce_dict(item)
        status = _clean_text(item.get("status"))
        url = _clean_text(item.get("url"))
        title = _clean_text(item.get("title"))
        summary = _clean_text(item.get("summary"))

        if status == "ready":
            line = f"{title or url}: {summary}".strip()
        else:
            line = f"{url or 'URL'}: {summary}".strip()

        summaries.append(_truncate(line, 300))

    return _truncate("\n".join(summaries), MAX_SUMMARY_CHARS)


def results_to_json(results: List[Dict[str, Any]]) -> str:
    safe_results = []
    for item in results[:MAX_URLS]:
        item = _coerce_dict(item)
        safe_results.append(
            {
                "url": _clean_text(item.get("url")),
                "domain": _clean_text(item.get("domain")),
                "title": _clean_text(item.get("title")),
                "summary": _clean_text(item.get("summary")),
                "status": _clean_text(item.get("status")),
                "status_code": item.get("status_code"),
                "content_type": _clean_text(item.get("content_type")),
                "meta": _coerce_dict(item.get("meta")),
            }
        )
    return json.dumps(safe_results, ensure_ascii=False, indent=2)