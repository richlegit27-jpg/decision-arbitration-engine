from nova_backend.services.normal_chat_carryover_guard_service import (
    repair_normal_chat_carryover,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA NORMAL CHAT CARRYOVER GUARD SMOKE")
print("=" * 80)


bad_response = {
    "assistant_message": {
        "role": "assistant",
        "text": "NOVA autonomy task brief: Build State Bridge",
        "content": "NOVA autonomy task brief: Build State Bridge",
    },
    "debug": {},
}


request_data = {
    "message": "hi",
    "session_id": "smoke_session_001",
}


result = repair_normal_chat_carryover(
    bad_response,
    request_data,
)


require(
    result["assistant_message"]["text"]
    == "Hey Richard - normal chat is still active.",
    "autonomy carryover replaced for normal greeting",
)


require(
    result["assistant_message"]["meta"]["normal_chat_priority"]
    is True,
    "normal chat priority metadata added",
)


require(
    result["debug"]["suppressed_autonomy_carryover"]
    is True,
    "suppression debug flag added",
)


normal_response = {
    "assistant_message": {
        "text": "Regular answer",
    }
}


unchanged = repair_normal_chat_carryover(
    normal_response,
    {
        "message": "Explain photosynthesis",
    },
)


require(
    unchanged["assistant_message"]["text"]
    == "Regular answer",
    "non-greeting response unchanged",
)


print()
print("=" * 80)
print("NOVA NORMAL CHAT CARRYOVER GUARD SMOKE: PASS")
print("=" * 80)