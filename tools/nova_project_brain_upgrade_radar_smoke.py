
from nova_backend.services.project_brain_upgrade_radar import (
    build_upgrade_radar_summary,
    get_upgrade_candidates,
    select_best_upgrade,
)
from nova_backend.services.project_brain_operator_planner import (
    choose_recommended_move,
    rank_moves,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def move_value(move, key, default=None):
    if isinstance(move, dict):
        return move.get(key, default)
    return getattr(move, key, default)


def main():
    print("NOVA PROJECT BRAIN UPGRADE RADAR SMOKE")
    print("======================================")

    candidates = get_upgrade_candidates()
    best = select_best_upgrade()
    summary = build_upgrade_radar_summary()

    assert_true("candidates exist", len(candidates) >= 3)
    assert_true("best upgrade radar", best.name == "Auto-Debug Brain v1", best.name)
    assert_true("best risk medium", best.risk == "medium", best.risk)
    assert_true("summary includes auto debug", "Auto-Debug Brain v1" in summary)
    assert_true("summary includes self-test selector", "Self-Test Selector v1" in summary)

    moves = rank_moves("next_move")
    first = moves[0]

    assert_true("rank moves exists", len(moves) >= 1)
    assert_true("rank first upgrade radar", move_value(first, "name") == "Auto-Debug Brain v1", move_value(first, "name"))
    assert_true("cleanup skipped from top", move_value(first, "name") != "Cleanup Strategy Engine v1")

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")

    assert_true("recommended upgrade radar", recommended_move == "Auto-Debug Brain v1", recommended_move)
    assert_true("recommended why gangster upgrades", "gangster upgrades" in why or "Classify tracebacks" in why, why)
    assert_true("recommended risk", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_auto_debug_brain.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN UPGRADE RADAR SMOKE PASSED")


if __name__ == "__main__":
    main()
