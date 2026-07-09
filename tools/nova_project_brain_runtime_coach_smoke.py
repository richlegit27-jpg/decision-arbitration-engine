
from nova_backend.services.project_brain_runtime_coach import (
    build_runtime_coach_answer,
    build_runtime_coach_dict,
    coach_runtime_output,
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
    print("NOVA PROJECT BRAIN RUNTIME COACH SMOKE")
    print("======================================")

    failure_output = """
PASS first
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\tools\\x.py", line 10, in main
    run()
TypeError: thing() got an unexpected keyword argument 'changed_files'
"""

    failure = coach_runtime_output(failure_output)
    assert_true("failure status", failure.status == "failed", failure.status)
    assert_true("failure recommends patch", failure.recommended_action == "patch", failure.recommended_action)
    assert_true("failure stop rule", "Do not commit" in failure.stop_rule, failure.stop_rule)

    dirty_output = """
PASS smoke
NOVA REGRESSION SMOKE PASSED
PS C:\\Users\\Owner\\nova> git status --short
 M nova_backend/services/project_brain_runtime_coach.py
?? tools/nova_project_brain_runtime_coach_smoke.py
"""

    dirty = coach_runtime_output(dirty_output)
    assert_true("dirty status", dirty.status == "green_uncommitted", dirty.status)
    assert_true("dirty recommends commit", dirty.recommended_action == "commit", dirty.recommended_action)

    clean_commit_output = """
PASS smoke
NOVA REGRESSION SMOKE PASSED
[post-frontend-polish-phase abc1234] Add Project Brain runtime coach
 3 files changed, 100 insertions(+)
PS C:\\Users\\Owner\\nova> git status --short
PS C:\\Users\\Owner\\nova>
"""

    locked = coach_runtime_output(clean_commit_output)
    locked_dict = build_runtime_coach_dict(clean_commit_output)
    answer = build_runtime_coach_answer(clean_commit_output)

    assert_true("locked status", locked.status == "locked_clean", locked.status)
    assert_true("locked recommends next", locked.recommended_action == "next_upgrade", locked.recommended_action)
    assert_true("locked clean", locked.working_tree_clean is True, locked.working_tree_clean)
    assert_true("dict status", locked_dict.get("status") == "locked_clean", locked_dict)
    assert_true("answer title", "Project Brain Runtime Coach" in answer)
    assert_true("answer next command", "Exact Next Command" in answer)

    best = select_best_upgrade()
    assert_true("radar returns ranked upgrade", best.name in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner returns ranked upgrade", move_value(moves[0], "name") in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended ranked upgrade", recommended_move in {"Project Brain Runtime Coach v1", "Project Brain Operator Memory Writer v1", "Project Brain State Bridge v1"}, recommended_move)
    assert_true("recommended why useful", bool(str(why or "").strip()), why)
    assert_true("recommended risk valid", risk in {"low", "medium", "high"}, risk)
    assert_true("recommended target files exist", bool(target_files), target_files)

    print("")
    print("NOVA PROJECT BRAIN RUNTIME COACH SMOKE PASSED")


if __name__ == "__main__":
    main()
