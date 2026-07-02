
from pathlib import Path
import json
import tempfile

from nova_backend.services.project_brain_state_bridge import (
    build_direct_recall_state_text,
    build_state_bridge_answer,
    build_state_bridge_record,
    load_latest_operator_milestone,
    write_state_bridge_memory,
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
    print("NOVA PROJECT BRAIN STATE BRIDGE SMOKE")
    print("=====================================")

    milestone = {
        "next_move": "Project Brain State Bridge v1",
        "locked_upgrades": [
            "Project Brain Upgrade Radar v1",
            "Auto-Debug Brain v1",
            "Self-Test Selector v1",
            "Patch Planner v1",
            "Operator Command Launcher v1",
            "Project Brain Action Card v1",
            "Project Brain Mission Autopilot v1 safe mode",
            "Project Brain Runtime Coach v1",
            "Project Brain Operator Memory Writer v1",
        ],
    }

    record = build_state_bridge_record(milestone=milestone)
    text = build_direct_recall_state_text(milestone=milestone)

    assert_true("record title", record.title == "Project Brain State Bridge v1", record.title)
    assert_true("record next move", record.next_move == "Project Brain State Bridge v1", record.next_move)
    assert_true("record locked memory writer", "Project Brain Operator Memory Writer v1" in record.locked_stack, record.locked_stack)
    assert_true("text mentions gangster", "gangster intelligence stack" in text, text)
    assert_true("text avoids active cleanup", "Next move: Start Project Brain cleanup/consolidation" not in text, text)
    assert_true("text next state bridge", "Next move: Project Brain State Bridge v1" in text, text)

    with tempfile.TemporaryDirectory() as temp_dir:
        operator_path = Path(temp_dir) / "operator_memory.json"
        memory_path = Path(temp_dir) / "nova_memory.json"

        operator_path.write_text(
            json.dumps({"latest": milestone, "milestones": [milestone]}, indent=2),
            encoding="utf-8",
        )
        memory_path.write_text(json.dumps({"memories": []}, indent=2), encoding="utf-8")

        latest = load_latest_operator_milestone(operator_path)
        assert_true("latest milestone loaded", latest.get("next_move") == "Project Brain State Bridge v1", latest)

        written = write_state_bridge_memory(
            memory_path=memory_path,
            operator_memory_path=operator_path,
            next_move="Project Brain State Bridge v1",
        )
        item = written.get("item", {})

        assert_true("memory item project state", item.get("type") == "project_state", item)
        assert_true("memory item pinned", item.get("pinned") is True, item)
        assert_true("memory item source", item.get("source") == "project_brain_state_bridge", item)
        assert_true("memory item next", "Project Brain State Bridge v1" in item.get("text", ""), item)

        answer = build_state_bridge_answer(
            memory_path=memory_path,
            operator_memory_path=operator_path,
            write=True,
        )

        assert_true("answer title", "Project Brain State Bridge" in answer)
        assert_true("answer written", "Written: True" in answer)
        assert_true("answer direct recall text", "Direct Recall Text" in answer)

    best = select_best_upgrade()
    assert_true("radar best state bridge", best.name == "Project Brain State Bridge v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first state bridge", move_value(moves[0], "name") == "Project Brain State Bridge v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended state bridge", recommended_move == "Project Brain State Bridge v1", recommended_move)
    assert_true("recommended why direct recall", "direct project-state recall" in why or "stale cleanup" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_state_bridge.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN STATE BRIDGE SMOKE PASSED")


if __name__ == "__main__":
    main()
