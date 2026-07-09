
import json
import tempfile
from pathlib import Path

from nova_backend.services.project_brain_state_recall_refresh import (
    PROJECT_STATE_ROUTE,
    answer_has_stale_cleanup,
    build_state_recall_refresh_answer,
    load_state_bridge_text,
    refresh_project_state_payload,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PROJECT BRAIN STATE RECALL REFRESH SMOKE")
    print("=============================================")

    state_text = (
        "Current Nova project state: Richard is working on the local Nova Flask app with Joe. "
        "Current checkpoint: Project Brain gangster intelligence stack is locked through Project Brain State Bridge v1. "
        "Current blocker: No active Project Brain intelligence blocker is open. "
        "Next move: Project Brain State Recall Refresh v1. "
        "Direct project-state recall should use this State Bridge record instead of stale cleanup wording."
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = Path(temp_dir) / "nova_memory.json"
        memory_path.write_text(
            json.dumps({
                "memories": [
                    {
                        "id": "old_project_state",
                        "source": "old_project_state",
                        "text": "Next move: Start Project Brain cleanup/consolidation",
                    },
                    {
                        "id": "project_brain_state_bridge_current",
                        "source": "project_brain_state_bridge",
                        "tags": ["project_state", "state_bridge"],
                        "text": state_text,
                    },
                ]
            }, indent=2),
            encoding="utf-8",
        )

        loaded = load_state_bridge_text(memory_path)
        assert_true("loads state bridge text", loaded == state_text, loaded)
        assert_true("detects stale cleanup", answer_has_stale_cleanup("Next move: Start Project Brain cleanup/consolidation"))

        payload = {
            "debug": {
                "route_taken": PROJECT_STATE_ROUTE,
            },
            "route": PROJECT_STATE_ROUTE,
            "assistant_message": {
                "text": "Next move: Start Project Brain cleanup/consolidation",
                "content": "Next move: Start Project Brain cleanup/consolidation",
            },
            "text": "Next move: Start Project Brain cleanup/consolidation",
        }

        refreshed = refresh_project_state_payload(payload, memory_path=memory_path)

        assert_true("refresh preserves route", refreshed["debug"]["route_taken"] == PROJECT_STATE_ROUTE, refreshed)
        assert_true("refresh marker", refreshed["debug"]["project_brain_state_recall_refresh"] is True, refreshed)
        assert_true("assistant text refreshed", refreshed["assistant_message"]["text"] == state_text, refreshed)
        assert_true("top text refreshed", refreshed["text"] == state_text, refreshed)
        assert_true("stale cleanup removed", "Start Project Brain cleanup/consolidation" not in refreshed["text"], refreshed["text"])
        assert_true("next move refreshed", "Next move: Project Brain State Recall Refresh v1" in refreshed["text"], refreshed["text"])

        general_payload = {
            "debug": {
                "route_taken": "project_brain_general_intelligence",
                "compact_project_context_delegated": True,
            },
            "route": "project_brain_general_intelligence",
            "intent": "general_project_answer",
            "compact_project_context_delegated": True,
            "assistant_message": {
                "text": "Remaining risk: Start Project Brain cleanup/consolidation",
                "content": "Remaining risk: Start Project Brain cleanup/consolidation",
            },
            "text": "Remaining risk: Start Project Brain cleanup/consolidation",
        }

        general_refreshed = refresh_project_state_payload(general_payload, memory_path=memory_path)
        assert_true("general intelligence route untouched", general_refreshed == general_payload, general_refreshed)


        normal_payload = {
            "debug": {"route_taken": "chat"},
            "assistant_message": {"text": "normal chat"},
            "text": "normal chat",
        }
        normal_refreshed = refresh_project_state_payload(normal_payload, memory_path=memory_path)
        assert_true("normal chat untouched", normal_refreshed == normal_payload, normal_refreshed)

        answer = build_state_recall_refresh_answer(memory_path)
        assert_true("answer title", "Project Brain State Recall Refresh" in answer, answer)
        assert_true("answer source", "project_brain_state_bridge" in answer, answer)

    print("")
    print("NOVA PROJECT BRAIN STATE RECALL REFRESH SMOKE PASSED")


if __name__ == "__main__":
    main()
