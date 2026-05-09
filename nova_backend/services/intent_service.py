# C:\Users\Owner\nova\nova_backend\services\intent_service.py

import re


class IntentService:
    INTENT_DEBUGGING = "debugging"
    INTENT_CODING = "coding"
    INTENT_PLANNING = "planning"
    INTENT_WRITING = "writing"
    INTENT_IMAGE = "image"
    INTENT_WEB = "web"
    INTENT_CHAT = "chat"

    def detect(self, user_text: str = "", route: str = "", mode: str = "") -> dict:
        text = str(user_text or "").strip().lower()
        route = str(route or "").strip().lower()
        mode = str(mode or "").strip().lower()

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
        ]

        if self._has_any(text, fresh_words):
            return self._result(self.INTENT_WEB, 0.98, ["fresh_web_trigger"])

        if "http://" in text or "https://" in text or "www." in text:
            return self._result(self.INTENT_WEB, 0.98, ["url_detected"])

        if self._has_any(text, [
            "open the first",
            "open first",
            "open 1",
            "first one",
            "open the top",
            "top one",
        ]):
            return self._result(self.INTENT_WEB, 0.96, ["followup_open_request"])

        if self._has_any(text, ["bug", "fix", "error", "traceback", "exception", "broken", "not working", "500"]):
            return self._result(self.INTENT_DEBUGGING, 0.95, ["debugging_signal"])

        if self._has_any(text, ["generate image", "create image", "draw", "/image"]):
            return self._result(self.INTENT_IMAGE, 0.95, ["image_signal"])

        if self._has_any(text, ["code", "function", "class", "python", "javascript", "html", "css", "smff"]):
            return self._result(self.INTENT_CODING, 0.9, ["coding_signal"])

        if self._has_any(text, ["plan", "next step", "roadmap", "strategy"]):
            return self._result(self.INTENT_PLANNING, 0.85, ["planning_signal"])

        if self._has_any(text, ["write", "rewrite", "draft", "email", "story"]):
            return self._result(self.INTENT_WRITING, 0.85, ["writing_signal"])

        return self._result(self.INTENT_CHAT, 0.55, ["default_chat"])

    def _has_any(self, text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)

    def _result(self, intent: str, confidence: float, reasons: list[str]) -> dict:
        return {
            "intent": intent,
            "confidence": confidence,
            "reasons": reasons,
        }

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