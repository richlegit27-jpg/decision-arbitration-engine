from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


def find_move(plan, name):
    for move in plan.get("ranked_moves", []):
        if move.get("name") == name:
            return move
    return None

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)

project_brain_decision_memory.store.save(
    {
        "events": []
    }
)


baseline = build_operator_plan_dict(
    user_text="fix the latest failure"
)

baseline_cleanup = find_move(
    baseline,
    "Cleanup Strategy Engine v1",
)

print(
    "BASELINE CLEANUP:",
    baseline_cleanup,
)

from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)

project_brain_decision_memory.record_outcome(
    recommended_move="Cleanup Strategy Engine v1",
    outcome="success",
)

learned = build_operator_plan_dict(
    user_text="fix the latest failure"
)

learned_cleanup = find_move(
    learned,
    "Cleanup Strategy Engine v1",
)

print(
    "SUCCESS MEMORY CLEANUP:",
    learned_cleanup,
)

assert learned_cleanup["memory_signal"] == 1
assert learned_cleanup["memory_rank_bonus"] == 1


project_brain_decision_memory.record_outcome(
    recommended_move="Cleanup Strategy Engine v1",
    outcome="failure",
)

failed = build_operator_plan_dict(
    user_text="fix the latest failure"
)

failed_cleanup = find_move(
    failed,
    "Cleanup Strategy Engine v1",
)

print(
    "FAILURE MEMORY CLEANUP:",
    failed_cleanup,
)

assert failed_cleanup["memory_signal"] == -1
assert failed_cleanup["memory_rank_penalty"] == 1


print(
    "PROJECT BRAIN DECISION MEMORY LIFECYCLE SMOKE PASS"
)