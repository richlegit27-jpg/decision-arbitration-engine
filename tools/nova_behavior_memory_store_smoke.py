from pathlib import Path

from nova_backend.services.nova_behavior_memory_store import (
    NovaBehaviorMemoryStore,
)


print("NOVA BEHAVIOR MEMORY STORE SMOKE")
print("=" * 45)


test_file = Path(
    "data/test_behavior_memory_store.json"
)


if test_file.exists():
    test_file.unlink()


store = NovaBehaviorMemoryStore(
    test_file
)


event = store.add_event(
    {
        "behavior_problem": "continuity_failure",
        "severity": "high",
        "upgrade": "improve_context"
    }
)


assert (
    event["behavior_problem"]
    ==
    "continuity_failure"
)

print("PASS saves behavior event")


events = store.get_events()

assert len(events) == 1

print("PASS reloads events")


count = store.count_problem(
    "continuity_failure"
)

assert count == 1

print("PASS counts behavior problems")


store.add_event(
    {
        "behavior_problem": "continuity_failure"
    }
)


assert (
    store.count_problem(
        "continuity_failure"
    )
    ==
    2
)

print("PASS tracks repeated problems")


print()
print(
    "NOVA BEHAVIOR MEMORY STORE SMOKE PASSED"
)


test_file.unlink()