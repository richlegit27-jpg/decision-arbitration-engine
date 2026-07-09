from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


class WebService:
    def __init__(self) -> None:
        self.timeout = 15
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    # =========================================================
    # public api
    # =========================================================

    def search_and_fetch(
        self,
        query: str,
        search_limit: int = 5,
        fetch_limit: int = 3,
    ) -> Dict[str, Any]:
        search_results = self.search_web(query=query, limit=search_limit)
        fetched_items: List[Dict[str, Any]] = []

        for item in search_results[:fetch_limit]:
            url = item.get("url", "").strip()
            rss_title = (item.get("title") or "").strip()
            rss_description = (item.get("description") or "").strip()

            fetched = self.fetch_url(url) if url else {
                "ok": False,
                "url": url,
                "title": rss_title or url,
                "description": rss_description,
                "content": "",
                "content_type": "",
                "status_code": 0,
                "source": "missing-url",
            }

            fetched_title = (fetched.get("title") or "").strip()
            fetched_content = (fetched.get("content") or "").strip()
            fetched_description = (fetched.get("description") or "").strip()

            bad_fetch = (
                not fetched.get("ok")
                or fetched_title.lower() == "google news"
                or fetched_content.lower() == "google news"
                or len(fetched_content) < 120
            )

            if bad_fetch:
                fallback_content_parts = []
                if rss_title:
                    fallback_content_parts.append(f"Headline: {rss_title}")
                if rss_description:
                    fallback_content_parts.append(f"Snippet: {rss_description}")

                fallback_content = "\n".join(fallback_content_parts).strip()

                fetched = {
                    "ok": True,
                    "url": url,
                    "title": rss_title or fetched_title or url,
                    "description": rss_description or fetched_description,
                    "content": fallback_content or rss_title or rss_description or url,
                    "content_type": "text/plain",
                    "status_code": 200,
                    "source": "rss-fallback",
                }

            fetched_items.append(fetched)

        return {
            "search": {
                "query": query,
                "results": search_results,
            },
            "fetch": {
                "items": fetched_items,
            },
        }

    def search_web(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        rss_url = self._google_news_rss_url(query)

        try:
            raw_xml = self._http_get_text(rss_url)
            return self._parse_google_news_rss(raw_xml, limit=limit)
        except Exception as e:
            return [{
                "title": "Web search failed",
                "url": "",
                "description": str(e),
                "ok": False,
            }]

    def fetch_url(self, url: str) -> Dict[str, Any]:
        url = (url or "").strip()
        if not url:
            return {
                "ok": False,
                "url": "",
                "title": "",
                "description": "Missing URL",
                "content": "",
                "content_type": "",
                "status_code": 0,
            }

        try:
            html_text = self._http_get_text(url)
            title = self._extract_title(html_text) or url
            description = self._extract_meta_description(html_text)
            content = self._extract_main_text(html_text)

            if not content.strip():
                content = description or title

            return {
                "ok": True,
                "url": url,
                "title": title,
                "description": description,
                "content": content[:12000],
                "content_type": "text/html",
                "status_code": 200,
                "source": "fetch",
            }

        except Exception as e:
            return {
                "ok": False,
                "url": url,
                "title": url,
                "description": str(e),
                "content": "",
                "content_type": "",
                "status_code": 0,
                "source": "fetch-error",
            }

    # =========================================================
    # internals
    # =========================================================

    def _google_news_rss_url(self, query: str) -> str:
        encoded = urllib.parse.quote(query)
        return (
            f"https://news.google.com/rss/search?q={encoded}"
            f"&hl=en-US&gl=US&ceid=US:en"
        )

    def _http_get_text(self, url: str) -> str:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")

    def _parse_google_news_rss(self, raw_xml: str, limit: int = 5) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        root = ET.fromstring(raw_xml)
        items = root.findall(".//item")

        for item in items[:limit]:
            title = self._safe_xml_text(item.find("title"))
            link = self._safe_xml_text(item.find("link"))
            description = self._safe_xml_text(item.find("description"))
            pub_date = self._safe_xml_text(item.find("pubDate"))
            source_name = self._safe_xml_text(item.find("source"))

            title = self._clean_text(title)
            description = self._clean_text(description)
            source_name = self._clean_text(source_name)

            extra_bits = []
            if source_name:
                extra_bits.append(f"Source: {source_name}")
            if pub_date:
                extra_bits.append(f"Published: {pub_date}")

            if extra_bits:
                description = (description + "\n" + "\n".join(extra_bits)).strip() if description else "\n".join(extra_bits)

            results.append({
                "title": title or link,
                "url": link,
                "description": description,
                "ok": True,
            })

        return results

    def _safe_xml_text(self, node) -> str:
        if node is None or node.text is None:
            return ""
        return node.text.strip()

    def _extract_title(self, raw_html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return self._clean_text(match.group(1))

    def _extract_meta_description(self, raw_html: str) -> str:
        patterns = [
            r'<meta[^>]+name="description"[^>]+content="([^"]*)"',
            r"<meta[^>]+name='description'[^>]+content='([^']*)'",
            r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
            r"<meta[^>]+property='og:description'[^>]+content='([^']*)'",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return self._clean_text(match.group(1))
        return ""

    def _extract_main_text(self, raw_html: str) -> str:
        text = raw_html

        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<noscript\b[^>]*>.*?</noscript>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)

        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</h[1-6]\s*>", "\n\n", text, flags=re.IGNORECASE)

        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n\s+", "\n", text)

        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if len(line) >= 40]

        joined = "\n".join(lines).strip()
        if len(joined) < 300:
            joined = text.strip()

        return joined[:12000]

    def _clean_text(self, value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", value or "")
        value = html.unescape(value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

