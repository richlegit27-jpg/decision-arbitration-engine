from pathlib import Path

from nova_backend.services.chat_execution_service import (
    ChatExecutionService,
)
from nova_backend.services.project_execution_handler import (
    ProjectExecutionHandler,
)
from nova_backend.services.execution_handler import (
    default_executor,
)


test_file = Path(
    r"C:\Users\Owner\nova\project_execution_flow_test.py"
)

if test_file.exists():
    test_file.unlink()


service = ChatExecutionService()

service.execution_handler = ProjectExecutionHandler(
    default_executor=default_executor
)


steps = [
    {
        "id": "step-1",
        "action": "analysis",
        "title": "Analyze test project",
        "description": (
            "Verify multi-step project execution."
        ),
    },
    {
        "id": "step-2",
        "action": "implement",
        "title": "Create test file",
        "description": (
            "Create the project execution test file."
        ),
        "target_file": str(test_file),
        "content": (
            'def execution_flow_test():\n'
            '    return "FLOW_OK"\n'
        ),
    },
    {
        "id": "step-3",
        "action": "review",
        "title": "Review execution result",
        "description": (
            "Verify the execution flow completed."
        ),
    },
]


session_id = "test-project-execution-flow"


print("\nSTARTING EXECUTION\n")

state = service.start(
    session_id=session_id,
    goal="Test complete project execution flow",
    steps=steps,
    context={
        "project_id": "test-project",
        "task_type": "project_execution",
    },
)

print("INITIAL STATE:")
print(state)


print("\nRUNNING ALL STEPS\n")

result = service.run_all(
    session_id=session_id
)


print("\nFINAL RESULT:")
print(result)


print("\nTEST FILE EXISTS:")
print(test_file.exists())


if test_file.exists():

    print("\nTEST FILE CONTENT:")
    print(
        test_file.read_text(
            encoding="utf-8"
        )
    )


print("\nFINAL STEP STATES:")

for step in result.get("steps", []):
    print(
        step.get("id"),
        "|",
        step.get("action"),
        "|",
        step.get("status"),
    )