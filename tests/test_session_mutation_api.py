from __future__ import annotations

import json

import pytest


@pytest.fixture
def isolated_session_api(monkeypatch, tmp_path):
    from app import app, session_service
    from nova_backend.services import session_auth_scope_service

    store_path = tmp_path / "nova_sessions.json"
    monkeypatch.setattr(session_service, "sessions_file", store_path)
    monkeypatch.setattr(session_auth_scope_service, "sessions_path", store_path)
    monkeypatch.setattr(session_auth_scope_service, "users_path", tmp_path / "users.json")
    monkeypatch.setitem(app.config, "SECRET_KEY", "session-mutation-test-secret")

    sessions = [
        {"id": "a-active", "user_id": "user-a", "title": "A active", "pinned": False, "messages": []},
        {"id": "b-other", "user_id": "user-b", "title": "B private", "pinned": False, "messages": []},
        {"id": "a-next", "user_id": "user-a", "title": "A next", "pinned": False, "messages": []},
    ]
    session_service._write_store({"active_session_id": "a-active", "sessions": sessions})
    return app.test_client(), session_service, store_path


def _login(client, user_id):
    with client.session_transaction() as state:
        state["nova_user_id"] = user_id


def _saved_sessions(path):
    return json.loads(path.read_text(encoding="utf-8"))["sessions"]


def test_authenticated_owner_can_rename_pin_unpin_and_delete(isolated_session_api):
    client, _service, store_path = isolated_session_api
    _login(client, "user-a")

    renamed = client.post("/api/sessions/rename", json={"session_id": "a-active", "title": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.get_json()["session"]["title"] == "Renamed"
    assert next(s for s in _saved_sessions(store_path) if s["id"] == "a-active")["title"] == "Renamed"
    refreshed = client.get("/api/sessions")
    assert next(s for s in refreshed.get_json()["sessions"] if s["id"] == "a-active")["title"] == "Renamed"

    pinned = client.post("/api/sessions/pin", json={"session_id": "a-active", "pinned": True})
    assert pinned.status_code == 200
    assert next(s for s in _saved_sessions(store_path) if s["id"] == "a-active")["pinned"] is True

    unpinned = client.post("/api/sessions/pin", json={"session_id": "a-active", "pinned": False})
    assert unpinned.status_code == 200
    assert next(s for s in _saved_sessions(store_path) if s["id"] == "a-active")["pinned"] is False

    deleted = client.post("/api/sessions/delete", json={"session_id": "a-active"})
    assert deleted.status_code == 200
    assert {s["id"] for s in _saved_sessions(store_path)} == {"b-other", "a-next"}
    assert deleted.get_json()["active_session_id"] == "a-next"
    assert next(s for s in _saved_sessions(store_path) if s["id"] == "b-other")["title"] == "B private"
    refreshed = client.get("/api/sessions")
    assert {s["id"] for s in refreshed.get_json()["sessions"]} == {"a-next"}


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/sessions/rename", {"session_id": "b-other", "title": "stolen"}),
        ("/api/sessions/pin", {"session_id": "b-other", "pinned": True}),
        ("/api/sessions/delete", {"session_id": "b-other"}),
    ],
)
def test_cross_user_mutations_are_not_applied(isolated_session_api, path, payload):
    client, _service, store_path = isolated_session_api
    _login(client, "user-a")

    response = client.post(path, json=payload)

    assert response.status_code == 404
    other = next(s for s in _saved_sessions(store_path) if s["id"] == "b-other")
    assert other["title"] == "B private"
    assert other["pinned"] is False


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/sessions/rename", {"session_id": "a-active", "title": "anonymous"}),
        ("/api/sessions/pin", {"session_id": "a-active", "pinned": True}),
        ("/api/sessions/delete", {"session_id": "a-active"}),
    ],
)
def test_anonymous_mutations_are_rejected(isolated_session_api, path, payload):
    client, _service, store_path = isolated_session_api

    response = client.post(path, json=payload, headers={"X-Nova-User-Id": "user-a"})

    assert response.status_code == 401
    sessions = _saved_sessions(store_path)
    active = next(s for s in sessions if s["id"] == "a-active")
    assert active["title"] == "A active"
    assert active["pinned"] is False
