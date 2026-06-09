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
from typing import Any, Dict, List


class PlannerService:
    def __init__(self) -> None:
        self.plans: Dict[str, Dict[str, Any]] = {}

    def build_plan(self, mission_name: str) -> Dict[str, Any]:
        safe_mission = str(mission_name or "generic").strip() or "generic"

        steps = [
            {
                "step": "design",
                "status": "pending",
                "description": f"Design the approach for {safe_mission}.",
            },
            {
                "step": "implement",
                "status": "pending",
                "description": f"Implement the solution for {safe_mission}.",
            },
            {
                "step": "test",
                "status": "pending",
                "description": f"Test and verify {safe_mission}.",
            },
        ]

        plan = {
            "mission": safe_mission,
            "goal": safe_mission,
            "steps": steps,
            "current_index": 0,
            "status": "pending",
            "created_at": time.time(),
        }

        self.plans[safe_mission] = plan
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
