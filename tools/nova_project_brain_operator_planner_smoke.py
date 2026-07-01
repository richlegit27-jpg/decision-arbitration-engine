from nova_backend.services.project_brain_operator_planner import (
    build_operator_plan,
    build_operator_plan_dict,
    classify_work_type,
    format_operator_plan,
    select_smokes,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN OPERATOR PLANNER SMOKE")
    print("=========================================")

    assert_true(
        "classifies gangster next upgrade",
        classify_work_type("keep it gangster endgame this bitch") == "operator_planning",
    )

    assert_true(
        "classifies cleanup",
        classify_work_type("clean up app.py guards") == "cleanup_strategy",
    )

    assert_true(
        "classifies failure",
        classify_work_type("smoke failed with traceback") == "failure_repair",
    )

    assert_true(
        "classifies smoke selection",
        classify_work_type("which smoke should we run") == "smoke_selection",
    )

    app_smokes = select_smokes("route_cleanup", ["app.py"])
    assert_true(
        "route cleanup uses audit",
        "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py" in app_smokes,
        app_smokes,
    )

    assert_true(
        "route cleanup uses regression",
        "python .\\tools\\nova_regression_smoke.py" in app_smokes,
        app_smokes,
    )

    plan = build_operator_plan("what is the next gangster upgrade")
    assert_true("planner recommends operator planner", plan.recommended_move == "Project Brain Operator Planner v1", plan)
    assert_true("planner risk low", plan.risk == "low", plan)
    assert_true("planner has target files", "nova_backend/services/project_brain_operator_planner.py" in plan.target_files, plan)
    assert_true("planner has focused smoke", "python .\\tools\\nova_project_brain_operator_planner_smoke.py" in plan.focused_smokes, plan)
    assert_true("planner blocks app.py guards", any("app.py route guards" in rule for rule in plan.avoid_rules), plan)

    cleanup_plan = build_operator_plan("extract app.py route guard")
    assert_true("cleanup strategy recommended", cleanup_plan.recommended_move == "Cleanup Strategy Engine v1", cleanup_plan)
    assert_true("cleanup medium risk", cleanup_plan.risk == "medium", cleanup_plan)
    assert_true("cleanup has one-family rule", any("one route/guard family" in rule for rule in cleanup_plan.avoid_rules), cleanup_plan)

    failure_plan = build_operator_plan("regression failed")
    assert_true("failure interpreter recommended", failure_plan.recommended_move == "Failure Interpreter v2", failure_plan)
    assert_true("failure reproduce rule", any("failing contract" in rule for rule in failure_plan.avoid_rules), failure_plan)

    data = build_operator_plan_dict("operator mode")
    assert_true("dict has recommended move", data.get("recommended_move") == "Project Brain Operator Planner v1", data)

    card = format_operator_plan(plan)
    assert_true("card title", "Project Brain Operator Plan:" in card, card)
    assert_true("card recommended move", "Recommended move: Project Brain Operator Planner v1" in card, card)
    assert_true("card stop rule", "Stop rule:" in card, card)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR PLANNER SMOKE PASSED")


if __name__ == "__main__":
    main()
