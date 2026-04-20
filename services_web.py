import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests


TAVILY_BASE_URL = "https://api.tavily.com"
REQUEST_TIMEOUT = 20


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def is_web(tavily_api_key: str) -> bool:
    return bool(_clean_text(tavily_api_key))


def _headers(tavily_api_key: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tavily_api_key}",
    }


def extract_first_url(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""

    match = re.search(r"(https?://[^\s]+)", text, flags=re.IGNORECASE)
    return match.group(1).rstrip(".,);]}>\"'") if match else ""


def looks_like_web_query(text: str) -> bool:
    text = _clean_text(text).lower()
    if not text:
        return False

    if extract_first_url(text):
        return True

    triggers = (
        "latest ",
        "news ",
        "headline",
        "headlines",
        "today",
        "current ",
        "look up ",
        "lookup ",
        "search ",
        "find online",
        "on the web",
        "web search",
        "google ",
        "bing ",
        "price of ",
        "stock ",
        "weather ",
        "who is ",
        "what happened",
        "recent ",
        "breaking ",
    )
    return any(token in text for token in triggers)


def _normalize_result(item: Dict[str, Any]) -> Dict[str, Any]:
    url = _clean_text(item.get("url"))
    title = _clean_text(item.get("title"))
    content = _clean_text(item.get("content") or item.get("snippet") or item.get("raw_content"))

    return {
        "title": title,
        "url": url,
        "content": content,
        "score": item.get("score", 0),
        "published_date": _clean_text(item.get("published_date")),
    }


def search_web_for_query(
    query: str,
    tavily_api_key: str,
    *,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
    include_raw_content: bool = False,
    topic: str = "general",
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Returns:
        (results, provider_name, meta)
    """
    query = _clean_text(query)
    tavily_api_key = _clean_text(tavily_api_key)

    if not tavily_api_key:
        return [], "tavily", {"ok": False, "error": "Missing TAVILY_API_KEY"}

    if not query:
        return [], "tavily", {"ok": False, "error": "Empty query"}

    payload = {
        "query": query[:400],
        "topic": topic,
        "search_depth": search_depth,
        "max_results": max(1, min(int(max_results or 5), 10)),
        "include_answer": bool(include_answer),
        "include_raw_content": bool(include_raw_content),
        "include_images": False,
        "include_image_descriptions": False,
        "auto_parameters": True,
    }

    try:
        response = requests.post(
            f"{TAVILY_BASE_URL}/search",
            headers=_headers(tavily_api_key),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json() or {}

        raw_results = data.get("results") or []
        results = [_normalize_result(item) for item in raw_results if isinstance(item, dict)]
        results = [r for r in results if r.get("title") or r.get("url") or r.get("content")]

        meta = {
            "ok": True,
            "provider": "tavily",
            "query": query,
            "answer": _clean_text(data.get("answer")),
            "response_time": data.get("response_time"),
            "results_count": len(results),
            "raw": data,
        }
        return results, "tavily", meta

    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = response.text[:1000]
        except Exception:
            pass
        return [], "tavily", {
            "ok": False,
            "error": f"HTTP error: {exc}",
            "detail": detail,
        }
    except requests.RequestException as exc:
        return [], "tavily", {
            "ok": False,
            "error": f"Request failed: {exc}",
        }
    except Exception as exc:
        return [], "tavily", {
            "ok": False,
            "error": f"Unexpected search failure: {exc}",
        }


def extract_webpage(
    url: str,
    tavily_api_key: str,
    *,
    include_images: bool = False,
    extract_depth: str = "basic",
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """
    Returns:
        (page, provider_name, meta)

    page shape:
        {
            "url": "...",
            "title": "...",
            "content": "...",
            "raw_content": "...",
        }
    """
    url = _clean_text(url)
    tavily_api_key = _clean_text(tavily_api_key)

    if not tavily_api_key:
        return {}, "tavily", {"ok": False, "error": "Missing TAVILY_API_KEY"}

    if not url:
        return {}, "tavily", {"ok": False, "error": "Empty URL"}

    payload = {
        "urls": [url],
        "include_images": bool(include_images),
        "extract_depth": extract_depth,
    }

    try:
        response = requests.post(
            f"{TAVILY_BASE_URL}/extract",
            headers=_headers(tavily_api_key),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json() or {}

        results = data.get("results") or []
        first = results[0] if results and isinstance(results[0], dict) else {}

        page = {
            "url": _clean_text(first.get("url") or url),
            "title": _clean_text(first.get("title")),
            "content": _clean_text(first.get("content")),
            "raw_content": _clean_text(first.get("raw_content")),
        }

        meta = {
            "ok": True,
            "provider": "tavily",
            "results_count": len(results),
            "raw": data,
        }
        return page, "tavily", meta

    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = response.text[:1000]
        except Exception:
            pass
        return {}, "tavily", {
            "ok": False,
            "error": f"HTTP error: {exc}",
            "detail": detail,
        }
    except requests.RequestException as exc:
        return {}, "tavily", {
            "ok": False,
            "error": f"Request failed: {exc}",
        }
    except Exception as exc:
        return {}, "tavily", {
            "ok": False,
            "error": f"Unexpected extract failure: {exc}",
        }


def format_web_results_for_prompt(
    query: str,
    results: List[Dict[str, Any]],
    *,
    answer: str = "",
    max_chars_per_result: int = 900,
) -> str:
    query = _clean_text(query)
    answer = _clean_text(answer)

    lines: List[str] = []
    if query:
        lines.append(f"Web results for: {query}")
    if answer:
        lines.append(f"Tavily answer: {answer}")

    for index, item in enumerate(results or [], start=1):
        title = _clean_text(item.get("title")) or "(untitled)"
        url = _clean_text(item.get("url"))
        content = _clean_text(item.get("content"))[:max_chars_per_result]
        lines.append(f"[{index}] {title}")
        if url:
            lines.append(f"URL: {url}")
        if content:
            lines.append(content)
        lines.append("")

    return "\n".join(lines).strip()


def build_web_artifact(
    query: str,
    results: List[Dict[str, Any]],
    *,
    answer: str = "",
    source_url: str = "",
    provider: str = "tavily",
    title_prefix: str = "Web search",
) -> Dict[str, Any]:
    preview = answer or (
        (results[0].get("content") or "")[:220] if results else f'No live web results found for "{query}".'
    )

    body_lines: List[str] = []
    if answer:
        body_lines.append(answer)
        body_lines.append("")

    for item in results or []:
        item_title = _clean_text(item.get("title")) or "(untitled)"
        item_url = _clean_text(item.get("url"))
        item_content = _clean_text(item.get("content"))
        body_lines.append(f"- {item_title}")
        if item_url:
            body_lines.append(f"  {item_url}")
        if item_content:
            body_lines.append(f"  {item_content}")
        body_lines.append("")

    return {
        "kind": "web_search",
        "title": f"{title_prefix}: {query}",
        "body": "\n".join(body_lines).strip() or f'No live web results found for "{query}".',
        "preview": _clean_text(preview),
        "source_url": _clean_text(source_url),
        "results": results or [],
        "provider": provider,
        "meta": {
            "query": _clean_text(query),
            "answer": _clean_text(answer),
            "provider": provider,
            "result_count": len(results or []),
        },
    }


def get_tavily_api_key() -> str:
    return _clean_text(
        os.getenv("TAVILY_API_KEY")
        or os.getenv("TAVILY_KEY")
        or os.getenv("NOVA_TAVILY_API_KEY")
    )