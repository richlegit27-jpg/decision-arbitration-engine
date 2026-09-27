from pathlib import Path

import app


test_file = Path(
    r"C:\Users\Owner\nova\chat_execution_real_test.py"
)

if test_file.exists():
    test_file.unlink()


execution_service = app.chat_service.chat_execution_service


start_state = execution_service.start(
    session_id="real-chat-execution-test",
    goal="Create a real Python file through ChatExecutionService.",
    steps=[
        {
            "id": "create-file",
            "action": "implement",
            "title": "Create real execution test file",
            "target_file": str(test_file),
            "content": (
                'def nova_real_execution_test():\n'
                '    return "REAL_CHAT_EXECUTION_OK"\n'
            ),
        }
    ],
    context={
        "test": True,
    },
)


print("\nSTART STATE:")
print(start_state)


result = execution_service.advance(
    session_id="real-chat-execution-test",
)


print("\nADVANCE RESULT:")
print(result)


print("\nAPPROVING THROUGH CHAT SERVICE...")
approval_result = app.chat_service.handle(
    user_text="approve",
    session_id="real-chat-execution-test",
)

print("\nAPPROVAL RESULT:")
print(approval_result)


print("\nFILE EXISTS =", test_file.exists())


if test_file.exists():
    print("\nFILE CONTENT:")
    print(
        test_file.read_text(
            encoding="utf-8"
        )
    )


print("\nFINAL STATE:")
final_state = execution_service.get_state(
    "real-chat-execution-test"
)
print(final_state)
