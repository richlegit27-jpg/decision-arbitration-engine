
from pathlib import Path

import app


test_file = Path(
    r"C:\Users\Owner\nova\project_execution_test_temp.py"
)


handler = app.chat_service.project_execution_handler

result = handler.run_next_step(
    action="run_step",
    session_id="test-project-fix-file",
    execution_state={
        "steps": [
            {
                "id": "step-fix-1",
                "action": "implement",
                "title": "Create test execution file",
                "target_file": str(test_file),
                "content": (
                    'def project_execution_test():\n'
                    '    return "PROJECT_EXECUTION_OK"\n'
                ),
            }
        ],
        "current_index": 0,
        "status": "running",
        "complete": False,
        "waiting": False,
    },
)


print("RESULT:")
print(result)

print()
print("FILE EXISTS =", test_file.exists())

if test_file.exists():
    print()
    print("FILE CONTENT:")
    print(test_file.read_text(encoding="utf-8"))