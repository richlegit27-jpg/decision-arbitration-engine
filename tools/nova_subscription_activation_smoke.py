from nova_backend.services.billing_service import (
    get_account,
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
    username = "stripe_test_user"

    account = set_subscription(
        username=username,
        subscription_id="sub_test_123",
        plan="standard",
    )

    assert_true(
        "plan activated",
        account.get("plan") == "standard",
        str(account),
    )

    assert_true(
        "monthly credits granted",
        account.get("monthly_credits") == 10000,
        str(account),
    )

    assert_true(
        "credits granted",
        account.get("credits") == 10000,
        str(account),
    )

    loaded = get_account(
        username
    )

    assert_true(
        "account persisted",
        loaded.get("subscription_id") == "sub_test_123",
        str(loaded),
    )

    print(
        "NOVA SUBSCRIPTION ACTIVATION SMOKE PASSED"
    )


if __name__ == "__main__":
    main()