from __future__ import annotations


def looks_like_url(text: str) -> bool:
    t = str(text or "").lower().strip()
    return ("http://" in t) or ("https://" in t) or ("www." in t)


def normalize_url_input(text: str) -> str:
    t = str(text or "").strip()
    if not t:
        return ""

    if t.lower().startswith("/web"):
        t = t[4:].strip()

    parts = t.split()
    candidate = parts[0] if parts else ""

    if candidate.startswith("www."):
        return "https://" + candidate

    if not candidate.startswith("http://") and not candidate.startswith("https://"):
        if "." in candidate:
            return "https://" + candidate

    return candidate


def should_route_to_web(user_text: str) -> bool:
    t = str(user_text or "").strip().lower()
    if not t:
        return False
    if t.startswith("/web"):
        return True
    if looks_like_url(t):
        return True
    return False