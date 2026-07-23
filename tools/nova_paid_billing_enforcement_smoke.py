from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, g

from nova_backend.services import billing_service
from nova_backend.services import model_gateway_service
from nova_backend.services import usage_ledger_service
from nova_backend.services.payments_readiness_service import (
    build_payments_readiness,
)


ROOT = Path(__file__).resolve().parents[1]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


def test_readiness():
    result = build_payments_readiness(
        "richard"
    )

    usage = result.get(
        "usage_enforcement"
    ) or {}

    assert_true(
        "gateway usage enforced",
        usage.get(
            "gateway_usage_enforced"
        )
        is True,
        str(usage),
    )

    assert_true(
        "chat usage enforced",
        usage.get(
            "chat_usage_enforced"
        )
        is True,
        str(usage),
    )

    assert_true(
        "all active model paths enforced",
        usage.get(
            "active_model_paths_gateway_enforced"
        )
        is True,
        str(usage),
    )

    assert_true(
        "duplicate finalizer billing disabled",
        usage.get(
            "duplicate_finalize_billing"
        )
        is False,
        str(usage),
    )


def test_authenticated_identity():
    app = Flask(__name__)

    previous_live = os.environ.get(
        "NOVA_PAYMENTS_LIVE"
    )

    os.environ[
        "NOVA_PAYMENTS_LIVE"
    ] = "1"

    try:
        with app.test_request_context(
            "/api/chat",
            method="POST",
            json={
                "session_id": "billing_identity_smoke",
            },
        ):
            g.nova_auth_user = {
                "username": "alice",
            }

            username, session_id, enforce = (
                model_gateway_service
                ._nova_pop_internal_kwargs(
                    {
                        "nova_username": "richard",
                    }
                )
            )

            assert_true(
                "authenticated username wins",
                username == "alice",
                username,
            )

            assert_true(
                "request session resolved",
                session_id
                == "billing_identity_smoke",
                session_id,
            )

            assert_true(
                "billing enforcement enabled",
                enforce is True,
                str(enforce),
            )

        with app.test_request_context(
            "/api/chat",
            method="POST",
            json={
                "session_id": "unauthenticated_smoke",
            },
        ):
            blocked = False

            try:
                model_gateway_service._nova_pop_internal_kwargs(
                    {}
                )
            except RuntimeError:
                blocked = True

            assert_true(
                "live unauthenticated model call blocked",
                blocked,
            )

    finally:
        if previous_live is None:
            os.environ.pop(
                "NOVA_PAYMENTS_LIVE",
                None,
            )
        else:
            os.environ[
                "NOVA_PAYMENTS_LIVE"
            ] = previous_live


def test_single_gateway_charge():
    import openai

    original_openai = openai.OpenAI
    original_get_account = (
        billing_service.get_account
    )
    original_consume = (
        billing_service.consume_usage
    )
    original_record = (
        usage_ledger_service.record_model_usage
    )

    charges = []

    class FakeResponses:
        def create(self, *args, **kwargs):
            return SimpleNamespace(
                output_text="pong",
                output=[],
                usage=SimpleNamespace(
                    input_tokens=10,
                    output_tokens=4,
                ),
            )

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.responses = FakeResponses()

    try:
        openai.OpenAI = FakeOpenAI

        billing_service.get_account = (
            lambda username: {
                "plan": "developer",
                "credits": 1000,
            }
        )

        def fake_consume_usage(**kwargs):
            charges.append(dict(kwargs))

            return {
                "ok": True,
                "cost": 1,
                "balance": 999,
            }

        billing_service.consume_usage = (
            fake_consume_usage
        )

        usage_ledger_service.record_model_usage = (
            lambda **kwargs: {
                "ok": True,
            }
        )

        response = (
            model_gateway_service.responses_create(
                nova_username="billing_smoke_user",
                nova_session_id="billing_smoke_session",
                nova_enforce_billing=True,
                model="billing-smoke-model",
                input="ping",
            )
        )

        assert_true(
            "gateway returned provider response",
            response.output_text == "pong",
        )

        assert_true(
            "gateway charged exactly once",
            len(charges) == 1,
            str(charges),
        )

        assert_true(
            "gateway used provider input tokens",
            charges[0].get(
                "input_tokens"
            )
            == 10,
            str(charges),
        )

        assert_true(
            "gateway used provider output tokens",
            charges[0].get(
                "output_tokens"
            )
            == 4,
            str(charges),
        )

    finally:
        openai.OpenAI = original_openai
        billing_service.get_account = (
            original_get_account
        )
        billing_service.consume_usage = (
            original_consume
        )
        usage_ledger_service.record_model_usage = (
            original_record
        )


def main():
    test_readiness()
    test_authenticated_identity()
    test_single_gateway_charge()

    print(
        "NOVA PAID BILLING ENFORCEMENT SMOKE PASSED"
    )


if __name__ == "__main__":
    main()