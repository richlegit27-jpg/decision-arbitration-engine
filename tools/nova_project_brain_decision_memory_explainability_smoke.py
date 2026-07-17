from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)
from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan_dict,
)


MOVE = "Cleanup Strategy Engine v1"


def find_move(plan, name):
    for move in plan.get("ranked_moves", []):
        if move.get("name") == name:
            return move
    return None


def reset_memory():
    project_brain_decision_memory.store.save(
        {
            "events": []
        }
    )


reset_memory()

project_brain_decision_memory.record_outcome(
    recommended_move=MOVE,
    outcome="success",
)

success_plan = build_operator_plan_dict(
    user_text="fix the latest failure"
)

success_move = find_move(
    success_plan,
    MOVE,
)

print(
    "SUCCESS EXPLANATION:",
    success_move,
)

assert success_move["memory_reason"] == "previous_success"
assert success_move["memory_influence"]["effect"] == "rank_bonus"
assert (
    success_move["memory_influence"]["reason"]
    == "previous successful outcome"
)


reset_memory()

project_brain_decision_memory.record_outcome(
    recommended_move=MOVE,
    outcome="failure",
)

failure_plan = build_operator_plan_dict(
    user_text="fix the latest failure"
)

failure_move = find_move(
    failure_plan,
    MOVE,
)

print(
    "FAILURE EXPLANATION:",
    failure_move,
)

assert failure_move["memory_reason"] == "previous_failure"
assert failure_move["memory_influence"]["effect"] == "rank_penalty"
assert (
    failure_move["memory_influence"]["reason"]
    == "previous failed outcome"
)


print(
    "PROJECT BRAIN DECISION MEMORY EXPLAINABILITY SMOKE PASS"
)