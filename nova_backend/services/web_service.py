from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class WebService:
    def __init__(self, timeout: int = 6):
        self.timeout = int(timeout or 12)
        self.cache: Dict[str, dict] = {}

        self.brave_api_key = str(os.getenv("BRAVE_SEARCH_API_KEY") or "").strip()
        self.brave_web_endpoint = "https://api.search.brave.com/res/v1/web/search"
        self.brave_news_endpoint = "https://api.search.brave.com/res/v1/news/search"

        self.trusted_domains = {
            "reuters.com",
            "apnews.com",
            "bloomberg.com",
            "cnbc.com",
            "wsj.com",
            "ft.com",
            "theverge.com",
            "techcrunch.com",
            "arstechnica.com",
            "coindesk.com",
            "cointelegraph.com",
            "sec.gov",
            "whitehouse.gov",
            "canada.ca",
            "weather.gc.ca",
            "openai.com",
            "nvidia.com",
            "microsoft.com",
            "google.com",
            "alphabet.com",
            "meta.com",
            "tesla.com",
            "apple.com",
            "amazon.com",
            "coingecko.com",
        }

        self.low_quality_domains = {
            "pinterest.com",
            "facebook.com",
            "instagram.com",
            "tiktok.com",
        }

        self.news_domains = {
            "reuters.com",
            "apnews.com",
            "bloomberg.com",
            "cnbc.com",
            "wsj.com",
            "ft.com",
            "theverge.com",
            "techcrunch.com",
            "arstechnica.com",
        }

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

    def _clean_url(self, url: str) -> str:
        url = str(url or "").strip()

        # ðŸ”¥ Fix Google News redirect URLs
        if "news.google.com/rss/articles" in url:
            try:
                import urllib.parse as up
                parsed = up.urlparse(url)
                qs = up.parse_qs(parsed.query)

                for key in ["url", "u"]:
                    if key in qs and qs[key]:
                        return qs[key][0]
            except:
                pass

        return url

    def _brave_headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        if self.brave_api_key:
            headers["X-Subscription-Token"] = self.brave_api_key
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

    def _summarize(self, text: str, max_len: int = 700) -> str:
        text = self._clean_text(text)
        if not text:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+", text)
        bullets = []

        for sentence in sentences:
            sentence = self._clean_text(sentence)
            if len(sentence) < 40:
                continue
            bullets.append(sentence[:220])
            if len(bullets) >= 3:
                break

        if bullets:
            return "\n".join(f"â€¢ {bullet}" for bullet in bullets)

        if len(text) <= max_len:
            return "â€¢ " + text

        cut = text[:max_len].rsplit(" ", 1)[0].strip()
        return "â€¢ " + (cut or text[:max_len])

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

    def _clean_source_url(self, url: str) -> str:
        url = str(url or "").strip()
        if not url:
            return ""

        if "news.google.com/rss/articles" in url:
            try:
                import base64
                import re
                import urllib.parse as up

                parsed = up.urlparse(url)
                qs = up.parse_qs(parsed.query)

                for key in ["url", "u"]:
                    if key in qs and qs[key]:
                        return qs[key][0]

                # Google RSS URLs often hide the real URL in an encoded path.
                # If we cannot safely decode it, keep original instead of crashing.
                path_part = parsed.path.split("/articles/")[-1].split("?")[0]
                path_part = path_part.replace("-", "+").replace("_", "/")
                path_part += "=" * (-len(path_part) % 4)

                decoded = base64.urlsafe_b64decode(path_part).decode("utf-8", errors="ignore")
                match = re.search(r"https?://[^\s\x00-\x1f\"']+", decoded)
                if match:
                    return match.group(0)
            except Exception:
                return url

        return url

    def normalize_url(self, url: str) -> str:
        url = str(url or "").strip()
        if not url:
            return ""
        if not re.match(r"^https?://", url, flags=re.I):
            url = "https://" + url
        return url

    def _domain_root(self, domain: str) -> str:
        domain = str(domain or "").strip().lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def _extract_domain(self, url: str) -> str:
        try:
            return self._domain_root(urlparse(str(url or "")).netloc)
        except Exception:
            return ""

    def _query_tokens(self, query: str) -> List[str]:
        raw = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-\._]+", str(query or "").lower())
        stop = {
            "the", "a", "an", "on", "in", "for", "of", "to", "and", "or",
            "is", "are", "what", "who", "where", "when", "latest", "news",
            "today", "current", "update", "price", "stock",
        }
        return [token for token in raw if token not in stop and len(token) > 1]

    def _wants_freshness(self, query: str) -> bool:
        q = str(query or "").lower()
        freshness_words = (
            "latest",
            "news",
            "today",
            "current",
            "update",
            "updates",
            "recent",
            "right now",
            "this week",
            "breaking",
        )
        return any(word in q for word in freshness_words)

    def _looks_like_news_query(self, query: str) -> bool:
        q = str(query or "").lower()
        news_words = (
            "latest",
            "news",
            "current",
            "today",
            "update",
            "updates",
            "recent",
            "breaking",
        )
        return any(word in q for word in news_words)

    def _looks_like_url(self, query: str) -> bool:
        q = str(query or "").strip().lower()
        return q.startswith("http://") or q.startswith("https://") or q.startswith("www.")

    # -----------------------
    # INTENT ROUTING
    # -----------------------

    def _search_cache_key(self, query: str) -> str:
        return "search:" + self._hash(query.lower().strip())

    def classify_web_query(self, query: str) -> str:
        q = str(query or "").strip().lower()
        if not q:
            return "search"

        if self._looks_like_url(q):
            return "url_fetch"

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
            if route == "url_fetch":
                fetched = self.fetch(query)
                if fetched.get("ok"):
                    return {
                        "ok": True,
                        "query": query,
                        "results": [
                            {
                                "title": str(fetched.get("title") or query).strip(),
                                "url": str(fetched.get("url") or query).strip(),
                                "snippet": str(fetched.get("summary") or "").strip(),
                                "domain": self._extract_domain(fetched.get("url") or query),
                            }
                        ],
                        "summary": str(fetched.get("summary") or "").strip(),
                        "source_type": "url_fetch",
                    }
                return {
                    "ok": False,
                    "query": query,
                    "results": [],
                    "summary": str(fetched.get("error") or "Fetch failed."),
                    "source_type": "url_fetch",
                }

            if route == "crypto_price":
                return self.lookup_crypto_price(query)

            if route == "weather":
                return self.lookup_weather(query)

            if route == "business_lookup":
                return self.lookup_business(query, max_results=max_results)

            return self.search_web_api(
                query,
                max_results=max_results,
                preferred_mode="news" if self._looks_like_news_query(query) else "general",
            )

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
                        "domain": "coingecko.com",
                        "score": 100.0,
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
        return self.search_web_api(query, max_results=5, preferred_mode="weather")

    def lookup_business(self, query: str, max_results: int = 5) -> dict:
        return self.search_web_api(query, max_results=max_results, preferred_mode="business")

    # -----------------------
    # RANKING
    # -----------------------

    def _score_search_result(self, query: str, item: dict, preferred_mode: str = "general") -> float:
        if not isinstance(item, dict):
            return -9999.0

        title = str(item.get("title") or "").strip().lower()
        snippet = str(item.get("snippet") or "").strip().lower()
        url = str(item.get("url") or "").strip().lower()
        domain = self._domain_root(item.get("domain") or self._extract_domain(url))
        age = str(item.get("age") or "").strip().lower()

        query_lower = str(query or "").strip().lower()
        query_tokens = self._query_tokens(query_lower)

        score = 0.0

        if title:
            score += 8.0
        if url:
            score += 4.0
        if snippet:
            score += 4.0

        if query_lower and query_lower in title:
            score += 55.0
        if query_lower and query_lower in snippet:
            score += 24.0

        token_hits_title = 0
        token_hits_snippet = 0
        for token in query_tokens:
            if token in title:
                token_hits_title += 1
            if token in snippet:
                token_hits_snippet += 1

        score += token_hits_title * 12.0
        score += token_hits_snippet * 5.0

        if query_tokens:
            coverage = (token_hits_title + token_hits_snippet) / max(len(query_tokens), 1)
            score += min(coverage * 10.0, 20.0)

        if domain in self.trusted_domains:
            score += 24.0

        if domain in self.low_quality_domains:
            score -= 30.0

        if domain:
            parts = domain.split(".")
            if len(parts) >= 2:
                base = ".".join(parts[-2:])
                for token in query_tokens:
                    if token and token in base:
                        score += 20.0

        if self._wants_freshness(query):
            freshness_markers = (
                "hour ago",
                "hours ago",
                "minute ago",
                "minutes ago",
                "today",
                "yesterday",
                "2026",
                "2025",
            )
            if any(marker in age for marker in freshness_markers):
                score += 18.0
            if age:
                score += 6.0

        finance_words = ("price", "stock", "shares", "market cap", "earnings", "crypto", "bitcoin", "btc")
        if any(word in query_lower for word in finance_words):
            if domain in {"coingecko.com", "coindesk.com", "cointelegraph.com", "cnbc.com", "bloomberg.com", "reuters.com"}:
                score += 18.0
            if any(word in title for word in ("price", "stock", "market", "btc", "bitcoin", "crypto")):
                score += 12.0

        if preferred_mode == "news" or self._wants_freshness(query):
            if domain in self.news_domains:
                score += 20.0
            if "/news" in url:
                score += 10.0

        if preferred_mode == "weather":
            if domain.endswith("weather.gc.ca"):
                score += 35.0
            if "weather" in domain or "forecast" in title:
                score += 10.0

        if preferred_mode == "business":
            if "maps" in url or "location" in url or "hours" in title:
                score += 18.0
            if any(word in snippet for word in ("open", "closed", "hours", "address", "phone")):
                score += 10.0

        if any(token in domain for token in query_tokens):
            if domain in {
                "nvidia.com",
                "microsoft.com",
                "google.com",
                "alphabet.com",
                "meta.com",
                "tesla.com",
                "apple.com",
                "amazon.com",
                "openai.com",
            }:
                score += 16.0

        if title and query_lower and title.startswith(query_lower):
            score += 12.0

        if len(title) > 180:
            score -= 4.0
        if not snippet:
            score -= 3.0

        return score

    def _rank_search_results(self, query: str, results: List[dict], preferred_mode: str = "general") -> List[dict]:
        ranked: List[dict] = []

        for item in results if isinstance(results, list) else []:
            if not isinstance(item, dict):
                continue

            normalized = dict(item)
            normalized["domain"] = self._domain_root(
                normalized.get("domain") or self._extract_domain(normalized.get("url") or "")
            )
            normalized["score"] = float(self._score_search_result(query, normalized, preferred_mode))
            ranked.append(normalized)

        ranked.sort(
            key=lambda x: (
                float(x.get("score") or 0.0),
                len(str(x.get("snippet") or "")),
                len(str(x.get("title") or "")),
            ),
            reverse=True,
        )
        return ranked

    # -----------------------
    # BRAVE API SEARCH
    # -----------------------

    def _check_api_key(self) -> str:
        if self.brave_api_key:
            return ""
        return "BRAVE_SEARCH_API_KEY is missing."

    def _normalize_brave_web_results(self, payload: dict) -> List[dict]:
        web_block = payload.get("web") if isinstance(payload, dict) else {}
        raw_results = web_block.get("results") if isinstance(web_block, dict) else []
        raw_results = raw_results if isinstance(raw_results, list) else []

        results: List[dict] = []

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            title = self._clean_text(item.get("title") or "")
            url = str(item.get("url") or "").strip()
            description = self._clean_text(item.get("description") or "")
            age = self._clean_text(item.get("age") or item.get("page_age") or "")

            meta_url = item.get("meta_url") if isinstance(item.get("meta_url"), dict) else {}
            display_url = str(meta_url.get("display_url") or url).strip()

            domain = self._extract_domain(url)

            if not (title or url):
                continue

            snippet = description
            if age and age not in snippet:
                snippet = f"{age} | {snippet}" if snippet else age

            results.append(
                {
                    "title": title[:200],
                    "url": url,
                    "snippet": snippet[:400],
                    "domain": domain,
                    "display_url": display_url,
                    "age": age,
                }
            )

        return results

    def _normalize_brave_news_results(self, payload: dict) -> List[dict]:
        results_block = payload.get("results") if isinstance(payload, dict) else []
        results_block = results_block if isinstance(results_block, list) else []

        results: List[dict] = []

        for item in results_block:
            if not isinstance(item, dict):
                continue

            title = self._clean_text(item.get("title") or "")
            url = str(item.get("url") or "").strip()
            description = self._clean_text(item.get("description") or item.get("snippet") or "")
            age = self._clean_text(item.get("age") or "")
            meta_url = item.get("meta_url") if isinstance(item.get("meta_url"), dict) else {}
            display_url = str(meta_url.get("display_url") or url).strip()
            domain = self._extract_domain(url)

            if not (title or url):
                continue

            snippet = description
            if age and age not in snippet:
                snippet = f"{age} | {snippet}" if snippet else age

            results.append(
                {
                    "title": title[:200],
                    "url": url,
                    "snippet": snippet[:400],
                    "domain": domain,
                    "display_url": display_url,
                    "age": age,
                }
            )

        return results

    def _duckduckgo_search(self, query: str, max_results: int = 5) -> List[dict]:
        try:
            url = "https://html.duckduckgo.com/html/"
            response = requests.post(
                url,
                data={"q": query},
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # ðŸ”¥ updated selectors (more reliable)
            for result in soup.find_all("div", class_="result__body"):
                title_tag = result.find("a", class_="result__a")
                snippet_tag = result.find("a", class_="result__snippet")

                if not title_tag:
                    continue

                title = self._clean_text(title_tag.get_text())
                link = title_tag.get("href")
                snippet = self._clean_text(snippet_tag.get_text() if snippet_tag else "")

                if not link:
                    continue

                results.append({
                    "title": title[:200],
                    "url": link,
                    "snippet": snippet[:400],
                    "domain": self._extract_domain(link),
                })

                if len(results) >= max_results * 3:
                    break

            return results

        except Exception as e:
            print("DDG ERROR:", e)  # ðŸ”¥ debug visibility
            return []

    def search_web_api(self, query: str, max_results: int = 5, preferred_mode: str = "general") -> dict:
        query = str(query or "").strip()
        if not query:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": "Empty query.",
                "source_type": "brave_web",
            }

        key_error = self._check_api_key()
        brave_error = ""

        if not key_error:
            try:
                response = requests.get(
                    self.brave_web_endpoint,
                    headers=self._brave_headers(),
                    params={
                        "q": query,
                        "count": min(max(max_results * 3, 5), 20),
                    },
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
                payload = response.json() or {}

                raw_results = self._normalize_brave_web_results(payload)
                ranked_results = self._rank_search_results(query, raw_results, preferred_mode=preferred_mode)
                final_results = ranked_results[:max_results]

                if final_results:
                    return {
                        "ok": True,
                        "query": query,
                        "results": final_results,
                        "summary": self._summarize_search_results(query, final_results),
                        "source_type": "brave_web",
                        "debug": {
                            "preferred_mode": preferred_mode,
                            "raw_results_count": len(raw_results),
                            "ranked_results_count": len(final_results),
                        },
                    }

                brave_error = "Brave returned no ranked results."

            except requests.RequestException as e:
                brave_error = f"Brave web request failed: {e}"
            except Exception as e:
                brave_error = f"Brave web parsing failed: {e}"
        else:
            brave_error = key_error

        ddg_results = self._duckduckgo_search(query, max_results=max_results)

        if ddg_results:
            ranked_results = self._rank_search_results(query, ddg_results, preferred_mode=preferred_mode)
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "duckduckgo",
                "debug": {
                    "preferred_mode": preferred_mode,
                    "brave_error": brave_error,
                    "fallback_used": "duckduckgo",
                    "ranked_results_count": len(final_results),
                },
            }

        bing_results = self._bing_search(query, max_results=max_results)

        if bing_results:
            ranked_results = self._rank_search_results(query, bing_results, preferred_mode=preferred_mode)
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "bing",
                "debug": {
                    "preferred_mode": preferred_mode,
                    "brave_error": brave_error,
                    "fallback_used": "bing",
                    "ranked_results_count": len(final_results),
                },
            }

        rss_results = []
        if preferred_mode == "news" and self._looks_like_news_query(query):
            rss_results = self._news_rss_search(query, max_results=max_results)

        if rss_results:
            ranked_results = self._rank_search_results(query, rss_results, preferred_mode=preferred_mode)
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "rss_news",
                "debug": {
                    "preferred_mode": preferred_mode,
                    "brave_error": brave_error,
                    "fallback_used": "rss_news",
                    "ranked_results_count": len(final_results),
                },
            }

        fallback_results: List[dict] = []

        if preferred_mode == "weather":
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/search?q={requests.utils.quote(query)}",
                "snippet": "Current weather and forecast lookup.",
                "domain": "google.com",
                "score": 70.0,
            })
        elif preferred_mode == "business":
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/maps/search/{requests.utils.quote(query)}",
                "snippet": "Nearby locations, hours, directions, and contact details.",
                "domain": "google.com",
                "score": 70.0,
            })
        else:
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/search?q={requests.utils.quote(query)}",
                "snippet": "Live results available via search.",
                "domain": "google.com",
                "score": 50.0,
            })

        ranked_results = self._rank_search_results(query, fallback_results, preferred_mode=preferred_mode)
        final_results = ranked_results[:max_results]

        return {
            "ok": True,
            "query": query,
            "results": final_results,
            "summary": self._summarize_search_results(query, final_results),
            "source_type": "fallback_web",
            "debug": {
                "preferred_mode": preferred_mode,
                "brave_error": brave_error,
                "fallback_used": "google_link",
                "ranked_results_count": len(final_results),
            },
        }

    def _clean_source_name(self, item: dict) -> str:
        source = (
            item.get("source")
            or item.get("publisher")
            or item.get("site")
            or item.get("domain")
            or ""
        )

        source = str(source).strip()

        if not source:
            title = str(item.get("title") or "").strip()
            if " - " in title:
                source = title.rsplit(" - ", 1)[-1].strip()

        if source.lower() in {"news.google.com", "google news", "google"}:
            title = str(item.get("title") or "").strip()
            if " - " in title:
                source = title.rsplit(" - ", 1)[-1].strip()

        if source:
            source = source.strip()

            # normalize casing
            source = source.replace(".com", "")
            source = " ".join(word.capitalize() for word in source.split())

        return source or "Source"

    def _clean_result_title(self, item: dict) -> str:
        title = str(item.get("title") or "").strip()

        if " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()

        return title

    def _clean_result_snippet(self, item: dict, clean_title: str) -> str:
        snippet = str(
            item.get("snippet")
            or item.get("description")
            or item.get("summary")
            or ""
        ).strip()

        if not snippet:
            return ""

        snippet_clean = snippet.lower().strip()
        title_clean = clean_title.lower().strip()

        # exact duplicate
        if snippet_clean == title_clean:
            return ""

        # snippet starts with title (common RSS duplication)
        if snippet_clean.startswith(title_clean):
            extra = snippet[len(clean_title):].strip()
            # if only small leftover (like source name), drop it
            if len(extra) <= 50:
                return ""

        return snippet
    def _is_google_news_redirect(self, url: str) -> bool:
        url = str(url or "").strip().lower()
        return "news.google.com/rss/articles/" in url or "news.google.com/articles/" in url

        # -----------------------
        # FALLBACK CHAIN
        # -----------------------

        fallback_results: List[dict] = []

        # 1ï¸âƒ£ DuckDuckGo fallback
        ddg_results = self._duckduckgo_search(query, max_results=max_results)
        print("DDG RESULTS COUNT:", len(ddg_results))

        if ddg_results:
            ranked_results = self._rank_search_results(
                query,
                ddg_results,
                preferred_mode=preferred_mode
            )
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "duckduckgo",
                "debug": {
                    "preferred_mode": preferred_mode,
                    "brave_error": brave_error,
                    "fallback_used": "duckduckgo",
                    "ranked_results_count": len(final_results),
                },
            }

        # 2ï¸âƒ£ Bing fallback
        bing_results = self._bing_search(query, max_results=max_results)

        if bing_results:
            ranked_results = self._rank_search_results(
                query,
                bing_results,
                preferred_mode=preferred_mode
            )
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "bing",
                "debug": {
                    "preferred_mode": preferred_mode,
                    "brave_error": brave_error,
                    "fallback_used": "bing",
                    "ranked_results_count": len(final_results),
                },
            }

        # 3ï¸âƒ£ RSS news fallback â€” only for real news/latest queries
        rss_results = []
        if preferred_mode == "news" and self._looks_like_news_query(query):
            rss_results = self._news_rss_search(query, max_results=max_results)

        if rss_results:
            ranked_results = self._rank_search_results(
                query,
                rss_results,
                preferred_mode=preferred_mode
            )
            final_results = ranked_results[:max_results]

            return {
                "ok": True,
                "query": query,
                "results": final_results,
                "summary": self._summarize_search_results(query, final_results),
                "source_type": "rss_news",
                "debug": {
                    "fallback_used": "rss_news",
                },
            }

        # 4ï¸âƒ£ Final fallback
        if preferred_mode == "weather":
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/search?q={requests.utils.quote(query)}",
                "snippet": "Current weather and forecast lookup.",
                "domain": "google.com",
                "score": 70.0,
            })

        elif preferred_mode == "business":
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/maps/search/{requests.utils.quote(query)}",
                "snippet": "Nearby locations, hours, directions, and contact details.",
                "domain": "google.com",
                "score": 70.0,
            })

        else:
            fallback_results.append({
                "title": query.strip().title(),
                "url": f"https://www.google.com/search?q={requests.utils.quote(query)}",
                "snippet": "Live results available via search.",
                "domain": "google.com",
                "score": 50.0,
            })

        ranked_results = self._rank_search_results(
            query,
            fallback_results,
            preferred_mode=preferred_mode
        )
        final_results = ranked_results[:max_results]

        return {
            "ok": True,
            "query": query,
            "results": final_results,
            "summary": self._summarize_search_results(query, final_results),
            "source_type": "fallback_web",
            "debug": {
                "preferred_mode": preferred_mode,
                "brave_error": brave_error,
                "fallback_used": "google_link",
                "ranked_results_count": len(final_results),
            },
        }

    def _bing_search(self, query: str, max_results: int = 5) -> List[dict]:
        try:
            url = "https://www.bing.com/search"
            response = requests.get(
                url,
                params={"q": query},
                headers=self._headers(),
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results: List[dict] = []

            for item in soup.select("li.b_algo"):
                title_tag = item.find("h2")
                link_tag = title_tag.find("a") if title_tag else None
                snippet_tag = item.find("p")

                if not link_tag:
                    continue

                title = self._clean_text(link_tag.get_text(" ", strip=True))
                link = str(link_tag.get("href") or "").strip()
                snippet = self._clean_text(snippet_tag.get_text(" ", strip=True) if snippet_tag else "")

                if not title or not link:
                    continue

                results.append({
                    "title": title[:200],
                    "url": link,
                    "snippet": snippet[:400],
                    "domain": self._extract_domain(link),
                })

                if len(results) >= max_results * 3:
                    break

            return results

        except Exception as e:
            print("BING ERROR:", e)
            return []
   
    def search_news_api(self, query: str, max_results: int = 5) -> dict:
        key_error = self._check_api_key()
        if key_error:
            return {
                "ok": False,
                "query": query,
                "results": [],
                "summary": key_error,
                "source_type": "brave_news",
            }

        try:
            response = requests.get(
                self.brave_news_endpoint,
                headers=self._brave_headers(),
                params={
                    "q": query,
                    "count": min(max(max_results * 3, 5), 50),
                },
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json() or {}

            raw_results = self._normalize_brave_news_results(payload)
            ranked_results = self._rank_search_results(query, raw_results, preferred_mode="news")
            final_results = ranked_results[:max_results]

            if final_results:
                return {
                    "ok": True,
                    "query": query,
                    "results": final_results,
                    "summary": self._summarize_search_results(query, final_results),
                    "source_type": "brave_news",
                    "debug": {
                        "preferred_mode": "news",
                        "raw_results_count": len(raw_results),
                        "ranked_results_count": len(final_results),
                    },
                }

            fallback = self.search_web_api(query, max_results=max_results, preferred_mode="news")
            if isinstance(fallback, dict):
                fallback["debug"] = {
                    **(fallback.get("debug") or {}),
                    "news_fallback_used": True,
                    "news_fallback_reason": "empty_news_results",
                }
            return fallback

        except requests.RequestException as e:
            fallback = self.search_web_api(query, max_results=max_results, preferred_mode="news")
            if isinstance(fallback, dict):
                fallback["debug"] = {
                    **(fallback.get("debug") or {}),
                    "news_fallback_used": True,
                    "news_fallback_reason": str(e),
                }
            return fallback

        except Exception as e:
            fallback = self.search_web_api(query, max_results=max_results, preferred_mode="news")
            if isinstance(fallback, dict):
                fallback["debug"] = {
                    **(fallback.get("debug") or {}),
                    "news_fallback_used": True,
                    "news_fallback_reason": f"unexpected: {e}",
                }
            return fallback

    def _summarize_search_results(self, query: str, results: List[dict]) -> str:
        query = str(query or "").strip()
        results = results if isinstance(results, list) else []

        cleaned: List[dict] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or item.get("name") or "").strip()
            snippet = str(item.get("snippet") or item.get("content") or item.get("body") or "").strip()
            url = self._clean_source_url(
             str(item.get("url") or item.get("source_url") or "").strip()
        )
            domain = str(item.get("domain") or "").strip()

            if not (title or snippet or url):
                continue

            cleaned.append({
                "title": title,
                "snippet": snippet,
                "url": url,
                "domain": domain,
            })

        if not cleaned:
            return f'I couldnâ€™t find strong live results for "{query}".'

        cleaned = self._rank_search_results(query, cleaned)

        top = cleaned[0]

        title = self._clean_result_title(top)
        source = self._clean_source_name(top)
        snippet = self._clean_result_snippet(top, title)

        lines = []

        if title:
            lines.append(title)

        if snippet:
            lines.append(snippet)

        if source:
            lines.append(f"Source: {source}")

        lines.append("")
        lines.append("â€” Top sources â€”")

        for idx, item in enumerate(cleaned[:5], start=1):
            item_title = self._clean_result_title(item)
            item_source = self._clean_source_name(item)
            item_url = str(item.get("url") or "").strip()

            lines.append(f"{idx}. {item_source} â€” {item_title}")

            if item_url:
                lines.append(item_url)

        return "\n".join(lines).strip()

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

    def preview(self, url: str) -> dict:
        url = self.normalize_url(url)

        if not url:
            return {
                "ok": False,
                "error": "Missing url",
                "title": "Source preview",
                "preview": "",
                "url": "",
            }

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=self.timeout,
                allow_redirects=True,
            )

            response.raise_for_status()

            final_url = response.url or url
            html = response.text or ""

            title = self._extract_title(html)
            text = self._strip_html(html)

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            preview = "\n".join(lines[:24]).strip()

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
            domain = str(item.get("domain") or "").strip()
            score = item.get("score")

            block = f"{idx}. {title}" if title else f"{idx}."
            if snippet:
                block += f"\n   {snippet}"
            if domain:
                block += f"\n   Source: {domain}"
            if url:
                block += f"\n   {url}"
            if score is not None:
                try:
                    block += f"\n   Score: {float(score):.1f}"
                except Exception:
                    pass
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

    def _resolve_google_news_url(self, url: str) -> str:
        url = str(url or "").strip()

        if not url:
            return ""

        if "news.google.com/rss/articles/" not in url and "news.google.com/articles/" not in url:
            return url

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=self.timeout,
                allow_redirects=True,
            )

            final_url = str(response.url or "").strip()

            if final_url and "news.google.com" not in final_url:
                return final_url

            return url

        except Exception:
            return url

    def _news_rss_search(self, query: str, max_results: int = 5) -> list:
        try:
            url = "https://news.google.com/rss/search"
            response = requests.get(
                url,
                params={
                    "q": query,
                    "hl": "en-US",
                    "gl": "US",
                    "ceid": "US:en",
                },
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "xml")
            results = []

            for item in soup.find_all("item"):
                title = self._clean_text(item.title.text if item.title else "")
                link = self._clean_text(item.link.text if item.link else "")
                snippet_html = item.description.text if item.description else ""
                snippet = self._clean_text(
                    BeautifulSoup(snippet_html, "html.parser").get_text(" ", strip=True)
                )

                if not title or not link:
                    continue

                clean_title = title
                source = ""

                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    clean_title = parts[0].strip()
                    source = parts[1].strip()

                resolved_link = self._resolve_google_news_url(link)

                clean_url = self._resolve_google_news_url(resolved_link or link)

                results.append({
                    "title": clean_title[:200],
                    "url": clean_url,
                    "snippet": snippet[:400],
                    "domain": source or self._extract_domain(clean_url),
                })

                if len(results) >= max_results:
                    break

            return results

        except Exception as e:
            print("RSS ERROR:", e)
            return []


