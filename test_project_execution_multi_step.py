from pathlib import Path

from app import project_execution_controller


test_file_one = Path(
    r"C:\Users\Owner\nova\project_multi_test_one.py"
)

test_file_two = Path(
    r"C:\Users\Owner\nova\project_multi_test_two.py"
)

for test_file in (
    test_file_one,
    test_file_two,
):
    if test_file.exists():
        test_file.unlink()


tasks = [
    {
        "id": "multi-test-1",
        "title": "Create first test file",
        "description": (
            "Create the first file in a multi-step project."
        ),
        "action": "implement",
        "target_file": str(test_file_one),
        "content": (
            'def first_project_step():\n'
            '    return "STEP_ONE_OK"\n'
        ),
        "status": "pending",
    },
    {
        "id": "multi-test-2",
        "title": "Create second test file",
        "description": (
            "Create the second file after the first step completes."
        ),
        "action": "implement",
        "target_file": str(test_file_two),
        "content": (
            'def second_project_step():\n'
            '    return "STEP_TWO_OK"\n'
        ),
        "status": "pending",
    },
]


result = (
    project_execution_controller
    ._execute_with_existing_orchestrator(
        project_id="test-project-multi-step",
        tasks=tasks,
        command="run_all",
    )
)


print("\nRESULT:")
print(result)

print("\nFIRST FILE EXISTS =", test_file_one.exists())
print("SECOND FILE EXISTS =", test_file_two.exists())

if test_file_one.exists():
    print("\nFIRST FILE CONTENT:")
    print(test_file_one.read_text(encoding="utf-8"))

if test_file_two.exists():
    print("\nSECOND FILE CONTENT:")
    print(test_file_two.read_text(encoding="utf-8"))