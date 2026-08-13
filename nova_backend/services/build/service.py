from nova_backend.services.build.service import BuildService

class PlannerService:

    def __init__(self, chat_service=None):
        self.chat_service = chat_service

    def clean_goal(self, value: str) -> str:
        text = str(value or "").strip()

        prefixes = (
            "auto-plan ",
            "autoplan ",
            "plan ",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
            "upgrade ",
        )

        lowered = text.lower()

        for prefix in prefixes:
            if lowered.startswith(prefix):
                return text[len(prefix):].strip() or "generic"

        return text or "generic"

    def build_execution_steps(self, goal_text: str):
        safe_goal = self.clean_goal(goal_text)

        return [
            f"Design the approach for {safe_goal}.",
            f"Implement the solution for {safe_goal}.",
            f"Test and verify {safe_goal}.",
        ]

    def build_fallback_state(self, goal_text: str) -> dict:
        safe_goal = self.clean_goal(goal_text)

        steps = self.build_execution_steps(safe_goal)

        return {
            "status": "waiting",
            "goal": safe_goal,
            "original_user_text": str(goal_text or ""),
            "steps": steps,
            "current_index": 0,
            "current_step": steps[0] if steps else None,
            "current_step_title": steps[0] if steps else None,
            "history": [],
            "waiting": True,
            "complete": False,
            "error": None,
            "planner_service_used": True,
            "planner_fallback": True,
            "source": "planner_service",
        }