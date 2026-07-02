
from nova_backend.services.project_brain_patch_planner import (
    build_patch_plan,
    build_patch_plan_dict,
    build_patch_planner_answer,
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
    print("NOVA PROJECT BRAIN PATCH PLANNER SMOKE")
    print("======================================")

    signature_trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 304, in build_operator_plan
    moves = rank_moves(work_type, changed_files=changed_files)
TypeError: rank_moves() got an unexpected keyword argument 'changed_files'
"""

    plan = build_patch_plan(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )
    plan_dict = build_patch_plan_dict(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )
    answer = build_patch_planner_answer(
        pasted_output=signature_trace,
        user_intent="command center",
        route_risk="low",
    )

    assert_true("plan title", plan.title == "Project Brain Patch Planner v1", plan.title)
    assert_true("signature failure carried", plan.failure_type == "signature_mismatch", plan.failure_type)
    assert_true("target file carried", plan.target_file == "nova_backend/services/project_brain_operator_planner.py", plan.target_file)
    assert_true("patch move signature", "signature" in plan.patch_move or "keyword" in plan.patch_move, plan.patch_move)
    assert_true("guardrail service level", any("service-level" in item for item in plan.guardrails), plan.guardrails)
    assert_true("py compile included", any("py_compile" in item for item in plan.focused_smokes), plan.focused_smokes)
    assert_true("command center smoke included", any("general_intelligence_command_center_smoke" in item for item in plan.focused_smokes), plan.focused_smokes)
    assert_true("dict focused smokes", bool(plan_dict.get("focused_smokes")), plan_dict)
    assert_true("answer title", "Project Brain Patch Planner" in answer)
    assert_true("answer patch move", "Patch Move" in answer)

    route_trace = "AssertionError: command center route FAILED chat"
    route_plan = build_patch_plan(
        pasted_output=route_trace,
        changed_files=["app.py"],
        user_intent="command_center_api",
        route_risk="medium",
    )

    assert_true("route failure carried", route_plan.failure_type == "route_contract_failure", route_plan.failure_type)
    assert_true("route api smoke included", any("command_center_api_smoke" in item for item in route_plan.focused_smokes), route_plan.focused_smokes)
    assert_true("route regression included", any("nova_regression_smoke" in item for item in route_plan.focused_smokes), route_plan.focused_smokes)
    assert_true("route risk medium", route_plan.risk == "medium", route_plan.risk)

    best = select_best_upgrade()
    assert_true("radar best patch planner", best.name == "Patch Planner v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first patch planner", move_value(moves[0], "name") == "Patch Planner v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended patch planner", recommended_move == "Patch Planner v1", recommended_move)
    assert_true("recommended why patch plans", "patch plans" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_patch_planner.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN PATCH PLANNER SMOKE PASSED")


if __name__ == "__main__":
    main()
