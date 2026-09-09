import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from nova_backend.services.email_verification_service import (
    EmailVerificationService,
)

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

        self.data_dir = (
            Path(__file__).resolve().parents[2]
            / "data"
        )

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.users_path = (
            self.data_dir
            / "nova_auth_users.json"
        )

    def install_routes(self):

        from nova_backend.services.mfa_service import (
            generate_secret,
            build_provisioning_uri,
            verify_code,
        )
        email_verification_service = (
            EmailVerificationService()
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

                if not isinstance(
                    data.get("users"),
                    list,
                ):
                    data["users"] = []

                return data

            except Exception:
                return {"users": []}

        def save_users(data):

            self.data_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

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

        def hash_password(password):

            return bcrypt.hashpw(
                str(password).encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

        def verify_bcrypt_password(
            password,
            password_hash,
        ):

            if not password_hash:
                return False

            try:
                return bcrypt.checkpw(
                    str(password).encode("utf-8"),
                    str(password_hash).encode(
                        "utf-8"
                    ),
                )

            except Exception:
                return False

        def legacy_hash_password(
            password,
            salt,
        ):
            """
            Compatibility only.

            Existing Nova accounts created before
            bcrypt migration used SHA-256 with a
            per-user salt.
            """

            import hashlib

            raw = (
                str(salt)
                + "::"
                + str(password)
            ).encode("utf-8")

            return hashlib.sha256(
                raw
            ).hexdigest()

        def verify_password(
            password,
            user,
        ):

            password_hash = str(
                user.get("password_hash")
                or ""
            )

            if password_hash.startswith(
                "$2a$"
            ) or password_hash.startswith(
                "$2b$"
            ) or password_hash.startswith(
                "$2y$"
            ):

                return (
                    verify_bcrypt_password(
                        password,
                        password_hash,
                    ),
                    False,
                )

            legacy_hash = legacy_hash_password(
                password,
                user.get("salt", ""),
            )

            if (
                legacy_hash
                == password_hash
            ):
                return True, True

            return False, False

        def public_user(user):

            if not user:
                return None

            return {
                "id": user.get("id"),
                "username": user.get(
                    "username"
                ),
                "email": user.get("email"),
                "plan": user.get(
                    "plan",
                    "free",
                ),
                "credits": user.get(
                    "credits",
                    0,
                ),
                "subscription_status": user.get(
                    "subscription_status",
                    "inactive",
                ),
                "mfa_enabled": bool(
                    user.get(
                        "mfa_enabled",
                        False,
                    )
                ),
            }

        def find_user(identifier):

            ident = clean(
                identifier
            ).lower()

            if not ident:
                return None

            for user in load_users().get(
                "users",
                [],
            ):

                username = clean(
                    user.get("username")
                ).lower()

                email = clean(
                    user.get("email")
                ).lower()

                if (
                    username
                    and username == ident
                ):
                    return user

                if (
                    email
                    and email == ident
                ):
                    return user

            return None

        def current_user():

            uid = session.get(
                "nova_user_id"
            )

            if not uid:
                return None

            for user in load_users().get(
                "users",
                [],
            ):

                if user.get("id") == uid:
                    return user

            return None

        def establish_session(user):

            session.clear()

            session["nova_user_id"] = user[
                "id"
            ]

            session["authenticated"] = True

            session["auth_mode"] = (
                user.get("auth_provider")
                or "local"
            )

        def auth_status():

            user = current_user()

            return jsonify({
                "ok": True,
                "authenticated": bool(user),
                "user": (
                    public_user(user)
                    if user
                    else None
                ),
                "mode": (
                    user.get(
                        "auth_provider",
                        "local",
                    )
                    if user
                    else "local"
                ),
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
            ).lower()

            password = str(
                payload.get("password")
                or ""
            )

            if not username and email:
                username = email.split(
                    "@",
                    1,
                )[0]

            if not username:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Username is required."
                    ),
                }), 400

            if (
                not email
                or "@" not in email
            ):
                return jsonify({
                    "ok": False,
                    "error": (
                        "A valid email is required."
                    ),
                }), 400

            if len(password) < 8:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Password must be at least "
                        "8 characters."
                    ),
                }), 400

            data = load_users()

            if (
                find_user(username)
                or find_user(email)
            ):
                return jsonify({
                    "ok": False,
                    "error": (
                        "User already exists."
                    ),
                }), 409

            verification = (
                email_verification_service
                .create_verification()
            )

            user = {
                "id": (
                    "user_"
                    + secrets.token_hex(12)
                ),
                "username": username,
                "email": email,
                "email_verified": False,
                "email_verification_token_hash": (
                    verification["token_hash"]
                ),
                "email_verification_expires_at": (
                    verification["expires_at"]
                ),
                "password_hash": hash_password(
                    password
                ),
                "password_algorithm": "bcrypt",
                "plan": "free",
                "credits": 100000,
                "subscription_status": "inactive",
                "mfa_enabled": False,
                "mfa_secret": "",
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            data["users"].append(user)

            save_users(data)

            establish_session(user)

            return jsonify({
                "ok": True,
                "authenticated": True,
                "email_verification_required": True,
                "verification_url": (
                    "/verify-email?token="
                    + verification["token"]
                ),
                "user": public_user(user),
            })

        def auth_verify_email():

            payload = request.get_json(
                silent=True
            ) or {}

            token = clean(
                payload.get("token")
            )

            if not token:

                return jsonify({
                    "ok": False,
                    "error": (
                        "Verification token is required."
                    ),
                }), 400

            data = load_users()

            verified_user = None

            for user in data.get(
                "users",
                [],
            ):

                if bool(
                    user.get(
                        "email_verified",
                        False,
                    )
                ):
                    continue

                valid = (
                    email_verification_service.verify_token(
                        token,
                        user.get(
                            "email_verification_token_hash"
                        ),
                        user.get(
                            "email_verification_expires_at"
                        ),
                    )
                )

                if not valid:
                    continue

                user["email_verified"] = True

                user[
                    "email_verified_at"
                ] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                user[
                    "email_verification_token_hash"
                ] = ""

                user[
                    "email_verification_expires_at"
                ] = ""

                verified_user = user

                break

            if not verified_user:

                return jsonify({
                    "ok": False,
                    "error": (
                        "Invalid or expired verification link."
                    ),
                }), 400

            save_users(data)

            return jsonify({
                "ok": True,
                "message": (
                    "Email verified successfully."
                ),
                "user": public_user(
                    verified_user
                ),
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
                    "error": (
                        "Invalid username or password."
                    ),
                }), 401

            password_valid, migrate_password = (
                verify_password(
                    password,
                    user,
                )
            )

            if not password_valid:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Invalid username or password."
                    ),
                }), 401

            if migrate_password:

                data = load_users()

                for item in data.get(
                    "users",
                    [],
                ):

                    if (
                        item.get("id")
                        == user.get("id")
                    ):

                        item["password_hash"] = (
                            hash_password(password)
                        )

                        item[
                            "password_algorithm"
                        ] = "bcrypt"

                        item.pop(
                            "salt",
                            None,
                        )

                        user = item

                        save_users(data)

                        break

            if bool(
                user.get(
                    "mfa_enabled",
                    False,
                )
            ):

                session.clear()

                session[
                    "nova_pending_mfa_user_id"
                ] = user["id"]

                session[
                    "nova_pending_mfa_at"
                ] = (
                    datetime.now(
                        timezone.utc
                    ).timestamp()
                )

                return jsonify({
                    "ok": True,
                    "authenticated": False,
                    "mfa_required": True,
                })

            establish_session(user)

            return jsonify({
                "ok": True,
                "authenticated": True,
                "mfa_required": False,
                "user": public_user(user),
            })

        def auth_password_reset_request():

            payload = request.get_json(
                silent=True
            ) or {}

            email = clean(
                payload.get("email")
            ).lower()

            user = find_user(email)

            if not user:
                return jsonify({
                    "ok": True,
                    "message": (
                        "If the account exists, "
                        "a reset request was created."
                    ),
                })

            token = secrets.token_urlsafe(32)

            user[
                "password_reset_token"
            ] = token

            user[
                "password_reset_expires"
            ] = (
                datetime.now(
                    timezone.utc
                ).timestamp()
                + 3600
            )

            data = load_users()

            for item in data["users"]:

                if (
                    item["id"]
                    == user["id"]
                ):
                    item.update(user)

            save_users(data)

            response = {
                "ok": True,
                "message": (
                    "If the account exists, "
                    "a reset request was created."
                ),
            }

            if app.config.get(
                "TESTING"
            ) or app.config.get(
                "NOVA_EXPOSE_RESET_TOKEN",
                False,
            ):
                response["token"] = token

            return jsonify(response)

        def auth_password_reset_confirm():

            payload = request.get_json(
                silent=True
            ) or {}

            token = clean(
                payload.get("token")
            )

            password = str(
                payload.get("password")
                or ""
            )

            if len(password) < 8:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Password must be at least "
                        "8 characters."
                    ),
                }), 400

            data = load_users()

            for user in data["users"]:

                if (
                    user.get(
                        "password_reset_token"
                    )
                    != token
                ):
                    continue

                expires = float(
                    user.get(
                        "password_reset_expires",
                        0,
                    )
                    or 0
                )

                if (
                    datetime.now(
                        timezone.utc
                    ).timestamp()
                    > expires
                ):
                    return jsonify({
                        "ok": False,
                        "error": (
                            "Reset token expired."
                        ),
                    }), 400

                user["password_hash"] = (
                    hash_password(password)
                )

                user[
                    "password_algorithm"
                ] = "bcrypt"

                user.pop(
                    "salt",
                    None,
                )

                user[
                    "password_reset_token"
                ] = ""

                user[
                    "password_reset_expires"
                ] = ""

                save_users(data)

                return jsonify({
                    "ok": True,
                    "message": (
                        "Password updated."
                    ),
                })

            return jsonify({
                "ok": False,
                "error": (
                    "Invalid reset token."
                ),
            }), 400

        def auth_logout():

            session.clear()

            return jsonify({
                "ok": True,
                "authenticated": False,
                "user": None,
                "redirect_to": "/login",
            })

        def auth_mfa_setup():

            user_id = session.get(
                "nova_user_id"
            )

            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Not authenticated"
                    ),
                }), 401

            data = load_users()

            for user in data.get(
                "users",
                [],
            ):

                if user.get("id") != user_id:
                    continue

                secret = generate_secret()

                user["mfa_secret"] = secret

                user[
                    "mfa_enabled"
                ] = False

                save_users(data)

                return jsonify({
                    "ok": True,
                    "secret": secret,
                    "uri": (
                        build_provisioning_uri(
                            user.get(
                                "username",
                                "Nova",
                            ),
                            secret,
                        )
                    ),
                })

            return jsonify({
                "ok": False,
                "error": (
                    "User not found"
                ),
            }), 404

        def auth_mfa_verify_setup():

            user_id = session.get(
                "nova_user_id"
            )

            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Not authenticated"
                    ),
                }), 401

            payload = request.get_json(
                silent=True
            ) or {}

            code = clean(
                payload.get("code")
            )

            data = load_users()

            for user in data.get(
                "users",
                [],
            ):

                if user.get("id") != user_id:
                    continue

                if not verify_code(
                    user.get(
                        "mfa_secret",
                        "",
                    ),
                    code,
                ):
                    return jsonify({
                        "ok": False,
                        "error": (
                            "Invalid MFA code."
                        ),
                    }), 400

                user[
                    "mfa_enabled"
                ] = True

                save_users(data)

                return jsonify({
                    "ok": True,
                    "mfa_enabled": True,
                })

            return jsonify({
                "ok": False,
                "error": (
                    "User not found"
                ),
            }), 404

        def auth_mfa_verify_login():

            user_id = session.get(
                "nova_pending_mfa_user_id"
            )

            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": (
                        "No MFA login is pending."
                    ),
                }), 401

            pending_at = session.get(
                "nova_pending_mfa_at",
                0,
            )

            now = datetime.now(
                timezone.utc
            ).timestamp()

            if (
                now - float(pending_at or 0)
                > 600
            ):
                session.clear()

                return jsonify({
                    "ok": False,
                    "error": (
                        "MFA login challenge expired."
                    ),
                }), 401

            payload = request.get_json(
                silent=True
            ) or {}

            code = clean(
                payload.get("code")
            )

            data = load_users()

            for user in data.get(
                "users",
                [],
            ):

                if user.get("id") != user_id:
                    continue

                if not bool(
                    user.get(
                        "mfa_enabled",
                        False,
                    )
                ):
                    session.clear()

                    return jsonify({
                        "ok": False,
                        "error": (
                            "MFA is not enabled."
                        ),
                    }), 400

                if not verify_code(
                    user.get(
                        "mfa_secret",
                        "",
                    ),
                    code,
                ):
                    return jsonify({
                        "ok": False,
                        "error": (
                            "Invalid MFA code."
                        ),
                    }), 401

                establish_session(user)

                return jsonify({
                    "ok": True,
                    "authenticated": True,
                    "user": public_user(user),
                })

            session.clear()

            return jsonify({
                "ok": False,
                "error": (
                    "User not found."
                ),
            }), 404

        def auth_mfa_disable():

            user_id = session.get(
                "nova_user_id"
            )

            if not user_id:
                return jsonify({
                    "ok": False,
                    "error": (
                        "Not authenticated"
                    ),
                }), 401

            payload = request.get_json(
                silent=True
            ) or {}

            code = clean(
                payload.get("code")
            )

            data = load_users()

            for user in data.get(
                "users",
                [],
            ):

                if user.get("id") != user_id:
                    continue

                if not verify_code(
                    user.get(
                        "mfa_secret",
                        "",
                    ),
                    code,
                ):
                    return jsonify({
                        "ok": False,
                        "error": (
                            "Invalid MFA code."
                        ),
                    }), 400

                user[
                    "mfa_enabled"
                ] = False

                user[
                    "mfa_secret"
                ] = ""

                save_users(data)

                return jsonify({
                    "ok": True,
                    "mfa_enabled": False,
                })

            return jsonify({
                "ok": False,
                "error": (
                    "User not found."
                ),
            }), 404

        routes = [
            (
                "/api/auth/status",
                "nova_auth_status_20260908",
                auth_status,
                ["GET"],
            ),
            (
                "/api/auth/register",
                "nova_auth_register_20260908",
                auth_register,
                ["POST"],
            ),
            (
                "/api/auth/verify-email",
                "nova_auth_verify_email_20260908",
                auth_verify_email,
                ["POST"],
            ),
            (
                "/api/auth/login",
                "nova_auth_login_20260908",
                auth_login,
                ["POST"],
            ),
            (
                "/api/auth/logout",
                "nova_auth_logout_20260908",
                auth_logout,
                ["POST"],
            ),
            (
                "/api/auth/password-reset/request",
                "nova_auth_password_reset_request_20260908",
                auth_password_reset_request,
                ["POST"],
            ),
            (
                "/api/auth/password-reset/confirm",
                "nova_auth_password_reset_confirm_20260908",
                auth_password_reset_confirm,
                ["POST"],
            ),
            (
                "/api/auth/mfa/setup",
                "nova_auth_mfa_setup_20260908",
                auth_mfa_setup,
                ["GET"],
            ),
            (
                "/api/auth/mfa/verify-setup",
                "nova_auth_mfa_verify_setup_20260908",
                auth_mfa_verify_setup,
                ["POST"],
            ),
            (
                "/api/auth/mfa/verify-login",
                "nova_auth_mfa_verify_login_20260908",
                auth_mfa_verify_login,
                ["POST"],
            ),
            (
                "/api/auth/mfa/disable",
                "nova_auth_mfa_disable_20260908",
                auth_mfa_disable,
                ["POST"],
            ),
        ]

        for rule, name, handler, methods in routes:

            if not route_exists(rule):

                app.add_url_rule(
                    rule,
                    name,
                    handler,
                    methods=methods,
                )