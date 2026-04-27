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

        # 🔥 DEBUG / CODING
        if self._has_any(text, ["bug", "fix", "error", "traceback", "exception", "broken", "not working", "500"]):
            return self._result(self.INTENT_DEBUGGING, 0.95, ["debugging_signal"])

        # 🔥 CODING
        if self._has_any(text, ["code", "function", "class", "python", "javascript", "html", "css"]):
            return self._result(self.INTENT_CODING, 0.85, ["coding_signal"])

        # 🔥 PLANNING
        if self._has_any(text, ["plan", "steps", "roadmap", "what should i do", "next step"]):
            return self._result(self.INTENT_PLANNING, 0.8, ["planning_signal"])

        # 🔥 IMAGE
        if self._has_any(text, ["generate image", "create image", "draw", "art", "picture"]):
            return self._result(self.INTENT_IMAGE, 0.9, ["image_signal"])

        # 🔥 URL DETECTION (AUTO WEB)
        if "http://" in text or "https://" in text or "www." in text:
            return self._result(self.INTENT_WEB, 0.99, ["url_detected"])

        # 🔥 LIVE DATA / FACT QUERIES (STRONG MATCH)
        if (
            "weather" in text
            or "temperature" in text
            or "news" in text
            or "latest" in text
            or "today" in text
            or "now" in text
            or "stock" in text
            or "price" in text
            or "score" in text
            or "standings" in text
            or "stats" in text
            or "results" in text
            or "who won" in text
            or "record" in text
        ):
            return self._result(self.INTENT_WEB, 0.99, ["live_data_query"])

        # 🔥 SPORTS FORCE
        if any(team in text for team in ["lakers", "nba", "nfl", "mlb", "nhl"]):
            return self._result(self.INTENT_WEB, 0.99, ["sports_query"])

        # 🔥 DEFAULT CHAT
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