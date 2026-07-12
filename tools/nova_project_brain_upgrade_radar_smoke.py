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

    assert_true(
        "candidates exist",
        len(candidates) >= 3,
    )

    assert_true(
        "best upgrade radar",
        best.name == "Nova Conversation Quality Field Test v1",
        best.name,
    )

    assert_true(
        "best risk valid",
        best.risk in {"low", "medium", "high"},
        best.risk,
    )

    assert_true(
        "summary includes conversation quality field test",
        "Nova Conversation Quality Field Test v1" in summary,
        summary,
    )

    assert_true(
        "summary includes app guard cleanup",
        "App.py Guard Cleanup Pass 2" in summary,
        summary,
    )

    moves = rank_moves("next_move")
    first = moves[0]

    assert_true(
        "rank moves exists",
        len(moves) >= 1,
    )

    assert_true(
        "rank first cleanup strategy",
        move_value(first, "name") == "Cleanup Strategy Engine v1",
        move_value(first, "name"),
    )

    recommended_move, why, risk, target_files = choose_recommended_move(
        "next_move"
    )

    assert_true(
        "recommended cleanup strategy",
        recommended_move == "Cleanup Strategy Engine v1",
        recommended_move,
    )

    assert_true(
        "recommended why exists",
        isinstance(why, str) and len(why) > 0,
        why,
    )

    assert_true(
        "recommended risk valid",
        risk in {"low", "medium", "high"},
        risk,
    )

    assert_true(
        "recommended target files exist",
        len(target_files) > 0,
        target_files,
    )

    print("")
    print("NOVA PROJECT BRAIN UPGRADE RADAR SMOKE PASSED")


if __name__ == "__main__":
    main()