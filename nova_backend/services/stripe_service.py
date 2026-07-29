from __future__ import annotations

import os


def stripe_is_configured() -> bool:
    return bool(
        str(
            os.environ.get("STRIPE_SECRET_KEY", "")
        ).strip()
    )


def get_stripe_client():
    if not stripe_is_configured():
        raise RuntimeError(
            "Stripe is not configured."
        )

    import stripe

    stripe.api_key = os.environ.get(
        "STRIPE_SECRET_KEY"
    )

    return stripe

def create_customer(
    email=None,
    username=None,
):
    stripe = get_stripe_client()

    params = {}

    if email:
        params["email"] = email

    if username:
        params["metadata"] = {
            "nova_username": str(username)
        }

    return stripe.Customer.create(
        **params
    )


def create_checkout_session(
    price_id,
    success_url,
    cancel_url,
    customer_id=None,
    username=None,
):
    stripe = get_stripe_client()

    params = {
        "mode": "subscription",
        "customer": customer_id,
        "line_items": [
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    if username:
        params["metadata"] = {
            "nova_username": str(username),
        }

    return stripe.checkout.Session.create(
        **params
    )


def verify_webhook(
    payload,
    signature,
):
    stripe = get_stripe_client()

    return stripe.Webhook.construct_event(
        payload,
        signature,
        os.environ.get(
            "STRIPE_WEBHOOK_SECRET"
        ),
    )