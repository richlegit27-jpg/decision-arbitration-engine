import pytest

from nova_backend.services.mfa_service import (
    consume_recovery_code,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    hash_recovery_code,
    verify_code_counter,
)
import pyotp
from cryptography.fernet import Fernet, InvalidToken


def test_totp_verification_returns_counter_and_rejects_replay():
    secret = pyotp.random_base32()
    now = 1_800_000_000
    code = pyotp.TOTP(secret).at(now)

    counter = verify_code_counter(secret, code, now=now)

    assert counter == now // 30
    assert verify_code_counter(secret, code, last_counter=counter, now=now) is None


def test_recovery_codes_are_hashed_and_single_use():
    codes = generate_recovery_codes(2)
    user = {"mfa_recovery_code_hashes": [hash_recovery_code(code) for code in codes]}

    assert len(codes) == 2
    assert all(code not in user["mfa_recovery_code_hashes"] for code in codes)
    assert consume_recovery_code(user, codes[0]) is True
    assert consume_recovery_code(user, codes[0]) is False
    assert consume_recovery_code(user, codes[1]) is True
    assert user["mfa_recovery_code_hashes"] == []


def test_totp_secret_is_encrypted_at_rest_and_requires_the_configured_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    encrypted = encrypt_totp_secret("sensitive-totp-secret", key)

    assert encrypted.startswith("fernet:")
    assert "sensitive-totp-secret" not in encrypted
    assert decrypt_totp_secret(encrypted, key) == "sensitive-totp-secret"
    with pytest.raises(InvalidToken):
        decrypt_totp_secret(encrypted, Fernet.generate_key().decode("ascii"))

    monkeypatch.delenv("NOVA_MFA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValueError, match="NOVA_MFA_ENCRYPTION_KEY"):
        encrypt_totp_secret("secret")
