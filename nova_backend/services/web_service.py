from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

import requests


class WebService:
    def __init__(self, timeout: int = 12, user_agent: str | None = None):
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    # -----------------------
    # HELPERS
    # -----------------------

    def normalize_url(self, url: str) -> str:
        value = str(url or "").strip()
        if not value:
            return ""

        if not value.startswith(("http://", "https://")):
            value = "https://" + value

        return value

    def _headers(self) -> dict:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _extract_title(self, html: str) -> str:
        text = str(html or "")
        lower = text.lower()

        start_tag = lower.find("<title>")
        end_tag = lower.find("</title>")

        if start_tag == -1 or end_tag == -1 or end_tag <= start_tag:
            return ""

        start = start_tag + len("<title>")
        return text[start:end_tag].strip()

    def _extract_meta_content(self, html: str, needle: str) -> str:
        text = str(html or "")
        lower = text.lower()
        needle_lower = needle.lower()

        pos = lower.find(needle_lower)
        if pos == -1:
            return ""

        content_pos = lower.find('content="', pos)
        quote = '"'
        if content_pos == -1:
            content_pos = lower.find("content='", pos)
            quote = "'"

        if content_pos == -1:
            return ""

        start = content_pos + len("content=") + 1
        end = text.find(quote, start)
        if end == -1:
            return ""

        return text[start:end].strip()

    def _strip_html(self, html: str) -> str:
        text = str(html or "")
        out = []
        inside = False

        for ch in text:
            if ch == "<":
                inside = True
                continue
            if ch == ">":
                inside = False
                out.append(" ")
                continue
            if not inside:
                out.append(ch)

        cleaned = "".join(out)
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()

    def _preview_text(self, text: str, limit: int = 400) -> str:
        value = str(text or "").strip()
        if len(value) <= limit:
            return value
        return value[:limit].rstrip() + "…"

    # -----------------------
    # FETCH
    # -----------------------

    def fetch(self, url: str) -> dict:
        target = self.normalize_url(url)
        if not target:
            return {
                "ok": False,
                "error": "Missing URL",
                "url": "",
                "ssl_verified": True,
            }

        try:
            response = requests.get(
                target,
                timeout=self.timeout,
                headers=self._headers(),
                allow_redirects=True,
            )
            html = response.text

            return self._build_result(
                url=target,
                final_url=str(response.url or target),
                status_code=int(response.status_code),
                html=html,
                ssl_verified=True,
                ok=True,
            )
        except requests.exceptions.SSLError:
            try:
                response = requests.get(
                    target,
                    timeout=self.timeout,
                    headers=self._headers(),
                    allow_redirects=True,
                    verify=False,
                )
                html = response.text

                return self._build_result(
                    url=target,
                    final_url=str(response.url or target),
                    status_code=int(response.status_code),
                    html=html,
                    ssl_verified=False,
                    ok=True,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "error": str(exc),
                    "url": target,
                    "ssl_verified": False,
                }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "url": target,
                "ssl_verified": True,
            }

    # -----------------------
    # RESULT BUILDING
    # -----------------------

    def _build_result(
        self,
        url: str,
        final_url: str,
        status_code: int,
        html: str,
        ssl_verified: bool,
        ok: bool,
    ) -> dict:
        title = self._extract_title(html)
        description = (
            self._extract_meta_content(html, 'name="description"')
            or self._extract_meta_content(html, 'property="og:description"')
        )
        site_name = self._extract_meta_content(html, 'property="og:site_name"')

        content_text = self._strip_html(html)
        preview = self._preview_text(content_text, 400)
        summary = self._preview_text(content_text, 1200)

        parsed = urlparse(final_url or url)
        domain = parsed.netloc or ""

        return {
            "ok": ok,
            "url": url,
            "final_url": final_url,
            "domain": domain,
            "status_code": status_code,
            "ssl_verified": ssl_verified,
            "title": title,
            "description": description,
            "site_name": site_name,
            "content": content_text,
            "preview": preview,
            "summary": summary,
            "html": html,
        }

    # -----------------------
    # ARTIFACT HELPERS
    # -----------------------

    def build_artifact_payload(self, fetch_result: Dict[str, Any]) -> dict:
        result = dict(fetch_result or {})

        title = str(result.get("title") or "Fetched page").strip() or "Fetched page"
        summary = str(result.get("summary") or result.get("preview") or "").strip()
        final_url = str(result.get("final_url") or result.get("url") or "").strip()

        return {
            "kind": "web_result",
            "title": title,
            "body": summary,
            "source": "web",
            "meta": {
                "url": final_url,
                "source_url": final_url,
                "status_code": result.get("status_code"),
                "domain": result.get("domain"),
                "site_name": result.get("site_name"),
                "description": result.get("description"),
                "ssl_verified": result.get("ssl_verified"),
            },
            "viewer": {
                "kind": "web_result",
                "title": title,
                "body": summary,
                "source_url": final_url,
                "image_url": "",
                "video_url": "",
                "audio_url": "",
                "analysis_text": "",
                "bullets": [],
            },
        }