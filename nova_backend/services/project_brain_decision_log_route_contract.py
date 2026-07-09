from __future__ import annotations

from typing import Any

from nova_backend.services.project_brain_decision_log import answer_recent_changes


DECISION_LOG_ROUTE_KEYWORDS = (
    "what changed recently",
    "what changed lately",
    "recent changes",
    "recent decisions",
    "decision log",
    "recent commits",
    "last commits",
    "latest commits",
    "what did we commit",
    "what did we lock recently",
    "what got locked recently",
    "locked upgrades",
    "operator timeline",
)

PROTECTED_DIRECT_RECALL_KEYWORDS = (
    "what are we working on",
    "what are we doing now",
    "current project state",
    "current blocker",
    "what is the blocker",
    "what should we do next",
)


def extract_user_text(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""

    for key in ("message", "question", "user_text", "text", "prompt"):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    return ""


def is_decision_log_question(user_text: str) -> bool:
    text = str(user_text or "").strip().lower()
    if not text:
        return False

    if any(needle in text for needle in PROTECTED_DIRECT_RECALL_KEYWORDS):
        return False

    return any(needle in text for needle in DECISION_LOG_ROUTE_KEYWORDS)


def build_decision_log_api_payload(limit: int = 8) -> dict[str, Any]:
    answer = answer_recent_changes(limit=limit)

    return {
        "ok": True,
        "text": answer,
        "assistant_message": {
            "role": "assistant",
            "text": answer,
            "content": answer,
            "attachments": [],
        },
        "debug": {
            "route": "project_brain_general_intelligence",
            "route_taken": "project_brain_general_intelligence",
            "intent": "decision_log",
            "decision_log_route_contract": True,
            "decision_log_route_service": True,
        },
    }


__all__ = [
    "DECISION_LOG_ROUTE_KEYWORDS",
    "PROTECTED_DIRECT_RECALL_KEYWORDS",
    "extract_user_text",
    "is_decision_log_question",
    "build_decision_log_api_payload",
]
