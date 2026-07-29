from nova_backend.services.billing_service import (
    get_account,
    set_subscription,
    cancel_subscription,
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
    username = "lifecycle_test_user"

    set_subscription(
        username=username,
        subscription_id="sub_pro_test",
        plan="pro",
    )

    account = get_account(
        username
    )

    assert_true(
        "subscription upgraded",
        account.get("plan") == "pro",
    )

    assert_true(
        "pro credits active",
        account.get("credits") == 50000,
    )

    set_subscription(
        username=username,
        subscription_id="sub_standard_test",
        plan="standard",
    )

    account = get_account(
        username
    )

    assert_true(
        "subscription downgraded",
        account.get("plan") == "standard",
    )

    cancel_subscription(
        username,
    )

    account = get_account(
        username
    )

    assert_true(
        "subscription cancelled",
        account.get("plan") == "free",
    )

    print(
        "NOVA STRIPE SUBSCRIPTION LIFECYCLE SMOKE PASSED"
    )


if __name__ == "__main__":
    main()