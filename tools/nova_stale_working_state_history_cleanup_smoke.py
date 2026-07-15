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
            "active_task": "cleanup finalizer blocks",
        },
        "messages": [
            {
                "role": "assistant",
                "text": "Current file:\nNo active file is currently tracked.",
                "content": "Current file:\nNo active file is currently tracked.",
            },
            {
                "role": "assistant",
                "text": "Active task:\nNo active task is currently tracked.",
                "content": "Active task:\nNo active task is currently tracked.",
            },
        ],
    }
}


result = clean_stale_working_state_history(
    payload,
    "smoke_session_001",
)


messages = result["session"]["messages"]


require(
    messages[0]["text"] == "Current file:\napp.py",
    "stale current file history repaired",
)


require(
    messages[1]["text"] == "Active task:\ncleanup finalizer blocks",
    "stale active task history repaired",
)


require(
    messages[0]["meta"]["stale_working_state_history_cleaned"] is True,
    "cleanup metadata added",
)


print()
print("=" * 80)
print("NOVA STALE WORKING STATE HISTORY CLEANUP SMOKE: PASS")
print("=" * 80)