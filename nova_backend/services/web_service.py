from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class WebService:
    def __init__(self, timeout: int = 12):
        self.timeout = int(timeout or 12)
        self.cache: Dict[str, dict] = {}

    # -----------------------
    # BASIC HELPERS
    # -----------------------

    def _hash(self, value: str) -> str:
        return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()

    def _headers(self) -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }

    def _search_headers(self) -> dict:
        headers = self._headers()
        headers["Accept-Language"] = "en-US,en;q=0.9"
        return headers

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _strip_html(self, html: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        main = soup.find("article")
        if main is None:
            main = soup.find("main")
        if main is None:
            main = soup.body if soup.body else soup

        text = main.get_text("\n", strip=True) if main else ""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _extract_title(self, html: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        return self._clean_text(title)[:300]

    def _summarize(self, text: str, max_len: int = 500) -> str:
        text = self._clean_text(text)
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        cut = text[:max_len].rsplit(" ", 1)[0].strip()
        return cut or text[:max_len]

    def _bullets(self, text: str, limit: int = 5) -> List[str]:
        text = str(text or "").strip()
        if not text:
            return []

        parts = re.split(r"(?<=[.!?])\s+", text)
        bullets: List[str] = []

        for part in parts:
            cleaned = self._clean_text(part)
            if not cleaned:
                continue
            bullets.append(cleaned[:220])
            if len(bullets) >= limit:
                break

        return bullets

    def _extract_links(self, html: str, base_url: str) -> List[dict]:
        soup = BeautifulSoup(html or "", "html.parser")
        seen = set()
        items: List[dict] = []

        for a in soup.find_all("a", href=True):
            href = str(a.get("href") or "").strip()
            text = self._clean_text(a.get_text(" ", strip=True))
            if not href:
                continue

            full = urljoin(base_url, href)
            if full in seen:
                continue
            seen.add(full)

            items.append(
                {
                    "text": text[:200],
                    "url": full,
                }
            )

            if len(items) >= 30:
                break

        return items

    def _extract_images(self, html: str, base_url: str) -> List[dict]:
        soup = BeautifulSoup(html or "", "html.parser")
        seen = set()
        items: List[dict] = []

        for img in soup.find_all("img"):
            src = str(img.get("src") or "").strip()
            alt = self._clean_text(img.get("alt") or "")
            if not src:
                continue

            full = urljoin(base_url, src)
            if full in seen:
                continue
            seen.add(full)

            items.append(
                {
                    "url": full,
                    "alt": alt[:200],
                }
            )

            if len(items) >= 30:
                break

        return items

    def _detect_type(self, text: str, url: str) -> str:
        lowered = str(text or "").lower()
        parsed = urlparse(str(url or ""))

        if "news" in parsed.netloc or "/news" in parsed.path:
            return "news"
        if "product" in lowered or "add to cart" in lowered:
            return "product"
        if "contact" in lowered or "hours" in lowered or "location" in lowered:
            return "business"
        return "web_page"

    def normalize_url(self, url: str) -> str:
        url = str(url or "").strip()
        if not url:
            return ""
        if not re.match(r"^https?://", url, flags=re.I):
            url = "https://" + url
        return url

    # -----------------------
    # INTENT ROUTING
    # -----------------------

    def _search_cache_key(self, query: str) -> str:
        return "search:" + self._hash(query.lower().strip())

    def classify_web_query(self, query: str) -> str:
        q = str(query or "").strip().lower()
        if not q:
            return "search"

        price_words = (
            "price",
            "quote",
            "trading",
            "market cap",
            "chart",
            "value",
            "worth",
        )
        crypto_words = (
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "solana",
            "sol",
            "dogecoin",
            "doge",
            "xrp",
            "ripple",
            "cardano",
            "ada",
            "litecoin",
            "ltc",
            "bnb",
            "binance coin",
        )
        weather_words = (
            "weather",
            "forecast",
            "temperature",
            "rain",
            "snow",
            "wind",
            "humidity",
            "hot",
            "cold",
        )
        business_words = (
            "hours",
            "open now",
            "closing time",
            "address",
            "phone number",
            "location",
            "directions",
            "near me",
        )

        if any(word in q for word in crypto_words) and any(word in q for word in price_words):
            return "crypto_price"

        if any(word in q for word in weather_words):
            return "weather"

        if any(word in q for word in business_words):
            return "business_lookup"

        return "search"

    # -----------------------
    # SEARCH ROUTER
    # -----------------------

def search(self, query: str, max_results: int = 5) -> dict:
    query = str(query or "").strip()

    if not query:
        return {
            "ok": False,
            "query": query,
            "results": [],
            "summary": "Empty query.",
            "source_type": "search",
        }

    route = self.classify_web_query(query)

    try:
        # --- CRYPTO ---
        if route == "crypto_price":
            return self.lookup_crypto_price(query)

        # --- WEATHER ---
        if route == "weather":
            return self.lookup_weather(query)

        # --- BUSINESS ---
        if route == "business_lookup":
            return self.lookup_business(query, max_results=max_results)

        # --- DEFAULT SEARCH ---
        return self.search_web_html(query, max_results=max_results)

    except Exception as e:
        return {
            "ok": False,
            "query": query,
            "results": [],
            "summary": f"Search failed: {e}",
            "source_type": "search_error",
        }

    # -----------------------
    # SPECIALIST LANES
    # -----------------------

    def _extract_crypto_id(self, query: str) -> str:
        q = str(query or "").lower()

        mapping = {
            "bitcoin": "bitcoin",
            "btc": "bitcoin",
            "ethereum": "ethereum",
            "eth": "ethereum",
            "solana": "solana",
            "sol": "solana",
            "dogecoin": "dogecoin",
            "doge": "dogecoin",
            "xrp": "ripple",
            "ripple": "ripple",
            "cardano": "cardano",
            "ada": "cardano",
            "litecoin": "litecoin",
            "ltc": "litecoin",
            "bnb": "binancecoin",
            "binance coin": "binancecoin",
        }

        for key, value in mapping.items():
            if re.search(rf"\b{re.escape(key)}\b", q):
                return value

        return ""

    def lookup_crypto_price(self, query: str) -> dict:
        coin_id = self._extract_crypto_id(query)

        if not coin_id:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": f'Crypto symbol not recognized for "{query}".',
                "source_type": "crypto_price",
                "coin_id": "",
            }

        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            }

            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers=self._headers(),
                allow_redirects=True,
            )
            response.raise_for_status()

            data = response.json() or {}
            coin_data = data.get(coin_id) or {}

            usd = coin_data.get("usd")
            change_24h = coin_data.get("usd_24h_change")
            market_cap = coin_data.get("usd_market_cap")

            if usd is None:
                return {
                    "ok": False,
                    "query": query,
                    "results": [],
                    "summary": f'CoinGecko returned no USD price for "{coin_id}".',
                    "source_type": "crypto_price",
                    "coin_id": coin_id,
                }

            pretty_name = (
                coin_id.replace("binancecoin", "Binance Coin")
                .replace("-", " ")
                .title()
            )

            summary_parts = [f"{pretty_name} price: ${usd:,.2f} USD"]

            if isinstance(change_24h, (int, float)):
                summary_parts.append(f"24h change: {change_24h:+.2f}%")

            if isinstance(market_cap, (int, float)):
                summary_parts.append(f"Market cap: ${market_cap:,.0f}")

            summary = " | ".join(summary_parts)

            return {
                "ok": True,
                "query": query,
                "results": [
                    {
                        "title": f"{pretty_name} price",
                        "url": f"https://www.coingecko.com/en/coins/{coin_id}",
                        "snippet": summary,
                        "domain": "www.coingecko.com",
                    }
                ],
                "summary": summary,
                "source_type": "crypto_price",
                "coin_id": coin_id,
            }

        except requests.RequestException as e:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": f"CoinGecko request failed: {e}",
                "source_type": "crypto_price",
                "coin_id": coin_id,
            }
        except Exception as e:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": f"Crypto price lookup failed: {e}",
                "source_type": "crypto_price",
                "coin_id": coin_id,
            }

    def lookup_weather(self, query: str) -> dict:
        # Safe starter: keep this routed through generic search until you add a weather API.
        result = self.search_web_html(query, max_results=5)
        result["source_type"] = "weather_search"
        return result

    def lookup_business(self, query: str, max_results: int = 5) -> dict:
        # Safe starter: keep this routed through generic search until you add a maps/business API.
        result = self.search_web_html(query, max_results=max_results)
        result["source_type"] = "business_search"
        return result

    # -----------------------
    # GENERIC HTML SEARCH
    # -----------------------

    def search_web_html(self, query: str, max_results: int = 5) -> dict:
        query = str(query or "").strip()

        try:
            url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self._search_headers(),
                allow_redirects=True,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text or "", "html.parser")
            results: List[dict] = []

            candidates = soup.select(".result")

            if not candidates:
                candidates = soup.select(".result__body")

            if not candidates:
                candidates = soup.select(".web-result")

            if not candidates:
                candidates = soup.select("a[href]")

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

                if "duckduckgo.com" in href:
                    continue

                final_url = self._extract_ddg_target(href) or href
                print("PARSED:", title, final_url)
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

            return {
                "ok": True,
                "query": query,
                "results": results,
                "summary": self._summarize_search_results(query, results),
                "source_type": "search_html",
            }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "query": query,
                "results": [],
                "summary": "",
                "source_type": "search_html",
            }

    def _clean_search_snippet(self, text: str) -> str:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return text[:300]

    def _extract_ddg_target(self, href: str) -> str:
        href = str(href or "").strip()
        if not href:
            return ""

        if href.startswith("http://") or href.startswith("https://"):
            return href

        match = re.search(r"[?&]uddg=([^&]+)", href)
        if match:
            try:
                return unquote(match.group(1))
            except Exception:
                return ""

        return ""

    def _summarize_search_results(self, query: str, results: List[dict]) -> str:
        query = str(query or "").strip()
        results = results if isinstance(results, list) else []

        cleaned: List[dict] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or item.get("name") or "").strip()
            snippet = str(
                item.get("snippet") or item.get("content") or item.get("body") or ""
            ).strip()
            url = str(item.get("url") or item.get("source_url") or "").strip()

            if not (title or snippet or url):
                continue

            cleaned.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                }
            )

        if not cleaned:
            return f'I searched for "{query}" but could not find strong live results.'

        lines: List[str] = []

        for item in cleaned[:5]:
            block: List[str] = []
            if item["title"]:
                block.append(item["title"])
            if item["snippet"]:
                block.append(item["snippet"])
            if item["url"]:
                block.append(item["url"])
            lines.append("\n".join(block).strip())

        return "\n\n".join(lines).strip()[:2000]

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
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self._headers(),
                allow_redirects=True,
            )
            response.raise_for_status()

            html = response.text
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
            return {
                "ok": False,
                "url": url,
                "error": str(e),
                "summary": "",
                "content": "",
                "bullets": [],
                "links": [],
                "images": [],
                "page_type": "web_page",
            }

    # -----------------------
    # ARTIFACT PAYLOADS
    # -----------------------

    def build_search_artifact_payload(self, result: Dict[str, Any]) -> dict:
        query = str(result.get("query") or "").strip()
        summary = str(result.get("summary") or "").strip()
        results = result.get("results") or []
        source_type = str(result.get("source_type") or "search").strip()

        lines: List[str] = []
        for idx, item in enumerate(results[:5], start=1):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snippet = str(item.get("snippet") or "").strip()

            block = f"{idx}. {title}" if title else f"{idx}."
            if snippet:
                block += f"\n   {snippet}"
            if url:
                block += f"\n   {url}"
            lines.append(block)

        body_parts: List[str] = []
        if summary:
            body_parts.append(summary)
        if lines:
            body_parts.append("\n\n".join(lines))

        body = "\n\n".join(part for part in body_parts if part).strip()

        return {
            "kind": "web_search",
            "title": f"Web search: {query}" if query else "Web search",
            "summary": summary,
            "body": body,
            "source_type": source_type,
            "meta": {
                "query": query,
                "source_type": source_type,
                "results_count": len(results),
            },
            "viewer": {
                "kind": "web_search",
                "title": f"Web search: {query}" if query else "Web search",
                "body": body,
            },
        }

    def build_fetch_artifact_payload(self, result: Dict[str, Any]) -> dict:
        title = str(result.get("title") or result.get("url") or "Web page").strip()
        summary = str(result.get("summary") or "").strip()
        url = str(result.get("url") or "").strip()
        content = str(result.get("content") or "").strip()

        body_parts: List[str] = []
        if summary:
            body_parts.append(summary)
        if url:
            body_parts.append(url)
        if content:
            body_parts.append(content[:4000])

        body = "\n\n".join(part for part in body_parts if part).strip()

        return {
            "kind": "web_fetch",
            "title": title,
            "summary": summary,
            "body": body,
            "source_url": url,
            "meta": {
                "url": url,
                "domain": str(result.get("domain") or "").strip(),
                "page_type": str(result.get("page_type") or "web_page").strip(),
            },
            "viewer": {
                "kind": "web_fetch",
                "title": title,
                "body": body,
                "source_url": url,
            },
        }