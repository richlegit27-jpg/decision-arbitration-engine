import json
import bcrypt

import pytest
from flask import Flask, redirect

from nova_backend.services.google_auth_route_service import (
    GoogleAuthRouteService,
)


class FakeGoogleClient:
    def __init__(self, profile=None):
        self.profile = profile or {
            "sub": "google-subject-1",
            "email": "person@example.test",
            "email_verified": True,
            "name": "Example Person",
        }
        self.redirect_uri = None
        self.nonce = None
        self.parsed_nonce = None

    def authorize_redirect(self, redirect_uri, nonce):
        self.redirect_uri = redirect_uri
        self.nonce = nonce
        return redirect("https://accounts.google.test/authorize")

    def authorize_access_token(self):
        return {"id_token": "test-token"}

    def parse_id_token(self, token, nonce):
        self.parsed_nonce = nonce
        return self.profile


@pytest.fixture
def auth_client(tmp_path):
    app = Flask(__name__)
    app.secret_key = "test-only-session-key"
    app.config.update(
        TESTING=True,
        GOOGLE_REDIRECT_URI="https://nova.example.test/api/auth/google/callback",
    )
    google = FakeGoogleClient()
    service = GoogleAuthRouteService(app, type("GoogleService", (), {"google": google})())
    service.users_path = tmp_path / "users.json"
    service.install_routes()
    return app.test_client(), service, google


def test_google_login_uses_configured_https_callback_and_nonce(auth_client):
    client, _, google = auth_client

    response = client.get("/api/auth/google")

    assert response.status_code == 302
    assert google.redirect_uri == "https://nova.example.test/api/auth/google/callback"
    assert google.nonce
    with client.session_transaction() as state:
        assert state["oauth_nonce"] == google.nonce


def test_google_callback_refuses_missing_nonce(auth_client):
    client, _, google = auth_client

    response = client.get("/api/auth/google/callback")

    assert response.status_code == 400
    assert google.parsed_nonce is None


def test_google_callback_requires_verified_stable_identity(auth_client):
    client, service, google = auth_client
    google.profile = {
        "sub": "google-subject-1",
        "email": "person@example.test",
        "email_verified": False,
    }
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    response = client.get("/api/auth/google/callback")

    assert response.status_code == 401
    assert not service.users_path.exists()


def test_google_callback_does_not_link_by_email_alone(auth_client):
    client, service, google = auth_client
    service.users_path.write_text(
        json.dumps({"users": [{"id": "local-1", "email": "PERSON@example.test", "username": "person"}]}),
        encoding="utf-8",
    )
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    response = client.get("/api/auth/google/callback")

    assert response.status_code == 409
    assert response.get_json()["account_link_required"] is True
    assert json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]["id"] == "local-1"


def test_google_callback_creates_and_reuses_account_by_subject(auth_client):
    client, service, google = auth_client
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    first = client.get("/api/auth/google/callback")

    assert first.status_code == 302
    assert first.headers["Location"] == "/app"
    stored_user = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]
    assert stored_user["google_sub"] == "google-subject-1"
    assert stored_user["email_verified"] is True
    assert google.parsed_nonce == "expected-nonce"

    google.profile = {
        "sub": "google-subject-1",
        "email": "renamed@example.test",
        "email_verified": True,
        "name": "Updated Name",
    }
    with client.session_transaction() as state:
        state["oauth_nonce"] = "second-nonce"
    second = client.get("/api/auth/google/callback")

    users = json.loads(service.users_path.read_text(encoding="utf-8"))["users"]
    assert second.status_code == 302
    assert second.headers["Location"] == "/app"
    assert users[0]["id"] == stored_user["id"]
    assert len(users) == 1


def test_google_callback_requires_nova_mfa_for_mfa_enabled_user(auth_client):
    client, service, _ = auth_client
    service.users_path.write_text(
        json.dumps({
            "users": [{
                "id": "google-user-1",
                "username": "person",
                "email": "person@example.test",
                "google_sub": "google-subject-1",
                "auth_provider": "google",
                "mfa_enabled": True,
            }]
        }),
        encoding="utf-8",
    )
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    response = client.get("/api/auth/google/callback")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?mfa=required"
    with client.session_transaction() as state:
        assert state["nova_pending_mfa_user_id"] == "google-user-1"
        assert "nova_user_id" not in state


def test_google_callback_never_returns_secret_account_fields(auth_client):
    client, service, _ = auth_client
    service.users_path.write_text(
        json.dumps({
            "users": [{
                "id": "google-user-1",
                "username": "person",
                "email": "person@example.test",
                "google_sub": "google-subject-1",
                "auth_provider": "google",
                "password_hash": "stored-hash",
                "mfa_secret": "stored-totp-secret",
                "mfa_recovery_code_hashes": ["stored-recovery-hash"],
            }]
        }),
        encoding="utf-8",
    )
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    response = client.get("/api/auth/google/callback")

    assert response.status_code == 302
    assert response.headers["Location"] == "/app"
    with client.session_transaction() as state:
        assert state["nova_user_id"] == "google-user-1"
        assert not {"password_hash", "mfa_secret", "mfa_recovery_code_hashes"} & set(state)


def test_google_account_link_requires_password_and_keeps_existing_account(auth_client):
    client, service, _ = auth_client
    password_hash = bcrypt.hashpw(b"local-password", bcrypt.gensalt()).decode("utf-8")
    service.users_path.write_text(
        json.dumps({
            "users": [{
                "id": "local-user-1",
                "username": "person",
                "email": "person@example.test",
                "auth_provider": "local",
                "password_hash": password_hash,
                "plan": "pro",
            }]
        }),
        encoding="utf-8",
    )
    with client.session_transaction() as state:
        state["nova_user_id"] = "local-user-1"
        state["username"] = "person"

    denied = client.post(
        "/api/auth/google/link",
        data={"current_password": "wrong-password"},
    )
    assert denied.status_code == 403
    with client.session_transaction() as state:
        assert "oauth_link_user_id" not in state

    started = client.post(
        "/api/auth/google/link",
        data={"current_password": "local-password"},
    )
    assert started.status_code == 302
    with client.session_transaction() as state:
        assert state["oauth_link_user_id"] == "local-user-1"
        state["oauth_nonce"] = "link-nonce"

    completed = client.get("/api/auth/google/callback")
    users = json.loads(service.users_path.read_text(encoding="utf-8"))["users"]

    assert completed.status_code == 302
    assert completed.headers["Location"] == "/account?google=linked"
    assert len(users) == 1
    assert users[0]["id"] == "local-user-1"
    assert users[0]["google_sub"] == "google-subject-1"
    assert users[0]["plan"] == "pro"
    with client.session_transaction() as state:
        assert state["nova_user_id"] == "local-user-1"
        assert state["auth_mode"] == "local"


def test_google_identity_already_linked_to_another_user_cannot_be_taken(auth_client):
    client, service, _ = auth_client
    password_hash = bcrypt.hashpw(b"local-password", bcrypt.gensalt()).decode("utf-8")
    service.users_path.write_text(
        json.dumps({
            "users": [
                {"id": "local-user-1", "username": "first", "email": "first@example.test", "auth_provider": "local", "password_hash": password_hash},
                {"id": "google-user-1", "username": "person", "email": "person@example.test", "auth_provider": "google", "google_sub": "google-subject-1"},
            ]
        }),
        encoding="utf-8",
    )
    with client.session_transaction() as state:
        state["nova_user_id"] = "local-user-1"
    started = client.post(
        "/api/auth/google/link",
        data={"current_password": "local-password"},
    )
    assert started.status_code == 302
    with client.session_transaction() as state:
        state["oauth_nonce"] = "expected-nonce"

    response = client.get("/api/auth/google/callback")
    users = json.loads(service.users_path.read_text(encoding="utf-8"))["users"]

    assert response.status_code == 409
    assert [user.get("google_sub") for user in users] == [None, "google-subject-1"]


def test_production_google_login_requires_configured_https_redirect(auth_client, monkeypatch):
    client, _, _ = auth_client
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    client.application.config.pop("GOOGLE_REDIRECT_URI")

    response = client.get("/api/auth/google")

    assert response.status_code == 503


def test_unconfigured_google_login_fails_with_service_unavailable():
    app = Flask(__name__)
    app.secret_key = "test-only-session-key"
    service = GoogleAuthRouteService(
        app,
        type("GoogleService", (), {"google": None})(),
    )
    service.install_routes()

    response = app.test_client().get("/api/auth/google")

    assert response.status_code == 503
