from nova_backend.services.project_brain_mission_control import (
    build_project_brain_mission_card,
    build_project_brain_mission_control_answer,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN MISSION CONTROL OPERATOR PLAN SMOKE")
    print("======================================================")

    card = build_project_brain_mission_card("operator mode")
    plan = card.operator_plan

    assert_true("card has operator plan", isinstance(plan, dict), plan)
    assert_true("operator plan has move", bool(plan.get("recommended_move")), plan)
    assert_true("operator plan has why", bool(plan.get("why")), plan)
    assert_true("operator plan has work type", bool(plan.get("work_type")), plan)
    assert_true("operator plan has smokes", bool(plan.get("focused_smokes")), plan)
    assert_true("operator plan has avoid rules", bool(plan.get("avoid_rules")), plan)
    assert_true("operator plan has stop rule", bool(plan.get("stop_rule")), plan)
    assert_true("operator plan has exact next command", bool(plan.get("exact_next_command")), plan)
    assert_true("operator plan has loop guard", bool(plan.get("loop_guard")), plan)
    assert_true("operator plan has ranked moves", len(plan.get("ranked_moves", [])) == 3, plan)
    assert_true("operator plan has rejected moves", len(plan.get("rejected_moves", [])) == 2, plan)

    answer = build_project_brain_mission_control_answer("operator mode")

    assert_true("answer has mission title", "Project Brain Mission Control:" in answer, answer)
    assert_true("answer has v14 console", "Mission Control v1.4 Operator Console" in answer, answer)
    assert_true("answer has best move", "Best Move:" in answer, answer)
    assert_true("answer has exact next command top", "Exact Next Command:" in answer, answer)
    assert_true("answer has stop rule top", "Stop Rule:" in answer, answer)
    assert_true("answer has loop guard top", "Loop Guard:" in answer, answer)
    assert_true("answer has legacy contract", "Legacy Contract:" in answer, answer)
    assert_true("answer has operator section", "Operator Plan:" in answer, answer)
    assert_true("answer has operator recommended move", "Operator recommended move:" in answer, answer)
    assert_true("answer has operator focused smokes", "Operator focused smokes:" in answer, answer)
    assert_true("answer has operator avoid rules", "Operator avoid rules:" in answer, answer)
    assert_true("answer has operator exact next command", "Operator exact next command:" in answer, answer)
    assert_true("answer has operator ranked moves", "Operator ranked moves:" in answer, answer)
    assert_true("answer has operator rejected moves", "Operator rejected moves:" in answer, answer)
    assert_true("answer has operator stop rule", "Operator stop rule:" in answer, answer)
    assert_true("answer has operator loop guard", "Operator loop guard:" in answer, answer)

    direct_answer = build_project_brain_mission_control_answer("what are we working on now")
    assert_true("direct text still formats mission card service only", "Project Brain Mission Control:" in direct_answer, direct_answer)
    assert_true("direct text has operator plan", "Operator Plan:" in direct_answer, direct_answer)

    print("")
    print("NOVA PROJECT BRAIN MISSION CONTROL OPERATOR PLAN SMOKE PASSED")


if __name__ == "__main__":
    main()

