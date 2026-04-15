from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urlparse


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _safe_text(value).lower()


class IntentRouterService:
    """
    Phase 1 router:
    - classify incoming requests early
    - keep it cheap and deterministic
    - do not depend on the model
    """

    URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)

    CODING_PATTERNS = [
        r"\bfix\b",
        r"\bbug\b",
        r"\berror\b",
        r"\btraceback\b",
        r"\bexception\b",
        r"\bcode\b",
        r"\bpython\b",
        r"\bflask\b",
        r"\bjavascript\b",
        r"\bjs\b",
        r"\bcss\b",
        r"\bhtml\b",
        r"\bapi\b",
        r"\broute\b",
        r"\bbackend\b",
        r"\bfrontend\b",
        r"\brefactor\b",
        r"\bsmff\b",
    ]

    PLANNING_PATTERNS = [
        r"\bplan\b",
        r"\broadmap\b",
        r"\bnext steps\b",
        r"\bphase\b",
        r"\bendgame\b",
        r"\barchitecture\b",
        r"\bstrategy\b",
        r"\bbuild order\b",
        r"\bhow should we\b",
    ]

    MEMORY_PATTERNS = [
        r"\bremember\b",
        r"\bmemory\b",
        r"\bwhat did i say\b",
        r"\bwhat do you know\b",
        r"\brecall\b",
        r"\bforget\b",
    ]

    RECON_PATTERNS = [
        r"\brecon\b",
        r"\banalyze this url\b",
        r"\bscan\b",
        r"\binvestigate\b",
        r"\btarget\b",
        r"\bheaders\b",
        r"\btech stack\b",
    ]

    ARTIFACT_PATTERNS = [
        r"\bartifact\b",
        r"\bsave this\b",
        r"\bopen artifact\b",
        r"\bshow artifact\b",
    ]

    SESSION_PATTERNS = [
        r"\brename session\b",
        r"\bdelete session\b",
        r"\bpin session\b",
        r"\bswitch session\b",
        r"\bnew chat\b",
    ]

    def normalize_url(self, url: str) -> str:
        text = _safe_text(url)
        if not text:
            return ""

        if text.startswith("www."):
            return f"https://{text}"

        parsed = urlparse(text)
        if parsed.scheme and parsed.netloc:
            return text

        if "." in text and " " not in text and not text.startswith("/"):
            return f"https://{text}"

        return text

    def extract_first_url(self, text: str) -> str:
        raw = _safe_text(text)
        if not raw:
            return ""

        match = self.URL_RE.search(raw)
        if not match:
            return ""

        return self.normalize_url(match.group(1))

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        lowered = _lower(text)
        return any(re.search(pattern, lowered) for pattern in patterns)

    def _has_attachments(self, attachments: Any) -> bool:
        return isinstance(attachments, list) and len(attachments) > 0

    def decide(self, user_text: str, attachments: Any = None) -> Dict[str, Any]:
        text = _safe_text(user_text)
        lowered = _lower(text)
        attachments_present = self._has_attachments(attachments)
        found_url = self.extract_first_url(text)

        mode = "chat"
        route = "chat"
        reasons: List[str] = []
        confidence = 0.55

        if attachments_present:
            mode = "analysis"
            route = "chat"
            reasons.append("attachments_present")
            confidence = 0.72

        if found_url:
            mode = "web"
            route = "web"
            reasons.append("url_detected")
            confidence = 0.95

        if self._matches_any(lowered, self.RECON_PATTERNS):
            mode = "recon"
            route = "recon"
            reasons.append("recon_pattern")
            confidence = 0.92

        elif self._matches_any(lowered, self.CODING_PATTERNS):
            mode = "coding"
            route = "chat"
            reasons.append("coding_pattern")
            confidence = max(confidence, 0.84)

        elif self._matches_any(lowered, self.PLANNING_PATTERNS):
            mode = "planning"
            route = "chat"
            reasons.append("planning_pattern")
            confidence = max(confidence, 0.82)

        elif self._matches_any(lowered, self.MEMORY_PATTERNS):
            mode = "memory"
            route = "chat"
            reasons.append("memory_pattern")
            confidence = max(confidence, 0.86)

        elif self._matches_any(lowered, self.ARTIFACT_PATTERNS):
            mode = "artifact"
            route = "chat"
            reasons.append("artifact_pattern")
            confidence = max(confidence, 0.74)

        elif self._matches_any(lowered, self.SESSION_PATTERNS):
            mode = "session_action"
            route = "chat"
            reasons.append("session_pattern")
            confidence = max(confidence, 0.75)

        use_memory = mode in {"chat", "coding", "planning", "memory", "artifact", "analysis"}
        save_memory = mode in {"chat", "planning", "memory"}
        save_artifact = mode in {"web", "recon", "analysis", "artifact"}

        memory_limit = 3
        if mode == "planning":
            memory_limit = 5
        elif mode == "coding":
            memory_limit = 4
        elif mode == "memory":
            memory_limit = 6

        return {
            "mode": mode,
            "route": route,
            "confidence": round(float(confidence), 3),
            "reasons": reasons,
            "url": found_url,
            "has_attachments": attachments_present,
            "use_memory": use_memory,
            "memory_limit": memory_limit,
            "save_memory": save_memory,
            "save_artifact": save_artifact,
        }