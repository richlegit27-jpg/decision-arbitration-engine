from types import SimpleNamespace

from nova_backend.services.billing_service import (
    get_account,
    plan_from_price_id,
    set_subscription,
)


def assert_true(
    name,
    condition,
    detail="",
):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(
        f"PASS {name}"
    )


def main():
    standard_price = "price_standard_test"

    pro_price = "price_pro_test"

    # simulate Stripe environment mapping
    import os

    os.environ[
        "NOVA_STRIPE_STANDARD_PRICE_ID"
    ] = standard_price

    os.environ[
        "NOVA_STRIPE_PRO_PRICE_ID"
    ] = pro_price

    assert_true(
        "standard price maps",
        plan_from_price_id(
            standard_price
        ) == "standard",
    )

    assert_true(
        "pro price maps",
        plan_from_price_id(
            pro_price
        ) == "pro",
    )

    session = SimpleNamespace(
        metadata={
            "nova_username": "webhook_test_user",
            "nova_price_id": pro_price,
        },
        subscription="sub_webhook_test_123",
    )

    username = session.metadata.get(
        "nova_username",
        "",
    )

    price_id = session.metadata.get(
        "nova_price_id",
        "",
    )

    set_subscription(
        username=username,
        subscription_id=session.subscription,
        plan=plan_from_price_id(
            price_id
        ),
    )

    account = get_account(
        username
    )

    assert_true(
        "webhook activates pro",
        account.get("plan") == "pro",
        str(account),
    )

    assert_true(
        "pro credits assigned",
        account.get("credits") == 50000,
        str(account),
    )

    print(
        "NOVA STRIPE WEBHOOK ACTIVATION SMOKE PASSED"
    )


if __name__ == "__main__":
    main()