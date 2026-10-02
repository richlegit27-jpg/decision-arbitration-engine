from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time

import pyotp


MFA_ISSUER = "Nova"


def encrypt_totp_secret(secret: str, key: str | None = None) -> str:
    configured_key = str(key or os.getenv("NOVA_MFA_ENCRYPTION_KEY") or "").strip()
    if not configured_key:
        raise ValueError("NOVA_MFA_ENCRYPTION_KEY is not configured.")

    from cryptography.fernet import Fernet

    encrypted = Fernet(configured_key.encode("ascii")).encrypt(
        str(secret).encode("utf-8")
    )
    return "fernet:" + encrypted.decode("ascii")


def decrypt_totp_secret(value: str, key: str | None = None) -> str:
    stored = str(value or "")
    if not stored.startswith("fernet:"):
        # Existing plaintext values remain readable until the account next verifies MFA.
        return stored

    configured_key = str(key or os.getenv("NOVA_MFA_ENCRYPTION_KEY") or "").strip()
    if not configured_key:
        raise ValueError("NOVA_MFA_ENCRYPTION_KEY is not configured.")

    from cryptography.fernet import Fernet

    return Fernet(configured_key.encode("ascii")).decrypt(
        stored.removeprefix("fernet:").encode("ascii")
    ).decode("utf-8")


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


def verify_code_counter(
    secret: str,
    code: str,
    last_counter: int = -1,
    valid_window: int = 1,
    now: float | None = None,
) -> int | None:
    """Return the matched TOTP counter only when it has not been used before."""
    if not secret or not code:
        return None

    try:
        totp = pyotp.TOTP(secret)
        supplied = str(code).strip()
        if not re.fullmatch(rf"[0-9]{{{totp.digits}}}", supplied):
            return None

        current_counter = int((time.time() if now is None else now) // totp.interval)
        earliest = max(0, current_counter - max(0, int(valid_window)))
        latest = current_counter + max(0, int(valid_window))
        previous_counter = int(last_counter if last_counter is not None else -1)
        for counter in range(earliest, latest + 1):
            if counter <= previous_counter:
                continue
            if hmac.compare_digest(totp.at(counter * totp.interval), supplied):
                return counter
    except Exception:
        return None

    return None


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(10) for _ in range(max(1, int(count)))]


def hash_recovery_code(code: str) -> str:
    normalized = re.sub(r"[\s-]", "", str(code or "")).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def consume_recovery_code(user: dict, code: str) -> bool:
    candidate = hash_recovery_code(code)
    stored = user.get("mfa_recovery_code_hashes")
    if not isinstance(stored, list) or not candidate:
        return False

    for index, digest in enumerate(stored):
        if isinstance(digest, str) and hmac.compare_digest(digest, candidate):
            del stored[index]
            return True
    return False


def get_current_code(secret: str) -> str:
    """
    Development helper for smoke testing only.
    Do not expose through an API route.
    """
    return pyotp.TOTP(secret).now()
