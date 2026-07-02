
from nova_backend.services.project_brain_operator_command_launcher import (
    build_operator_command_launcher_answer,
    build_operator_command_plan,
    build_operator_command_plan_from_best_move,
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
    print("NOVA PROJECT BRAIN OPERATOR COMMAND LAUNCHER SMOKE")
    print("==================================================")

    plan = build_operator_command_plan(
        move_name="Patch Planner v1",
        target_files=[
            "nova_backend/services/project_brain_patch_planner.py",
            "tools/nova_project_brain_patch_planner_smoke.py",
        ],
        focused_smokes=[
            r"python .\tools\nova_project_brain_patch_planner_smoke.py",
        ],
        risk="medium",
    )

    assert_true("plan title", plan.title == "Project Brain Project Brain Action Card v1", plan.title)
    assert_true("move carried", plan.move_name == "Patch Planner v1", plan.move_name)
    assert_true("py compile service", any("project_brain_patch_planner.py" in item and "py_compile" in item for item in plan.commands), plan.commands)
    assert_true("py compile smoke", any("nova_project_brain_patch_planner_smoke.py" in item and "py_compile" in item for item in plan.commands), plan.commands)
    assert_true("focused smoke included", any("nova_project_brain_patch_planner_smoke.py" in item and "py_compile" not in item for item in plan.commands), plan.commands)
    assert_true("regression included medium", any("nova_regression_smoke.py" in item for item in plan.commands), plan.commands)
    assert_true("git status included", plan.commands[-1] == "git status --short", plan.commands)
    assert_true("stop rule exists", "stop" in plan.stop_rule.lower(), plan.stop_rule)

    low_plan = build_operator_command_plan(
        move_name="Self-Test Selector v1",
        target_files=["nova_backend/services/project_brain_smoke_selector.py"],
        focused_smokes=[r"python .\tools\nova_project_brain_smoke_selector_smoke.py"],
        risk="low",
    )

    assert_true("low risk no regression by default", not any("nova_regression_smoke.py" in item for item in low_plan.commands), low_plan.commands)

    answer = build_operator_command_launcher_answer(
        move_name="Patch Planner v1",
        target_files=["nova_backend/services/project_brain_patch_planner.py"],
        focused_smokes=[r"python .\tools\nova_project_brain_patch_planner_smoke.py"],
        risk="medium",
    )

    assert_true("answer title", "Project Brain Operator Command Launcher" in answer)
    assert_true("answer command block", "Command Block" in answer)
    assert_true("answer regression", "nova_regression_smoke.py" in answer)

    best = select_best_upgrade()
    assert_true("radar best launcher", best.name == "Project Brain Action Card v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first launcher", move_value(moves[0], "name") == "Project Brain Action Card v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended launcher", recommended_move == "Project Brain Action Card v1", recommended_move)
    assert_true("recommended why command blocks", "command blocks" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_action_card.py" in target_files, target_files)

    best_plan = build_operator_command_plan_from_best_move()
    assert_true("best plan launcher move", best_plan.move_name == "Project Brain Action Card v1", best_plan.move_name)
    assert_true("best plan has commands", bool(best_plan.commands), best_plan.commands)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR COMMAND LAUNCHER SMOKE PASSED")


if __name__ == "__main__":
    main()
