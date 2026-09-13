from nova_backend.services.project_execution_handler import ProjectExecutionHandler


class EmptyResultExecutionStepService:
    def execute_step_logic(self, session_id, step):
        updated_step = dict(step)
        updated_step["status"] = "active"
        updated_step["result"] = ""
        return updated_step


def main():
    handler = ProjectExecutionHandler(
        execution_step_service=EmptyResultExecutionStepService()
    )

    execution_state = {
        "status": "ready",
        "goal": "Test empty AI result handling",
        "task_type": "general",
        "steps": [
            {
                "id": "analysis-empty",
                "action": "analysis",
                "title": "Empty analysis result",
                "description": "This step must fail when the AI returns no result.",
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
        "test-empty-result",
        execution_state,
    )

    final_state = result["execution_state"]

    assert result["ok"] is False, result
    assert final_state["status"] == "failed", final_state
    assert final_state["complete"] is False, final_state
    assert final_state["waiting"] is False, final_state
    assert final_state["current_index"] == 0, final_state
    assert final_state["current_step"]["id"] == "analysis-empty", final_state
    assert final_state["current_step"]["status"] == "failed", final_state
    assert final_state["steps"][0]["status"] == "failed", final_state
    assert "empty result" in final_state["error"].lower(), final_state

    print("EMPTY RESULT REGRESSION TEST PASSED")


if __name__ == "__main__":
    main()