from __future__ import annotations


def ensure_mfa_fields(user: dict) -> dict:
    """
    Add safe defaults for existing accounts.
    Existing users do not need a migration.
    """
    if not isinstance(user, dict):
        return user

    user.setdefault("mfa_enabled", False)
    user.setdefault("mfa_secret", "")

    return user


def get_mfa_state(user: dict) -> dict:
    if not isinstance(user, dict):
        return {
            "enabled": False,
            "secret": "",
        }

    ensure_mfa_fields(user)

    return {
        "enabled": bool(user.get("mfa_enabled", False)),
        "secret": str(user.get("mfa_secret") or ""),
    }


def enable_mfa(user: dict, secret: str) -> dict:
    if not isinstance(user, dict):
        return user

    user["mfa_enabled"] = True
    user["mfa_secret"] = str(secret or "")

    return user


def disable_mfa(user: dict) -> dict:
    if not isinstance(user, dict):
        return user

    user["mfa_enabled"] = False
    user["mfa_secret"] = ""

    return user