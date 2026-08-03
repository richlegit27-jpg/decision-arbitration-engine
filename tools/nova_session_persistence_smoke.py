from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.session_service import (
    SessionService,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


def main():
    with TemporaryDirectory() as temp_dir:
        sessions_file = (
            Path(temp_dir)
            / "sessions.json"
        )

        service = SessionService(
            sessions_file=sessions_file
        )

        created = service.create_session(
            title="Persistence Test",
            user_id="user_test",
        )

        session_id = created["id"]

        service.append_message(
            session_id,
            {
                "role": "user",
                "text": "Remember this message",
            },
            user_id="user_test",
        )
        service.update_working_state(
            session_id,
            {
                "active_task": "Test session restart",
                "current_file": "session_service.py",
                "next_move": "Reload the service",
            },
        )

        restarted = SessionService(
            sessions_file=sessions_file
        )

        restored = restarted.get_session(
            session_id,
            user_id="user_test",
        )

        assert_true(
            "session_survives_restart",
            isinstance(restored, dict),
            restored,
        )

        assert_true(
            "session_title_preserved",
            restored.get("title")
            == "Persistence Test",
            restored,
        )

        assert_true(
            "session_message_preserved",
            any(
                message.get("text")
                == "Remember this message"
                for message in restored.get(
                    "messages",
                    [],
                )
            ),
            restored,
        )

        working_state = (
            restored.get("working_state")
            or {}
        )

        assert_true(
            "working_state_preserved",
            working_state.get("active_task")
            == "Test session restart",
            working_state,
        )

        assert_true(
            "working_file_preserved",
            working_state.get("current_file")
            == "session_service.py",
            working_state,
        )

        assert_true(
            "next_move_preserved",
            working_state.get("next_move")
            == "Reload the service",
            working_state,
        )

        session_a = service.create_session(
            title="Session A",
            user_id="user_test",
        )

        session_b = service.create_session(
            title="Session B",
            user_id="user_test",
        )

        session_a_id = session_a["id"]
        session_b_id = session_b["id"]

        active_b = service.set_active(
            session_b_id,
            user_id="user_test",
        )

        assert_true(
            "session_b_set_active",
            isinstance(active_b, dict),
            active_b,
        )

        restarted_active_service = SessionService(
            sessions_file=sessions_file
        )

        assert_true(
            "active_session_survives_restart",
            restarted_active_service.get_active_session_id()
            == session_b_id,
            restarted_active_service.get_active_session_id(),
        )

        deleted = restarted_active_service.delete(
            session_b_id,
            user_id="user_test",
        )

        assert_true(
            "active_session_deleted",
            deleted is True,
            deleted,
        )

        restarted_after_delete = SessionService(
            sessions_file=sessions_file
        )

        assert_true(
            "deleted_session_stays_deleted",
            restarted_after_delete.get_session(
                session_b_id,
                user_id="user_test",
            )
            is None,
            session_b_id,
        )

        fallback_active_id = (
            restarted_after_delete.get_active_session_id()
        )

        assert_true(
            "active_session_falls_back",
            fallback_active_id != session_b_id,
            fallback_active_id,
        )

        restored_session_a = (
            restarted_after_delete.get_session(
                session_a_id,
                user_id="user_test",
            )
        )

        assert_true(
            "fallback_session_exists",
            isinstance(restored_session_a, dict),
            restored_session_a,
        )

        print(
            "\nNOVA SESSION PERSISTENCE "
            "SMOKE PASSED"
        )


if __name__ == "__main__":
    main()