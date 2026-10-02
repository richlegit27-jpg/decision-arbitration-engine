import json

from flask import Flask, session

from nova_backend.services import billing_service
from nova_backend.services.account_profile_service import AccountProfileService


def make_service(tmp_path, monkeypatch):
    users_path = tmp_path / "users.json"
    users_path.write_text(
        json.dumps({
            "users": [
                {"id": "user-a", "username": "alice"},
                {"id": "user-b", "username": "richard"},
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        billing_service,
        "BILLING_FILE",
        tmp_path / "billing.json",
    )
    billing_service.add_credits(user_id="user-a", username="alice", amount=120)
    billing_service.add_credits(user_id="user-b", username="richard", amount=900)

    app = Flask(__name__)
    app.secret_key = "test-session-secret"
    return app, AccountProfileService(users_path=users_path)


def test_account_profile_rejects_anonymous_without_mutating_billing(
    tmp_path,
    monkeypatch,
):
    app, service = make_service(tmp_path, monkeypatch)
    billing_path = billing_service.BILLING_FILE
    before = billing_path.read_bytes()

    with app.test_request_context("/api/account"):
        response, status = service.get_profile()

    assert status == 401
    assert response.get_json()["ok"] is False
    assert billing_path.read_bytes() == before


def test_account_profile_reads_only_the_authenticated_user_billing_identity(
    tmp_path,
    monkeypatch,
):
    app, service = make_service(tmp_path, monkeypatch)
    with app.test_request_context("/api/account"):
        session["nova_user_id"] = "user-a"
        session["username"] = "richard"  # Session username is not the account authority.
        response = service.get_profile()

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["username"] == "alice"
    assert payload["credits"] == 10120


def test_account_profile_rejects_stale_authenticated_identity(
    tmp_path,
    monkeypatch,
):
    app, service = make_service(tmp_path, monkeypatch)
    with app.test_request_context("/api/account"):
        session["nova_user_id"] = "deleted-user"
        session["username"] = "richard"
        response, status = service.get_profile()

    assert status == 401
    assert response.get_json()["ok"] is False

