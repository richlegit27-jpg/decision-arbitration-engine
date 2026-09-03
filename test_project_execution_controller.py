from pathlib import Path

from app import project_execution_controller


test_file = Path(
    r"C:\Users\Owner\nova\project_controller_test_temp.py"
)

if test_file.exists():
    test_file.unlink()


tasks = [
    {
        "id": "controller-test-1",
        "title": "Create controller execution test file",
        "description": (
            "Verify the complete project controller "
            "execution pipeline."
        ),
        "action": "implement",
        "target_file": str(test_file),
        "content": (
            'def controller_execution_test():\n'
            '    return "PROJECT_CONTROLLER_OK"\n'
        ),
        "status": "pending",
    }
]


result = (
    project_execution_controller
    ._execute_with_existing_orchestrator(
        project_id="test-project-controller",
        tasks=tasks,
        command="run_all",
    )
)


print("\nRESULT:")
print(result)

print("\nFILE EXISTS =", test_file.exists())

if test_file.exists():
    print("\nFILE CONTENT:")
    print(
        test_file.read_text(
            encoding="utf-8"
        )
    )