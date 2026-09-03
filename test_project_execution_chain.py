from pathlib import Path

from nova_backend.services.project_execution_handler import (
    ProjectExecutionHandler,
)

from nova_backend.services.execution_handler import (
    default_executor,
)

from nova_backend.services.chat_execution_service import (
    ChatExecutionService,
)


test_file = Path(
    r"C:\Users\Owner\nova\project_execution_chain_test.py"
)


handler = ProjectExecutionHandler(
    default_executor=default_executor,
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
            "target_file": str(test_file),
            "content": (
                "def project_execution_chain_test():\n"
                "    return 'CHAIN_EXECUTION_OK'\n"
            ),
        },
    ],
    context={
        "project_execution": True,
    },
)


print("\nINITIAL STATE:")
print(
    service.get_state(
        session_id=session_id,
    )
)


print("\nADVANCE 1:")
result_1 = service.advance(
    session_id=session_id,
)

print(result_1)


print("\nADVANCE 2:")
result_2 = service.advance(
    session_id=session_id,
)

print(result_2)


print("\nFINAL STATE:")
final_state = service.get_state(
    session_id=session_id,
)

print(final_state)


print("\nFILE EXISTS =", test_file.exists())


if test_file.exists():
    print("\nFILE CONTENT:")
    print(
        test_file.read_text(
            encoding="utf-8",
        )
    )