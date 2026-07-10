from nova_backend.services.nova_behavior_context_service import (
    build_behavior_context,
)


print(
    "NOVA BEHAVIOR CONTEXT IMPROVEMENT SMOKE"
)

print(
    "======================================"
)


context = build_behavior_context()


assert isinstance(
    context,
    list
)

print(
    "PASS builds behavior context"
)


assert any(
    "improvement focus"
    in item.lower()
    for item in context
)

print(
    "PASS includes improvement focus"
)


print(
    "NOVA BEHAVIOR CONTEXT IMPROVEMENT SMOKE PASSED"
)