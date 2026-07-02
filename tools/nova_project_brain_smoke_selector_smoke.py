from nova_backend.services.project_brain_smoke_selector import (
    build_smoke_selection,
    build_smoke_selection_dict,
    classify_smoke_work_type,
    format_smoke_selection,
    normalize_files,
    select_focused_smokes,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN SMOKE SELECTOR SMOKE")
    print("=======================================")

    assert_true(
        "normalizes files",
        normalize_files(["app.py", "app.py", "tools/test.py"]) == ["app.py", "tools\\test.py"],
    )

    assert_true(
        "classifies failure",
        classify_smoke_work_type("traceback failed") == "failure_repair",
    )

    assert_true(
        "classifies route cleanup by file",
        classify_smoke_work_type("", ["app.py"]) == "route_cleanup",
    )

    assert_true(
        "classifies mission control",
        classify_smoke_work_type("", ["nova_backend/services/project_brain_mission_control.py"]) == "mission_control_api",
    )

    assert_true(
        "classifies decision engine",
        classify_smoke_work_type("", ["nova_backend/services/project_brain_decision_engine.py"]) == "decision_engine",
    )

    assert_true(
        "classifies operator planner",
        classify_smoke_work_type("", ["nova_backend/services/project_brain_operator_planner.py"]) == "operator_planner",
    )

    assert_true(
        "classifies smoke selector",
        classify_smoke_work_type("", ["nova_backend/services/project_brain_smoke_selector.py"]) == "smoke_selector",
    )

    route_smokes = select_focused_smokes("route_cleanup", ["app.py"])
    assert_true("route uses audit", "python .\\tools\\nova_project_brain_route_patch_audit_smoke.py" in route_smokes, route_smokes)
    assert_true("route uses api", "python .\\tools\\nova_project_brain_mission_control_api_smoke.py" in route_smokes, route_smokes)
    assert_true("route uses regression", "python .\\tools\\nova_regression_smoke.py" in route_smokes, route_smokes)

    mission_smokes = select_focused_smokes("mission_control_api", ["nova_backend/services/project_brain_mission_control.py"])
    assert_true("mission uses operator plan smoke", "python .\\tools\\nova_project_brain_mission_control_operator_plan_smoke.py" in mission_smokes, mission_smokes)
    assert_true("mission uses api smoke", "python .\\tools\\nova_project_brain_mission_control_api_smoke.py" in mission_smokes, mission_smokes)

    decision_smokes = select_focused_smokes("decision_engine", ["nova_backend/services/project_brain_decision_engine.py"])
    assert_true("decision uses operator planner decision smoke", "python .\\tools\\nova_project_brain_decision_engine_operator_planner_smoke.py" in decision_smokes, decision_smokes)
    assert_true("decision uses decision engine smoke", "python .\\tools\\nova_project_brain_decision_engine_smoke.py" in decision_smokes, decision_smokes)

    planner_smokes = select_focused_smokes("operator_planner", ["nova_backend/services/project_brain_operator_planner.py"])
    assert_true("planner uses planner smoke only", planner_smokes == ["python .\\tools\\nova_project_brain_operator_planner_smoke.py"], planner_smokes)

    selector = build_smoke_selection(
        user_text="upgrade smoke selector",
        changed_files=["nova_backend/services/project_brain_smoke_selector.py"],
    )
    assert_true("selector work type", selector.work_type == "smoke_selector", selector)
    assert_true("selector focused smoke", selector.focused_smokes == ["python .\\tools\\nova_project_brain_smoke_selector_smoke.py"], selector)
    assert_true("selector no regression", selector.run_regression is False, selector)
    assert_true("selector no api", selector.run_api_smoke is False, selector)
    assert_true("selector reason", "Smoke Selector changed" in selector.reason, selector.reason)

    route_selection = build_smoke_selection(changed_files=["app.py"])
    assert_true("route selection regression", route_selection.run_regression is True, route_selection)
    assert_true("route selection api", route_selection.run_api_smoke is True, route_selection)

    data = build_smoke_selection_dict(changed_files=["nova_backend/services/project_brain_operator_planner.py"])
    assert_true("dict work type", data.get("work_type") == "operator_planner", data)
    assert_true("dict focused smoke", data.get("focused_smokes") == ["python .\\tools\\nova_project_brain_operator_planner_smoke.py"], data)

    formatted = format_smoke_selection(selector)
    assert_true("formatted title", "Project Brain Smoke Selection:" in formatted, formatted)
    assert_true("formatted work type", "Work type: smoke_selector" in formatted, formatted)
    assert_true("formatted smoke", "nova_project_brain_smoke_selector_smoke.py" in formatted, formatted)
    assert_true("formatted stop rule", "Stop rule:" in formatted, formatted)

    print("")
    print("NOVA PROJECT BRAIN SMOKE SELECTOR SMOKE PASSED")


if __name__ == "__main__":
    main()
