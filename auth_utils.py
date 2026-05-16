from __future__ import annotations

import os
import re
from typing import Any

from flask import jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash


USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")
DEV_BYPASS_AUTH = (os.getenv("NOVA_DEV_BYPASS_AUTH", "1") or "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_username(value: str) -> str:
    return clean_text(value).lower()


def validate_username(username: str) -> str | None:
    if not USERNAME_RE.fullmatch(username):
        return "Username must be 3 to 32 chars using lowercase letters, numbers, underscore, or dash."
    return None


def validate_password(password: str) -> str | None:
    if len(password or "") < 8:
        return "Password must be at least 8 characters."
    return None


def create_user(users: dict[str, dict[str, Any]], username: str, password: str, now_iso_func) -> tuple[bool, str]:
    username = normalize_username(username)
    err = validate_username(username)
    if err:
        return False, err

    err = validate_password(password)
    if err:
        return False, err

    if username in users:
        return False, "Username already exists."

    users[username] = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "created_at": now_iso_func(),
    }
    return True, "Account created."


def authenticate_user(users: dict[str, dict[str, Any]], username: str, password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    user = users.get(username)

    if not user:
        return False, "Invalid username or password."

    try:
        ok = check_password_hash(str(user.get("password_hash", "")), password or "")
    except Exception:
        ok = False

    if not ok:
        return False, "Invalid username or password."

    return True, username


def current_user() -> str | None:
    if DEV_BYPASS_AUTH:
        value = session.get("username")
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        return "dev"

    value = session.get("username")
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return None


def is_logged_in(users: dict[str, dict[str, Any]]) -> bool:
    if DEV_BYPASS_AUTH:
        return True
    user = current_user()
    return bool(user and user in users)


def login_user(username: str) -> None:
    session["username"] = normalize_username(username)
    session["logged_in"] = True


def logout_user() -> None:
    session.clear()


def require_page_auth(users: dict[str, dict[str, Any]]):
    if DEV_BYPASS_AUTH:
        return None
    if not is_logged_in(users):
        return redirect("/login")
    return None


def protect_routes(users: dict[str, dict[str, Any]]):
    if DEV_BYPASS_AUTH:
        return None

    public_paths = {
        "/login",
        "/logout",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/health",
    }

    path = request.path or "/"

    if path.startswith("/static/"):
        return None

    if path in public_paths:
        return None

    if path == "/" or path == "/mobile":
        if not is_logged_in(users):
            return redirect("/login")
        return None

    if path.startswith("/api/"):
        if not is_logged_in(users):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return None

    return None