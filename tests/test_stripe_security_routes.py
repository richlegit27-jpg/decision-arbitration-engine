import json

import pytest
from flask import Flask

from nova_backend.routes.payments_routes import register_payments_routes
from nova_backend.services import billing_service, stripe_service


@pytest.fixture
def client():
    app = Flask(__name__)
    app.secret_key = "test-only-session-key"
    register_payments_routes(app)
    test_client = app.test_client()
    with test_client.session_transaction() as state:
        state["nova_user_id"] = "billing-user-1"
        state["username"] = "billing-user"
    return test_client


@pytest.fixture
def isolated_ledger(tmp_path, monkeypatch):
    ledger = tmp_path / "billing-test.json"
    monkeypatch.setattr(billing_service, "BILLING_FILE", ledger)
    return ledger


def test_checkout_ignores_untrusted_origin_and_uses_configured_site_url(
    client,
    isolated_ledger,
    monkeypatch,
):
    captured = {}
    customer_metadata = {}
    monkeypatch.setenv("NOVA_STRIPE_PLUS_PRICE_ID", "price_plus_test")
    monkeypatch.setenv("NOVA_PUBLIC_URL", "https://nova.example.test")
    monkeypatch.setattr(stripe_service, "stripe_is_configured", lambda: True)
    monkeypatch.setattr(
        stripe_service,
        "create_customer",
        lambda **kwargs: customer_metadata.update(kwargs) or {"id": "cus_test"},
    )
    monkeypatch.setattr(
        billing_service,
        "plan_from_price_id",
        lambda _price_id: "plus",
    )

    def create_checkout_session(**kwargs):
        captured.update(kwargs)
        return {"url": "https://checkout.stripe.test/session"}

    monkeypatch.setattr(stripe_service, "create_checkout_session", create_checkout_session)

    response = client.post(
        "/api/billing/checkout",
        json={"plan": "plus"},
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 200
    assert captured["success_url"] == "https://nova.example.test/billing?checkout=success"
    assert captured["cancel_url"] == "https://nova.example.test/billing?checkout=cancelled"
    assert captured["username"] == "billing-user"
    assert captured["user_id"] == "billing-user-1"
    assert customer_metadata["user_id"] == "billing-user-1"


def test_production_checkout_fails_closed_without_configured_public_url(
    client,
    isolated_ledger,
    monkeypatch,
):
    calls = []
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("NOVA_PUBLIC_URL", raising=False)
    monkeypatch.setenv("NOVA_STRIPE_PLUS_PRICE_ID", "price_plus_test")
    monkeypatch.setattr(stripe_service, "stripe_is_configured", lambda: True)
    monkeypatch.setattr(billing_service, "plan_from_price_id", lambda _price_id: "plus")
    monkeypatch.setattr(
        stripe_service,
        "create_customer",
        lambda **_kwargs: calls.append("customer"),
    )

    response = client.post("/api/billing/checkout", json={"plan": "plus"})

    assert response.status_code == 503
    assert calls == []


def test_signed_paid_checkout_webhook_is_persisted_and_duplicate_is_idempotent(
    client,
    isolated_ledger,
    monkeypatch,
):
    event = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "nova_username": "billing-user",
                    "nova_price_id": "price_plus_test",
                },
                "mode": "subscription",
                "payment_status": "paid",
                "subscription": "sub_test_1",
            }
        },
    }
    monkeypatch.setenv("NOVA_STRIPE_PLUS_PRICE_ID", "price_plus_test")
    monkeypatch.setattr(stripe_service, "verify_webhook", lambda _body, _sig: event)
    monkeypatch.setattr(billing_service, "plan_from_price_id", lambda _price: "plus")

    first = client.post(
        "/api/billing/webhook",
        data=b"signed-by-test-provider",
        headers={"Stripe-Signature": "test-signature"},
    )
    second = client.post(
        "/api/billing/webhook",
        data=b"signed-by-test-provider",
        headers={"Stripe-Signature": "test-signature"},
    )

    account = billing_service.get_account(username="billing-user")
    ledger = json.loads(isolated_ledger.read_text(encoding="utf-8"))
    assert first.status_code == 200
    assert first.get_json()["processed"] is True
    assert second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert account["plan"] == "plus"
    assert account["subscription_id"] == "sub_test_1"
    assert ledger["processed_stripe_events"] == ["evt_checkout_1"]


def test_unpaid_checkout_does_not_activate_paid_plan(
    client,
    isolated_ledger,
    monkeypatch,
):
    event = {
        "id": "evt_checkout_unpaid",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "nova_username": "billing-user",
                    "nova_price_id": "price_plus_test",
                },
                "mode": "subscription",
                "payment_status": "unpaid",
                "subscription": "sub_unpaid",
            }
        },
    }
    monkeypatch.setattr(stripe_service, "verify_webhook", lambda _body, _sig: event)
    monkeypatch.setattr(billing_service, "plan_from_price_id", lambda _price: "plus")

    response = client.post(
        "/api/billing/webhook",
        data=b"signed-by-test-provider",
        headers={"Stripe-Signature": "test-signature"},
    )

    assert response.status_code == 200
    assert billing_service.get_account(username="billing-user")["plan"] == "free"


def test_invalid_webhook_signature_is_rejected_without_persisting_event(
    client,
    isolated_ledger,
    monkeypatch,
):
    def reject_signature(_body, _sig):
        raise ValueError("signature verification failed")

    monkeypatch.setattr(stripe_service, "verify_webhook", reject_signature)

    response = client.post(
        "/api/billing/webhook",
        data=b"unsigned-event",
        headers={"Stripe-Signature": "invalid"},
    )

    assert response.status_code == 400
    assert not isolated_ledger.exists()


def test_user_id_metadata_routes_stripe_subscription_to_canonical_billing_account(
    client,
    isolated_ledger,
    monkeypatch,
):
    event = {
        "id": "evt_checkout_user_id_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "nova_username": "billing-user",
                    "nova_user_id": "billing-user-1",
                    "nova_price_id": "price_plus_test",
                },
                "mode": "subscription",
                "payment_status": "paid",
                "subscription": "sub_user_id_test",
            }
        },
    }
    monkeypatch.setenv("NOVA_STRIPE_PLUS_PRICE_ID", "price_plus_test")
    monkeypatch.setattr(stripe_service, "verify_webhook", lambda _body, _sig: event)
    monkeypatch.setattr(billing_service, "plan_from_price_id", lambda _price: "plus")

    response = client.post(
        "/api/billing/webhook",
        data=b"signed-by-test-provider",
        headers={"Stripe-Signature": "test-signature"},
    )

    account = billing_service.get_account(
        username="billing-user",
        user_id="billing-user-1",
    )
    assert response.status_code == 200
    assert account["plan"] == "plus"
    assert account["subscription_id"] == "sub_user_id_test"
    assert account["user_id"] == "billing-user-1"


def test_billing_readiness_api_returns_the_authenticated_user_ledger(
    client,
    isolated_ledger,
):
    billing_service.add_credits(
        user_id="billing-user-1",
        username="billing-user",
        amount=25,
    )

    response = client.get("/api/billing/readiness")

    assert response.status_code == 200
    assert response.get_json()["account"]["credits"] == 10025



def test_subscription_update_reconciles_paid_plan_by_user_id(
    client,
    isolated_ledger,
    monkeypatch,
):
    event = {
        "id": "evt_subscription_updated_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_updated_test",
                "status": "active",
                "metadata": {
                    "nova_username": "billing-user",
                    "nova_user_id": "billing-user-1",
                },
                "items": {
                    "data": [{"price": {"id": "price_pro_test"}}],
                },
            }
        },
    }
    monkeypatch.setenv("NOVA_STRIPE_PRO_PRICE_ID", "price_pro_test")
    monkeypatch.setattr(stripe_service, "verify_webhook", lambda _body, _sig: event)
    monkeypatch.setattr(billing_service, "plan_from_price_id", lambda _price: "pro")

    response = client.post(
        "/api/billing/webhook",
        data=b"signed-by-test-provider",
        headers={"Stripe-Signature": "test-signature"},
    )

    account = billing_service.get_account(
        username="billing-user",
        user_id="billing-user-1",
    )
    assert response.status_code == 200
    assert account["plan"] == "pro"
    assert account["subscription_id"] == "sub_updated_test"
