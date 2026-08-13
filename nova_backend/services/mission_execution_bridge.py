class MissionExecutionBridge:

    def __init__(self, execution_state_service):
        self.execution_state_service = execution_state_service

    def start_mission_execution(self, session_id, mission):
        execution = {
            "id": mission.get("id"),
            "goal": mission.get("title") or mission.get("goal"),
            "status": "running",
            "steps": mission.get("steps", []),
            "current_step_index": mission.get("current_step", 0),
            "complete": False,
        }

        return self.execution_state_service.save_execution_state(
            session_id,
            execution,
        )