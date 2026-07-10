from nova_backend.services.nova_behavior_learning_loop import (
    process_conversation_behavior,
)

from pathlib import Path

from nova_backend.services.nova_behavior_memory_store import (
    NovaBehaviorMemoryStore,
)


print("NOVA BEHAVIOR LEARNING LOOP SMOKE")
print("=" * 45)


test_file = Path(
    "data/test_learning_behavior.json"
)


if test_file.exists():
    test_file.unlink()


# temporarily use isolated store
import nova_backend.services.nova_behavior_learning_loop as loop


loop.behavior_memory_store = (
    NovaBehaviorMemoryStore(test_file)
)


evaluation = {
    "continuity": 40,
    "helpfulness": 80,
    "reasoning": 90,
    "actionability": 90,
    "issues": [
        "User requested continuity but no previous context was available."
    ],
}


result = process_conversation_behavior(
    evaluation
)


assert (
    result["behavior_problem"]
    ==
    "continuity_failure"
)

print("PASS detects behavior issue")


assert (
    result["upgrade"]
    ==
    "prioritize_available_context_before_generic_response"
)

print("PASS creates upgrade")


stored = loop.behavior_memory_store.get_events()

assert len(stored) == 1

print("PASS stores learning event")


print()
print(
    "NOVA BEHAVIOR LEARNING LOOP SMOKE PASSED"
)


test_file.unlink()