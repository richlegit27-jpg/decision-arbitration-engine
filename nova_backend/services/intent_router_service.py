from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urlparse


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _safe_text(value).lower()


class IntentRouterService:
    URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        lowered = _lower(text)
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _has_attachments(self, attachments: Any) -> bool:
        return isinstance(attachments, list) and len(attachments) > 0

    def extract_first_url(self, text: str) -> str:
        raw = _safe_text(text)
        if not raw:
            return ""

        match = self.URL_RE.search(raw)
        if not match:
            return ""

        return match.group(1)

    def decide(self, user_text: str, attachments: Any = None) -> Dict[str, Any]:
        text = _safe_text(user_text)
        lowered = _lower(text)

        # =============================
        # EXECUTION FIX
        # =============================
        execution_triggers = [
            "run it",
            "run step",
            "run all",
            "execute",
            "retry",
        ]

        if any(trigger in lowered for trigger in execution_triggers):
            return {
                "mode": "execution",
                "route": "execution",
                "confidence": 0.95,
                "reasons": ["execution_trigger"],
                "url": "",
                "has_attachments": False,
                "use_memory": False,
                "memory_limit": 0,
                "save_memory": False,
                "save_artifact": False,
            }

        # =============================
        # DEFAULT
        # =============================
        return {
            "mode": "chat",
            "route": "chat",
            "confidence": 0.6,
            "reasons": ["default_chat"],
            "url": "",
            "has_attachments": False,
            "use_memory": True,
            "memory_limit": 3,
            "save_memory": True,
            "save_artifact": False,
        }

