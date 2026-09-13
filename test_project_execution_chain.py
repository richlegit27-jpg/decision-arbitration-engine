from pathlib import Path

from nova_backend.services.project_execution_handler import (
    ProjectExecutionHandler,
)

from nova_backend.services.execution_handler import (
    default_executor,
)

from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)

from nova_backend.services.chat_execution_service import (
    ChatExecutionService,
)


test_file = Path(
    r"C:\Users\Owner\nova\project_execution_chain_test.py"
)


execution_step_service = ExecutionStepService()

handler = ProjectExecutionHandler(
    default_executor=default_executor,
    execution_step_service=execution_step_service,
)


service = ChatExecutionService()

service.execution_handler = handler


session_id = "test-project-chain"


service.start(
    session_id=session_id,
    goal="Verify multi-step project execution",
    steps=[
        {
            "id": "analysis-1",
            "action": "analysis",
            "title": "Analyze project execution",
            "description": "Verify the first execution step completes.",
        },
        {
            "id": "implement-1",
            "action": "implement",
            "title": "Create chain execution test file",
            "description": "Create the project execution chain test file.",
            "target_file": str(test_file),
            "content": (
                "print('Nova project execution chain test passed.')\n"
            ),
        },
    ],
)


print("\nINITIAL STATE")
print(service.get_state(session_id))


print("\nADVANCE 1")
result_one = service.advance(
    session_id=session_id,
)

print(result_one)
print(service.get_state(session_id))


print("\nADVANCE 2")
result_two = service.advance(
    session_id=session_id,
)

print(result_two)
print(service.get_state(session_id))


print("\nFILE EXISTS =", test_file.exists())

if test_file.exists():
    print(
        "FILE CONTENT =",
        test_file.read_text(encoding="utf-8"),
    )