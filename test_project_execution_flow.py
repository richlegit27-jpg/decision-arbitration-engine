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
from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)
from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)
from nova_backend.services.python_runner_service import (
    PythonRunnerService,
)


test_file = Path(
    r"C:\Users\Owner\nova\project_execution_flow_test.py"
)

if test_file.exists():
    test_file.unlink()


service = ChatExecutionService()

approval_service = ExecutionApprovalService()
python_runner = PythonRunnerService()

execution_step_service = ExecutionStepService(
    safe_str=lambda value: str(value or ""),
    python_runner=python_runner,
    approval_service=approval_service,
    tool_executor=default_executor,
)

service.execution_handler = ProjectExecutionHandler(
    default_executor=default_executor,
    execution_step_service=execution_step_service,
)

steps = [
    {
        "id": "step-1",
        "action": "implement",
        "title": "Create test file",
        "description": "Create the Python test file.",
        "target_file": (
            r"C:\Users\Owner\nova\project_execution_flow_test.py"
        ),
        "content": 'print("FLOW_OK")\n',
        "completion_criteria": [
            "The Python file exists.",
        ],
    },
    {
        "id": "step-2",
        "action": "execute",
        "title": "Execute test file",
        "description": (
            "Execute the created Python file through the real "
            "project execution pipeline."
        ),
        "execution_file": (
            r"C:\Users\Owner\nova\project_execution_flow_test.py"
        ),
        "expected_output": "FLOW_OK",
        "completion_criteria": [
            "The Python subprocess completed successfully.",
            "stdout contains FLOW_OK.",
        ],
    },
    {
        "id": "step-3",
        "action": "review",
        "title": "Review execution result",
        "description": (
            "Verify that the Python subprocess completed successfully "
            "and returned FLOW_OK."
        ),
        "expected_output": "FLOW_OK",
        "completion_criteria": [
            "The execution result is successful.",
            "stdout contains FLOW_OK.",
        ],
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