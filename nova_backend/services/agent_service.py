from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class AgentService:
    """
    Nova routing + behavior override layer.

    This service decides:
    - mode
    - response style
    - whether memory should be used
    - whether memory should be extracted
    - whether output should be saved as an artifact
    """

    VALID_MODES = {
        "chat",
        "coding",
        "planning",
        "writing",
        "analysis",
        "web",
        "image",
        "recon",
    }

    DEFAULT_MODE = "chat"
    DEFAULT_RESPONSE_STYLE = "direct"

    DIRECT_STYLE_MARKERS = (
        "concise",
        "direct",
        "no fluff",
        "solution-first",
        "full file",
        "full files",
        "smff",
        "powershell me always",
    )

    CODING_MARKERS = (
        "code",
        "python",
        "flask",
        "javascript",
        "js",
        "css",
        "html",
        "bug",
        "fix",
        "debug",
        "error",
        "traceback",
        "stack trace",
        "route",
        "endpoint",
        "function",
        "class",
        "api",
        "backend",
        "frontend",
        "refactor",
        "wire",
        "implement",
        "patch",
        "file",
        "app.py",
        "nova",
    )

    PLANNING_MARKERS = (
        "plan",
        "roadmap",
        "next step",
        "next move",
        "sequence",
        "phases",
        "milestone",
        "priority",
        "what is next",
        "what should i do next",
    )

    WRITING_MARKERS = (
        "write",
        "rewrite",
        "draft",
        "edit",
        "email",
        "message",
        "post",
        "bio",
        "story",
        "book",
        "chapter",
        "title",
    )

    ANALYSIS_MARKERS = (
        "analyze",
        "analysis",
        "compare",
        "why",
        "root cause",
        "reason",
        "what happened",
        "investigate",
        "explain",
    )

    WEB_MARKERS = (
        "http://",
        "https://",
        "www.",
        "/web",
        "url",
        "website",
        "site",
        "link",
        "page",
        "browse",
        "fetch",
    )

    IMAGE_MARKERS = (
        "/image",
        "image",
        "picture",
        "photo",
        "screenshot",
        "generate an image",
        "edit this image",
        "analyze this image",
    )

    RECON_MARKERS = (
        "recon",
        "enumerate",
        "subdomain",
        "headers",
        "target",
        "surface",
        "fingerprint",
        "crawl",
    )

    SAVE_ARTIFACT_MARKERS = (
        "save this",
        "keep this",
        "artifact",
        "remember output",
    )

    MEMORY_OVERRIDE_PROJECT_MARKERS = (
        "nova",
        "project",
        "backend",
        "frontend",
        "app.py",
        "flask",
        "build",
        "working on",
        "checkpoint",
    )

    def decide(
        self,
        *,
        user_text: str,
        attachments: List[dict] | None = None,
        memory_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        attachments = attachments or []
        memory_context = memory_context or {}

        clean_user = self._clean_text(user_text)
        base_mode_scores = self._score_base_modes(clean_user, attachments)
        winning_mode, _winning_score = self._pick_mode(base_mode_scores)

        response_style = self.DEFAULT_RESPONSE_STYLE
        mode_override = ""
        override_reasons: List[str] = []
        style_reasons: List[str] = []

        memory_items = memory_context.get("items", [])
        preference_lock = bool(memory_context.get("preference_lock"))

        memory_mode_override, memory_mode_reasons = self._memory_mode_override(
            user_text=clean_user,
            memory_items=memory_items,
            base_mode=winning_mode,
        )
        if memory_mode_override and memory_mode_override in self.VALID_MODES:
            mode_override = memory_mode_override
            override_reasons.extend(memory_mode_reasons)

        response_style, style_reasons = self._memory_style_override(
            user_text=clean_user,
            memory_items=memory_items,
            default_style=response_style,
        )

        final_mode = mode_override or winning_mode
        mode_scores = self._apply_mode_override_to_scores(
            dict(base_mode_scores),
            final_mode=final_mode,
            reasons=override_reasons,
        )

        use_memory = self._should_use_memory(
            user_text=clean_user,
            memory_context=memory_context,
            final_mode=final_mode,
            preference_lock=preference_lock,
        )

        decision = {
            "mode": final_mode,
            "confidence": self._confidence_from_scores(mode_scores, final_mode),
            "winning_score": float(mode_scores.get(final_mode, 0.0)),
            "response_style": response_style,
            "use_memory": use_memory,
            "extract_memory": self._should_extract_memory(clean_user),
            "save_artifact": self._should_save_artifact(
                clean_user,
                final_mode,
                memory_context,
            ),
            "mode_scores": self._sorted_scores(mode_scores),
            "base_mode_scores": self._sorted_scores(base_mode_scores),
            "override": {
                "mode_override_applied": bool(mode_override),
                "mode_override": mode_override or "",
                "mode_override_reasons": override_reasons,
                "response_style_override": response_style,
                "response_style_reasons": style_reasons,
                "preference_lock": preference_lock,
            },
        }

        return decision

    def _score_base_modes(
        self,
        user_text: str,
        attachments: List[dict],
    ) -> Dict[str, float]:
        scores = {
            "chat": 1.0,
            "coding": 0.0,
            "planning": 0.0,
            "writing": 0.0,
            "analysis": 0.0,
            "web": 0.0,
            "image": 0.0,
            "recon": 0.0,
        }

        lowered = user_text.lower()

        scores["coding"] += self._marker_score(lowered, self.CODING_MARKERS, 1.8)
        scores["planning"] += self._marker_score(lowered, self.PLANNING_MARKERS, 1.8)
        scores["writing"] += self._marker_score(lowered, self.WRITING_MARKERS, 1.8)
        scores["analysis"] += self._marker_score(lowered, self.ANALYSIS_MARKERS, 1.5)
        scores["web"] += self._marker_score(lowered, self.WEB_MARKERS, 2.0)
        scores["image"] += self._marker_score(lowered, self.IMAGE_MARKERS, 2.0)
        scores["recon"] += self._marker_score(lowered, self.RECON_MARKERS, 1.8)

        if attachments:
            scores["analysis"] += 1.0
            scores["image"] += 0.5

        if self._looks_like_short_greeting(lowered):
            scores["chat"] += 2.0

        if "?" in lowered:
            scores["analysis"] += 0.4
            scores["chat"] += 0.3

        if any(token in lowered for token in ("fix", "wire", "smff", "full file", "full files")):
            scores["coding"] += 2.2

        if any(token in lowered for token in ("next", "what is next", "what's next")):
            scores["planning"] += 1.2

        return scores

    def _pick_mode(self, scores: Dict[str, float]) -> Tuple[str, float]:
        if not scores:
            return self.DEFAULT_MODE, 0.0

        winner = max(scores.items(), key=lambda kv: kv[1])
        mode = winner[0] if winner[0] in self.VALID_MODES else self.DEFAULT_MODE
        return mode, float(winner[1])

    def _memory_mode_override(
        self,
        *,
        user_text: str,
        memory_items: List[Dict[str, Any]],
        base_mode: str,
    ) -> Tuple[str, List[str]]:
        reasons: List[str] = []
        if not memory_items:
            return "", reasons

        text_pool = " ".join(
            self._clean_text(item.get("text") or item.get("content") or "")
            for item in memory_items
        ).strip()

        if not text_pool:
            return "", reasons

        if self._looks_like_coding_request(user_text) and self._looks_like_project_context(text_pool):
            reasons.append("coding request reinforced by project memory")
            return "coding", reasons

        if self._looks_like_planning_request(user_text) and self._looks_like_project_context(text_pool):
            reasons.append("planning request reinforced by project memory")
            return "planning", reasons

        if base_mode == "chat" and self._looks_like_project_context(text_pool):
            if any(word in user_text for word in ("fix", "build", "wire", "update", "edit", "file", "smff")):
                reasons.append("chat overridden to coding by project memory")
                return "coding", reasons

        return "", reasons

    def _memory_style_override(
        self,
        *,
        user_text: str,
        memory_items: List[Dict[str, Any]],
        default_style: str,
    ) -> Tuple[str, List[str]]:
        style = default_style
        reasons: List[str] = []

        for item in memory_items:
            kind = self._clean_text(item.get("kind"))
            text = self._clean_text(item.get("text") or item.get("content") or "")

            if kind not in {"preference", "style", "instruction"}:
                continue

            if any(marker in text for marker in self.DIRECT_STYLE_MARKERS):
                style = "direct"
                reasons.append(f"direct style from {kind} memory")
                break

        if any(term in user_text for term in ("smff", "full file", "full files")):
            style = "direct"
            reasons.append("direct style reinforced by current request")

        return style, reasons

    def _apply_mode_override_to_scores(
        self,
        scores: Dict[str, float],
        *,
        final_mode: str,
        reasons: List[str],
    ) -> Dict[str, float]:
        if final_mode not in scores:
            scores[final_mode] = 0.0

        if reasons:
            scores[final_mode] = max(float(scores.get(final_mode, 0.0)), 9.0)

        return scores

    def _should_use_memory(
        self,
        *,
        user_text: str,
        memory_context: Dict[str, Any],
        final_mode: str,
        preference_lock: bool,
    ) -> bool:
        if preference_lock:
            return True

        if memory_context.get("items"):
            return True

        if final_mode in {"coding", "planning", "writing", "analysis"}:
            return True

        if any(token in user_text for token in ("nova", "project", "continue", "next", "remember")):
            return True

        return False

    def _should_extract_memory(self, user_text: str) -> bool:
        triggers = (
            "remember that",
            "note that",
            "from now on",
            "i prefer",
            "my name is",
            "i am working on",
            "my project is",
            "the project is",
        )
        return any(trigger in user_text for trigger in triggers)

    def _should_save_artifact(
        self,
        user_text: str,
        final_mode: str,
        memory_context: Dict[str, Any] | None = None,
    ) -> bool:
        user_text = self._clean_text(user_text)
        memory_context = memory_context or {}

        if any(marker in user_text for marker in self.SAVE_ARTIFACT_MARKERS):
            return True

        memory_items = memory_context.get("items", [])
        project_context = any(
            "nova" in self._clean_text(item.get("text"))
            or "project" in self._clean_text(item.get("text"))
            for item in memory_items
        )

        if project_context and final_mode in {"coding", "planning", "analysis"}:
            return True

        if final_mode in {"web", "recon", "image"}:
            return True

        if final_mode == "planning":
            return True

        return False

    def _sorted_scores(self, scores: Dict[str, float]) -> List[Dict[str, float]]:
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [{"mode": mode, "score": round(float(score), 3)} for mode, score in ordered]

    def _confidence_from_scores(self, scores: Dict[str, float], winner_mode: str) -> float:
        if not scores or winner_mode not in scores:
            return 0.0

        ordered = sorted(scores.values(), reverse=True)
        top = float(ordered[0]) if ordered else 0.0
        second = float(ordered[1]) if len(ordered) > 1 else 0.0
        gap = max(top - second, 0.0)
        return round(min(0.55 + (gap / 10.0), 0.99), 3)

    def _marker_score(self, text: str, markers: Tuple[str, ...], weight: float) -> float:
        score = 0.0
        for marker in markers:
            if marker in text:
                score += weight
        return score

    def _looks_like_short_greeting(self, text: str) -> bool:
        return text.strip() in {"hi", "hello", "hey", "yo", "sup"}

    def _looks_like_coding_request(self, text: str) -> bool:
        coding_tokens = (
            "fix",
            "wire",
            "build",
            "edit",
            "update",
            "refactor",
            "debug",
            "error",
            "traceback",
            "full file",
            "smff",
            "app.py",
            "js",
            "python",
            "flask",
            "backend",
            "frontend",
        )
        return any(token in text for token in coding_tokens)

    def _looks_like_planning_request(self, text: str) -> bool:
        planning_tokens = (
            "next",
            "plan",
            "roadmap",
            "priority",
            "what is next",
            "what should i do next",
            "sequence",
            "phase",
            "milestone",
        )
        return any(token in text for token in planning_tokens)

    def _looks_like_project_context(self, text: str) -> bool:
        return any(token in text for token in self.MEMORY_OVERRIDE_PROJECT_MARKERS)

    def _clean_text(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text