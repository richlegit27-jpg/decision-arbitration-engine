from nova_backend.services.project_execution_handler import ProjectExecutionHandler


class WaitingExecutionStepService:
    def execute_step_logic(self, session_id, step):
        updated_step = dict(step)
        updated_step["status"] = "waiting"
        updated_step["completion_status"] = "needs_input"
        updated_step["result"] = "Please provide more detail on the relevant code or process to verify completion."
        return updated_step


def main():
    handler = ProjectExecutionHandler(
        execution_step_service=WaitingExecutionStepService()
    )

    execution_state = {
        "status": "ready",
        "goal": "Test waiting state handling",
        "task_type": "general",
        "steps": [
            {
                "id": "analysis-uncertainty",
                "action": "analysis",
                "title": "Uncertain analysis",
                "description": "This step must pause when input is required.",
                "target_file": "",
                "target_files": [],
                "target_function": "",
                "status": "pending",
                "result": "",
                "error": None,
                "payload": {},
                "execution_mode": "",
                "dependencies": [],
                "expected_output": "",
                "completion_criteria": [],
                "next_action": None,
                "mutation_ready": False,
            }
        ],
        "current_index": 0,
        "current_step": None,
        "history": [],
        "waiting": True,
        "complete": False,
        "mission_id": None,
        "error": None,
    }

    result = handler.run_next_step(
        "run_step",
        "test-uncertainty-state",
        execution_state,
    )

    final_state = result["execution_state"]

    assert result["ok"] is True, result
    assert final_state["status"] == "waiting", final_state
    assert final_state["waiting"] is True, final_state
    assert final_state["complete"] is False, final_state
    assert final_state["current_index"] == 0, final_state
    assert final_state["current_step"]["id"] == "analysis-uncertainty", final_state
    assert final_state["current_step"]["status"] == "waiting", final_state
    assert final_state["steps"][0]["status"] == "waiting", final_state
    assert final_state["history"] == [], final_state

    print("UNCERTAINTY STATE REGRESSION TEST PASSED")


if __name__ == "__main__":
    main()
