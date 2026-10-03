from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from nova_backend.services.session_service import SessionService


def test_concurrent_message_append_and_metadata_update_preserve_both(tmp_path, monkeypatch):
    service = SessionService(tmp_path / "sessions.json")
    created = service.create_session("Original", user_id="user-a")
    session_id = created["id"]

    first_loaded = Event()
    release_first = Event()
    second_loaded = Event()
    calls_lock = Lock()
    calls = 0
    original_load = service._load_sessions

    def coordinated_load():
        nonlocal calls
        with calls_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            first_loaded.set()
            assert release_first.wait(timeout=3)
        elif call_number == 2:
            second_loaded.set()
        return original_load()

    monkeypatch.setattr(service, "_load_sessions", coordinated_load)

    with ThreadPoolExecutor(max_workers=2) as pool:
        append_future = pool.submit(
            service.append_message,
            session_id,
            {"role": "user", "text": "preserve this message"},
            "user-a",
        )
        assert first_loaded.wait(timeout=3)
        rename_future = pool.submit(
            service.rename,
            session_id,
            "Updated title",
            "user-a",
        )

        # The second transaction must wait until the first has committed.
        assert not second_loaded.wait(timeout=0.05)
        release_first.set()
        assert append_future.result(timeout=3)
        assert rename_future.result(timeout=3)

    persisted = service.get_session(session_id, user_id="user-a")
    assert persisted["title"] == "Updated title"
    assert [message["text"] for message in persisted["messages"]] == [
        "preserve this message"
    ]
