from __future__ import annotations

import re
import hashlib
from typing import Any, Dict, List
from urllib.parse import urlparse, urljoin

import requests


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

    def _hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        }

    # -----------------------
    # EXTRACTION
    # -----------------------

    def _strip_html(self, html: str) -> str:
        text = str(html or "")

        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        links = re.findall(r'href=["\'](.*?)["\']', html, re.I)
        results = []

        for link in links:
            if link.startswith("#") or "javascript:" in link:
                continue
            full = urljoin(base_url, link)
            if full.startswith("http"):
                results.append(full)

        return list(dict.fromkeys(results))[:20]

    def _extract_images(self, html: str, base_url: str) -> List[str]:
        imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html, re.I)
        results = []

        for img in imgs:
            full = urljoin(base_url, img)
            if full.startswith("http"):
                results.append(full)

        return list(dict.fromkeys(results))[:10]

    # -----------------------
    # INTELLIGENCE
    # -----------------------

    def _summarize(self, text: str) -> str:
        parts = re.split(r"\. |\n", text)
        return ". ".join(parts[:3]).strip()

    def _bullets(self, text: str) -> List[str]:
        parts = re.split(r"\. |\n", text)
        bullets = []

        for p in parts:
            p = p.strip()
            if 40 < len(p) < 200:
                bullets.append(p)
            if len(bullets) >= 5:
                break

        return bullets

    def _detect_type(self, text: str, url: str) -> str:
        if "login" in text.lower():
            return "auth"
        if len(text) > 2000:
            return "article"
        return "general"

    # -----------------------
    # FETCH
    # -----------------------

    def fetch(self, url: str) -> dict:
        url = self.normalize_url(url)
        if not url:
            return {"ok": False, "error": "bad url"}

        key = self._hash(url)

        # CACHE HIT
        if key in self.cache:
            return self.cache[key]

        try:
            r = requests.get(url, timeout=self.timeout, headers=self._headers())
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

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title>(.*?)</title>", html, re.I)
        return m.group(1).strip() if m else ""

    # -----------------------
    # ARTIFACT
    # -----------------------

    def build_artifact_payload(self, r: Dict[str, Any]) -> dict:
        title = r.get("title") or "Web page"
        summary = r.get("summary") or ""
        content = r.get("content") or ""
        url = r.get("url") or ""

        return {
            "kind": "web_result",
            "title": title,
            "summary": summary,
            "body": summary + "\n\n" + content[:2000],
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