from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request, Response

PBKDF2_ITERATIONS = 200_000
PASSWORD_SALT_BYTES = 16
SESSION_HOURS = 24

COOKIE_NAME = "nova_session"
COOKIE_MAX_AGE = SESSION_HOURS * 60 * 60
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"
COOKIE_HTTPONLY = True
COOKIE_SECURE = False  # set True when running over HTTPS

SECRET_KEY = os.getenv("NOVA_SECRET_KEY", "nova-dev-secret-change-this")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _sign(data: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _timing_safe_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def hash_password(password: str) -> str:
    password = str(password or "")
    if not password:
        raise ValueError("Password is required.")

    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, hash_hex = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        str(password or "").encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(candidate, expected)


def validate_username(username: str) -> str:
    username = str(username or "").strip()

    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")

    if len(username) > 50:
        raise ValueError("Username must be 50 characters or less.")

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if any(ch not in allowed for ch in username):
        raise ValueError("Username contains invalid characters.")

    return username


def validate_password(password: str) -> str:
    password = str(password or "")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    if len(password) > 256:
        raise ValueError("Password is too long.")

    return password


def build_session_user(username: str) -> dict[str, Any]:
    expires_at = (_utc_now() + timedelta(hours=SESSION_HOURS)).replace(microsecond=0).isoformat()

    return {
        "username": username,
        "created_at": _utc_now_iso(),
        "expires_at": expires_at,
        "authenticated": True,
    }


def _build_cookie_value(username: str) -> str:
    expires_at = int((_utc_now() + timedelta(hours=SESSION_HOURS)).timestamp())

    payload = {
        "username": username,
        "exp": expires_at,
    }

    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    signature = _sign(payload_b64)

    return f"{payload_b64}.{signature}"


def _parse_cookie_value(cookie_value: str) -> dict[str, Any] | None:
    try:
        payload_b64, signature = cookie_value.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(payload_b64)
    if not _timing_safe_equal(signature, expected_signature):
        return None

    try:
        payload_raw = _b64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_raw)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    username = str(payload.get("username", "")).strip()
    exp = payload.get("exp")

    if not username:
        return None

    try:
        exp_int = int(exp)
    except Exception:
        return None

    if exp_int <= int(_utc_now().timestamp()):
        return None

    return {
        "username": username,
        "expires_at": datetime.fromtimestamp(exp_int, tz=timezone.utc).replace(microsecond=0).isoformat(),
        "authenticated": True,
    }


def set_auth_cookie(response: Response, username: str) -> dict[str, Any]:
    user = build_session_user(username)
    cookie_value = _build_cookie_value(username)

    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        max_age=COOKIE_MAX_AGE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path=COOKIE_PATH,
    )

    return user


def clear_auth_cookie(response: Response) -> dict[str, Any]:
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
    )

    return {
        "ok": True,
        "authenticated": False,
    }


def get_session_user(request: Request) -> dict[str, Any] | None:
    cookie_value = request.cookies.get(COOKIE_NAME, "")
    if not cookie_value:
        return None

    parsed = _parse_cookie_value(cookie_value)
    if not parsed:
        return None

    return parsed


def require_session_user(request: Request) -> dict[str, Any]:
    user = get_session_user(request)
    if not user:
        raise ValueError("Authentication required.")
    return user


def is_authenticated(request: Request) -> bool:
    return get_session_user(request) is not None