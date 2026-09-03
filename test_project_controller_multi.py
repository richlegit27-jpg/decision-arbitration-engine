from pathlib import Path

from app import (
    project_execution_controller,
    project_workspace_service,
)


first_file = Path(
    r"C:\Users\Owner\nova\project_multi_test_one.py"
)

second_file = Path(
    r"C:\Users\Owner\nova\project_multi_test_two.py"
)


for test_file in (
    first_file,
    second_file,
):
    if test_file.exists():
        test_file.unlink()


project = (
    project_workspace_service.create_project(
        name="Project Controller Multi Test",
        description=(
            "Integration test for multi-step project execution."
        ),
    )
)


if not project:
    raise RuntimeError(
        "Could not create test project."
    )


PROJECT_ID = project.get("id")


print("\nPROJECT ID:")
print(PROJECT_ID)


first_task = (
    project_workspace_service.add_task(
        PROJECT_ID,
        title="Create first test file",
        description=(
            "Create the first file in a multi-step "
            "project execution."
        ),
        action="implement",
        target_file=str(first_file),
        content=(
            'def first_project_step():\n'
            '    return "STEP_ONE_OK"\n'
        ),
    )
)


second_task = (
    project_workspace_service.add_task(
        PROJECT_ID,
        title="Create second test file",
        description=(
            "Create the second file after the first "
            "step completes."
        ),
        action="implement",
        target_file=str(second_file),
        content=(
            'def second_project_step():\n'
            '    return "STEP_TWO_OK"\n'
        ),
    )
)


if not first_task:
    raise RuntimeError(
        "Could not create first test task."
    )


if not second_task:
    raise RuntimeError(
        "Could not create second test task."
    )


print("\nFIRST TASK ID:")
print(first_task.get("id"))

print("\nSECOND TASK ID:")
print(second_task.get("id"))


result = (
    project_execution_controller.run_all(
        PROJECT_ID
    )
)


print("\nRUN ALL RESULT:")
print(result)


print(
    "\nFIRST FILE EXISTS =",
    first_file.exists(),
)

print(
    "SECOND FILE EXISTS =",
    second_file.exists(),
)


if first_file.exists():

    print("\nFIRST FILE CONTENT:")

    print(
        first_file.read_text(
            encoding="utf-8"
        )
    )


if second_file.exists():

    print("\nSECOND FILE CONTENT:")

    print(
        second_file.read_text(
            encoding="utf-8"
        )
    )


final_project = (
    project_workspace_service.get_project(
        PROJECT_ID
    )
)


print("\nFINAL TASK STATES:")

for task in final_project.get(
    "tasks",
    [],
):

    print(
        {
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),
            "target_file": task.get(
                "target_file"
            ),
        }
    )


final_execution = (
    project_workspace_service
    .get_execution_state(
        PROJECT_ID
    )
)


print("\nFINAL EXECUTION STATE:")
print(final_execution)


if (
    first_file.exists()
    and second_file.exists()
    and all(
        task.get("status") == "completed"
        for task in final_project.get(
            "tasks",
            [],
        )
    )
    and final_execution.get("status")
    == "completed"
):
    print("\nMULTI-STEP PROJECT TEST: PASS")

else:
    print("\nMULTI-STEP PROJECT TEST: FAIL")