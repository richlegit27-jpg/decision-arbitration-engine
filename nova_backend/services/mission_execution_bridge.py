class MissionExecutionBridge:

    def __init__(self, execution_state_service):
        self.execution_state_service = execution_state_service

    def start_mission_execution(self, session_id, mission):
        execution = {
            "id": mission.get("id"),
            "mission_id": mission.get("id"),
            "goal": (
                mission.get("title")
                or mission.get("goal")
                or "Untitled mission"
            ),
            "status": "running",
            "task_type": "general",
            "context": {
                "source": "mission_execution_bridge",
                "mission": mission,
            },
            "execution_decision": {},
            "steps": mission.get("steps", []),
            "current_index": mission.get(
                "current_step",
                0,
            ),
            "current_step_index": mission.get(
                "current_step",
                0,
            ),
            "current_step": None,
            "history": [],
            "waiting": False,
            "complete": False,
            "error": None,
        }

        return self.execution_state_service.save_execution_state(
            session_id,
            execution,
        )