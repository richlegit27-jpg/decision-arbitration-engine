import asyncio
import os

from app import project_execution_controller


PROJECT_ID = "test-project-dependencies"
SESSION_ID = (
    "project:test-project-dependencies:dependency-test-1"
)

FIRST_FILE = (
    r"C:\Users\Owner\nova\project_dependency_branch_one.py"
)

SECOND_FILE = (
    r"C:\Users\Owner\nova\project_dependency_branch_two.py"
)

FINAL_FILE = (
    r"C:\Users\Owner\nova\project_dependency_final.py"
)


STEPS = [
    {
        "id": "project_task_dependency-1",
        "task_id": "dependency-1",
        "task_title": "Create first dependency branch",
        "title": "Create first dependency branch",
        "description": "Create the first independent branch.",
        "action": "implement",
        "status": "pending",
        "target_file": FIRST_FILE,
        "content": (
            "def dependency_branch_one():\n"
            '    return "BRANCH_ONE_OK"\n'
        ),
        "dependencies": [],
    },
    {
        "id": "project_task_dependency-2",
        "task_id": "dependency-2",
        "task_title": "Create second dependency branch",
        "title": "Create second dependency branch",
        "description": "Create the second independent branch.",
        "action": "implement",
        "status": "pending",
        "target_file": SECOND_FILE,
        "content": (
            "def dependency_branch_two():\n"
            '    return "BRANCH_TWO_OK"\n'
        ),
        "dependencies": [],
    },
    {
        "id": "project_task_dependency-3",
        "task_id": "dependency-3",
        "task_title": "Create converged final task",
        "title": "Create converged final task",
        "description": (
            "Create the final task after both branches complete."
        ),
        "action": "implement",
        "status": "pending",
        "target_file": FINAL_FILE,
        "content": (
            "def dependency_final_step():\n"
            '    return "FINAL_STEP_OK"\n'
        ),
        "dependencies": [
            "dependency-1",
            "dependency-2",
        ],
    },
]


async def main():
    for path in (FIRST_FILE, SECOND_FILE, FINAL_FILE):
        if os.path.exists(path):
            os.remove(path)

    result = (
        project_execution_controller
        ._execute_with_existing_orchestrator(
            project_id=PROJECT_ID,
            tasks=STEPS,
            command="run_all",
        )
    )

    print("\nRESULT:")
    print(result)

    execution = result.get("execution", result)

    assert execution.get("status") == "complete", (
        f"Expected complete status, got: {execution.get('status')}"
    )

    assert execution.get("complete") is True, (
        "Execution did not report complete=True"
    )

    assert execution.get("waiting") is False, (
        "Execution incorrectly remains waiting"
    )

    completed_steps = execution.get("steps", [])

    assert len(completed_steps) == 3, (
        f"Expected 3 steps, got {len(completed_steps)}"
    )

    for step in completed_steps:
        assert step.get("status") == "completed", (
            f"Step did not complete: {step}"
        )

    assert os.path.exists(FIRST_FILE), (
        "First dependency branch file was not created"
    )

    assert os.path.exists(SECOND_FILE), (
        "Second dependency branch file was not created"
    )

    assert os.path.exists(FINAL_FILE), (
        "Final converged file was not created"
    )

    print("\nDEPENDENCY EXECUTION TEST PASSED")
    print("First branch exists =", os.path.exists(FIRST_FILE))
    print("Second branch exists =", os.path.exists(SECOND_FILE))
    print("Final task exists =", os.path.exists(FINAL_FILE))


if __name__ == "__main__":
    asyncio.run(main())