"""
NOVA LIVE BEHAVIOR OBSERVATION SMOKE

Validates:

real Nova chat response
    ->
conversation quality evaluator
    ->
behavior signal builder
    ->
behavior memory
"""

import requests

from nova_backend.services.nova_conversation_quality_evaluator import (
    evaluate_conversation,
)

from nova_backend.services.nova_behavior_signal_builder import (
    NovaBehaviorSignalBuilder,
)

from nova_backend.services.nova_behavior_memory import (
    NovaBehaviorMemory,
)


BASE_URL = "http://127.0.0.1:5001"


def run():
    print("NOVA LIVE BEHAVIOR OBSERVATION SMOKE")
    print("====================================")

    session_id = "behavior_live_test_001"

    user_message = (
        "What should we do next with Nova Project Brain?"
    )

    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": user_message,
            "session_id": session_id,
        },
        timeout=30,
    )

    assert response.status_code == 200
    print("PASS chat response received")

    data = response.json()

    assistant_message = (
        data
        .get("assistant_message", {})
        .get("content", "")
    )

    assert assistant_message
    print("PASS assistant response exists")

    quality = evaluate_conversation(
        user_message=user_message,
        assistant_message=assistant_message,
        previous_context="Nova Project Brain work.",
    )

    assert quality is not None
    print("PASS evaluates live response")

    builder = NovaBehaviorSignalBuilder()

    signals = builder.build(
        user_text=user_message,
        assistant_text=assistant_message,
        context="Nova Project Brain work.",
    )

    assert signals is not None
    print("PASS builds live behavior signals")

    memory = NovaBehaviorMemory()

    memory.record_behavior(
        quality
    )

    print("PASS stores behavior observation")

    print(
        "NOVA LIVE BEHAVIOR OBSERVATION SMOKE PASSED"
    )


if __name__ == "__main__":
    run()