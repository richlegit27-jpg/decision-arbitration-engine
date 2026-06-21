from __future__ import annotations

import re


URL_REGEX = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+)",
    re.IGNORECASE,
)


def extract_url(text: str) -> str:
    match = URL_REGEX.search(str(text or ""))
    if not match:
        return ""
    return match.group(0)


def clean_image_prompt(text: str) -> str:
    t = str(text or "").strip()

    if t.startswith("/image"):
        t = t[len("/image"):].strip()

    return t or "an interesting image"


def detect_tool(user_text: str) -> str:
    text = str(user_text or "").lower().strip()

    if text.startswith("/image"):
        return "image"

    if extract_url(text):
        return "web"

    return "chat"


def parse_tool_input(user_text: str) -> dict:
    """
    Returns clean inputs for tools
    """
    tool = detect_tool(user_text)

    if tool == "web":
        return {
            "tool": "web",
            "url": extract_url(user_text),
        }

    if tool == "image":
        return {
            "tool": "image",
            "prompt": clean_image_prompt(user_text),
        }

    return {
        "tool": "chat",
        "text": user_text,
    }


def should_store_memory(text: str) -> bool:
    t = str(text or "").lower()

    triggers = [
        "remember",
        "note that",
        "my name is",
        "i prefer",
        "i am",
        "i'm",
        "from now on",
    ]

    return any(x in t for x in triggers)

