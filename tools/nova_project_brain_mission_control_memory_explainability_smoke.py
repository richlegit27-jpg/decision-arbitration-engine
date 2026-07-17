from nova_backend.services.project_brain_decision_memory import (
    project_brain_decision_memory,
)
from nova_backend.services.project_brain_mission_control import (
    build_project_brain_mission_card,
)


def reset_memory():
    project_brain_decision_memory.store.save(
        {
            "events": []
        }
    )


reset_memory()

project_brain_decision_memory.record_outcome(
    recommended_move="Cleanup Strategy Engine v1",
    outcome="failure",
)

card = build_project_brain_mission_card(
    user_text="fix the latest failure",
)

card_dict = card.to_dict()

print(
    "MISSION CONTROL CARD:",
    card_dict,
)

assert card_dict

assert (
    "operator_plan"
    in card_dict
)

operator_plan = card_dict["operator_plan"]

assert operator_plan

plan_text = str(operator_plan)

assert "memory_signal" in plan_text
assert "previous_failure" in plan_text
assert "rank_penalty" in plan_text


print(
    "PROJECT BRAIN MISSION CONTROL MEMORY EXPLAINABILITY SMOKE PASS"
)