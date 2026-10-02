import json
import time
from pathlib import Path

import bcrypt
import pyotp
import pytest
from flask import Flask, jsonify, request, session
from cryptography.fernet import Fernet

from nova_backend.services.local_auth_route_service import LocalAuthRouteService
from nova_backend.services.login_page_route_service import LoginPageRouteService
from nova_backend.services.mfa_service import hash_recovery_code


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "NOVA_MFA_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parents[1] / "templates"),
    )
    app.secret_key = "test-only-session-key"
    app.config.update(TESTING=True)

    service = object.__new__(LocalAuthRouteService)
    service.app = app
    service.request = request
    service.jsonify = jsonify
    service.session = session
    service.data_dir = tmp_path
    service.users_path = tmp_path / "users.json"
    app.config["NOVA_AUTH_USERS_PATH"] = service.users_path
    service.install_routes()
    LoginPageRouteService().install_routes(app)
    return app.test_client(), service


def write_users(service, users):
    service.users_path.write_text(
        json.dumps({"users": users}),
        encoding="utf-8",
    )


def test_mfa_login_accepts_totp_once_and_persists_counter(auth_client):
    client, service = auth_client
    secret = pyotp.random_base32()
    user = {
        "id": "mfa-user",
        "username": "mfa-user",
        "email": "mfa@example.test",
        "mfa_enabled": True,
        "mfa_secret": secret,
        "mfa_last_counter": -1,
    }
    write_users(service, [user])
    code = pyotp.TOTP(secret).now()
    with client.session_transaction() as state:
        state["nova_pending_mfa_user_id"] = user["id"]
        state["nova_pending_mfa_at"] = time.time()

    accepted = client.post("/api/auth/mfa/verify-login", json={"code": code})
    persisted = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]

    assert accepted.status_code == 200
    assert accepted.get_json()["authenticated"] is True
    assert persisted["mfa_last_counter"] >= 0

    replay_client = client.application.test_client()
    with replay_client.session_transaction() as state:
        state["nova_pending_mfa_user_id"] = user["id"]
        state["nova_pending_mfa_at"] = time.time()
    replay = replay_client.post("/api/auth/mfa/verify-login", json={"code": code})

    assert replay.status_code == 401
    assert replay.get_json()["ok"] is False
    with replay_client.session_transaction() as state:
        assert "nova_user_id" not in state


def test_recovery_code_is_consumed_on_successful_mfa_login(auth_client):
    client, service = auth_client
    recovery_code = "abc123-recovery-code"
    user = {
        "id": "mfa-user",
        "username": "mfa-user",
        "mfa_enabled": True,
        "mfa_secret": pyotp.random_base32(),
        "mfa_recovery_code_hashes": [hash_recovery_code(recovery_code)],
    }
    write_users(service, [user])
    with client.session_transaction() as state:
        state["nova_pending_mfa_user_id"] = user["id"]
        state["nova_pending_mfa_at"] = time.time()

    response = client.post(
        "/api/auth/mfa/verify-login",
        json={"code": recovery_code},
    )

    persisted = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]
    assert response.status_code == 200
    assert persisted["mfa_recovery_code_hashes"] == []

    replay_client = client.application.test_client()
    with replay_client.session_transaction() as state:
        state["nova_pending_mfa_user_id"] = user["id"]
        state["nova_pending_mfa_at"] = time.time()
    replay = replay_client.post(
        "/api/auth/mfa/verify-login",
        json={"code": recovery_code},
    )
    assert replay.status_code == 401


def test_mfa_enrollment_is_pending_until_verified_and_issues_hashed_recovery_codes(auth_client):
    client, service = auth_client
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode("utf-8")
    write_users(service, [{
        "id": "mfa-user",
        "username": "mfa-user",
        "mfa_enabled": False,
        "password_hash": password_hash,
    }])
    with client.session_transaction() as state:
        state["nova_user_id"] = "mfa-user"
        state["authenticated"] = True

    setup = client.post(
        "/api/auth/mfa/setup",
        json={"current_password": "test-password"},
    )
    assert setup.get_json()["qr_data_url"].startswith("data:image/png;base64,")
    setup_user = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]
    assert setup.status_code == 200
    assert setup_user["mfa_enabled"] is False
    assert "mfa_pending_secret" in setup_user
    assert "mfa_secret" not in setup_user

    code = pyotp.TOTP(setup.get_json()["secret"]).now()
    verified = client.post("/api/auth/mfa/verify-setup", json={"code": code})
    persisted = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]

    assert verified.status_code == 200
    assert persisted["mfa_enabled"] is True
    assert persisted["mfa_secret"].startswith("fernet:")
    assert "mfa_recovery_code_hashes" in persisted
    assert len(verified.get_json()["recovery_codes"]) == 10
    assert all(code not in persisted["mfa_recovery_code_hashes"] for code in verified.get_json()["recovery_codes"])


def test_mfa_enrollment_requires_current_password(auth_client):
    client, service = auth_client
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode("utf-8")
    write_users(service, [{
        "id": "mfa-user",
        "username": "mfa-user",
        "mfa_enabled": False,
        "password_hash": password_hash,
    }])
    with client.session_transaction() as state:
        state["nova_user_id"] = "mfa-user"

    response = client.post(
        "/api/auth/mfa/setup",
        json={"current_password": "wrong-password"},
    )
    persisted = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]

    assert response.status_code == 403
    assert "mfa_pending_secret" not in persisted


def test_password_reset_token_is_hashed_at_rest_and_single_use(auth_client):
    client, service = auth_client
    write_users(service, [{
        "id": "reset-user",
        "username": "reset-user",
        "email": "reset@example.test",
        "password_hash": "old-hash",
    }])

    issued = client.post(
        "/api/auth/password-reset/request",
        json={"email": "reset@example.test"},
    )
    token = issued.get_json()["token"]
    stored = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]

    assert issued.status_code == 200
    assert stored["password_reset_token_hash"]
    assert "password_reset_token" not in stored
    assert token not in json.dumps(stored)

    confirmed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "a-long-test-password"},
    )
    persisted = json.loads(service.users_path.read_text(encoding="utf-8"))["users"][0]
    reused = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "another-test-password"},
    )

    assert confirmed.status_code == 200
    assert "password_reset_token_hash" not in persisted
    assert reused.status_code == 400


def test_account_security_page_requires_ownership_and_renders_for_signed_in_user(auth_client):
    client, service = auth_client
    write_users(service, [{
        "id": "account-user",
        "username": "account-user",
        "auth_provider": "local",
        "mfa_enabled": False,
        "password_hash": "private-password-hash",
        "mfa_secret": "private-totp-secret",
    }])

    anonymous = client.get("/account")
    assert anonymous.status_code == 302
    assert anonymous.headers["Location"] == "/login"

    with client.session_transaction() as state:
        state["nova_user_id"] = "someone-else"
    non_owner = client.get("/account")
    assert non_owner.status_code == 302

    with client.session_transaction() as state:
        state["nova_user_id"] = "account-user"
    account = client.get("/account")

    assert account.status_code == 200
    assert b"Two-factor authentication" in account.data
    assert b"Verify and link Google" in account.data
    assert b"private-password-hash" not in account.data
    assert b"private-totp-secret" not in account.data


def test_registration_does_not_authenticate_before_email_verification(auth_client):
    client, service = auth_client
    response = client.post(
        "/api/auth/register",
        json={
            "username": "new-user",
            "email": "new-user@example.test",
            "password": "a-long-test-password",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["email_verification_required"] is True
    assert payload["authenticated"] is False
    with client.session_transaction() as state:
        assert "nova_user_id" not in state

    denied = client.post(
        "/api/auth/login",
        json={"username": "new-user", "password": "a-long-test-password"},
    )
    assert denied.status_code == 403
    assert denied.get_json()["email_verification_required"] is True

    token = payload["verification_url"].split("token=", 1)[1]
    verified = client.post("/api/auth/verify-email", json={"token": token})
    assert verified.status_code == 200

    logged_in = client.post(
        "/api/auth/login",
        json={"username": "new-user", "password": "a-long-test-password"},
    )
    assert logged_in.status_code == 200
    assert logged_in.get_json()["authenticated"] is True


def test_registration_never_discloses_verification_token_in_production_mode(auth_client):
    client, _service = auth_client
    client.application.testing = False

    response = client.post(
        "/api/auth/register",
        json={
            "username": "secure-user",
            "email": "secure-user@example.test",
            "password": "a-long-test-password",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["email_verification_required"] is True
    assert "verification_url" not in response.get_json()


def test_password_login_hash_verification_and_logout(auth_client):
    client, service = auth_client
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode("utf-8")
    write_users(service, [{
        "id": "login-user",
        "username": "login-user",
        "email": "login@example.test",
        "email_verified": True,
        "password_hash": password_hash,
    }])

    rejected = client.post(
        "/api/auth/login",
        json={"username": "login-user", "password": "incorrect-password"},
    )
    assert rejected.status_code == 401
    with client.session_transaction() as state:
        assert "nova_user_id" not in state

    accepted = client.post(
        "/api/auth/login",
        json={"username": "login-user", "password": "test-password"},
    )
    assert accepted.status_code == 200
    assert accepted.get_json()["authenticated"] is True
    with client.session_transaction() as state:
        assert state["nova_user_id"] == "login-user"

    logged_out = client.post("/api/auth/logout")
    assert logged_out.status_code == 200
    assert logged_out.get_json()["authenticated"] is False
    with client.session_transaction() as state:
        assert "nova_user_id" not in state


def test_password_login_cannot_bypass_mfa_challenge(auth_client):
    client, service = auth_client
    secret = pyotp.random_base32()
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode("utf-8")
    write_users(service, [{
        "id": "mfa-login-user",
        "username": "mfa-login-user",
        "email_verified": True,
        "password_hash": password_hash,
        "mfa_enabled": True,
        "mfa_secret": secret,
        "mfa_last_counter": -1,
    }])

    login = client.post(
        "/api/auth/login",
        json={"username": "mfa-login-user", "password": "test-password"},
    )
    assert login.status_code == 200
    assert login.get_json()["mfa_required"] is True
    assert login.get_json()["authenticated"] is False
    with client.session_transaction() as state:
        assert state.get("nova_pending_mfa_user_id") == "mfa-login-user"
        assert "nova_user_id" not in state

    rejected_factor = client.post(
        "/api/auth/mfa/verify-login",
        json={"code": "not-a-code"},
    )
    assert rejected_factor.status_code == 401
    with client.session_transaction() as state:
        assert "nova_user_id" not in state

    accepted_factor = client.post(
        "/api/auth/mfa/verify-login",
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert accepted_factor.status_code == 200
    assert accepted_factor.get_json()["authenticated"] is True


def test_auth_user_credit_fields_match_canonical_billing_ledger(
    auth_client,
    tmp_path,
    monkeypatch,
):
    client, service = auth_client
    from nova_backend.services import billing_service

    monkeypatch.setattr(
        billing_service,
        "BILLING_FILE",
        tmp_path / "billing.json",
    )
    billing_service.add_credits(
        user_id="credits-user",
        username="credits-user",
        amount=17,
    )
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode("utf-8")
    write_users(service, [{
        "id": "credits-user",
        "username": "credits-user",
        "email_verified": True,
        "password_hash": password_hash,
        "plan": "pro",
        "credits": 999999,
    }])

    response = client.post(
        "/api/auth/login",
        json={"username": "credits-user", "password": "test-password"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["plan"] == "free"
    assert response.get_json()["user"]["credits"] == 10017
