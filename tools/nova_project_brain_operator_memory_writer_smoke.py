
from pathlib import Path
import tempfile

from nova_backend.services.project_brain_operator_memory_writer import (
    LOCKED_GANGSTER_STACK,
    build_operator_memory_writer_answer,
    build_operator_milestone,
    build_operator_milestone_from_runtime_output,
    build_state_update_text,
    load_operator_memory,
    write_operator_milestone,
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
    print("NOVA PROJECT BRAIN OPERATOR MEMORY WRITER SMOKE")
    print("================================================")

    runtime_output = """
NOVA PROJECT BRAIN RUNTIME COACH SMOKE PASSED
NOVA PROJECT BRAIN COMMAND CENTER API SMOKE PASSED
NOVA REGRESSION SMOKE PASSED
[post-frontend-polish-phase 63c159f] Add Project Brain runtime coach
 5 files changed, 842 insertions(+), 7 deletions(-)
PS C:\\Users\\Owner\\nova> git status --short
PS C:\\Users\\Owner\\nova>
"""

    milestone = build_operator_milestone_from_runtime_output(runtime_output)

    assert_true("milestone title", milestone.title == "Project Brain Operator Memory Writer v1", milestone.title)
    assert_true("commit hash parsed", milestone.commit_hash == "63c159f", milestone.commit_hash)
    assert_true("commit message parsed", milestone.commit_message == "Add Project Brain runtime coach", milestone.commit_message)
    assert_true("working tree clean parsed", milestone.working_tree_clean is True, milestone.working_tree_clean)
    assert_true("runtime coach locked", "Project Brain Runtime Coach v1" in milestone.locked_upgrades, milestone.locked_upgrades)
    assert_true("regression smoke parsed", any("REGRESSION" in item for item in milestone.passed_smokes), milestone.passed_smokes)
    assert_true("state update mentions stale cleanup", "stop saying cleanup" in milestone.state_update, milestone.state_update)

    manual = build_operator_milestone(
        commit_hash="abc1234",
        commit_message="Manual test",
        passed_smokes=["NOVA REGRESSION SMOKE PASSED"],
        working_tree_clean=True,
        next_move="Project Brain State Bridge v1",
        locked_upgrades=LOCKED_GANGSTER_STACK,
    )

    assert_true("manual next move", manual.next_move == "Project Brain State Bridge v1", manual.next_move)

    state_text = build_state_update_text(next_move="Project Brain State Bridge v1")
    assert_true("state text includes next", "Project Brain State Bridge v1" in state_text, state_text)

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "operator_memory.json"
        before = load_operator_memory(path)
        assert_true("empty memory", before.get("milestones") == [], before)

        written = write_operator_milestone(milestone, path)
        assert_true("written latest", written.get("latest", {}).get("commit_hash") == "63c159f", written)
        assert_true("written milestone count", len(written.get("milestones", [])) == 1, written)

        written_again = write_operator_milestone(milestone, path)
        assert_true("deduped milestone count", len(written_again.get("milestones", [])) == 1, written_again)

    answer = build_operator_memory_writer_answer(runtime_output)
    assert_true("answer title", "Project Brain Operator Memory Writer" in answer)
    assert_true("answer locked upgrades", "Locked Upgrades" in answer)
    assert_true("answer state update", "State Update" in answer)

    best = select_best_upgrade()
    assert_true("radar best memory writer", best.name == "Project Brain Operator Memory Writer v1", best.name)

    moves = rank_moves("next_move")
    assert_true("operator planner first memory writer", move_value(moves[0], "name") == "Project Brain Operator Memory Writer v1", move_value(moves[0], "name"))

    recommended_move, why, risk, target_files = choose_recommended_move("next_move")
    assert_true("recommended memory writer", recommended_move == "Project Brain Operator Memory Writer v1", recommended_move)
    assert_true("recommended why milestones", "milestones" in why or "state-update" in why, why)
    assert_true("recommended risk medium", risk == "medium", risk)
    assert_true("recommended target file", "nova_backend/services/project_brain_operator_memory_writer.py" in target_files, target_files)

    print("")
    print("NOVA PROJECT BRAIN OPERATOR MEMORY WRITER SMOKE PASSED")


if __name__ == "__main__":
    main()
