from pathlib import Path

from nova_backend.services.nova_behavior_observer import (
    NovaBehaviorObserver,
)

import nova_backend.services.nova_behavior_observer as observer_module

from nova_backend.services.nova_behavior_memory_store import (
    NovaBehaviorMemoryStore,
)


print("NOVA BEHAVIOR OBSERVER SMOKE")
print("=" * 40)


test_file = Path(
    "data/test_behavior_observer.json"
)


if test_file.exists():
    test_file.unlink()


import nova_backend.services.nova_behavior_learning_loop as loop

loop.behavior_memory_store = (
    NovaBehaviorMemoryStore(test_file)
)


observer = NovaBehaviorObserver()


result = observer.observe(
    {
        "continuity": 40,
        "helpfulness": 80,
        "reasoning": 90,
        "actionability": 90,
        "issues": [
            "User requested continuity but no previous context was available."
        ],
    }
)


assert result["observed"] is True

print("PASS observes conversation")


events = loop.behavior_memory_store.get_events()

assert len(events) == 1

print("PASS records behavior event")


observer.enabled = False


disabled = observer.observe({})

assert disabled["observed"] is False

print("PASS supports safe disable")


print()
print(
    "NOVA BEHAVIOR OBSERVER SMOKE PASSED"
)


test_file.unlink()