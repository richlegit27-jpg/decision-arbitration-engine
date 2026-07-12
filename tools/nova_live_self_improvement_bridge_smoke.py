"""
NOVA LIVE SELF IMPROVEMENT BRIDGE SMOKE

Tests:

evaluation
    ↓
behavior upgrade
    ↓
memory store
    ↓
priority engine
    ↓
self improvement coordinator
"""


from nova_backend.services.nova_behavior_learning_loop import (
    process_conversation_behavior,
)


print(
    "NOVA LIVE SELF IMPROVEMENT BRIDGE SMOKE"
)

print(
    "======================================="
)


evaluation = {

    "continuity": 40,

    "helpfulness": 90,

    "reasoning": 90,

    "actionability": 90,

    "issues": [
        "continuity failure"
    ],

}


print(
    "\nINPUT EVALUATION:"
)

print(
    evaluation
)


result = (
    process_conversation_behavior(
        evaluation
    )
)


print(
    "\nLEARNING RESULT:"
)

print(
    result
)


if not result.get(
    "stored_event"
):

    raise Exception(
        "FAIL behavior event not stored"
    )


if not result.get(
    "improvement_priority"
):

    raise Exception(
        "FAIL no improvement priority"
    )


print(
    "\nPASS live self improvement bridge works"
)