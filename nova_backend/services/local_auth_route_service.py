import json
import secrets
import hashlib
from pathlib import Path


class LocalAuthRouteService:

    def __init__(
        self,
        app,
        request,
        jsonify,
        session,
    ):
        self.app = app
        self.request = request
        self.jsonify = jsonify
        self.session = session

        self.data_dir = Path(__file__).resolve().parents[2] / "data"

        self.users_path = (
            self.data_dir / "nova_auth_users.json"
        )

    def install_routes(self):

        from nova_backend.services.mfa_service import (
            generate_secret,
            build_provisioning_uri,
        )

        app = self.app
        request = self.request
        jsonify = self.jsonify
        session = self.session

        def route_exists(rule):
            return any(
                str(r.rule) == rule
                for r in app.url_map.iter_rules()
            )

        def load_users():
            if not self.users_path.exists():
                return {"users": []}

            try:
                data = json.loads(
                    self.users_path.read_text(
                        encoding="utf-8"
                    )
                )

                if not isinstance(data, dict):
                    return {"users": []}

                if not isinstance(data.get("users"), list):
                    data["users"] = []

                return data

            except Exception:
                return {"users": []}

        def save_users(data):
            self.users_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        def clean(value):
            return str(value or "").strip()

        def hash_password(password, salt):
            raw = (
                str(salt)
                + "::"
                + str(password)
            ).encode("utf-8")

            return hashlib.sha256(raw).hexdigest()

        def public_user(user):
            return {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email"),
            }

        def find_user(identifier):
            ident = clean(identifier).lower()

            for user in load_users().get("users", []):
                if clean(user.get("username")).lower() == ident:
                    return user

                if clean(user.get("email")).lower() == ident:
                    return user

            return None

        def current_user():
            uid = session.get("nova_user_id")

            if not uid:
                return None

            for user in load_users().get("users", []):
                if user.get("id") == uid:
                    return user

            return None

        def auth_status():
            user = current_user()

            return jsonify({
                "ok": True,
                "authenticated": bool(user),
                "user": public_user(user) if user else None,
                "mode": "local",
            })

        def auth_register():
            payload = request.get_json(
                silent=True
            ) or {}

            username = clean(
                payload.get("username")
                or payload.get("name")
            )

            email = clean(
                payload.get("email")
            )

            password = str(
                payload.get("password")
                or ""
            )

            if not username and email:
                username = email.split("@", 1)[0]

            if not username:
                return jsonify({
                    "ok": False,
                    "error": "Username is required.",
                }), 400

            if len(password) < 4:
                return jsonify({
                    "ok": False,
                    "error": "Password must be at least 4 characters.",
                }), 400

            data = load_users()

            if find_user(username) or (
                email and find_user(email)
            ):
                return jsonify({
                    "ok": False,
                    "error": "User already exists.",
                }), 409

            salt = secrets.token_hex(16)

            user = {
                "id": "user_" + secrets.token_hex(12),
                "username": username,
                "email": email,
                "salt": salt,
                "password_hash": hash_password(
                    password,
                    salt,
                ),
            }

            data["users"].append(user)

            save_users(data)

            session["nova_user_id"] = user["id"]
            session.pop("user_id", None)
            session.pop("username", None)
            session["authenticated"] = True
            session["auth_mode"] = "local"

            return jsonify({
                "ok": True,
                "authenticated": True,
                "user": public_user(user),
            })

        def auth_login():
            payload = request.get_json(
                silent=True
            ) or {}

            identifier = clean(
                payload.get("username")
                or payload.get("email")
                or payload.get("login")
            )

            password = str(
                payload.get("password")
                or ""
            )

            user = find_user(identifier)

            if not user:
                return jsonify({
                    "ok": False,
                    "error": "Invalid username or password.",
                }), 401

            if hash_password(
                password,
                user.get("salt", ""),
            ) != user.get("password_hash"):

                return jsonify({
                    "ok": False,
                    "error": "Invalid username or password.",
                }), 401

            session["nova_user_id"] = user["id"]
            session.pop("user_id", None)
            session.pop("username", None)
            session["authenticated"] = True
            session["auth_mode"] = "local"

            return jsonify({
                "ok": True,
                "authenticated": True,
                "user": public_user(user),
            })

        def auth_logout():
            session.pop(
                "nova_user_id",
                None,
            )

            return jsonify({
                "ok": True,
                "authenticated": False,
                "user": None,
            })

        def auth_mfa_setup():
            user_id = session.get(
                "nova_user_id"
            )

            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": "Not authenticated",
                }), 401

            for user in load_users().get("users", []):
                if user.get("id") == user_id:
                    secret = generate_secret()

                    return jsonify({
                        "ok": True,
                        "secret": secret,
                        "uri": build_provisioning_uri(
                            user.get("username", "Nova"),
                            secret,
                        ),
                    })

            return jsonify({
                "ok": False,
                "error": "User not found",
            }), 404


        routes = [
            ("/api/auth/status", "nova_auth_status_20260610", auth_status, ["GET"]),
            ("/api/auth/register", "nova_auth_register_20260610", auth_register, ["POST"]),
            ("/api/auth/login", "nova_auth_login_20260610", auth_login, ["POST"]),
            ("/api/auth/logout", "nova_auth_logout_20260610", auth_logout, ["POST"]),
            ("/api/auth/mfa/setup", "nova_auth_mfa_setup_20260716", auth_mfa_setup, ["GET"]),
            ("/api/login", "nova_api_login_20260610", auth_login, ["POST"]),
            ("/api/logout", "nova_api_logout_20260610", auth_logout, ["POST"]),
            ("/api/register", "nova_api_register_20260610", auth_register, ["POST"]),
        ]

        for rule, name, handler, methods in routes:
            if not route_exists(rule):
                app.add_url_rule(
                    rule,
                    name,
                    handler,
                    methods=methods,
                )