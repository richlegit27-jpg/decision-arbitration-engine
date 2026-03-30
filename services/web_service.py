from __future__ import annotations

import html
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )
}


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""


class WebService:
    def __init__(
        self,
        timeout: int = 12,
        max_fetch_bytes: int = 2_000_000,
        max_text_chars: int = 12_000,
    ) -> None:
        self.timeout = timeout
        self.max_fetch_bytes = max_fetch_bytes
        self.max_text_chars = max_text_chars
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # =========================================================
    # Public API
    # =========================================================

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {
                "ok": False,
                "error": "Missing query",
                "query": query,
                "results": [],
            }

        try:
            results = self._duckduckgo_search(query=query, limit=limit)
            return {
                "ok": True,
                "query": query,
                "count": len(results),
                "results": [asdict(r) for r in results],
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Search failed: {exc}",
                "query": query,
                "results": [],
            }

    def fetch_url(self, url: str) -> Dict[str, Any]:
        url = (url or "").strip()
        if not url:
            return {
                "ok": False,
                "error": "Missing url",
            }

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True,
            )

            content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()
            final_url = response.url
            status_code = response.status_code

            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= self.max_fetch_bytes:
                    break

            raw = b"".join(chunks)
            text = raw.decode(response.encoding or "utf-8", errors="replace")

            parsed = self._parse_html(final_url, text) if "html" in content_type or "<html" in text.lower() else {
                "title": final_url,
                "description": "",
                "content": text[: self.max_text_chars],
                "site_name": "",
                "images": [],
                "videos": [],
                "audios": [],
            }

            return {
                "ok": 200 <= status_code < 400,
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "content_type": content_type,
                "title": parsed["title"],
                "description": parsed["description"],
                "site_name": parsed["site_name"],
                "content": parsed["content"],
                "image_count": len(parsed["images"]),
                "video_count": len(parsed["videos"]),
                "audio_count": len(parsed["audios"]),
                "images": parsed["images"][:12],
                "videos": parsed["videos"][:8],
                "audios": parsed["audios"][:8],
            }
        except Exception as exc:
            return {
                "ok": False,
                "url": url,
                "error": f"Fetch failed: {exc}",
            }

    def fetch_many(self, urls: List[str], limit: int = 3) -> Dict[str, Any]:
        cleaned: List[str] = []
        seen = set()

        for raw in urls or []:
            url = (raw or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            cleaned.append(url)

        cleaned = cleaned[:limit]
        items = [self.fetch_url(url) for url in cleaned]

        return {
            "ok": True,
            "count": len(items),
            "items": items,
        }

    def search_and_fetch(self, query: str, search_limit: int = 5, fetch_limit: int = 3) -> Dict[str, Any]:
        search_data = self.search(query=query, limit=search_limit)
        if not search_data.get("ok"):
            return {
                "ok": False,
                "query": query,
                "search": search_data,
                "fetch": {"ok": False, "items": []},
            }

        urls = [item.get("url", "") for item in search_data.get("results", [])]
        fetch_data = self.fetch_many(urls=urls, limit=fetch_limit)

        return {
            "ok": True,
            "query": query,
            "search": search_data,
            "fetch": fetch_data,
        }

    # =========================================================
    # Search helpers
    # =========================================================

    def _duckduckgo_search(self, query: str, limit: int) -> List[SearchHit]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results: List[SearchHit] = []

        for block in soup.select(".result"):
            a = block.select_one(".result__title a") or block.select_one("a.result__a")
            if not a:
                continue

            href = (a.get("href") or "").strip()
            title = self._clean_text(a.get_text(" ", strip=True))
            snippet_el = block.select_one(".result__snippet")
            snippet = self._clean_text(snippet_el.get_text(" ", strip=True) if snippet_el else "")

            if not href or not title:
                continue

            href = html.unescape(href)
            href = self._unwrap_duckduckgo_redirect(href)

            results.append(
                SearchHit(
                    title=title,
                    url=href,
                    snippet=snippet,
                )
            )

            if len(results) >= limit:
                break

        return results

    def _unwrap_duckduckgo_redirect(self, href: str) -> str:
        # DuckDuckGo sometimes returns direct URLs already.
        if href.startswith("http://") or href.startswith("https://"):
            return href

        match = re.search(r"uddg=([^&]+)", href)
        if match:
            try:
                from urllib.parse import unquote
                return unquote(match.group(1))
            except Exception:
                return href

        return href

    # =========================================================
    # HTML parsing helpers
    # =========================================================

    def _parse_html(self, base_url: str, html_text: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_text, "html.parser")

        for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
            tag.decompose()

        title = self._extract_title(soup, base_url)
        description = self._extract_description(soup)
        site_name = self._extract_site_name(soup)

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.body
            or soup
        )

        text = self._clean_text(main.get_text("\n", strip=True))
        text = self._trim_repeated_lines(text)
        text = text[: self.max_text_chars]

        images = self._extract_media_urls(soup, base_url, "img", "src")
        videos = self._extract_media_urls(soup, base_url, "video", "src")
        audios = self._extract_media_urls(soup, base_url, "audio", "src")

        for meta_prop in [
            ("meta[property='og:image']", "content", images),
            ("meta[name='twitter:image']", "content", images),
            ("meta[property='og:video']", "content", videos),
            ("meta[name='twitter:player']", "content", videos),
        ]:
            node = soup.select_one(meta_prop[0])
            if node and node.get(meta_prop[1]):
                absolute = urljoin(base_url, node.get(meta_prop[1]).strip())
                if absolute not in meta_prop[2]:
                    meta_prop[2].insert(0, absolute)

        return {
            "title": title,
            "description": description,
            "site_name": site_name,
            "content": text,
            "images": images,
            "videos": videos,
            "audios": audios,
        }

    def _extract_title(self, soup: BeautifulSoup, fallback: str) -> str:
        selectors = [
            "meta[property='og:title']",
            "meta[name='twitter:title']",
            "title",
            "h1",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            value = (node.get("content") or node.get_text(" ", strip=True) or "").strip()
            if value:
                return self._clean_text(value)
        return fallback

    def _extract_description(self, soup: BeautifulSoup) -> str:
        selectors = [
            "meta[name='description']",
            "meta[property='og:description']",
            "meta[name='twitter:description']",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            value = (node.get("content") or "").strip()
            if value:
                return self._clean_text(value)
        return ""

    def _extract_site_name(self, soup: BeautifulSoup) -> str:
        selectors = [
            "meta[property='og:site_name']",
            "meta[name='application-name']",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            value = (node.get("content") or "").strip()
            if value:
                return self._clean_text(value)
        return ""

    def _extract_media_urls(
        self,
        soup: BeautifulSoup,
        base_url: str,
        tag_name: str,
        attr_name: str,
    ) -> List[str]:
        urls: List[str] = []
        seen = set()

        for node in soup.find_all(tag_name):
            raw = (node.get(attr_name) or "").strip()
            if not raw:
                source = node.find("source")
                raw = ((source.get("src") if source else "") or "").strip()

            if not raw:
                continue

            absolute = urljoin(base_url, raw)
            if absolute in seen:
                continue

            seen.add(absolute)
            urls.append(absolute)

        return urls

    def _trim_repeated_lines(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        output: List[str] = []
        seen_recent: List[str] = []

        for line in lines:
            if not line:
                continue
            if line in seen_recent:
                continue
            output.append(line)
            seen_recent.append(line)
            if len(seen_recent) > 20:
                seen_recent.pop(0)

        return "\n".join(output)

    def _clean_text(self, value: str) -> str:
        value = html.unescape(value or "")
        value = re.sub(r"[ \t\r\f\v]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()