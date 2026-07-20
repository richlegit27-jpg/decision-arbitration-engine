from __future__ import annotations

import requests
from bs4 import BeautifulSoup


class WebPreviewRouteService:

    def preview(self, url):
        url = str(url or "").strip()

        if not url:
            return {
                "ok": False,
                "error": "Missing url",
                "title": "Source preview",
                "preview": "",
                "url": "",
            }

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            if (
                "news.google.com/rss/articles/" in url
                or "news.google.com/articles/" in url
            ):
                try:
                    redirect_response = requests.get(
                        url,
                        headers=headers,
                        timeout=10,
                        allow_redirects=True,
                    )

                    if redirect_response.url:
                        url = redirect_response.url

                except Exception:
                    pass

            response = requests.get(
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True,
            )

            final_url = response.url or url
            html = response.text or ""

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            for tag in soup([
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
                "noscript",
                "svg",
            ]):
                tag.decompose()

            title = ""

            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            article = soup.find("article")

            if article:
                text = article.get_text(
                    "\n",
                    strip=True,
                )
            else:
                text = soup.get_text(
                    "\n",
                    strip=True,
                )

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            junk_phrases = [
                "sign in",
                "subscribe",
                "advertisement",
                "cookie",
                "privacy policy",
                "terms of use",
                "enable javascript",
                "all rights reserved",
            ]

            cleaned_lines = []

            for line in lines:
                low = line.lower()

                if any(
                    junk in low
                    for junk in junk_phrases
                ):
                    continue

                if len(line) < 20:
                    continue

                cleaned_lines.append(line)

            preview = "\n".join(
                cleaned_lines[:24]
            ).strip()

            if not preview:
                preview = (
                    "Preview route is working, "
                    "but no readable article text was found."
                )

            return {
                "ok": True,
                "title": title or "Source preview",
                "preview": preview[:4000],
                "url": final_url,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "title": "Source preview",
                "preview": "Preview failed on backend.",
                "url": url,
            }