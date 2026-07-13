from nova_backend.services.weak_response_guard_service import (
    apply_weak_response_guard,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)

    print("PASS", message)


print("=" * 80)
print("NOVA FINALIZER WEAK RESPONSE GUARD BOUNDARY SMOKE")
print("=" * 80)


weak_payload = {
    "assistant_message": {
        "role": "assistant",
        "text": (
            "Ready. What are we working on?"
        ),
        "content": (
            "Ready. What are we working on?"
        ),
    }
}

fixed = apply_weak_response_guard(
    "what are we working on",
    weak_payload,
)

require(
    fixed["assistant_message"]["meta"]["weak_response_guarded"],
    "weak response metadata preserved",
)

require(
    "personal life story" in fixed["assistant_message"]["text"],
    "weak response replacement preserved",
)


normal_payload = {
    "assistant_message": {
        "role": "assistant",
        "text": "Here is your answer.",
        "content": "Here is your answer.",
    }
}

normal = apply_weak_response_guard(
    "hello",
    normal_payload,
)

require(
    normal["assistant_message"]["text"]
    == "Here is your answer.",
    "normal response unchanged",
)


print()
print("=" * 80)
print("NOVA FINALIZER WEAK RESPONSE GUARD BOUNDARY SMOKE: PASS")
print("=" * 80)