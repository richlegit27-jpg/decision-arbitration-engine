from __future__ import annotations

import re
import hashlib
from typing import Any, Dict, List
from urllib.parse import urlparse, urljoin, quote_plus

import requests
from bs4 import BeautifulSoup


class WebService:
    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.cache: Dict[str, dict] = {}

    # -----------------------
    # CORE HELPERS
    # -----------------------

    def normalize_url(self, url: str) -> str:
        url = str(url or "").strip()
        if not url:
            return ""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _hash(self, value: str) -> str:
        return hashlib.md5(str(value or "").encode()).hexdigest()

    def _headers(self) -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }

    def _search_headers(self) -> dict:
        headers = self._headers()
        headers["Accept-Language"] = "en-US,en;q=0.9"
        return headers

    # -----------------------
    # EXTRACTION
    # -----------------------

    def _strip_html(self, html: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        main = soup.find("article")
        if main is None:
            main = soup.find("main")
        if main is None:
            main = soup.body if soup.body else soup

        text = main.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:5000]

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        links = re.findall(r'href=["\'](.*?)["\']', html, re.I)
        results: List[str] = []

        for link in links:
            if link.startswith("#") or "javascript:" in link.lower():
                continue
            full = urljoin(base_url, link)
            if full.startswith("http"):
                results.append(full)

        return list(dict.fromkeys(results))[:20]

    def _extract_images(self, html: str, base_url: str) -> List[str]:
        imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html, re.I)
        results: List[str] = []

        for img in imgs:
            full = urljoin(base_url, img)
            if full.startswith("http"):
                results.append(full)

        return list(dict.fromkeys(results))[:10]

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        if not m:
            return ""
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title

    # -----------------------
    # INTELLIGENCE
    # -----------------------

    def _summarize(self, text: str) -> str:
        text = str(text or "").strip()
        if not text:
            return ""

        parts = re.split(r"\. |\n", text)
        cleaned: List[str] = []

        for p in parts:
            p = p.strip()
            if len(p) < 40:
                continue

            lowered = p.lower()
            if "advertisement" in lowered:
                continue
            if "skip to" in lowered:
                continue
            if "search the web" in lowered:
                continue
            if "all rights reserved" in lowered:
                continue
            if "privacy" in lowered:
                continue
            if "terms" in lowered:
                continue

            cleaned.append(p)

            if len(cleaned) >= 5:
                break

        return ". ".join(cleaned).strip()

    def _bullets(self, text: str) -> List[str]:
        text = str(text or "").strip()
        if not text:
            return []

        parts = re.split(r"\. |\n", text)
        bullets: List[str] = []

        for p in parts:
            p = p.strip()
            if not p:
                continue

            lowered = p.lower()

            if len(p) < 40 or len(p) > 200:
                continue
            if "advertisement" in lowered:
                continue
            if "skip to" in lowered:
                continue
            if "search the web" in lowered:
                continue
            if "all rights reserved" in lowered:
                continue
            if "privacy" in lowered:
                continue
            if "terms" in lowered:
                continue

            bullets.append(p)

            if len(bullets) >= 5:
                break

        return bullets

    def _detect_type(self, text: str, url: str) -> str:
        lowered = text.lower()
        if "login" in lowered or "sign in" in lowered:
            return "auth"
        if len(text) > 2000:
            return "article"
        return "general"

    # -----------------------
    # SEARCH
    # -----------------------

    def _clean_search_snippet(self, text: str) -> str:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return text[:300]

    def _search_cache_key(self, query: str) -> str:
        return "search:" + self._hash(query.lower().strip())

    def search(self, query: str, max_results: int = 5) -> dict:
        query = str(query or "").strip()
        if not query:
            return {"ok": False, "error": "empty query", "query": "", "results": []}

        cache_key = self._search_cache_key(query)
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)

            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self._search_headers(),
                allow_redirects=True,
            )
            response.raise_for_status()

            print("WEB SEARCH URL =", url)
            print("WEB SEARCH STATUS =", response.status_code)
            print("WEB SEARCH HTML PREVIEW =", response.text[:800])

            soup = BeautifulSoup(response.text or "", "html.parser")

            results: List[dict] = []

            candidates = (
                soup.select(".result")
                or soup.select(".result__body")
                or soup.select("div")
            )

            for result in candidates:
                title_el = (
                    result.select_one("a.result__a")
                    or result.select_one(".result__title a")
                    or result.select_one("h2 a")
                    or result.find("a")
                )

                snippet_el = (
                    result.select_one(".result__snippet")
                    or result.select_one(".result__content")
                    or result.find("span")
                )

                if title_el is None:
                    continue

                title = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()
                href = str(title_el.get("href") or "").strip()

                snippet = ""
                if snippet_el is not None:
                    snippet = self._clean_search_snippet(
                        snippet_el.get_text(" ", strip=True)
                    )

                if not href or not title:
                    continue

                final_url = self._extract_ddg_target(href) or href

                domain = ""
                try:
                    domain = urlparse(final_url).netloc
                except Exception:
                    domain = ""

                if not domain and not final_url.startswith("http"):
                    continue

                results.append(
                    {
                        "title": title,
                        "url": final_url,
                        "snippet": snippet,
                        "domain": domain,
                    }
                )

                if len(results) >= max_results:
                    break

            print("WEB SEARCH RESULT COUNT =", len(results))

            payload = {
                "ok": True,
                "query": query,
                "results": results,
                "summary": self._summarize_search_results(query, results),
            }

            self.cache[cache_key] = payload
            return payload

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "query": query,
                "results": [],
                "summary": "",
            }

    def _extract_ddg_target(self, href: str) -> str:
        href = str(href or "").strip()
        if not href:
            return ""

        # direct absolute url
        if href.startswith("http://") or href.startswith("https://"):
            return href

        # ddg redirect form /l/?uddg=...
        m = re.search(r"[?&]uddg=([^&]+)", href)
        if m:
            try:
                from urllib.parse import unquote
                return unquote(m.group(1))
            except Exception:
                return ""

        return ""

    def _summarize_search_results(self, query: str, results: List[dict]) -> str:
        if not results:
            return f'I searched for "{query}" but didn’t find strong results. Try opening a specific site or refining the query.'

        lines: List[str] = []

        for item in results[:3]:
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            domain = str(item.get("domain") or "").strip()

            if title and snippet:
                lines.append(f"{title}: {snippet}")
            elif title:
                lines.append(title)

        return " | ".join(lines)[:1200]

    # -----------------------
    # FETCH
    # -----------------------

    def fetch(self, url: str) -> dict:
        url = self.normalize_url(url)
        if not url:
            return {"ok": False, "error": "bad url"}

        key = "fetch:" + self._hash(url)

        if key in self.cache:
            return self.cache[key]

        try:
            r = requests.get(
                url,
                timeout=self.timeout,
                headers=self._headers(),
                allow_redirects=True,
            )
            r.raise_for_status()

            html = r.text
            text = self._strip_html(html)

            result = {
                "ok": True,
                "url": url,
                "domain": urlparse(url).netloc,
                "title": self._extract_title(html),
                "content": text,
                "summary": self._summarize(text),
                "bullets": self._bullets(text),
                "links": self._extract_links(html, url),
                "images": self._extract_images(html, url),
                "page_type": self._detect_type(text, url),
            }

            self.cache[key] = result
            return result

        except Exception as e:
            return {"ok": False, "error": str(e)}

    # -----------------------
    # ARTIFACTS
    # -----------------------

    def build_artifact_payload(self, r: Dict[str, Any]) -> dict:
        title = r.get("title") or "Web page"
        summary = r.get("summary") or ""
        content = r.get("content") or ""
        url = r.get("url") or ""

        body_parts = []
        if summary:
            body_parts.append(summary)
        if content:
            body_parts.append(content[:2000])

        body = "\n\n".join(body_parts).strip()

        return {
            "kind": "web_result",
            "title": title,
            "summary": summary,
            "body": body,
            "source_url": url,
            "meta": {
                "domain": r.get("domain"),
                "page_type": r.get("page_type"),
                "links": r.get("links"),
                "images": r.get("images"),
            },
            "viewer": {
                "title": title,
                "analysis_text": summary,
                "body": content[:2000],
                "bullets": r.get("bullets"),
                "links": r.get("links"),
                "images": r.get("images"),
                "source_url": url,
            },
        }

    def build_search_artifact_payload(self, r: Dict[str, Any]) -> dict:
        query = str(r.get("query") or "").strip()
        summary = str(r.get("summary") or "").strip()
        results = r.get("results") or []

        lines: List[str] = []
        for idx, item in enumerate(results[:5], start=1):
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("snippet") or "").strip()

            block = f"{idx}. {title}"
            if snippet:
                block += f"\n   {snippet}"
            if url:
                block += f"\n   {url}"
            lines.append(block)

        body_parts = []
        if summary:
            body_parts.append(summary)
        if lines:
            body_parts.append("\n\n".join(lines))

        body = "\n\n".join(body_parts).strip()

        return {
            "kind": "web_search",
            "title": f'Web search: {query}' if query else "Web search",
            "summary": summary,
            "body": body,
            "source_url": "",
            "meta": {
                "query": query,
                "result_count": len(results),
            },
            "viewer": {
                "title": f'Web search: {query}' if query else "Web search",
                "analysis_text": summary,
                "body": body,
                "results": results,
                "source_url": "",
            },
        }