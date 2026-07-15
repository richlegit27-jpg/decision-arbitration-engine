from nova_backend.services.stale_working_state_history_service import (
    clean_stale_working_state_history,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


payload = {
    "session": {
        "working_state": {
            "active_task": "Cleanup Strategy Engine v1",
            "current_file": "project_brain_operator_planner.py",
        },
        "messages": [
            {
                "role": "assistant",
                "text": "No active task is currently tracked.",
                "content": "No active task is currently tracked.",
            },
            {
                "role": "assistant",
                "text": "Cleanup Strategy Engine v1",
                "content": "Cleanup Strategy Engine v1",
            },
        ],
    }
}


result = clean_stale_working_state_history(
    payload,
    "smoke_session",
)


require(
    isinstance(result, dict),
    "returns payload dict",
)

messages = (
    result
    .get("session", {})
    .get("messages", [])
)

joined = "\n".join(
    str(x.get("text") or "")
    for x in messages
    if isinstance(x, dict)
)


require(
    "No active task is currently tracked." not in joined,
    "stale active-task history removed",
)

require(
    "Cleanup Strategy Engine v1" in joined,
    "current working state preserved",
)


print()
print("=" * 80)
print("NOVA STALE WORKING STATE HISTORY FINALIZER SMOKE PASSED")
print("=" * 80)