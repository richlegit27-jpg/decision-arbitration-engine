
from nova_backend.services.project_brain_smoke_selector import (
    build_smoke_selector_answer,
    select_smokes,
)
from nova_backend.services.project_brain_upgrade_radar import select_best_upgrade
from nova_backend.services.project_brain_operator_planner import choose_recommended_move, rank_moves


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def move_value(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def main():
    print("NOVA PROJECT BRAIN SELF-TEST SELECTOR SMOKE")
    print("===========================================")

    service_selection = select_smokes(
        changed_files=[
            "nova_backend/services/project_brain_operator_planner.py",
            "tools/nova_project_brain_operator_planner_smoke.py",
        ],
        failure_type="signature_mismatch",
        failing_layer="operator_planner",
        user_intent="command center",
        route_risk="low",
    )

    assert_true("py compile included", any("py_compile" in item for item in service_selection.focused_smokes), service_selection.focused_smokes)
    assert_true("service smoke included", any("general_intelligence_command_center_smoke" in item for item in service_selection.focused_smokes), service_selection.focused_smokes)
    assert_true("service reason", "Project Brain service-layer" in service_selection.reason or "Changed Python files" in service_selection.reason, service_selection.reason)

    route_selection = select_smokes(
        changed_files=["app.py"],
        failure_type="route_contract_failure",
        failing_layer="api_route_gate",
        user_intent="command_center_api",
        route_risk="medium",
    )

    assert_true("api smoke included", any("command_center_api_smoke" in item for item in route_selection.focused_smokes), route_selection.focused_smokes)
    assert_true("regression included for medium risk", any("nova_regression_smoke" in item for item in route_selection.focused_smokes), route_selection.focused_smokes)
    assert_true("medium risk preserved", route_selection.risk == "medium", route_selection.risk)

    selector_selection = select_smokes(
        changed_files=["nova_backend/services/project_brain_patch_planner.py"],
        failing_layer="smoke_selector",
        user_intent="self-test",
        route_risk="low",
    )

    assert_true("selector smoke included", any("smoke_selector_smoke" in item for item in selector_selection.focused_smokes), selector_selection.focused_smokes)

    answer = build_smoke_selector_answer(
        changed_files=["nova_backend/services/project_brain_patch_planner.py"],
        failing_layer="smoke_selector",
        user_intent="self-test",
    )

    assert_true("answer title", "Project Brain Self-Test Selector" in answer)
    assert_true("answer focused smokes", "Focused Smokes" in answer)

    best = select_best_upgrade()
    assert_true("radar best self-test selector", best.name == "Patch Planner v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first self-test", move_value(moves[0], "name") == "Patch Planner v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended self-test", recommended_move == "Patch Planner v1", recommended_move)
    assert_true("recommended why smoke set", "smoke set" in why, why)
    assert_true("recommended risk low", risk == "low", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_patch_planner.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN SELF-TEST SELECTOR SMOKE PASSED")


if __name__ == "__main__":
    main()
