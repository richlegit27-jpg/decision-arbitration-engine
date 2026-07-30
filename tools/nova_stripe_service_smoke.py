from __future__ import annotations

import os

from nova_backend.services import stripe_service


def check(name, value):
    if not value:
        raise RuntimeError(
            f"{name} failed"
        )

    print(f"PASS {name}")


def main():
    os.environ.pop(
        "STRIPE_SECRET_KEY",
        None,
    )

    check(
        "stripe missing key detected",
        not stripe_service.stripe_is_configured(),
    )

    try:
        stripe_service.get_stripe_client()
    except RuntimeError:
        print(
            "PASS stripe client blocks without key"
        )
    else:
        raise RuntimeError(
            "stripe client should block"
        )

    print(
        "NOVA STRIPE SERVICE SMOKE PASSED"
    )


if __name__ == "__main__":
    main()