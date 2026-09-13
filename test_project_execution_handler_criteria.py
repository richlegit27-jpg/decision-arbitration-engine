from nova_backend.services.project_execution_handler import ProjectExecutionHandler


class CriteriaExecutionStepService:
    def execute_step_logic(self, session_id, step):
        updated_step = dict(step)
        updated_step["status"] = "completed"
        updated_step["completion_status"] = "completed"
        updated_step["result"] = "The analysis is complete, but the required file was not verified."
        return updated_step


def main():
    handler = ProjectExecutionHandler(
        execution_step_service=CriteriaExecutionStepService()
    )

    execution_state = {
        "status": "running",
        "complete": False,
        "waiting": False,
        "current_index": 0,
        "current_step": {
            "id": "analysis-criteria",
            "type": "analysis",
            "status": "pending",
            "completion_status": None,
            "completion_criteria": [
                "verify the required file exists",
                "confirm the file compiles",
            ],
            "expected_output": "verified compilation result",
        },
        "steps": [
            {
                "id": "analysis-criteria",
                "type": "analysis",
                "status": "pending",
                "completion_status": None,
                "completion_criteria": [
                    "verify the required file exists",
                    "confirm the file compiles",
                ],
                "expected_output": "verified compilation result",
            },
            {
                "id": "implementation-after-analysis",
                "type": "implementation",
                "status": "pending",
                "completion_status": None,
            },
        ],
        "error": None,
    }

    result = handler.run_next_step(
        "run_step",
        "test-criteria-state",
        execution_state,
    )

    assert result["ok"] is True, result

    final_state = result["execution_state"]
    current_step = final_state["current_step"]

    assert current_step["id"] == "analysis-criteria", final_state
    assert current_step["status"] == "waiting", final_state
    assert current_step["completion_status"] == "needs_input", final_state
    assert final_state["waiting"] is True, final_state
    assert final_state["complete"] is False, final_state
    assert final_state["current_index"] == 0, final_state
    assert final_state["steps"][1]["status"] == "pending", final_state

    print("COMPLETION CRITERIA REGRESSION TEST PASSED")


if __name__ == "__main__":
    main()
