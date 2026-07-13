from nova_backend.services.session_response_cleanup import (
    cleanup_session_response,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA SESSION RESPONSE CLEANUP SMOKE")
print("=" * 80)


response_session = {
    "working_state": {
        "active_task": "Build State Bridge",
    },
    "messages": [
        {
            "role": "assistant",
            "text": "No active task is currently tracked.",
            "content": "No active task is currently tracked.",
        }
    ],
}


result = cleanup_session_response(
    response_session,
    session_id="smoke_session_001",
)


require(
    isinstance(result, dict),
    "returns response session",
)


text = result["messages"][0]["text"]


require(
    text == "Active task:\nBuild State Bridge",
    "stale task history replaced with current working state",
)


require(
    result["messages"][0]["meta"]["stale_working_state_history_cleaned"]
    is True,
    "cleanup metadata applied",
)


print()
print("=" * 80)
print("NOVA SESSION RESPONSE CLEANUP SMOKE: PASS")
print("=" * 80)
