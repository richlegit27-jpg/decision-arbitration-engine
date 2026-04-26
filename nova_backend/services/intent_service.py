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

        if self._has_any(text, [
            "bug", "fix", "error", "issue", "traceback", "exception",
            "broken", "not working", "doesn't work", "doesnt work",
            "isn't working", "isnt working", "crash", "fail",
            "debug", "problem", "500"
        ]):
            return self._result(self.INTENT_DEBUGGING, 0.99, ["debugging_signal"])

        if len(text.split()) <= 5 and self._has_any(text, ["fix", "bug", "error"]):
            return self._result(self.INTENT_DEBUGGING, 0.9, ["short_debug_command"])

        if self._has_any(text, [
            "code", "function", "class", "python", "javascript",
            "html", "css", "flask"
        ]):
            return self._result(self.INTENT_CODING, 0.85, ["coding_signal"])

        if self._has_any(text, [
            "plan", "roadmap", "steps", "strategy", "next move"
        ]):
            return self._result(self.INTENT_PLANNING, 0.85, ["planning_signal"])

        if self._has_any(text, [
            "write", "rewrite", "make this sound", "caption", "pitch"
        ]):
            return self._result(self.INTENT_WRITING, 0.8, ["writing_signal"])

        if "image" in route or "image" in mode:
            return self._result(self.INTENT_IMAGE, 0.9, ["route_image"])

        if "web" in route or "web" in mode:
            return self._result(self.INTENT_WEB, 0.9, ["route_web"])

        return self._result(self.INTENT_CHAT, 0.5, ["default_chat"])

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