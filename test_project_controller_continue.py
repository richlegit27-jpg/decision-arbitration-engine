from pathlib import Path

from app import (
    project_execution_controller,
    project_workspace_service,
)


first_file = Path(
    r"C:\Users\Owner\nova\project_continue_test_one.py"
)

second_file = Path(
    r"C:\Users\Owner\nova\project_continue_test_two.py"
)


for test_file in (
    first_file,
    second_file,
):
    if test_file.exists():
        test_file.unlink()


project = (
    project_workspace_service.create_project(
        name="Continue Project Controller Test",
        description=(
            "Verify project tasks execute one at a time "
            "through continue_project()."
        ),
    )
)


PROJECT_ID = project["id"]


print("\nPROJECT ID:")
print(PROJECT_ID)


first_task = (
    project_workspace_service.add_task(
        PROJECT_ID,
        title="Create first continue test file",
        description=(
            "Create the first file using the first "
            "continue_project() call."
        ),
        action="implement",
        target_file=str(first_file),
        content=(
            'def first_continue_step():\n'
            '    return "CONTINUE_ONE_OK"\n'
        ),
    )
)


second_task = (
    project_workspace_service.add_task(
        PROJECT_ID,
        title="Create second continue test file",
        description=(
            "Create the second file using the second "
            "continue_project() call."
        ),
        action="implement",
        target_file=str(second_file),
        content=(
            'def second_continue_step():\n'
            '    return "CONTINUE_TWO_OK"\n'
        ),
    )
)


print("\nFIRST CONTINUE CALL")

first_result = (
    project_execution_controller
    .continue_project(
        PROJECT_ID
    )
)

print(first_result)


print(
    "\nAFTER FIRST CONTINUE:"
)

print(
    "FIRST FILE EXISTS =",
    first_file.exists(),
)

print(
    "SECOND FILE EXISTS =",
    second_file.exists(),
)


project_after_first = (
    project_workspace_service.get_project(
        PROJECT_ID
    )
)


print("\nTASK STATES AFTER FIRST CONTINUE:")

for task in project_after_first.get(
    "tasks",
    [],
):
    print(
        {
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),
        }
    )


print("\nSECOND CONTINUE CALL")

second_result = (
    project_execution_controller
    .continue_project(
        PROJECT_ID
    )
)

print(second_result)


print(
    "\nAFTER SECOND CONTINUE:"
)

print(
    "FIRST FILE EXISTS =",
    first_file.exists(),
)

print(
    "SECOND FILE EXISTS =",
    second_file.exists(),
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


first_ok = (
    first_file.exists()
)

second_ok = (
    second_file.exists()
)


tasks = final_project.get(
    "tasks",
    [],
)


all_completed = (
    len(tasks) == 2
    and all(
        task.get("status") == "completed"
        for task in tasks
    )
)


execution_completed = (
    isinstance(final_execution, dict)
    and final_execution.get("status")
    == "completed"
    and final_execution.get("current_task_id")
    is None
)


if (
    first_ok
    and second_ok
    and all_completed
    and execution_completed
):
    print(
        "\nCONTINUE PROJECT TEST: PASS"
    )
else:
    print(
        "\nCONTINUE PROJECT TEST: FAIL"
    )