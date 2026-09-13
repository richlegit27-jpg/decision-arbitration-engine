from nova_backend.services.project_execution_handler import ProjectExecutionHandler


class CriteriaPassExecutionStepService:
    def execute_step_logic(self, session_id, step):
        step_id = step.get("id", "")

        if step_id.endswith("-completion-validation"):
            updated_step = dict(step)
            updated_step["status"] = "completed"
            updated_step["completion_status"] = "completed"
            updated_step["result"] = "PASS"
            return updated_step

        updated_step = dict(step)
        updated_step["status"] = "completed"
        updated_step["completion_status"] = "completed"
        updated_step["result"] = (
            "The required file exists and the file compiles successfully."
        )
        return updated_step


def main():
    handler = ProjectExecutionHandler(
        execution_step_service=CriteriaPassExecutionStepService()
    )

    execution_state = {
        "status": "running",
        "complete": False,
        "waiting": False,
        "current_index": 0,
        "current_step": {
            "id": "analysis-criteria-pass",
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
                "id": "analysis-criteria-pass",
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
        "test-criteria-pass-state",
        execution_state,
    )

    assert result["ok"] is True, result

    final_state = result["execution_state"]

    assert final_state["waiting"] is False, final_state
    assert final_state["complete"] is False, final_state
    assert final_state["current_index"] == 1, final_state
    assert final_state["status"] == "running", final_state

    assert (
        final_state["steps"][0]["status"]
        == "completed"
    ), final_state

    assert (
        final_state["steps"][0]["completion_status"]
        == "completed"
    ), final_state

    assert (
        final_state["steps"][1]["status"]
        == "active"
    ), final_state

    assert (
        final_state["current_step"]["id"]
        == "implementation-after-analysis"
    ), final_state

    assert (
        final_state["current_step"]["status"]
        == "active"
    ), final_state

    print("COMPLETION CRITERIA PASS REGRESSION TEST PASSED")


if __name__ == "__main__":
    main()
