from nova_backend.services.stale_working_state_history_service import (
    clean_stale_working_state_history,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA STALE WORKING STATE HISTORY CLEANUP SMOKE")
print("=" * 80)

payload = {
    "session": {
        "working_state": {
            "current_file": "app.py",
            "active_task": "cleanup extraction",
        },
        "messages": [
            {
                "role": "assistant",
                "text": "No active file is currently tracked.",
                "content": "No active file is currently tracked.",
            },
            {
                "role": "assistant",
                "text": "No active task is currently tracked.",
                "content": "No active task is currently tracked.",
            },
        ],
    }
}

result = clean_stale_working_state_history(
    payload,
    "test_session",
)

messages = result["session"]["messages"]

require(
    messages[0]["text"] == "Current file:\napp.py",
    "stale current file repaired",
)

require(
    messages[1]["text"] == "Active task:\ncleanup extraction",
    "stale active task repaired",
)

require(
    messages[0]["meta"]["stale_working_state_history_cleaned"],
    "cleanup metadata written",
)

print()
print("=" * 80)
print("NOVA STALE WORKING STATE HISTORY CLEANUP SMOKE: PASS")
print("=" * 80)