# C:\Users\Owner\nova\nova_backend\services\intent_service.py

import re


class IntentService:
    INTENT_WORKING_STATE = "working_state"
    INTENT_ATTACHMENT = "attachment"
    INTENT_IMAGE = "image"
    INTENT_WEB = "web"
    INTENT_DEBUGGING = "debugging"
    INTENT_CODING = "coding"
    INTENT_PLANNING = "planning"
    INTENT_WRITING = "writing"
    INTENT_CHAT = "chat"

    ROUTE_GENERAL_CHAT = "general_chat"
    ROUTE_IMAGE_GENERATION = "image_generation"
    ROUTE_WEB_FETCH = "web_fetch"
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"
    ROUTE_PLANNING = "planning"
    ROUTE_MEMORY_RECALL = "memory_recall"
    ROUTE_WORKING_STATE_RECALL = "working_state_recall"
    ROUTE_PROJECT_BRAIN = "project_brain_general_intelligence"

    def detect(self, user_text: str = "", route: str = "", mode: str = "") -> dict:
        text = str(user_text or "").strip()
        lower = self._normalize(text)
        route = str(route or "").strip().lower()
        mode = str(mode or "").strip().lower()

        if not lower:
            return self._result(
                self.INTENT_CHAT,
                self.ROUTE_GENERAL_CHAT,
                "chat",
                0.5,
                ["empty_or_default_chat"],
            )

        # 1. Working-state recall must beat "current" web triggers.
        if lower in {
            "what file are we in",
            "what file are we working in",
            "what file are we working on",
            "current file",
            "what file",
            "which file",
            "active task",
            "current task",
            "what are we doing",
            "what are we working on",
            "what are we working on now",
        }:
            return self._result(
                self.INTENT_WORKING_STATE,
                self.ROUTE_MEMORY_RECALL,
                "working_state_recall",
                1.0,
                ["direct_working_state_recall", "project_state_memory_recall"],
                memory_limit=5,
            )

        # 2. Project Brain questions beat normal chat.
        if self._has_any(lower, [
            "actual blocker",
            "real blocker",
            "what's the blocker",
            "whats the blocker",
            "blocker on nova",
            "blocking nova",
            "where's the project",
            "where is the project",
            "current project",
            "what is locked",
            "what's locked",
            "what got locked",
            "what did we lock",
            "what did we lock recently",
            "what got locked recently",
        ]):
            return self._result(
                "project_brain_general_intelligence",
                "project_brain_general_intelligence",
                "project_brain_general_intelligence",
                0.95,
                ["project_brain_trigger"],
            )


        # 2. Attachment/file requests must beat web.
        attachment_markers = [
            "attached file",
            "attachment",
            "uploaded file",
            "summarize this file",
            "summarize the file",
            "read this file",
            "analyze this file",
            "what does this file",
            "this image",
            "attached image",
            "uploaded image",
            "look at this image",
            "describe this image",
        ]

        if self._has_any(lower, attachment_markers):
            return self._result(
                self.INTENT_ATTACHMENT,
                self.ROUTE_ATTACHMENT_ANALYSIS,
                "attachment_analysis",
                0.97,
                ["attachment_language"],
            )

        # 3. Explicit image generation.
        if self._is_image_generation(lower):
            return self._result(
                self.INTENT_IMAGE,
                self.ROUTE_IMAGE_GENERATION,
                "image_generation",
                0.96,
                ["explicit_image_generation"],
                save_artifact=True,
                save_memory=False,
                use_memory=False,
            )

        # 4. Fresh/current web.
        fresh_words = [
            "latest",
            "today",
            "current",
            "right now",
            "recent",
            "newest",
            "news",
            "update",
            "updates",
            "what happened",
            "score",
            "standings",
            "stock",
            "earnings",
            "price",
            "weather",
            "who won",
            "schedule",
            "near me",
        ]

        if "http://" in lower or "https://" in lower or "www." in lower:
            return self._result(
                self.INTENT_WEB,
                self.ROUTE_WEB_FETCH,
                "direct_url",
                0.98,
                ["url_detected"],
                save_artifact=True,
                save_memory=False,
            )

        if self._has_any(lower, fresh_words):
            return self._result(
                self.INTENT_WEB,
                self.ROUTE_WEB_FETCH,
                "search",
                0.94,
                ["fresh_web_trigger"],
                save_artifact=True,
                save_memory=False,
            )

        if self._has_any(lower, [
            "open the first",
            "open first",
            "open 1",
            "first one",
            "open the top",
            "top one",
        ]):
            return self._result(
                self.INTENT_WEB,
                self.ROUTE_WEB_FETCH,
                "followup_web_open",
                0.96,
                ["followup_open_request"],
                save_artifact=True,
                save_memory=False,
            )

        # 5. Debugging/coding/planning/writing.
        if self._has_any(lower, [
            "bug",
            "fix",
            "error",
            "traceback",
            "exception",
            "broken",
            "not working",
            "500",
            "syntaxerror",
            "indentationerror",
        ]):
            return self._result(
                self.INTENT_DEBUGGING,
                self.ROUTE_GENERAL_CHAT,
                "debugging",
                0.92,
                ["debugging_signal"],
            )

        if self._has_any(lower, [
            "code",
            "function",
            "class",
            "python",
            "javascript",
            "html",
            "css",
            "smff",
            "powershell",
            "flask",
        ]):
            return self._result(
                self.INTENT_CODING,
                self.ROUTE_GENERAL_CHAT,
                "coding",
                0.88,
                ["coding_signal"],
            )

        if self._has_any(lower, ["plan", "next step", "roadmap", "strategy"]):
            return self._result(
                self.INTENT_PLANNING,
                self.ROUTE_PLANNING,
                "planning",
                0.85,
                ["planning_signal"],
            )

        if self._has_any(lower, ["write", "rewrite", "draft", "email", "story"]):
            return self._result(
                self.INTENT_WRITING,
                self.ROUTE_GENERAL_CHAT,
                "writing",
                0.85,
                ["writing_signal"],
            )

        return self._result(
            self.INTENT_CHAT,
            self.ROUTE_GENERAL_CHAT,
            "chat",
            0.55,
            ["default_chat"],
        )

    def _is_image_generation(self, lower: str) -> bool:
        lower = self._normalize(lower)

        explicit_phrases = [
            "generate image",
            "create image",
            "make image",
            "draw image",
            "generate a picture",
            "create a picture",
            "make a picture",
            "draw a picture",
            "generate an image",
            "create an image",
            "make an image",
            "draw an image",
            "/image",
        ]

        if self._has_any(lower, explicit_phrases):
            return True

        if re.match(r"^(draw|generate|create|make)\s+(me\s+)?(a|an|the)?\s*.+", lower):
            visual_words = [
                "image",
                "picture",
                "photo",
                "logo",
                "poster",
                "robot",
                "character",
                "scene",
                "illustration",
                "3d",
                "cartoon",
                "anime",
                "portrait",
            ]

            return self._has_any(lower, visual_words)

        return False

    def _normalize(self, value: str) -> str:
        return " ".join(str(value or "").strip().lower().split())

    def _has_any(self, text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)

    def _result(
        self,
        intent: str,
        route: str,
        mode: str,
        confidence: float,
        reasons: list[str],
        **extra,
    ) -> dict:
        result = {
            "intent": intent,
            "route": route,
            "mode": mode,
            "confidence": confidence,
            "reasons": reasons,
        }

        result.update(extra)
        return result

    def build_plan(self, intent: str, user_text: str = "") -> list[str]:
        intent = str(intent or "").lower()

        if intent == "debugging":
            return [
                "Reproduce the bug",
                "Check error logs / traceback",
                "Identify where it breaks",
                "Fix the root cause",
                "Verify the fix",
            ]

        if intent == "coding":
            return [
                "Define the requirement",
                "Write the code",
                "Run and test",
                "Fix issues",
                "Finalize",
            ]

        if intent == "planning":
            return [
                "Define the goal",
                "Break into steps",
                "Order by priority",
                "Execute step-by-step",
            ]

        return []