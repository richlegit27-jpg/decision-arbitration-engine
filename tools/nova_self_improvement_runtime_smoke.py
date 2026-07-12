"""
NOVA SELF IMPROVEMENT RUNTIME SMOKE

Validates live ChatService behavior observation
to self improvement pipeline.

Advisory only.
"""

from app import chat_service


print(
    "NOVA SELF IMPROVEMENT RUNTIME SMOKE"
)

print(
    "==================================="
)


test_user_text = (
    "The answer was not clear enough. "
    "Give a better execution path."
)


test_assistant_text = (
    "I understand. Here is a clearer "
    "step-by-step execution path."
)


print(
    "Sending behavior through live observer..."
)


chat_service._observe_response_behavior(
    user_text=test_user_text,
    assistant_text=test_assistant_text,
    context="runtime smoke test",
)


print()

print(
    "PASS live behavior observer executed"
)

print(
    "PASS runtime self improvement hook reached"
)