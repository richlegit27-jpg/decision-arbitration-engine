
from nova_backend.services.project_brain_mission_autopilot import (
    build_mission_autopilot_answer,
    build_mission_autopilot_dict,
    build_mission_autopilot_plan,
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
    print("NOVA PROJECT BRAIN MISSION AUTOPILOT SMOKE")
    print("==========================================")

    plan = build_mission_autopilot_plan()
    plan_dict = build_mission_autopilot_dict()
    answer = build_mission_autopilot_answer()

    assert_true("plan title", plan.title == "Project Brain Mission Autopilot v1", plan.title)
    assert_true("safe mode", plan.mode == "safe_mode", plan.mode)
    assert_true("allowed", plan.allowed is True, plan.allowed)
    assert_true("selected autopilot", plan.selected_move == "Project Brain Mission Autopilot v1", plan.selected_move)
    assert_true("target file", "nova_backend/services/project_brain_mission_autopilot.py" in plan.target_files, plan.target_files)
    assert_true("autopilot smoke command", any("mission_autopilot_smoke" in item for item in plan.commands), plan.commands)
    assert_true("git status command", plan.commands[-1] == "git status --short", plan.commands)
    assert_true("stop on failure", "Stop on the first failing command" in plan.stop_rule, plan.stop_rule)
    assert_true("dict commands", bool(plan_dict.get("commands")), plan_dict)
    assert_true("answer title", "Project Brain Mission Autopilot" in answer)
    assert_true("answer command block", "Command Block" in answer)

    refused = build_mission_autopilot_plan(
        changed_files=["app.py"],
        user_text="cleanup app.py wrappers",
        route_risk="low",
    )

    assert_true("refuses risky app route", refused.allowed is False, refused)
    assert_true("refusal reason app.py", "app.py" in refused.refusal_reason, refused.refusal_reason)
    assert_true("refusal only git status", refused.commands == ("git status --short",), refused.commands)

    explicit_route = build_mission_autopilot_plan(
        changed_files=["app.py"],
        user_text="route_contract_failure command_center_api",
        route_risk="medium",
    )

    assert_true("explicit route allowed", explicit_route.allowed is True, explicit_route.refusal_reason)
    assert_true("explicit route regression", any("nova_regression_smoke" in item for item in explicit_route.commands), explicit_route.commands)

    best = select_best_upgrade()
    assert_true("radar best autopilot", best.name == "Project Brain Mission Autopilot v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first autopilot", move_value(moves[0], "name") == "Project Brain Mission Autopilot v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended autopilot", recommended_move == "Project Brain Mission Autopilot v1", recommended_move)
    assert_true("recommended why stop failure", "stop-on-failure" in why or "bounded service-level move" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_mission_autopilot.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN MISSION AUTOPILOT SMOKE PASSED")


if __name__ == "__main__":
    main()
