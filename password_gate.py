import time
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from auth_utils import (
    bootstrap_password_from_env,
    change_password,
    get_password_record,
    verify_password,
    set_password,
)

password_gate_bp = Blueprint("password_gate", __name__)

FAILED_LOGINS = {}
LOCKOUT_SECONDS = 300
MAX_ATTEMPTS = 5

STATIC_PREFIXES = (
    "/static/",
)

PUBLIC_PATHS = {
    "/favicon.ico",
    "/login",
    "/logout",
    "/reset-password-direct",
}

PUBLIC_API_PATHS = {
    "/api/state",
    "/api/models",
}


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.remote_addr or "unknown").strip()


def _safe_next_url(value: str | None) -> str:
    if not value:
        return "/"

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return "/"

    if not value.startswith("/"):
        return "/"

    return value


def _gate_enabled() -> bool:
    return bool(get_password_record())


def _password_ok(candidate: str) -> bool:
    candidate = (candidate or "").strip()
    if not candidate:
        return False
    return verify_password(candidate, get_password_record())


def _is_static_request(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in STATIC_PREFIXES)


def _is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True

    if _is_static_request(path):
        return True

    if path in PUBLIC_API_PATHS:
        return True

    return False


def _is_exempt_request() -> bool:
    path = request.path or "/"

    if _is_public_path(path):
        return True

    endpoint = request.endpoint or ""
    if endpoint.startswith("password_gate."):
        return True

    return False


def _get_fail_state(ip: str) -> dict:
    state = FAILED_LOGINS.get(ip)
    now = time.time()

    if not state:
        state = {
            "count": 0,
            "locked_until": 0.0,
        }
        FAILED_LOGINS[ip] = state

    if state["locked_until"] and now >= state["locked_until"]:
        state["count"] = 0
        state["locked_until"] = 0.0

    return state


def _is_locked_out(ip: str) -> tuple[bool, int]:
    state = _get_fail_state(ip)
    now = time.time()

    if state["locked_until"] > now:
        remaining = int(state["locked_until"] - now)
        return True, remaining

    return False, 0


def _record_failed_attempt(ip: str) -> tuple[bool, int]:
    state = _get_fail_state(ip)
    state["count"] += 1

    if state["count"] >= MAX_ATTEMPTS:
        state["locked_until"] = time.time() + LOCKOUT_SECONDS
        return True, LOCKOUT_SECONDS

    return False, 0


def _clear_failed_attempts(ip: str) -> None:
    if ip in FAILED_LOGINS:
        FAILED_LOGINS[ip]["count"] = 0
        FAILED_LOGINS[ip]["locked_until"] = 0.0


@password_gate_bp.before_app_request
def require_password_gate():
    if not _gate_enabled():
        return None

    if _is_exempt_request():
        return None

    if session.get("nova_gate_ok") is True:
        return None

    header_password = request.headers.get("X-NOVA-PASSWORD", "")
    if _password_ok(header_password):
        session["nova_gate_ok"] = True
        session.permanent = True
        return None

    path = request.path or "/"

    if path.startswith("/api/"):
        return jsonify(
            {
                "ok": False,
                "error": "Password required.",
                "login_url": url_for("password_gate.login"),
            }
        ), 401

    next_url = request.full_path if request.query_string else request.path
    return redirect(url_for("password_gate.login", next=_safe_next_url(next_url)))


@password_gate_bp.route("/login", methods=["GET", "POST"])
def login():
    if not _gate_enabled():
        return redirect("/")

    error = ""
    next_url = _safe_next_url(request.values.get("next"))
    ip = _client_ip()

    locked, remaining = _is_locked_out(ip)
    if locked:
        error = f"Too many attempts. Try again in {remaining} seconds."
        return render_template(
            "password_gate.html",
            error=error,
            next_url=next_url,
        ), 429

    if request.method == "POST":
        submitted_password = request.form.get("password", "")

        if _password_ok(submitted_password):
            _clear_failed_attempts(ip)
            session["nova_gate_ok"] = True
            session.permanent = True
            return redirect(next_url)

        locked_now, remaining_now = _record_failed_attempt(ip)
        if locked_now:
            error = f"Too many attempts. Try again in {remaining_now} seconds."
            return render_template(
                "password_gate.html",
                error=error,
                next_url=next_url,
            ), 429

        attempts_left = MAX_ATTEMPTS - _get_fail_state(ip)["count"]
        error = f"Wrong password. {attempts_left} attempt(s) left."

    return render_template(
        "password_gate.html",
        error=error,
        next_url=next_url,
    )


@password_gate_bp.route("/reset-password-direct", methods=["GET"])
def reset_password_direct():
    ip = request.remote_addr or ""

    if ip not in ("127.0.0.1", "::1"):
        return "Forbidden", 403

    new_password = request.args.get("pw", "").strip()
    if not new_password or len(new_password) < 4:
        return "Provide ?pw=yourpassword (min 4 chars)", 400

    set_password(new_password)
    session["nova_gate_ok"] = True
    session.permanent = True

    return f"Password reset to: {new_password}"


@password_gate_bp.route("/admin/change-password", methods=["GET", "POST"])
def admin_change_password():
    if session.get("nova_gate_ok") is not True:
        return redirect(url_for("password_gate.login", next="/admin/change-password"))

    error = ""
    success = ""

    if request.method == "POST":
        current_password = (request.form.get("current_password") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        if not current_password or not new_password or not confirm_password:
            error = "All fields are required."
        elif len(new_password) < 8:
            error = "New password must be at least 8 characters."
        elif new_password != confirm_password:
            error = "New password and confirm password do not match."
        elif current_password == new_password:
            error = "New password must be different from current password."
        elif not change_password(current_password, new_password):
            error = "Current password is wrong."
        else:
            success = "Password changed successfully."

    return render_template(
        "admin_change_password.html",
        error=error,
        success=success,
    )


@password_gate_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("password_gate.login"))


def init_password_gate(app):
    bootstrap_password_from_env()

    app.config["SECRET_KEY"] = (
        app.config.get("SECRET_KEY")
        or "change-this-now-before-deploy"
    )

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

    app.register_blueprint(password_gate_bp)