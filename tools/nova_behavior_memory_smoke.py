from nova_backend.services.nova_behavior_memory import (
    NovaBehaviorMemory,
)


print("NOVA BEHAVIOR MEMORY SMOKE")
print("=" * 40)


memory = NovaBehaviorMemory()


event = memory.record_behavior(
    {
        "behavior_problem": "continuity_failure",
        "severity": "high",
        "upgrade": "improve_context_lookup",
        "action": "check_memory_path",
        "reason": "Missing previous context",
    }
)


assert event["behavior_problem"] == "continuity_failure"

print("PASS records behavior event")


memory.record_behavior(
    {
        "behavior_problem": "continuity_failure"
    }
)


counts = memory.get_behavior_counts()

assert counts["continuity_failure"] == 2

print("PASS increments repeated failures")


memory.record_behavior(
    {
        "behavior_problem": "low_helpfulness_depth"
    }
)


ranked = memory.rank_behavior_problems()

assert ranked[0]["problem"] == "continuity_failure"

print("PASS ranks repeated problems")


priority = memory.create_improvement_priority()

assert priority["focus"] == "continuity_failure"

print("PASS creates improvement priority")


report = memory.export_report()

assert report["total_events"] == 3

print("PASS exports behavior report")


print()
print("NOVA BEHAVIOR MEMORY SMOKE PASSED")