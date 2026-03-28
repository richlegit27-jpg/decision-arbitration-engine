# notepad C:\Users\Owner\nova\services\web_service.py
from __future__ import annotations

import html
import json
import mimetypes
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None  # type: ignore


# =========================================================
# config
# =========================================================

MAX_URLS = 5
MAX_FETCH_BYTES = 1500000
MAX_RESPONSE_CHARS = 50000
MAX_PREVIEW_CHARS = 5000
MAX_SUMMARY_CHARS = 600
MAX_TEXT_BLOCK_CHARS = 12000
MAX_MEDIA_ITEMS = 12
MAX_MEDIA_PREVIEW_ITEMS = 6
REQUEST_TIMEOUT = 15

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 Nova/1.0"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "text/plain;q=0.8,application/json;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# =========================================================
# helpers
# =========================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _collapse_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value)).strip()


def _truncate(value: Any, limit: int) -> str:
    text = _clean_text(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "...(truncated)"


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _collapse_ws(value).lower()
    return text in {"1", "true", "yes", "on"}


def _unique_preserve(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _unique_dicts_by_key(items: List[Dict[str, Any]], key_name: str) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        item = _coerce_dict(item)
        key = _clean_text(item.get(key_name)).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _is_probable_url(value: str) -> bool:
    value = value.strip()
    return value.startswith("http://") or value.startswith("https://")


def _normalize_url(value: str) -> str:
    value = _clean_text(value).strip()
    if not value:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", value):
        return value
    if "." in value and " " not in value:
        return "https://" + value
    return value


def _absolutize_url(base_url: str, maybe_relative: str) -> str:
    candidate = _clean_text(maybe_relative).strip()
    if not candidate:
        return ""
    try:
        return urljoin(base_url, candidate)
    except Exception:
        return candidate


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _guess_media_kind(url: str, mime_type: str = "") -> str:
    url_lower = _clean_text(url).lower()
    mime_lower = _clean_text(mime_type).lower()

    if mime_lower.startswith("image/"):
        return "image"
    if mime_lower.startswith("video/"):
        return "video"
    if mime_lower.startswith("audio/"):
        return "audio"

    guessed, _ = mimetypes.guess_type(url_lower)
    guessed = guessed or ""
    if guessed.startswith("image/"):
        return "image"
    if guessed.startswith("video/"):
        return "video"
    if guessed.startswith("audio/"):
        return "audio"

    if re.search(r"\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)", url_lower):
        return "image"
    if re.search(r"\.(mp4|webm|mov|m4v|ogg|ogv)(\?|#|$)", url_lower):
        return "video"
    if re.search(r"\.(mp3|wav|m4a|aac|flac|oga)(\?|#|$)", url_lower):
        return "audio"

    return "file"


def _looks_like_html(content_type: str, text: str) -> bool:
    ctype = _collapse_ws(content_type).lower()
    if "html" in ctype or "xhtml" in ctype:
        return True
    probe = text[:1000].lower()
    return "<html" in probe or "<body" in probe or "<title" in probe or "<meta" in probe


def _strip_html_tags(html_text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<svg.*?>.*?</svg>", " ", text)
    text = re.sub(r"(?is)<iframe.*?>.*?</iframe>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)</div\s*>", "\n", text)
    text = re.sub(r"(?is)</h[1-6]\s*>", "\n\n", text)
    text = re.sub(r"(?is)<li\s*>", "• ", text)
    text = re.sub(r"(?is)<.*?>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_urls_from_text(text: str) -> List[str]:
    raw_text = _clean_text(text)
    found = re.findall(r"https?://[^\s<>()\"']+", raw_text, flags=re.IGNORECASE)

    normalized: List[str] = []
    for url in found:
        cleaned = url.strip().rstrip(".,);!?]}>")
        if _is_probable_url(cleaned):
            normalized.append(cleaned)

    return _unique_preserve(normalized)[:MAX_URLS]


def _extract_meta_content(soup: Any, *, name: str = "", prop: str = "") -> str:
    if not soup:
        return ""
    tag = None
    if name:
        tag = soup.find("meta", attrs={"name": re.compile(rf"^{re.escape(name)}$", re.I)})
    if not tag and prop:
        tag = soup.find("meta", attrs={"property": re.compile(rf"^{re.escape(prop)}$", re.I)})
    if tag and tag.get("content"):
        return _collapse_ws(tag.get("content"))
    return ""


def _extract_attr(tag: Any, attr: str) -> str:
    if tag and tag.get(attr):
        return _collapse_ws(tag.get(attr))
    return ""


def _collect_media_from_bs4(soup: Any, base_url: str) -> Dict[str, List[Dict[str, Any]]]:
    images: List[Dict[str, Any]] = []
    videos: List[Dict[str, Any]] = []
    audios: List[Dict[str, Any]] = []

    og_image = _extract_meta_content(soup, prop="og:image")
    if og_image:
        images.append(
            {
                "url": _absolutize_url(base_url, og_image),
                "kind": "image",
                "source": "og:image",
                "alt": "",
                "title": "",
                "mime_type": "",
                "poster": "",
            }
        )

    twitter_image = _extract_meta_content(soup, name="twitter:image")
    if twitter_image:
        images.append(
            {
                "url": _absolutize_url(base_url, twitter_image),
                "kind": "image",
                "source": "twitter:image",
                "alt": "",
                "title": "",
                "mime_type": "",
                "poster": "",
            }
        )

    og_video = _extract_meta_content(soup, prop="og:video")
    if og_video:
        videos.append(
            {
                "url": _absolutize_url(base_url, og_video),
                "kind": "video",
                "source": "og:video",
                "alt": "",
                "title": "",
                "mime_type": "",
                "poster": _absolutize_url(base_url, _extract_meta_content(soup, prop="og:image")),
            }
        )

    twitter_player = _extract_meta_content(soup, name="twitter:player")
    if twitter_player:
        videos.append(
            {
                "url": _absolutize_url(base_url, twitter_player),
                "kind": "video",
                "source": "twitter:player",
                "alt": "",
                "title": "",
                "mime_type": "",
                "poster": _absolutize_url(base_url, _extract_meta_content(soup, name="twitter:image")),
            }
        )

    for img in soup.find_all("img")[:MAX_MEDIA_ITEMS]:
        src = _extract_attr(img, "src") or _extract_attr(img, "data-src") or _extract_attr(img, "data-original")
        src = _absolutize_url(base_url, src)
        if not src:
            continue
        images.append(
            {
                "url": src,
                "kind": "image",
                "source": "img",
                "alt": _extract_attr(img, "alt"),
                "title": _extract_attr(img, "title"),
                "mime_type": "",
                "poster": "",
            }
        )

    for video in soup.find_all("video")[:MAX_MEDIA_ITEMS]:
        src = _extract_attr(video, "src")
        if not src:
            source_tag = video.find("source")
            src = _extract_attr(source_tag, "src")
        src = _absolutize_url(base_url, src)
        if not src:
            continue
        mime_type = ""
        source_tag = video.find("source")
        if source_tag:
            mime_type = _extract_attr(source_tag, "type")
        videos.append(
            {
                "url": src,
                "kind": "video",
                "source": "video",
                "alt": "",
                "title": _extract_attr(video, "title"),
                "mime_type": mime_type,
                "poster": _absolutize_url(base_url, _extract_attr(video, "poster")),
            }
        )

    for audio in soup.find_all("audio")[:MAX_MEDIA_ITEMS]:
        src = _extract_attr(audio, "src")
        if not src:
            source_tag = audio.find("source")
            src = _extract_attr(source_tag, "src")
        src = _absolutize_url(base_url, src)
        if not src:
            continue
        mime_type = ""
        source_tag = audio.find("source")
        if source_tag:
            mime_type = _extract_attr(source_tag, "type")
        audios.append(
            {
                "url": src,
                "kind": "audio",
                "source": "audio",
                "alt": "",
                "title": _extract_attr(audio, "title"),
                "mime_type": mime_type,
                "poster": "",
            }
        )

    return {
        "images": _unique_dicts_by_key(images, "url")[:MAX_MEDIA_ITEMS],
        "videos": _unique_dicts_by_key(videos, "url")[:MAX_MEDIA_ITEMS],
        "audios": _unique_dicts_by_key(audios, "url")[:MAX_MEDIA_ITEMS],
    }


def _extract_html_fields_with_bs4(html_text: str, base_url: str) -> Dict[str, Any]:
    result = {
        "title": "",
        "description": "",
        "content": "",
        "site_name": "",
        "author": "",
        "canonical_url": "",
        "images": [],
        "videos": [],
        "audios": [],
    }

    if not BeautifulSoup:
        return result

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return result

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        try:
            tag.decompose()
        except Exception:
            pass

    title = ""
    if soup.title and soup.title.string:
        title = _collapse_ws(soup.title.string)

    description = (
        _extract_meta_content(soup, name="description")
        or _extract_meta_content(soup, prop="og:description")
        or _extract_meta_content(soup, name="twitter:description")
    )

    site_name = _extract_meta_content(soup, prop="og:site_name")
    author = _extract_meta_content(soup, name="author")

    canonical_url = ""
    canonical = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
    if canonical and canonical.get("href"):
        canonical_url = _absolutize_url(base_url, canonical.get("href"))

    main_node = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("section")
        or soup.body
        or soup
    )

    content = _collapse_ws(main_node.get_text("\n", strip=True)) if main_node else ""
    content = _truncate(content, MAX_TEXT_BLOCK_CHARS)

    media = _collect_media_from_bs4(soup, canonical_url or base_url)

    result["title"] = title
    result["description"] = description
    result["content"] = content
    result["site_name"] = site_name
    result["author"] = author
    result["canonical_url"] = canonical_url
    result["images"] = media["images"]
    result["videos"] = media["videos"]
    result["audios"] = media["audios"]
    return result


def _extract_html_fields_fallback(html_text: str, base_url: str) -> Dict[str, Any]:
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text)
    title = _collapse_ws(title_match.group(1)) if title_match else ""

    description = ""
    meta_match = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html_text,
    )
    if meta_match:
        description = _collapse_ws(meta_match.group(1))

    content = _strip_html_tags(html_text)
    content = _truncate(content, MAX_TEXT_BLOCK_CHARS)

    image_urls = re.findall(r'(?is)<img[^>]+(?:src|data-src)=["\'](.*?)["\']', html_text)
    video_urls = re.findall(r'(?is)<video[^>]+src=["\'](.*?)["\']', html_text)
    source_video_urls = re.findall(r'(?is)<source[^>]+src=["\'](.*?)["\'][^>]*type=["\']video/', html_text)

    images = [
        {
            "url": _absolutize_url(base_url, url),
            "kind": "image",
            "source": "img",
            "alt": "",
            "title": "",
            "mime_type": "",
            "poster": "",
        }
        for url in image_urls[:MAX_MEDIA_ITEMS]
        if _absolutize_url(base_url, url)
    ]
    videos = [
        {
            "url": _absolutize_url(base_url, url),
            "kind": "video",
            "source": "video",
            "alt": "",
            "title": "",
            "mime_type": "",
            "poster": "",
        }
        for url in (video_urls + source_video_urls)[:MAX_MEDIA_ITEMS]
        if _absolutize_url(base_url, url)
    ]

    return {
        "title": title,
        "description": description,
        "content": content,
        "site_name": "",
        "author": "",
        "canonical_url": "",
        "images": _unique_dicts_by_key(images, "url")[:MAX_MEDIA_ITEMS],
        "videos": _unique_dicts_by_key(videos, "url")[:MAX_MEDIA_ITEMS],
        "audios": [],
    }


def _extract_html_fields(html_text: str, base_url: str) -> Dict[str, Any]:
    if BeautifulSoup:
        parsed = _extract_html_fields_with_bs4(html_text, base_url)
        if (
            parsed.get("title")
            or parsed.get("description")
            or parsed.get("content")
            or parsed.get("images")
            or parsed.get("videos")
        ):
            return parsed
    return _extract_html_fields_fallback(html_text, base_url)


def _build_media_summary(images: List[Dict[str, Any]], videos: List[Dict[str, Any]], audios: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    if images:
        parts.append(f"{len(images)} image(s)")
    if videos:
        parts.append(f"{len(videos)} video(s)")
    if audios:
        parts.append(f"{len(audios)} audio item(s)")
    return ", ".join(parts)


def _build_summary(
    title: str,
    description: str,
    content: str,
    domain: str,
    images: List[Dict[str, Any]],
    videos: List[Dict[str, Any]],
    audios: List[Dict[str, Any]],
) -> str:
    media_summary = _build_media_summary(images, videos, audios)

    if description and media_summary:
        return _truncate(f"{description} Media found: {media_summary}.", MAX_SUMMARY_CHARS)
    if description:
        return _truncate(description, MAX_SUMMARY_CHARS)

    if title and content and media_summary:
        return _truncate(f"{title} — {content} Media found: {media_summary}.", MAX_SUMMARY_CHARS)
    if title and content:
        return _truncate(f"{title} — {content}", MAX_SUMMARY_CHARS)

    if content and media_summary:
        return _truncate(f"{content} Media found: {media_summary}.", MAX_SUMMARY_CHARS)
    if content:
        return _truncate(content, MAX_SUMMARY_CHARS)

    if title and media_summary:
        return _truncate(f"Web page fetched from {domain}: {title}. Media found: {media_summary}.", MAX_SUMMARY_CHARS)
    if title:
        return _truncate(f"Web page fetched from {domain}: {title}", MAX_SUMMARY_CHARS)

    if media_summary:
        return _truncate(f"Web page fetched from {domain}. Media found: {media_summary}.", MAX_SUMMARY_CHARS)

    return _truncate(f"Web page fetched from {domain}.", MAX_SUMMARY_CHARS)


def _build_preview(
    title: str,
    description: str,
    content: str,
    images: List[Dict[str, Any]],
    videos: List[Dict[str, Any]],
    audios: List[Dict[str, Any]],
) -> str:
    parts: List[str] = []
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if images:
        parts.append("Images:")
        for item in images[:MAX_MEDIA_PREVIEW_ITEMS]:
            label = _clean_text(item.get("alt") or item.get("title") or item.get("url"))
            parts.append(f"- {label}")
    if videos:
        parts.append("Videos:")
        for item in videos[:MAX_MEDIA_PREVIEW_ITEMS]:
            label = _clean_text(item.get("title") or item.get("url"))
            parts.append(f"- {label}")
    if audios:
        parts.append("Audio:")
        for item in audios[:MAX_MEDIA_PREVIEW_ITEMS]:
            label = _clean_text(item.get("title") or item.get("url"))
            parts.append(f"- {label}")
    if content:
        parts.append("Content Preview:")
        parts.append(content)

    return _truncate("\n".join(parts).strip(), MAX_PREVIEW_CHARS)


def _build_prompt_text(
    url: str,
    title: str,
    description: str,
    content: str,
    images: List[Dict[str, Any]],
    videos: List[Dict[str, Any]],
    audios: List[Dict[str, Any]],
) -> str:
    parts = [f"Fetched URL: {url}"]

    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")

    if images:
        parts.append("Image URLs:")
        for item in images[:MAX_MEDIA_PREVIEW_ITEMS]:
            parts.append(f"- {_clean_text(item.get('url'))}")

    if videos:
        parts.append("Video URLs:")
        for item in videos[:MAX_MEDIA_PREVIEW_ITEMS]:
            parts.append(f"- {_clean_text(item.get('url'))}")

    if audios:
        parts.append("Audio URLs:")
        for item in audios[:MAX_MEDIA_PREVIEW_ITEMS]:
            parts.append(f"- {_clean_text(item.get('url'))}")

    if content:
        parts.append("Extracted content:")
        parts.append(content)

    return _truncate("\n".join(parts), MAX_TEXT_BLOCK_CHARS)


def _media_item_to_attachment(item: Dict[str, Any], page_url: str) -> Dict[str, Any]:
    item = _coerce_dict(item)
    url = _clean_text(item.get("url"))
    kind = _clean_text(item.get("kind")) or _guess_media_kind(url, _clean_text(item.get("mime_type")))
    name = urlparse(url).path.split("/")[-1] if url else ""
    if not name:
        name = f"{kind}_asset"

    return {
        "id": "",
        "name": name,
        "mime_type": _clean_text(item.get("mime_type")),
        "type": kind,
        "url": url,
        "source_url": page_url,
        "stored_path": "",
        "path": "",
        "size": 0,
        "meta": {
            "kind": kind,
            "source": _clean_text(item.get("source")),
            "alt": _clean_text(item.get("alt")),
            "title": _clean_text(item.get("title")),
            "poster": _clean_text(item.get("poster")),
            "page_url": page_url,
        },
    }


def _fallback_media_from_non_html(final_url: str, content_type: str) -> Dict[str, List[Dict[str, Any]]]:
    media_kind = _guess_media_kind(final_url, content_type)
    item = {
        "url": final_url,
        "kind": media_kind,
        "source": "direct",
        "alt": "",
        "title": "",
        "mime_type": content_type,
        "poster": "",
    }
    if media_kind == "image":
        return {"images": [item], "videos": [], "audios": []}
    if media_kind == "video":
        return {"images": [], "videos": [item], "audios": []}
    if media_kind == "audio":
        return {"images": [], "videos": [], "audios": [item]}
    return {"images": [], "videos": [], "audios": []}


# =========================================================
# network
# =========================================================

def _requests_available() -> bool:
    return requests is not None


def fetch_url_preview(url: str) -> Dict[str, Any]:
    normalized_url = _normalize_url(url)
    domain = _domain_from_url(normalized_url)

    base = {
        "url": normalized_url,
        "domain": domain,
        "title": "",
        "summary": "",
        "preview": "",
        "prompt_text": "",
        "status": "error",
        "status_code": None,
        "content_type": "",
        "images": [],
        "videos": [],
        "audios": [],
        "attachments": [],
        "meta": {},
    }

    if not normalized_url or not _is_probable_url(normalized_url):
        base["summary"] = "Invalid URL."
        base["meta"] = {"reason": "invalid_url"}
        return base

    if not _requests_available():
        base["summary"] = "Web fetching is unavailable because the requests package is not installed."
        base["meta"] = {"reason": "requests_unavailable"}
        return base

    try:
        response = requests.get(  # type: ignore[union-attr]
            normalized_url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )

        content_chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            content_chunks.append(chunk)
            total += len(chunk)
            if total >= MAX_FETCH_BYTES:
                break

        raw_bytes = b"".join(content_chunks)
        encoding = response.encoding or getattr(response, "apparent_encoding", None) or "utf-8"
        text = raw_bytes.decode(encoding, errors="ignore")
        text = _truncate(text, MAX_RESPONSE_CHARS)

        content_type = _clean_text(response.headers.get("Content-Type"))
        final_url = _clean_text(response.url) or normalized_url
        final_domain = _domain_from_url(final_url)

        base["url"] = final_url
        base["domain"] = final_domain
        base["status_code"] = response.status_code
        base["content_type"] = content_type

        if response.status_code >= 400:
            base["summary"] = f"Fetch failed with status {response.status_code}."
            base["meta"] = {
                "reason": "http_error",
                "status_code": response.status_code,
            }
            return base

        if _looks_like_html(content_type, text):
            extracted = _extract_html_fields(text, final_url)

            title = _truncate(extracted.get("title", ""), 300)
            description = _truncate(extracted.get("description", ""), 800)
            content = _truncate(extracted.get("content", ""), MAX_TEXT_BLOCK_CHARS)
            site_name = _truncate(extracted.get("site_name", ""), 200)
            author = _truncate(extracted.get("author", ""), 200)
            canonical_url = _clean_text(extracted.get("canonical_url")) or final_url

            images = _unique_dicts_by_key(_coerce_list(extracted.get("images")), "url")[:MAX_MEDIA_ITEMS]
            videos = _unique_dicts_by_key(_coerce_list(extracted.get("videos")), "url")[:MAX_MEDIA_ITEMS]
            audios = _unique_dicts_by_key(_coerce_list(extracted.get("audios")), "url")[:MAX_MEDIA_ITEMS]

            attachments = []
            for item in images + videos + audios:
                attachments.append(_media_item_to_attachment(item, canonical_url))

            base["title"] = title
            base["summary"] = _build_summary(title, description, content, final_domain, images, videos, audios)
            base["preview"] = _build_preview(title, description, content, images, videos, audios)
            base["prompt_text"] = _build_prompt_text(canonical_url, title, description, content, images, videos, audios)
            base["images"] = images
            base["videos"] = videos
            base["audios"] = audios
            base["attachments"] = attachments
            base["status"] = "ready"
            base["meta"] = {
                "mode": "html",
                "bytes_read": len(raw_bytes),
                "final_url": final_url,
                "canonical_url": canonical_url,
                "status_code": response.status_code,
                "site_name": site_name,
                "author": author,
                "image_count": len(images),
                "video_count": len(videos),
                "audio_count": len(audios),
            }
            return base

        plain_text = _collapse_ws(text)
        plain_text = _truncate(plain_text, MAX_TEXT_BLOCK_CHARS)

        media = _fallback_media_from_non_html(final_url, content_type)
        images = media["images"]
        videos = media["videos"]
        audios = media["audios"]

        attachments = []
        for item in images + videos + audios:
            attachments.append(_media_item_to_attachment(item, final_url))

        base["summary"] = _build_summary("", "", plain_text, final_domain, images, videos, audios)
        base["preview"] = _build_preview("", "", plain_text, images, videos, audios)
        base["prompt_text"] = _build_prompt_text(final_url, "", "", plain_text, images, videos, audios)
        base["images"] = images
        base["videos"] = videos
        base["audios"] = audios
        base["attachments"] = attachments
        base["status"] = "ready"
        base["meta"] = {
            "mode": "text_or_binary",
            "bytes_read": len(raw_bytes),
            "final_url": final_url,
            "status_code": response.status_code,
            "image_count": len(images),
            "video_count": len(videos),
            "audio_count": len(audios),
        }
        return base

    except Exception as exc:
        base["summary"] = _truncate(f"Fetch failed: {exc}", MAX_SUMMARY_CHARS)
        base["meta"] = {"reason": "exception", "error": _truncate(str(exc), 300)}
        return base


# =========================================================
# public workflow
# =========================================================

def analyze_web_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = _coerce_dict(payload)

    text = _clean_text(payload.get("text") or payload.get("content"))
    explicit_urls = [_normalize_url(_clean_text(x)) for x in _coerce_list(payload.get("urls"))]
    discovered_urls = extract_urls_from_text(text)

    urls = _unique_preserve(
        [url for url in explicit_urls + discovered_urls if _is_probable_url(url)]
    )[:MAX_URLS]

    results: List[Dict[str, Any]] = []
    for url in urls:
        results.append(fetch_url_preview(url))

    ready_results = [item for item in results if _clean_text(item.get("status")) == "ready"]
    failed_results = [item for item in results if _clean_text(item.get("status")) != "ready"]

    combined_prompt_parts: List[str] = []
    collected_attachments: List[Dict[str, Any]] = []
    collected_images: List[Dict[str, Any]] = []
    collected_videos: List[Dict[str, Any]] = []
    collected_audios: List[Dict[str, Any]] = []

    for item in ready_results:
        prompt_text = _clean_text(item.get("prompt_text"))
        if prompt_text:
            combined_prompt_parts.append(prompt_text)

        for attachment in _coerce_list(item.get("attachments")):
            collected_attachments.append(_coerce_dict(attachment))
        for media_item in _coerce_list(item.get("images")):
            collected_images.append(_coerce_dict(media_item))
        for media_item in _coerce_list(item.get("videos")):
            collected_videos.append(_coerce_dict(media_item))
        for media_item in _coerce_list(item.get("audios")):
            collected_audios.append(_coerce_dict(media_item))

    combined_prompt = _truncate("\n\n---\n\n".join(combined_prompt_parts), MAX_TEXT_BLOCK_CHARS)

    collected_attachments = _unique_dicts_by_key(collected_attachments, "url")[: MAX_MEDIA_ITEMS * MAX_URLS]
    collected_images = _unique_dicts_by_key(collected_images, "url")[: MAX_MEDIA_ITEMS * MAX_URLS]
    collected_videos = _unique_dicts_by_key(collected_videos, "url")[: MAX_MEDIA_ITEMS * MAX_URLS]
    collected_audios = _unique_dicts_by_key(collected_audios, "url")[: MAX_MEDIA_ITEMS * MAX_URLS]

    return {
        "ok": True,
        "urls": urls,
        "count": len(results),
        "ready_count": len(ready_results),
        "failed_count": len(failed_results),
        "results": results,
        "prompt_text": combined_prompt,
        "summary": _truncate(
            f"Resolved {len(ready_results)} web preview(s)"
            + (f"; {len(failed_results)} failed." if failed_results else "."),
            MAX_SUMMARY_CHARS,
        ),
        "attachments": collected_attachments,
        "images": collected_images,
        "videos": collected_videos,
        "audios": collected_audios,
        "meta": {
            "image_count": len(collected_images),
            "video_count": len(collected_videos),
            "audio_count": len(collected_audios),
            "attachment_count": len(collected_attachments),
        },
    }


def analyze_web_text(text: str) -> Dict[str, Any]:
    return analyze_web_request({"text": text})


def build_web_debug_payload(text: str) -> Dict[str, Any]:
    analyzed = analyze_web_text(text)

    previews = []
    for item in analyzed.get("results", []):
        item = _coerce_dict(item)
        previews.append(
            {
                "url": _clean_text(item.get("url")),
                "domain": _clean_text(item.get("domain")),
                "title": _clean_text(item.get("title")),
                "summary": _clean_text(item.get("summary")),
                "preview": _clean_text(item.get("preview")),
                "status": _clean_text(item.get("status")),
                "status_code": item.get("status_code"),
                "content_type": _clean_text(item.get("content_type")),
                "images": _coerce_list(item.get("images")),
                "videos": _coerce_list(item.get("videos")),
                "audios": _coerce_list(item.get("audios")),
                "attachments": _coerce_list(item.get("attachments")),
                "meta": _coerce_dict(item.get("meta")),
            }
        )

    return {
        "enabled": True,
        "input": _truncate(text, 2000),
        "urls": analyzed.get("urls", []),
        "summary": _clean_text(analyzed.get("summary")),
        "prompt_text": _clean_text(analyzed.get("prompt_text")),
        "previews": previews,
        "attachments": _coerce_list(analyzed.get("attachments")),
        "images": _coerce_list(analyzed.get("images")),
        "videos": _coerce_list(analyzed.get("videos")),
        "audios": _coerce_list(analyzed.get("audios")),
        "meta": {
            "count": analyzed.get("count", 0),
            "ready_count": analyzed.get("ready_count", 0),
            "failed_count": analyzed.get("failed_count", 0),
            "image_count": _coerce_dict(analyzed.get("meta")).get("image_count", 0),
            "video_count": _coerce_dict(analyzed.get("meta")).get("video_count", 0),
            "audio_count": _coerce_dict(analyzed.get("meta")).get("audio_count", 0),
            "attachment_count": _coerce_dict(analyzed.get("meta")).get("attachment_count", 0),
        },
    }


def merge_web_prompt_into_message_context(
    text: str,
    existing_context_blocks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    existing_context_blocks = existing_context_blocks or []
    web = analyze_web_text(text)
    merged_blocks = list(existing_context_blocks)

    prompt_text = _clean_text(web.get("prompt_text"))
    if prompt_text:
        merged_blocks.append(prompt_text)

    return {
        "web": web,
        "context_blocks": merged_blocks,
        "attachments": _coerce_list(web.get("attachments")),
        "images": _coerce_list(web.get("images")),
        "videos": _coerce_list(web.get("videos")),
        "audios": _coerce_list(web.get("audios")),
    }


def extract_first_url(text: str) -> str:
    urls = extract_urls_from_text(text)
    return urls[0] if urls else ""


def summarize_web_results(results: List[Dict[str, Any]]) -> str:
    summaries: List[str] = []
    for item in results[:MAX_URLS]:
        item = _coerce_dict(item)
        status = _clean_text(item.get("status"))
        url = _clean_text(item.get("url"))
        title = _clean_text(item.get("title"))
        summary = _clean_text(item.get("summary"))

        if status == "ready":
            line = f"{title or url}: {summary}".strip()
        else:
            line = f"{url or 'URL'}: {summary}".strip()

        summaries.append(_truncate(line, 300))

    return _truncate("\n".join(summaries), MAX_SUMMARY_CHARS)


def results_to_json(results: List[Dict[str, Any]]) -> str:
    safe_results = []
    for item in results[:MAX_URLS]:
        item = _coerce_dict(item)
        safe_results.append(
            {
                "url": _clean_text(item.get("url")),
                "domain": _clean_text(item.get("domain")),
                "title": _clean_text(item.get("title")),
                "summary": _clean_text(item.get("summary")),
                "status": _clean_text(item.get("status")),
                "status_code": item.get("status_code"),
                "content_type": _clean_text(item.get("content_type")),
                "images": _coerce_list(item.get("images")),
                "videos": _coerce_list(item.get("videos")),
                "audios": _coerce_list(item.get("audios")),
                "attachments": _coerce_list(item.get("attachments")),
                "meta": _coerce_dict(item.get("meta")),
            }
        )
    return json.dumps(safe_results, ensure_ascii=False, indent=2)