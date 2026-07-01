import json
import tempfile
from pathlib import Path

from nova_backend.services.project_brain_current_state_adapter import (
    build_project_brain_current_state,
)
from nova_backend.services.project_brain_freshness_snapshot import (
    build_project_brain_freshness_snapshot,
)


DEFAULT_CHECKPOINT = "Default checkpoint from snapshot."
DEFAULT_BLOCKER = "Default blocker with answer freshness and fallback."
DEFAULT_NEXT_MOVE = "Default next concrete move / safe move from snapshot."


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def write_temp_memory(payload):
    directory = tempfile.TemporaryDirectory()
    path = Path(directory.name) / "nova_memory.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory, path


def main():
    print("NOVA PROJECT BRAIN CURRENT STATE ADAPTER SMOKE")
    print("=============================================")

    fresh_memory = {
        "items": [
            {
                "type": "project_state",
                "content": (
                    "Current checkpoint: Adapter smoke checkpoint is active. "
                    "Current blocker: Adapter smoke blocker is active. "
                    "Next move: Adapter smoke next move is active."
                ),
            }
        ]
    }

    directory, path = write_temp_memory(fresh_memory)
    try:
        state = build_project_brain_current_state(
            default_checkpoint=DEFAULT_CHECKPOINT,
            default_blocker=DEFAULT_BLOCKER,
            default_next_move=DEFAULT_NEXT_MOVE,
            memory_path=path,
        )

        assert_true("fresh memory used", state.used_memory, state)
        assert_true("checkpoint extracted", state.checkpoint == "Adapter smoke checkpoint is active.", state.checkpoint)
        assert_true("blocker extracted", state.blocker == "Adapter smoke blocker is active.", state.blocker)
        assert_true("next move extracted", state.next_move == "Adapter smoke next move is active.", state.next_move)

    finally:
        directory.cleanup()

    stale_memory = {
        "items": [
            {
                "type": "project_state",
                "content": (
                    "Current checkpoint: answer-policy intelligence is 100%. "
                    "Current blocker: new blocker is general intelligence routing. "
                    "Next move: make `what's next?` return project context."
                ),
            }
        ]
    }

    directory, path = write_temp_memory(stale_memory)
    try:
        state = build_project_brain_current_state(
            default_checkpoint=DEFAULT_CHECKPOINT,
            default_blocker=DEFAULT_BLOCKER,
            default_next_move=DEFAULT_NEXT_MOVE,
            memory_path=path,
        )

        assert_true("stale memory rejected", not state.used_memory, state)
        assert_true("stale checkpoint defaulted", state.checkpoint == DEFAULT_CHECKPOINT, state.checkpoint)
        assert_true("stale blocker defaulted", state.blocker == DEFAULT_BLOCKER, state.blocker)
        assert_true("stale next move defaulted", state.next_move == DEFAULT_NEXT_MOVE, state.next_move)
        assert_true("stale values recorded", len(state.ignored_stale_values) >= 1, state.ignored_stale_values)

    finally:
        directory.cleanup()

    snapshot = build_project_brain_freshness_snapshot()

    assert_true("snapshot checkpoint exists", bool(snapshot.checkpoint), snapshot)
    assert_true("snapshot blocker has answer freshness", "answer freshness" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("snapshot blocker has fallback", "fallback" in snapshot.blocker.lower(), snapshot.blocker)
    assert_true("snapshot next has safe move", "safe move" in snapshot.next_move.lower(), snapshot.next_move)
    assert_true("snapshot validation exists", any("git status --short" in command for command in snapshot.validation), snapshot.validation)

    print("")
    print("NOVA PROJECT BRAIN CURRENT STATE ADAPTER SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
