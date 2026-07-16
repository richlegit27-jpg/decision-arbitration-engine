from __future__ import annotations

import pyotp


MFA_ISSUER = "Nova"


def generate_secret() -> str:
    return pyotp.random_base32()


def build_provisioning_uri(
    username: str,
    secret: str,
) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=MFA_ISSUER,
    )


def verify_code(
    secret: str,
    code: str,
) -> bool:
    if not secret or not code:
        return False

    try:
        totp = pyotp.TOTP(secret)

        return bool(
            totp.verify(
                str(code).strip(),
                valid_window=1,
            )
        )

    except Exception:
        return False


def get_current_code(secret: str) -> str:
    """
    Development helper for smoke testing only.
    Do not expose through an API route.
    """
    return pyotp.TOTP(secret).now()