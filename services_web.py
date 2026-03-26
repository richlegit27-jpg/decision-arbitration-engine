from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def is_web(tavily_api_key: str) -> bool:
    return bool(_clean_text(tavily_api_key))


def wants_web_search(text: str) -> bool:
    value = _clean_text(text).lower()
    if not value:
        return False

    triggers = [
        "latest",
        "news",
        "current",
        "today",
        "recent",
        "lookup",
        "look up",
        "search",
        "web",
        "online",
        "find out",
        "what happened",
        "price",
        "weather",
        "score",
        "standings",
        "stock",
    ]

    return any(trigger in value for trigger in triggers)


def _normalize_results(items: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if not isinstance(items, list):
        return results

    for item in items:
        if not isinstance(item, dict):
            continue

        results.append(
            {
                "title": _clean_text(item.get("title")),
                "url": _clean_text(item.get("url")),
                "snippet": _clean_text(item.get("content") or item.get("snippet") or item.get("body")),
            }
        )

    return results


def search_web_for_query(query: str, tavily_api_key: str) -> tuple[list[dict[str, Any]], str]:
    query = _clean_text(query)
    tavily_api_key = _clean_text(tavily_api_key)

    if not query:
        return [], ""

    if not tavily_api_key:
        return [], ""

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": 5,
        "include_answer": False,
        "include_raw_content": False,
    }

    req = Request(
        url="https://api.tavily.com/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tavily_api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            results = _normalize_results(data.get("results"))
            return results, "tavily"
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return [], "tavily"
    except Exception:
        return [], "tavily"