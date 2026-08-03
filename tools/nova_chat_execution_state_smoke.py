from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.chat_execution_service import (
    ChatExecutionService,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


def main():
    with TemporaryDirectory() as temp_dir:
        state_path = (
            Path(temp_dir)
            / "execution_state.json"
        )

        service = ChatExecutionService(
            state_path=str(state_path)
        )

        session_id = "execution_state_smoke"

        idle = service.get_state(session_id)

        assert_true(
            "initial_state_idle",
            idle.get("status") == "idle",
            idle,
        )

        started = service.start(
            session_id=session_id,
            goal="Test execution reliability",
            steps=[
                "first step",
                "second step",
            ],
        )

        assert_true(
            "start_state_ready",
            started.get("status") == "ready",
            started,
        )

        assert_true(
            "start_waiting_true",
            started.get("waiting") is True,
            started,
        )

        assert_true(
            "start_current_step_first",
            started.get("current_step")
            == "first step",
            started,
        )

        waiting_restart_service = ChatExecutionService(
            state_path=str(state_path)
        )

        waiting_restart_state = (
            waiting_restart_service.get_state(
                session_id
            )
        )

        assert_true(
            "ready_survives_restart",
            waiting_restart_state.get("status")
            == "ready",
            waiting_restart_state,
        )

        assert_true(
            "ready_restart_preserves_index",
            waiting_restart_state.get(
                "current_index"
            )
            == 0,
            waiting_restart_state,
        )

        assert_true(
            "ready_restart_preserves_step",
            waiting_restart_state.get(
                "current_step"
            )
            == "first step",
            waiting_restart_state,
        )

        first = service.advance(session_id)

        assert_true(
            "first_advance_waiting",
            first.get("status") == "waiting",
            first,
        )

        assert_true(
            "first_advance_index",
            first.get("current_index") == 1,
            first,
        )

        assert_true(
            "first_advance_current_step",
            first.get("current_step")
            == "second step",
            first,
        )

        restarted_waiting_service = (
            ChatExecutionService(
                state_path=str(state_path)
            )
        )

        restarted_waiting = (
            restarted_waiting_service.get_state(
                session_id
            )
        )

        assert_true(
            "waiting_survives_restart",
            restarted_waiting.get("status")
            == "waiting",
            restarted_waiting,
        )

        assert_true(
            "waiting_restart_preserves_index",
            restarted_waiting.get(
                "current_index"
            )
            == 1,
            restarted_waiting,
        )

        assert_true(
            "waiting_restart_preserves_step",
            restarted_waiting.get(
                "current_step"
            )
            == "second step",
            restarted_waiting,
        )

        assert_true(
            "waiting_restart_preserves_history",
            len(
                restarted_waiting.get(
                    "history",
                    [],
                )
            )
            == 1,
            restarted_waiting,
        )

        second = service.advance(session_id)

        assert_true(
            "second_advance_complete",
            second.get("status") == "complete",
            second,
        )

        assert_true(
            "complete_flag_true",
            second.get("complete") is True,
            second,
        )

        assert_true(
            "complete_waiting_false",
            second.get("waiting") is False,
            second,
        )

        assert_true(
            "complete_current_step_none",
            second.get("current_step") is None,
            second,
        )

        complete_again = service.advance(session_id)

        assert_true(
            "complete_is_idempotent",
            complete_again.get("status")
            == "complete",
            complete_again,
        )

        restarted_service = ChatExecutionService(
            state_path=str(state_path)
        )

        restarted_complete = (
            restarted_service.get_state(
                session_id
            )
        )

        assert_true(
            "complete_survives_restart",
            restarted_complete.get("status")
            == "complete",
            restarted_complete,
        )

        assert_true(
            "restart_preserves_goal",
            restarted_complete.get("goal")
            == "Test execution reliability",
            restarted_complete,
        )

        assert_true(
            "restart_preserves_history",
            len(
                restarted_complete.get(
                    "history",
                    [],
                )
            )
            == 2,
            restarted_complete,
        )

        reset = service.reset(session_id)



        assert_true(
            "reset_returns_idle",
            reset.get("status") == "idle",
            reset,
        )

        assert_true(
            "reset_clears_goal",
            reset.get("goal") is None,
            reset,
        )

        print(
            "\nNOVA CHAT EXECUTION STATE "
            "SMOKE PASSED"
        )


if __name__ == "__main__":
    main()