from nova_backend.services.normal_chat_bleed_guard_service import (
    is_normal_chat,
    is_bleed,
    is_safe_probe,
    safe_answer,
    set_answer,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA NORMAL CHAT BLEED GUARD SMOKE")
print("=" * 80)


require(
    is_normal_chat("hi"),
    "normal greeting detected",
)


require(
    not is_normal_chat("continue nova project"),
    "project context rejected",
)


require(
    is_safe_probe("2+2"),
    "safe probe detected",
)


require(
    is_bleed("Next move: continue project state"),
    "project bleed detected",
)


require(
    safe_answer("2+2") == "2 plus 2 is 4.",
    "safe answer generated",
)


payload = {}

result = set_answer(
    payload,
    "I'm here. What would you like to talk about?",
)


require(
    result["text"]
    == "I'm here. What would you like to talk about?",
    "response payload replaced",
)


require(
    result["debug"]["suppressed_project_state_bleed"] is True,
    "bleed suppression metadata added",
)


print()
print("=" * 80)
print("NOVA NORMAL CHAT BLEED GUARD SMOKE: PASS")
print("=" * 80)