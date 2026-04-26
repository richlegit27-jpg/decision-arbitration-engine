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

        if self._has_any(text, ["bug", "error", "traceback", "exception", "broken", "not working", "500"]):
            return self._result(self.INTENT_DEBUGGING, 0.95, ["debugging_signal"])

        if self._has_any(text, ["code", "function", "class", "python", "javascript", "html", "css", "flask"]):
            return self._result(self.INTENT_CODING, 0.85, ["coding_signal"])

        if self._has_any(text, ["plan", "roadmap", "steps", "strategy", "next move"]):
            return self._result(self.INTENT_PLANNING, 0.85, ["planning_signal"])

        if self._has_any(text, ["write", "rewrite", "make this sound", "caption", "pitch"]):
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