"""
Nova Mission Service v1

Purpose:
- Create and manage user goals as missions
- Separate user intent from execution mechanics
- Provide a stable contract for future:
    - execution engine
    - tool registry
    - calendar/email integrations
    - memory updates

This is intentionally simple.
Do not put tool execution here.
This only owns mission state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid

class MissionService:
    """
    Owns mission creation and state transitions.
    """

    VALID_STATUS = {
        "planning",
        "ready",
        "running",
        "paused",
        "blocked",
        "complete",
        "failed",
        "cancelled",
    }

    def __init__(
        self,
        state_path: Optional[str] = None,
    ):
        self.state_path = (
            Path(state_path)
            if state_path
            else Path(
                "C:/Users/Owner/nova/data/"
                "nova_missions.json"
            )
        )

        self._missions: Dict[
            str,
            Dict[str, Any],
        ] = {}

        self._load_missions()

    # ---------------------------------------------------------
    # Mission creation
    # ---------------------------------------------------------

    def create_mission(
        self,
        goal: str,
        steps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new mission.

        Example:

        create_mission(
            "Build customer notes system",
            [
                "Design data model",
                "Create backend",
                "Test"
            ]
        )
        """

        mission_id = "mission_" + uuid.uuid4().hex[:12]

        now = self._now()

        mission = {
            "id": mission_id,
            "goal": goal,
            "status": "planning",
            "created_at": now,
            "updated_at": now,

            "steps": [
                {
                    "index": index,
                    "title": step,
                    "status": "pending",
                }
                for index, step in enumerate(steps or [], start=1)
            ],

            "current_step": 0,

            "progress": 0,

            "metadata": metadata or {},

            "results": [],

            "available_tools": [],
        }

        if mission["steps"]:
            mission["status"] = "ready"

        self._missions[mission_id] = mission
        self._save_missions()

        return mission

    # ---------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------

    def get_mission(
        self,
        mission_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._missions.get(mission_id)


    def list_missions(self) -> List[Dict[str, Any]]:
        return list(self._missions.values())


    # ---------------------------------------------------------
    # Execution state
    # ---------------------------------------------------------

    def start_mission(
        self,
        mission_id: str,
    ) -> Optional[Dict[str, Any]]:

        mission = self.get_mission(mission_id)

        if not mission:
            return None

        mission["status"] = "running"

        self._touch(mission)
        self._save_missions()

        return mission



    def advance_step(
        self,
        mission_id: str,
        result: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:

        mission = self.get_mission(mission_id)

        if not mission:
            return None


        current = mission["current_step"]


        if current < len(mission["steps"]):

            mission["steps"][current]["status"] = "complete"


            if result:
                mission["results"].append(result)


            mission["current_step"] += 1



        completed = mission["current_step"] >= len(mission["steps"])


        if completed:

            mission["progress"] = 100
            mission["status"] = "complete"


            metadata = (
                mission.get(
                    "metadata",
                    {}
                )
            )


            if (
                metadata.get(
                    "mission_type"
                )
                ==
                "self_improvement"
            ):

                from nova_backend.services.nova_improvement_outcome_recorder import (
                    improvement_outcome_recorder,
                )


                improvement_outcome_recorder.record_outcome(
                    mission,
                    "completed",
                )

                from nova_backend.services.project_brain_decision_outcome_recorder import (
                    project_brain_decision_outcome_recorder,
                )

                project_brain_decision_outcome_recorder.record_outcome(
                    mission.get(
                        "metadata",
                        {},
                    ).get(
                        "project_brain_decision",
                        {},
                    ),
                    "completed",
                    evidence=mission.get(
                        "results",
                        [],
                    ),
                )

        else:

            mission["progress"] = int(
                (
                    mission["current_step"]
                    /
                    max(len(mission["steps"]), 1)
                )
                * 100
            )


        self._touch(mission)
        self._save_missions()

        return mission



    # ---------------------------------------------------------
    # Control
    # ---------------------------------------------------------

    def update_status(
        self,
        mission_id: str,
        status: str,
    ) -> Optional[Dict[str, Any]]:

        mission = self.get_mission(mission_id)

        if not mission:
            return None


        if status not in self.VALID_STATUS:
            raise ValueError(
                f"Invalid mission status: {status}"
            )


        previous_status = (
            mission.get(
                "status"
            )
        )

        mission["status"] = status

        self._touch(mission)


        if (
            status
            ==
            "failed"
            and
            previous_status
            !=
            "failed"
        ):

            metadata = (
                mission.get(
                    "metadata",
                    {}
                )
            )


            if (
                metadata.get(
                    "mission_type"
                )
                ==
                "self_improvement"
            ):

                from nova_backend.services.nova_improvement_outcome_recorder import (
                    improvement_outcome_recorder,
                )


                improvement_outcome_recorder.record_outcome(
                    mission,
                    "failed",
                )

                from nova_backend.services.project_brain_decision_outcome_recorder import (
                    project_brain_decision_outcome_recorder,
                )

                project_brain_decision_outcome_recorder.record_outcome(
                    mission.get(
                        "metadata",
                        {},
                    ).get(
                        "project_brain_decision",
                        {},
                    ),
                    "failed",
                    evidence=mission.get(
                        "results",
                        [],
                    ),
                )

        self._save_missions()

        return mission

    def add_tool(
        self,
        mission_id: str,
        tool_name: str,
    ) -> Optional[Dict[str, Any]]:

        mission = self.get_mission(mission_id)

        if not mission:
            return None


        if tool_name not in mission["available_tools"]:
            mission["available_tools"].append(tool_name)


        self._touch(mission)
        self._save_missions()

        return mission


    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _load_missions(self) -> None:
        try:
            if not self.state_path.exists():
                return

            data = json.loads(
                self.state_path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(data, dict):
                self._missions = data

        except Exception:
            self._missions = {}

    def _save_missions(self) -> None:
        self.state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.state_path.write_text(
            json.dumps(
                self._missions,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _touch(
        self,
        mission: Dict[str, Any],
    ):
        mission["updated_at"] = self._now()


    def _now(self):
        return datetime.now(
            timezone.utc
        ).isoformat()



mission_service = MissionService()