class DecisionService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def safe_str(self, value):
        return str(value or "").strip()

    def _decide_route(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:

        user_text = self.safe_str(user_text)

        lower_text = user_text.lower()

        short_chat = (
            "hello",
            "hi",
            "hey",
            "yo",
            "thanks",
            "thank you",
        )

        if lower_text.strip() in short_chat:
            return {
                "route": "general_chat",
                "mode": "chat",
                "intent": "conversation",
                "confidence": 0.95,
                "reasons": [
                    "short_chat",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        execution_triggers = (
            "next",
            "continue",
            "keep going",
            "run step",
            "run all",
            "execute",
            "advance",
            "status",
            "mission status",
            "execution status",
            "stop",
            "cancel",
        )

        if lower_text.strip() in execution_triggers:
            return {
                "route": "execution",
                "mode": "execution",
                "intent": "execution_control",
                "confidence": 1.0,
                "reasons": [
                    "execution_command",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        if lower_text.startswith(
            (
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            )
        ):
            return {
                "route": "execution",
                "mode": "auto_plan",
                "intent": "mission_creation",
                "confidence": 1.0,
                "reasons": [
                    "auto_plan_command",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        project_state_triggers = (
            "what's next",
            "whats next",
            "next move",
            "current blocker",
            "where are we",
            "where are we at",
            "what are we doing",
            "what is left",
        )

        if any(
            trigger in lower_text
            for trigger in project_state_triggers
        ):
            return {
                "route": "project_brain",
                "mode": "project_state",
                "intent": "mission_control",
                "confidence": 0.95,
                "reasons": [
                    "project_state_question",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        planning_triggers = (
            "plan",
            "planning",
            "roadmap",
            "strategy",
            "launch plan",
            "project plan",
            "create a plan",
            "make a plan",
            "build a plan",
            "implementation plan",
            "development plan",
            "technical plan",
            "architecture plan",
        )

        if any(
            trigger in lower_text
            for trigger in planning_triggers
        ):
            return {
                "route": "planner",
                "mode": "planning",
                "intent": "planning",
                "confidence": 0.95,
                "reasons": [
                    "explicit_planning_request",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        return {
            "route": "general_chat",
            "mode": "chat",
            "confidence": 0.6,
            "reasons": [
                "default_chat",
            ],
            "save_artifact": True,
            "save_memory": True,
            "use_memory": True,
            "prompt": user_text,
        }