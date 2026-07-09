from nova_backend.services.project_brain_command_center import (
    build_project_brain_command_center_answer,
)
from nova_backend.services.project_brain_completed_move_filter import (
    is_move_completed,
)
from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan,
    rank_moves,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN OPERATOR PLANNER COMPLETED MOVE FILTER SMOKE")
    print("================================================================")

    assert_true("operator quality is completed", is_move_completed("Operator Plan Quality v2"))
    assert_true("smoke selector is completed", is_move_completed("Smoke Selector v1"))

    ranked = rank_moves("operator_planning")
    assert_true("ranked moves exist", bool(ranked), ranked)
    assert_true("rank one is cleanup strategy", ranked[0].name == "Cleanup Strategy Engine v1", ranked)
    assert_true(
        "operator quality moved to rejected",
        any(
            move.name == "Operator Plan Quality v2"
            and "Already locked" in move.loses_to_best_because
            for move in ranked[1:]
        ),
        ranked,
    )
    assert_true(
        "smoke selector moved to rejected",
        any(
            move.name == "Smoke Selector v1"
            and "Already locked" in move.loses_to_best_because
            for move in ranked[1:]
        ),
        ranked,
    )

    plan = build_operator_plan("next upgrade")
    assert_true("plan no longer recommends operator quality", plan.recommended_move != "Operator Plan Quality v2", plan)
    assert_true("plan recommends cleanup strategy", plan.recommended_move == "Cleanup Strategy Engine v1", plan)
    assert_true("plan rejected completed operator", any("Already locked" in move.loses_to_best_because for move in plan.rejected_moves), plan)

    answer = build_project_brain_command_center_answer("next upgrade")
    assert_true("command center no old best move", "Best Move: Operator Plan Quality v2" not in answer, answer)
    assert_true("command center cleanup best move", "Best Move: Cleanup Strategy Engine v1" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR PLANNER COMPLETED MOVE FILTER SMOKE PASSED")


if __name__ == "__main__":
    main()
