
import json

import pytest

from nova_backend.services import billing_service as billing


@pytest.fixture
def isolated_billing_file(tmp_path, monkeypatch):
    """Use an isolated ledger and deterministic zero-credit defaults."""
    ledger = tmp_path / "nova_billing_test.json"

    monkeypatch.setattr(billing, "BILLING_FILE", ledger)
    monkeypatch.setattr(
        billing,
        "DEFAULT_USER",
        {
            **billing.DEFAULT_USER,
            "credits": 0,
        },
    )

    return ledger


def test_gateway_rejected_billing_does_not_record_usage(monkeypatch):
    from types import SimpleNamespace

    from nova_backend.services import billing_service as billing_module
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service as usage_module

    recorded = []

    monkeypatch.setattr(
        billing_module,
        "consume_usage",
        lambda **kwargs: {
            "ok": False,
            "reason": "insufficient credits",
        },
    )
    monkeypatch.setattr(
        usage_module,
        "record_model_usage",
        lambda **kwargs: recorded.append(kwargs),
    )

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    with pytest.raises(RuntimeError, match="insufficient credits"):
        gateway._nova_consume_and_record_usage(
            user_id="gateway-test-user",
            username="gateway-test-user",
            session_id="gateway-test-session",
            model="gpt-4o-mini",
            messages=[],
            response=response,
            enforce=True,
        )

    assert recorded == []

def test_consume_usage_deducts_credits_and_persists_transaction(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-user",
        user_id="billing-test-001",
        amount=100,
    )

    result = billing.consume_usage(
        username="billing-test-user",
        user_id="billing-test-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
    )

    assert result["ok"] is True
    assert result["cost"] == 1
    assert result["balance"] == 99
    assert billing.get_balance(
        user_id="billing-test-001",
        username="billing-test-user",
    ) == 99

    data = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    transactions = [
        item for item in data["transactions"]
        if item.get("user_id") == "billing-test-001"
        and item.get("type") == "usage"
    ]

    assert len(transactions) == 1
    assert transactions[0]["amount"] == -1
    assert transactions[0]["balance_after"] == 99


def test_insufficient_credits_does_not_deduct_or_record_usage(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-poor",
        user_id="billing-test-002",
        amount=1,
    )

    before = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    usage_before = sum(
        1 for item in before["transactions"]
        if item.get("user_id") == "billing-test-002"
        and item.get("type") == "usage"
    )

    result = billing.consume_usage(
        username="billing-test-poor",
        user_id="billing-test-002",
        model="gpt-5.4",
        input_tokens=1000,
        output_tokens=0,
    )

    assert result["ok"] is False
    assert result["reason"] == "insufficient credits"
    assert result["balance"] == 1

    after = json.loads(
        isolated_billing_file.read_text(encoding="utf-8")
    )
    account = after["users"]["billing-test-002"]
    usage_after = sum(
        1 for item in after["transactions"]
        if item.get("user_id") == "billing-test-002"
        and item.get("type") == "usage"
    )

    assert account["credits"] == 1
    assert usage_after == usage_before


def test_usage_deduction_does_not_change_another_users_balance(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-test-alpha",
        user_id="billing-test-alpha-id",
        amount=50,
    )
    billing.add_credits(
        username="billing-test-beta",
        user_id="billing-test-beta-id",
        amount=70,
    )

    result = billing.consume_usage(
        username="billing-test-alpha",
        user_id="billing-test-alpha-id",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
    )

    assert result["ok"] is True
    assert billing.get_balance(
        user_id="billing-test-alpha-id",
    ) == 49
    assert billing.get_balance(
        user_id="billing-test-beta-id",
    ) == 70



def test_gateway_preserves_successful_charge_when_usage_ledger_fails(
    monkeypatch,
    caplog,
):
    from types import SimpleNamespace

    from nova_backend.services import billing_service as billing_module
    from nova_backend.services import model_gateway_service as gateway
    from nova_backend.services import usage_ledger_service as usage_module

    charges = []

    monkeypatch.setattr(
        billing_module,
        "consume_usage",
        lambda **kwargs: (
            charges.append(kwargs)
            or {"ok": True, "cost": 1, "balance": 99}
        ),
    )

    def fail_usage_record(**kwargs):
        raise OSError("simulated usage ledger write failure")

    monkeypatch.setattr(
        usage_module,
        "record_model_usage",
        fail_usage_record,
    )

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
    )

    result = gateway._nova_consume_and_record_usage(
        user_id="gateway-test-user",
        username="gateway-test-user",
        session_id="gateway-test-session",
        model="gpt-4o-mini",
        messages=[],
        response=response,
        enforce=True,
    )

    assert len(charges) == 1
    assert result["ok"] is True
    assert result["cost"] == 1
    assert result["balance"] == 99
    assert "usage analytics write failed" in caplog.text
    assert "simulated usage ledger write failure" in caplog.text

def test_consume_usage_is_idempotent_for_same_key(
    isolated_billing_file,
):
    billing.add_credits(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        amount=100,
    )

    first = billing.consume_usage(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
        idempotency_key="provider_response:test-123",
    )

    second = billing.consume_usage(
        username="billing-idempotency-user",
        user_id="billing-idempotency-001",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=100,
        idempotency_key="provider_response:test-123",
    )

    assert first["ok"] is True
    assert second["ok"] is True

    assert second.get("idempotent_replay") is True
    assert second["transaction_id"] == first["transaction_id"]

    assert billing.get_balance(
        user_id="billing-idempotency-001",
        username="billing-idempotency-user",
    ) == 99

    data = billing._load()

    matching_transactions = [
        transaction
        for transaction in data.get("transactions", [])
        if (
            transaction.get("type") == "usage"
            and transaction.get("user_id")
            == "billing-idempotency-001"
            and transaction.get("meta", {}).get(
                "idempotency_key"
            ) == "provider_response:test-123"
        )
    ]

    assert len(matching_transactions) == 1