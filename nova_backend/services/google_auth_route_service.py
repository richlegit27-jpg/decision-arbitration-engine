import json
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from filelock import FileLock, Timeout
import bcrypt

from flask import current_app, jsonify, redirect, request, session, url_for


def _verify_local_password(user, password):
    password_hash = str(user.get("password_hash") or "")
    try:
        if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(
                str(password).encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        legacy_hash = hashlib.sha256(
            (
                str(user.get("salt") or "")
                + "::"
                + str(password)
            ).encode("utf-8")
        ).hexdigest()
        return bool(password_hash) and hmac.compare_digest(
            legacy_hash,
            password_hash,
        )
    except Exception:
        return False


class GoogleAuthRouteService:

    def __init__(
        self,
        app,
        google_auth_service,
    ):
        self.app = app
        self.google_auth_service = google_auth_service

        self.users_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "nova_auth_users.json"
        )


    def install_routes(self):

        google = self.google_auth_service.google

        if not google:
            @self.app.route(
                "/api/auth/google",
                methods=["GET"],
                endpoint="nova_google_login_unavailable_20261002",
            )
            def google_login_unavailable():
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in is not configured.",
                }), 503

            @self.app.route(
                "/api/auth/google/link",
                methods=["POST"],
                endpoint="nova_google_link_unavailable_20261002",
            )
            def google_link_unavailable():
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in is not configured.",
                }), 503

            print(
                "[GOOGLE AUTH ROUTES] skipped"
            )
            return


        def load_users():

            if not self.users_path.exists():
                return {
                    "users": []
                }

            return json.loads(
                self.users_path.read_text(
                    encoding="utf-8"
                )
            )


        def save_users(data):

            self.users_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.users_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                ),
                encoding="utf-8",
            )


        def find_email(email):
            normalized = str(email or "").strip().casefold()
            for user in load_users().get(
                "users",
                [],
            ):
                if str(user.get("email") or "").strip().casefold() == normalized:
                    return user

            return None


        def find_google_subject(subject):
            for user in load_users().get("users", []):
                if str(user.get("google_sub") or "") == str(subject or ""):
                    return user
            return None


        def start_google_authorization():
            nonce = secrets.token_urlsafe(32)
            session["oauth_nonce"] = nonce
            configured_redirect = str(
                current_app.config.get("GOOGLE_REDIRECT_URI")
                or os.getenv("GOOGLE_REDIRECT_URI")
                or ""
            ).strip()
            is_production = (
                str(current_app.config.get("NOVA_ENV") or "").lower() == "production"
                or str(os.getenv("FLASK_ENV") or "").lower() == "production"
                or str(os.getenv("RAILWAY_ENVIRONMENT") or "").lower() == "production"
            )
            if is_production and not configured_redirect:
                session.pop("oauth_nonce", None)
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in requires a configured HTTPS callback URL.",
                }), 503

            redirect_uri = configured_redirect or url_for(
                "google_callback",
                _external=True,
                _scheme=(
                    "https"
                    if current_app.config.get("PREFERRED_URL_SCHEME") == "https"
                    else None
                ),
            )
            parsed_redirect = urlsplit(redirect_uri)
            if (
                (is_production and parsed_redirect.scheme != "https")
                or parsed_redirect.scheme not in ("http", "https")
                or not parsed_redirect.netloc
                or parsed_redirect.username
                or parsed_redirect.password
                or parsed_redirect.path != "/api/auth/google/callback"
                or parsed_redirect.query
                or parsed_redirect.fragment
            ):
                session.pop("oauth_nonce", None)
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in requires a valid callback URL.",
                }), 503

            return google.authorize_redirect(redirect_uri, nonce=nonce)


        @self.app.route(
            "/api/auth/google",
            methods=["GET"],
        )
        def google_login():
            return start_google_authorization()


        @self.app.route(
            "/api/auth/google/link",
            methods=["POST"],
        )
        def google_link():
            user_id = str(session.get("nova_user_id") or "").strip()
            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": "Sign in before linking Google.",
                }), 401

            payload = request.get_json(silent=True) or request.form or {}
            password = str(payload.get("current_password") or "")
            user = next(
                (
                    item
                    for item in load_users().get("users", [])
                    if str(item.get("id") or "") == user_id
                ),
                None,
            )
            if not user or not password or not _verify_local_password(user, password):
                return jsonify({
                    "ok": False,
                    "error": "Confirm the account password before linking Google.",
                }), 403

            if user.get("google_sub"):
                return jsonify({
                    "ok": False,
                    "error": "A Google identity is already linked to this account.",
                }), 409

            session["oauth_link_user_id"] = user_id
            session["oauth_link_started_at"] = datetime.now(
                timezone.utc
            ).timestamp()
            return start_google_authorization()

        @self.app.route(
            "/api/auth/google/callback",
            methods=["GET"],
        )
        def google_callback():
            expected_nonce = str(session.pop("oauth_nonce", "") or "")
            link_user_id = str(session.pop("oauth_link_user_id", "") or "")
            link_started_at = float(session.pop("oauth_link_started_at", 0) or 0)
            is_linking = bool(link_user_id)
            if not expected_nonce:
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in session expired. Please try again.",
                }), 400

            try:
                token = google.authorize_access_token()
                profile = google.parse_id_token(
                    token,
                    nonce=expected_nonce,
                )
            except Exception:
                current_app.logger.warning("Google sign-in callback validation failed.")
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in could not be verified. Please try again.",
                }), 401

            subject = str((profile or {}).get("sub") or "").strip()
            email = str((profile or {}).get("email") or "").strip().lower()
            email_verified = (profile or {}).get("email_verified")
            if (
                not subject
                or not email
                or email_verified not in (True, "true", "True", 1)
            ):
                return jsonify({
                    "ok": False,
                    "error": "Google did not provide a verified account identity.",
                }), 401

            try:
                with FileLock(str(self.users_path) + ".lock", timeout=5):
                    if is_linking:
                        if (
                            str(session.get("nova_user_id") or "") != link_user_id
                            or not link_started_at
                            or datetime.now(timezone.utc).timestamp() - link_started_at > 600
                        ):
                            return jsonify({
                                "ok": False,
                                "error": "Account linking expired. Start again from Security Settings.",
                            }), 401

                        data = load_users()
                        user = next(
                            (
                                item
                                for item in data.get("users", [])
                                if str(item.get("id") or "") == link_user_id
                            ),
                            None,
                        )
                        existing_owner = next(
                            (
                                item
                                for item in data.get("users", [])
                                if str(item.get("google_sub") or "") == subject
                            ),
                            None,
                        )
                        if not user:
                            return jsonify({
                                "ok": False,
                                "error": "The account could not be found.",
                            }), 404
                        if existing_owner and str(existing_owner.get("id")) != link_user_id:
                            return jsonify({
                                "ok": False,
                                "error": "This Google identity is already linked to another account.",
                            }), 409
                        if user.get("google_sub") and user.get("google_sub") != subject:
                            return jsonify({
                                "ok": False,
                                "error": "A different Google identity is already linked to this account.",
                            }), 409
                        user["google_sub"] = subject
                        user["google_email"] = email
                        user["google_email_verified"] = True
                        save_users(data)
                    else:
                        user = find_google_subject(subject)
                        if not user and find_email(email):
                            return jsonify({
                                "ok": False,
                                "error": "An account already uses this email. Sign in to that account before linking Google.",
                                "account_link_required": True,
                            }), 409

                        name = profile.get("name") or email.split("@", 1)[0]
                        if not user:
                            data = load_users()
                            user = {
                                "id": "user_" + secrets.token_hex(12),
                                "username": name,
                                "email": email,
                                "email_verified": True,
                                "auth_provider": "google",
                                "google_sub": subject,
                                "plan": "free",
                                "credits": 100000,
                                "subscription_status": "inactive",
                            }
                            data["users"].append(user)
                            save_users(data)
            except Timeout:
                return jsonify({
                    "ok": False,
                    "error": "Google sign-in is temporarily busy. Please retry.",
                }), 503

            session.clear()
            if bool(user.get("mfa_enabled", False)):
                session["nova_pending_mfa_user_id"] = user["id"]
                session["nova_pending_mfa_at"] = datetime.now(
                    timezone.utc
                ).timestamp()
                session["nova_pending_auth_mode"] = "google"
                return redirect("/login?mfa=required")

            session["nova_user_id"] = user["id"]
            session["authenticated"] = True
            session["username"] = str(user.get("username") or "")
            session["auth_mode"] = str(
                user.get("auth_provider") or "google"
            )

            return redirect("/account?google=linked" if is_linking else "/app")


        print(
            "[GOOGLE AUTH ROUTES] installed"
        )
