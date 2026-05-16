from __future__ import annotations

import re
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12
MAX_TEXT_CHARS = 12000


def _clean_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_html_response(content_type: str) -> bool:
    lowered = str(content_type or "").lower()
    return ("text/html" in lowered) or (lowered == "") or ("application/xhtml+xml" in lowered)


def _extract_main_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe", "footer", "nav"]):
        tag.decompose()

    preferred = None
    for selector in ("main", "article", "[role='main']"):
        preferred = soup.select_one(selector)
        if preferred:
            break

    root = preferred or soup.body or soup

    text = root.get_text(separator=" ", strip=True)
    text = _clean_text(text)
    return text[:MAX_TEXT_CHARS]


def fetch_page(url: str) -> Optional[Dict[str, str]]:
    raw_url = str(url or "").strip()
    if not raw_url:
        return None

    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    try:
        response = requests.get(
            raw_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except Exception:
        return None

    content_type = response.headers.get("content-type", "")
    if not _is_html_response(content_type):
        return None

    text = _extract_main_text(response.text)
    if not text:
        return None

    title = ""
    try:
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.title:
            title = _clean_text(soup.title.get_text(" ", strip=True))[:300]
    except Exception:
        title = ""

    return {
        "url": response.url or raw_url,
        "title": title,
        "text": text,
    }