# C:\Users\Owner\nova\nova_backend\services\planner_service.py
# NOVA_MINIMAL_PLANNER_SERVICE_20260609
#
# Minimal PlannerService restore.
# Purpose:
# - Give Nova a stable planner module again.
# - Support simple auto-plan smoke tests.
# - Restore known mission module names:
#   notes_cleanup, csv_cleaner, backup_script, file_organizer, quiz, generic.

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from nova_backend.utils.file_utils import (
    load_json_file,
    save_json_file,
)
from nova_backend.services.mission_service import mission_service
from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)

class PlannerService:

    def __init__(self, chat_service=None):
        self.chat_service = chat_service

        self.plans_path = Path(
            "runtime/planner_plans.json"
        )

        self.plans: Dict[str, Dict[str, Any]] = (
            self._load_plans()
        )
    def _load_plans(self) -> Dict[str, Dict[str, Any]]:
        data = load_json_file(
            self.plans_path,
            default={},
        )

        if isinstance(data, dict):
            return data

        return {}

    def _save_plans(self) -> None:
        save_json_file(
            self.plans_path,
            self.plans,
        )

    def create_mission(self, mission_name: str) -> Dict[str, Any]:
        """
        Convert a planner output into a Nova Mission.
        Keeps planning and execution separated.
        """

        plan = self.build_plan(mission_name)

        steps = [
            (
                item.get("step", "").strip()
                if isinstance(item, dict)
                else str(item)
            )
            for item in plan.get("steps", [])
        ]

        mission = mission_service.create_mission(
            goal=plan.get(
                "goal",
                mission_name,
            ),
            steps=steps,
            metadata={
                "source": "planner_service",
                "planner_status": plan.get(
                    "status",
                ),
                "project_brain_decision": plan.get(
                    "project_brain_decision",
                    {},
                ),
            },
        )
        

        return mission

    def _generate_steps(
        self,
        goal: str,
    ) -> List[Dict[str, Any]]:

        text = str(goal or "").lower()

        if any(
            word in text
            for word in (
                "python",
                "code",
                "project",
                "app",
                "software",
                "bug",
                "fix",
                "feature",
            )
        ):
            return [
                {
                    "step": "analyze",
                    "status": "pending",
                    "description": (
                        f"Analyze the current state and requirements for {goal}."
                    ),
                },
                {
                    "step": "implement",
                    "status": "pending",
                    "description": (
                        f"Make the required changes for {goal}."
                    ),
                },
                {
                    "step": "verify",
                    "status": "pending",
                    "description": (
                        f"Verify the result and check for problems with {goal}."
                    ),
                },
            ]

        if any(
            word in text
            for word in (
                "write",
                "email",
                "document",
                "article",
            )
        ):
            return [
                {
                    "step": "understand",
                    "status": "pending",
                    "description": (
                        f"Understand the purpose and requirements for {goal}."
                    ),
                },
                {
                    "step": "draft",
                    "status": "pending",
                    "description": (
                        f"Create a first version of {goal}."
                    ),
                },
                {
                    "step": "review",
                    "status": "pending",
                    "description": (
                        f"Review and improve the final result for {goal}."
                    ),
                },
            ]

        return [
            {
                "step": "plan",
                "status": "pending",
                "description": (
                    f"Plan the best approach for {goal}."
                ),
            },
            {
                "step": "execute",
                "status": "pending",
                "description": (
                    f"Complete the main work for {goal}."
                ),
            },
            {
                "step": "review",
                "status": "pending",
                "description": (
                    f"Review the completed work for {goal}."
                ),
            },
        ]

    def build_plan(self, mission_name: str) -> Dict[str, Any]:
        safe_mission = str(mission_name or "generic").strip() or "generic"

        task_type = "general"

        mission_lower = safe_mission.lower()

        if any(
            word in mission_lower
            for word in (
                "python",
                "code",
                "project",
                "app",
                "software",
                "bug",
                "fix",
            )
        ):
            task_type = "coding"

        elif any(
            word in mission_lower
            for word in (
                "write",
                "email",
                "document",
                "report",
                "essay",
            )
        ):
            task_type = "writing"

        elif any(
            word in mission_lower
            for word in (
                "research",
                "learn",
                "study",
                "analyze",
            )
        ):
            task_type = "research"


        if task_type == "coding":
            steps = [
                {
                    "step": "understand",
                    "status": "pending",
                    "description": (
                        f"Understand the current structure and goal "
                        f"for {safe_mission}."
                    ),
                },
                {
                    "step": "analyze",
                    "status": "pending",
                    "description": (
                        "Analyze the current files, problems, "
                        "and possible improvements."
                    ),
                },
                {
                    "step": "implement",
                    "status": "pending",
                    "description": (
                        "Apply the safest useful changes "
                        "without breaking working systems."
                    ),
                },
                {
                    "step": "verify",
                    "status": "pending",
                    "description": (
                        "Verify the result and summarize "
                        "the next move."
                    ),
                },
            ]

        elif task_type == "writing":
            steps = [
                {
                    "step": "understand",
                    "status": "pending",
                    "description": "Understand the purpose and audience.",
                },
                {
                    "step": "draft",
                    "status": "pending",
                    "description": "Create the first draft.",
                },
                {
                    "step": "review",
                    "status": "pending",
                    "description": "Review and improve the writing.",
                },
            ]

        else:
            steps = [
                {
                    "step": "understand",
                    "status": "pending",
                    "description": (
                        f"Understand the goal: {safe_mission}."
                    ),
                },
                {
                    "step": "plan",
                    "status": "pending",
                    "description": "Create the best approach.",
                },
                {
                    "step": "complete",
                    "status": "pending",
                    "description": "Complete the task and review the result.",
                },
            ]

        project_brain_decision = (
            build_operator_plan_dict(
                user_text=safe_mission,
            )
        )

        plan = {
            "mission": safe_mission,
            "goal": safe_mission,
            "task_type": task_type,
            "steps": steps,
            "current_index": 0,
            "status": "pending",
            "created_at": time.time(),
            "project_brain_decision": project_brain_decision,
        }

        self.plans[safe_mission] = plan
        self._save_plans()

        return plan

    def build_execution_steps(self, mission_name: str) -> List[str]:
        plan = self.build_plan(mission_name)

        return [
            str(item.get("description") or item.get("step") or "").strip()
            for item in plan.get("steps", [])
            if str(item.get("description") or item.get("step") or "").strip()
        ]

    def advance_step(self, mission_name: str) -> Dict[str, Any]:
        safe_mission = str(mission_name or "generic").strip() or "generic"
        plan = self.plans.get(safe_mission)

        if not plan:
            plan = self.build_plan(safe_mission)

        current_index = int(plan.get("current_index") or 0)
        steps = plan.get("steps") or []

        if current_index >= len(steps):
            plan["status"] = "complete"
            return plan

        steps[current_index]["status"] = "complete"
        current_index += 1

        plan["current_index"] = current_index
        plan["status"] = "complete" if current_index >= len(steps) else "running"

        self._save_plans()

        return plan

    def notes_cleanup(self) -> str:
        return "notes_cleanup done"

    def csv_cleaner(self) -> str:
        return "csv_cleaner done"

    def backup_script(self) -> str:
        return "backup_script done"

    def file_organizer(self) -> str:
        return "file_organizer done"

    def quiz(self) -> str:
        return "quiz done"

    def generic(self) -> str:
        return "generic done"

    def list_modules(self) -> List[str]:
        return [
            "notes_cleanup",
            "csv_cleaner",
            "backup_script",
            "file_organizer",
            "quiz",
            "generic",
        ]


planner_service = PlannerService()


