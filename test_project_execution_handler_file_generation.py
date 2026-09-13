from pprint import pprint

from nova_backend.services.project_execution_handler import (
    ProjectExecutionHandler,
)


class SuccessfulExecutionResult:
    status = "completed"
    result = "File generated successfully."


class SuccessfulExecutor:
    def __init__(self):
        self.moves = []

    def __call__(self, move):
        self.moves.append(move)

        return SuccessfulExecutionResult()


def main():
    executor = SuccessfulExecutor()

    handler = ProjectExecutionHandler(
        default_executor=executor,
    )

    execution_state = {
        "status": "running",
        "complete": False,
        "waiting": False,
        "current_index": 0,
        "current_step": None,
        "steps": [
            {
                "id": "file-generation-step",
                "title": "Generate file",
                "description": "Generate a test file.",
                "type": "build",
                "action": "build",
                "status": "active",
                "target_file": "generated_test.txt",
                "content": (
                    "Nova file-generation regression test."
                ),
            },
            {
                "id": "next-step",
                "title": "Next step",
                "description": "Continue after file generation.",
                "type": "analysis",
                "action": "analysis",
                "status": "pending",
            },
        ],
    }

    execution_state["current_step"] = (
        execution_state["steps"][0]
    )

    result = handler.run_next_step(
        action="run_step",
        session_id="test-file-generation-advancement",
        execution_state=execution_state,
    )

    print("FULL RESULT:")
    pprint(result)

    assert result["ok"] is True

    updated_state = result["execution_state"]
    updated_steps = updated_state["steps"]

    assert len(executor.moves) == 1

    move = executor.moves[0]

    assert getattr(move, "type", None) == "fix_file"
    assert getattr(move, "id", None) == "file-generation-step"

    move_payload = getattr(move, "payload", None)

    assert isinstance(move_payload, dict)

    assert move_payload["file_path"] == (
        "generated_test.txt"
    )

    assert move_payload["file_paths"] == [
        "generated_test.txt"
    ]

    assert move_payload["code"] == (
        "Nova file-generation regression test."
    )

    assert updated_steps[0]["status"] == "completed"
    assert updated_steps[0].get("error") is None

    assert updated_state["current_index"] == 1

    assert updated_state["current_step"]["id"] == (
        "next-step"
    )

    assert updated_steps[1]["status"] == "active"
    assert updated_state["waiting"] is False
    assert updated_state["complete"] is False
    assert updated_state["status"] == "running"

    assert updated_state.get("history")

    print(
        "FILE GENERATION ADVANCEMENT REGRESSION TEST PASSED"
    )


if __name__ == "__main__":
    main()