from __future__ import annotations


def test_session_api_auth_guard_rejects_anonymous_and_ignores_identity_headers(monkeypatch):
    from app import app, session_service

    monkeypatch.setitem(app.config, "SECRET_KEY", "test-only-session-secret")
    client = app.test_client()
    requested_owners = []

    def fake_get_session(session_id, user_id=""):
        requested_owners.append(user_id)
        return {"id": session_id, "messages": []}

    def fake_append_message(session_id, message, user_id=""):
        requested_owners.append(user_id)
        return {"id": session_id}

    monkeypatch.setattr(session_service, "get_session", fake_get_session)
    monkeypatch.setattr(session_service, "append_message", fake_append_message)

    anonymous = client.put(
        "/api/sessions/private-session",
        json={"messages": [{"role": "user", "text": "attempt"}]},
        headers={"X-Nova-User-Id": "victim"},
    )
    assert anonymous.status_code == 401
    assert requested_owners == []

    with client.session_transaction() as state:
        state["nova_user_id"] = "authenticated-user"

    authenticated = client.put(
        "/api/sessions/private-session",
        json={"messages": [{"role": "user", "text": "hello"}]},
        headers={"X-Nova-User-Id": "victim"},
    )

    assert authenticated.status_code == 200
    assert authenticated.get_json()["ok"] is True
    assert requested_owners == ["authenticated-user"] * 3


def test_session_api_auth_guard_covers_session_compatibility_routes():
    from nova_backend.services.auth_context import session_api_auth_required

    protected_paths = (
        "/api/sessions",
        "/api/sessions/new",
        "/api/sessions/private-session",
        "/api/chats",
        "/api/chats/private-session",
        "/api/chat",
        "/api/chat/private-session",
        "/api/mobile/session/persist",
        "/history",
        "/history/private-session",
        "/history/private-session/send",
        "/new-session",
        "/open-session/private-session",
    )
    for path in protected_paths:
        assert session_api_auth_required(path) is True
        assert session_api_auth_required(path, "authenticated-user") is False

    assert session_api_auth_required("/api/chatty") is False


def test_ownerless_legacy_session_requires_explicit_server_migration_owner(monkeypatch):
    from nova_backend.services.session_service import SessionService

    service = SessionService.__new__(SessionService)
    ownerless = {"id": "legacy-session", "user_id": ""}
    monkeypatch.delenv("NOVA_LEGACY_SESSION_OWNER_ID", raising=False)

    assert service._belongs_to_user(ownerless, "user-a") is False

    monkeypatch.setenv("NOVA_LEGACY_SESSION_OWNER_ID", "user-a")
    assert service._belongs_to_user(ownerless, "user-a") is True
    assert service._belongs_to_user(ownerless, "user-b") is False

    owned = {"id": "owned-session", "user_id": "user-b"}
    assert service._belongs_to_user(owned, "user-a") is False
