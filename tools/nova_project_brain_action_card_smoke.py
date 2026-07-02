
from nova_backend.services.project_brain_action_card import (
    build_project_brain_action_card,
    build_project_brain_action_card_answer,
    build_project_brain_action_card_dict,
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
    print("NOVA PROJECT BRAIN ACTION CARD SMOKE")
    print("====================================")

    card = build_project_brain_action_card()
    card_dict = build_project_brain_action_card_dict()
    answer = build_project_brain_action_card_answer()

    assert_true("card title", card.title == "Project Brain Action Card v1", card.title)
    assert_true("card move action card", card.move_name == "Project Brain Action Card v1", card.move_name)
    assert_true("card target files", "nova_backend/services/project_brain_action_card.py" in card.target_files, card.target_files)
    assert_true("card focused smokes", any("action_card_smoke" in item for item in card.focused_smokes), card.focused_smokes)
    assert_true("card commands", any("action_card_smoke" in item for item in card.commands), card.commands)
    assert_true("card git status", card.commands[-1] == "git status --short", card.commands)
    assert_true("dict commands", bool(card_dict.get("commands")), card_dict)
    assert_true("answer title", "Project Brain Action Card" in answer)
    assert_true("answer command block", "Command Block" in answer)

    trace = """
Traceback (most recent call last):
  File "C:\\Users\\Owner\\nova\\nova_backend\\services\\project_brain_operator_planner.py", line 304, in build_operator_plan
    moves = rank_moves(work_type, changed_files=changed_files)
TypeError: rank_moves() got an unexpected keyword argument 'changed_files'
"""

    failure_card = build_project_brain_action_card(
        pasted_output=trace,
        user_text="command center",
        route_risk="low",
    )

    assert_true("failure type carried", failure_card.failure_type == "signature_mismatch", failure_card.failure_type)
    assert_true("patch move carried", "signature" in failure_card.patch_move or "keyword" in failure_card.patch_move, failure_card.patch_move)
    assert_true("failure command smokes", any("general_intelligence_command_center_smoke" in item for item in failure_card.commands), failure_card.commands)

    best = select_best_upgrade()
    assert_true("radar best action card", best.name == "Project Brain Action Card v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first action card", move_value(moves[0], "name") == "Project Brain Action Card v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended action card", recommended_move == "Project Brain Action Card v1", recommended_move)
    assert_true("recommended why operator card", "operator card" in why or "exact commands" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_action_card.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN ACTION CARD SMOKE PASSED")


if __name__ == "__main__":
    main()
