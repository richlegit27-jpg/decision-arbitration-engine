"""
Nova interpretation service.

This is the pre-router brain:
raw messy user input -> normalized intent -> route hint -> rewritten query/action.

It is deliberately deterministic and cheap. It does not call an LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class Interpretation:
    raw_text: str
    normalized_text: str
    intent: str
    confidence: float
    route_hint: str
    rewritten_text: str
    reason: str
    flags: dict[str, Any]


_WORD_RE = re.compile(r"[a-z0-9']+")


def normalize_user_text(text: str | None) -> str:
    raw = str(text or "").strip().lower()
    words = _WORD_RE.findall(raw)
    return " ".join(words)


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _topic_before_news(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\b(today|latest|current|recent|breaking|updates?|headlines?)\b", " ", text)
    text = re.sub(r"\b(news|newz)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _rewrite_news_query(text: str) -> str:
    topic = _topic_before_news(text)

    if not topic:
        return "latest top news today"

    return f"latest {topic} news today"


def interpret_user_text(
    user_text: str | None,
    *,
    has_active_execution: bool = False,
    has_attachments: bool = False,
    has_active_session: bool = True,
) -> dict[str, Any]:
    raw = str(user_text or "")
    text = normalize_user_text(raw)

    flags: dict[str, Any] = {
        "has_active_execution": bool(has_active_execution),
        "has_attachments": bool(has_attachments),
        "has_active_session": bool(has_active_session),
    }

    if not text:
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="empty",
            confidence=1.0,
            route_hint="empty",
            rewritten_text="",
            reason="empty input",
            flags=flags,
        )
        return asdict(result)

    # Short acknowledgements must be contextual.
    if text in {"k", "ok", "okay", "kk", "yup", "yeah", "yes", "sure"}:
        if has_active_execution:
            result = Interpretation(
                raw_text=raw,
                normalized_text=text,
                intent="execution_continue",
                confidence=0.95,
                route_hint="execution",
                rewritten_text="continue",
                reason="short acknowledgement while execution is active",
                flags=flags,
            )
        else:
            result = Interpretation(
                raw_text=raw,
                normalized_text=text,
                intent="acknowledgement",
                confidence=0.75,
                route_hint="chat",
                rewritten_text=raw.strip(),
                reason="short acknowledgement without active execution",
                flags=flags,
            )
        return asdict(result)

    # Web/news/current intent. This is broad on purpose.
    news_phrases = [
        "news",
        "latest",
        "breaking",
        "headlines",
        "current events",
        "whats going on",
        "what's going on",
        "what is going on",
        "anything new",
        "updates on",
        "update on",
        "latest on",
        "today",
    ]

    if _has_any(text, news_phrases):
        rewritten = _rewrite_news_query(text)
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="fresh_web_news",
            confidence=0.9,
            route_hint="web",
            rewritten_text=rewritten,
            reason="fresh/current/news phrasing detected",
            flags={**flags, "fresh": True},
        )
        return asdict(result)

    # Memory / recall.
    memory_phrases = [
        "remember",
        "recall",
        "what did i say",
        "what did we talk about",
        "what were we talking about",
        "last time",
        "previous",
        "memory",
        "do you remember",
    ]

    if _has_any(text, memory_phrases):
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="memory_recall",
            confidence=0.88,
            route_hint="memory",
            rewritten_text=raw.strip(),
            reason="memory or prior-context phrasing detected",
            flags=flags,
        )
        return asdict(result)

    # Attachments/files.
    attachment_phrases = [
        "attachment",
        "attached",
        "upload",
        "file",
        "pdf",
        "docx",
        "image",
        "picture",
        "screenshot",
        "analyze this",
        "what's in this",
        "whats in this",
    ]

    if has_attachments or _has_any(text, attachment_phrases):
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="attachment_analysis",
            confidence=0.86,
            route_hint="attachments",
            rewritten_text=raw.strip(),
            reason="attachment/file phrasing or active attachments detected",
            flags=flags,
        )
        return asdict(result)

    # Execution / planner / coding workflow.
    execution_phrases = [
        "run",
        "next",
        "continue",
        "execute",
        "run step",
        "run all",
        "auto plan",
        "autoplan",
        "build",
        "implement",
        "fix",
        "repair",
        "patch",
        "test",
        "commit",
        "tag",
        "debug",
    ]

    if _has_any(text, execution_phrases):
        route = "execution" if has_active_execution or text in {"next", "continue", "run", "run step", "run it"} else "planner"
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="execution_or_planning",
            confidence=0.84,
            route_hint=route,
            rewritten_text=raw.strip(),
            reason="execution/planning/build/debug phrasing detected",
            flags=flags,
        )
        return asdict(result)

    # UI/session/project debugging.
    ui_phrases = [
        "session",
        "button",
        "panel",
        "desktop",
        "mobile",
        "login",
        "memory stuck",
        "loading",
        "source card",
        "cards",
        "refresh",
        "browser",
        "console",
    ]

    if _has_any(text, ui_phrases):
        result = Interpretation(
            raw_text=raw,
            normalized_text=text,
            intent="project_ui_debug",
            confidence=0.8,
            route_hint="project_debug",
            rewritten_text=raw.strip(),
            reason="Nova UI/session/debug phrasing detected",
            flags=flags,
        )
        return asdict(result)

    result = Interpretation(
        raw_text=raw,
        normalized_text=text,
        intent="general_chat",
        confidence=0.55,
        route_hint="chat",
        rewritten_text=raw.strip(),
        reason="no stronger specialized intent detected",
        flags=flags,
    )
    return asdict(result)


__all__ = ["interpret_user_text", "normalize_user_text", "Interpretation"]
