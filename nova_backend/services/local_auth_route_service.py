import json
import secrets
import base64
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from filelock import FileLock, Timeout
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
            consume_recovery_code,
            decrypt_totp_secret,
            encrypt_totp_secret,
            generate_recovery_codes,
            hash_recovery_code,
            verify_code_counter,
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

            try:
                from nova_backend.services.billing_service import get_account

                billing_account = get_account(
                    username=user.get("username"),
                    user_id=user.get("id"),
                )
            except Exception:
                billing_account = None

            return {
                "id": user.get("id"),
                "username": user.get(
                    "username"
                ),
                "email": user.get("email"),
                "plan": (
                    billing_account.get("plan")
                    if isinstance(billing_account, dict)
                    else None
                ),
                "credits": (
                    billing_account.get("credits")
                    if isinstance(billing_account, dict)
                    else None
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
            session["username"] = str(user.get("username") or "")

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

            return jsonify({
                "ok": True,
                "authenticated": False,
                "email_verification_required": True,
                "user": public_user(user),
                **(
                    {
                        "verification_url": (
                            "/verify-email?token="
                            + verification["token"]
                        )
                    }
                    if app.testing
                    or (
                        app.debug
                        and app.config.get(
                            "NOVA_EXPOSE_EMAIL_VERIFICATION_TOKEN",
                            False,
                        )
                    )
                    else {}
                ),
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

            if (
                "email_verified" in user
                and not bool(user.get("email_verified"))
            ):
                return jsonify({
                    "ok": False,
                    "error": "Verify your email address before signing in.",
                    "email_verification_required": True,
                }), 403

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

            user["password_reset_token_hash"] = (
                email_verification_service.hash_token(token)
            )
            user.pop("password_reset_token", None)

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

            if app.testing or (
                app.debug
                and app.config.get("NOVA_EXPOSE_RESET_TOKEN", False)
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

                stored_hash = str(
                    user.get("password_reset_token_hash") or ""
                )
                token_matches = bool(stored_hash) and secrets.compare_digest(
                    email_verification_service.hash_token(token),
                    stored_hash,
                )
                if not stored_hash:
                    # One-time compatibility for unexpired tokens issued before
                    # reset tokens were changed to hashed-at-rest storage.
                    token_matches = secrets.compare_digest(
                        str(user.get("password_reset_token") or ""),
                        token,
                    )
                if not token_matches:
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

                user.pop("password_reset_token", None)
                user.pop("password_reset_token_hash", None)

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

            payload = request.get_json(silent=True) or {}
            current_password = str(payload.get("current_password") or "")
            data = load_users()

            for user in data.get(
                "users",
                [],
            ):

                if user.get("id") != user_id:
                    continue

                password_valid, _ = verify_password(current_password, user)
                if not password_valid:
                    return jsonify({
                        "ok": False,
                        "error": "Confirm your current password before changing MFA settings.",
                    }), 403

                if bool(user.get("mfa_enabled", False)):
                    return jsonify({
                        "ok": False,
                        "error": "MFA is already enabled. Verify an existing factor before changing it.",
                    }), 409

                secret = generate_secret()
                try:
                    encrypted_secret = encrypt_totp_secret(secret)
                except Exception:
                    return jsonify({
                        "ok": False,
                        "error": "MFA setup is unavailable until Nova's encryption key is configured.",
                    }), 503

                user["mfa_pending_secret"] = encrypted_secret
                user["mfa_pending_expires_at"] = (
                    datetime.now(timezone.utc).timestamp() + 600
                )

                save_users(data)

                provisioning_uri = build_provisioning_uri(
                    user.get("username", "Nova"),
                    secret,
                )
                enrollment_payload = {
                    "ok": True,
                    "secret": secret,
                    "uri": provisioning_uri,
                }
                try:
                    import qrcode

                    image = qrcode.make(provisioning_uri)
                    image_bytes = BytesIO()
                    image.save(image_bytes, format="PNG")
                    enrollment_payload["qr_data_url"] = (
                        "data:image/png;base64,"
                        + base64.b64encode(image_bytes.getvalue()).decode("ascii")
                    )
                except Exception:
                    app.logger.warning("QR generation is unavailable for MFA setup.")

                return jsonify(enrollment_payload)

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

                pending_expires_at = float(
                    user.get("mfa_pending_expires_at", 0) or 0
                )
                if pending_expires_at < datetime.now(timezone.utc).timestamp():
                    return jsonify({
                        "ok": False,
                        "error": "MFA enrollment expired. Start setup again.",
                    }), 400

                try:
                    pending_secret = decrypt_totp_secret(
                        user.get("mfa_pending_secret", "")
                    )
                except Exception:
                    return jsonify({
                        "ok": False,
                        "error": "MFA setup could not be verified. Start setup again.",
                    }), 503

                counter = verify_code_counter(pending_secret, code)
                if counter is None:
                    return jsonify({
                        "ok": False,
                        "error": "Invalid MFA code.",
                    }), 400

                recovery_codes = generate_recovery_codes()
                user["mfa_secret"] = user.pop("mfa_pending_secret")
                user.pop("mfa_pending_expires_at", None)
                user["mfa_last_counter"] = counter
                user[
                    "mfa_enabled"
                ] = True
                user["mfa_recovery_code_hashes"] = [
                    hash_recovery_code(item) for item in recovery_codes
                ]

                save_users(data)

                return jsonify({
                    "ok": True,
                    "mfa_enabled": True,
                    "recovery_codes": recovery_codes,
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

            authenticated_user = None
            failure_status = 401
            failure_message = "Invalid MFA code."
            try:
                with FileLock(str(self.users_path) + ".lock", timeout=5):
                    data = load_users()
                    for user in data.get("users", []):
                        if user.get("id") != user_id:
                            continue
                        if not bool(user.get("mfa_enabled", False)):
                            session.clear()
                            return jsonify({
                                "ok": False,
                                "error": "MFA is not enabled.",
                            }), 400

                        stored_secret = str(user.get("mfa_secret", "") or "")
                        try:
                            active_secret = decrypt_totp_secret(stored_secret)
                        except Exception:
                            active_secret = ""
                        counter = verify_code_counter(
                            active_secret,
                            code,
                            last_counter=user.get("mfa_last_counter", -1),
                        )
                        accepted = counter is not None
                        if accepted:
                            user["mfa_last_counter"] = counter
                            if not stored_secret.startswith("fernet:"):
                                try:
                                    user["mfa_secret"] = encrypt_totp_secret(stored_secret)
                                except Exception:
                                    pass
                        else:
                            accepted = consume_recovery_code(user, code)
                        if not accepted:
                            break
                        save_users(data)
                        authenticated_user = dict(user)
                        break
                    else:
                        failure_status = 404
                        failure_message = "User not found."
            except Timeout:
                return jsonify({
                    "ok": False,
                    "error": "MFA verification is temporarily busy. Please retry.",
                }), 503

            if not authenticated_user:
                return jsonify({
                    "ok": False,
                    "error": failure_message,
                }), failure_status

            establish_session(authenticated_user)
            return jsonify({
                "ok": True,
                "authenticated": True,
                "user": public_user(authenticated_user),
            })

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

                try:
                    active_secret = decrypt_totp_secret(
                        user.get("mfa_secret", "")
                    )
                except Exception:
                    return jsonify({
                        "ok": False,
                        "error": "MFA is temporarily unavailable. Check Nova's encryption configuration.",
                    }), 503

                counter = verify_code_counter(
                    active_secret,
                    code,
                    last_counter=user.get("mfa_last_counter", -1),
                )
                if counter is None:
                    return jsonify({
                        "ok": False,
                        "error": (
                            "Invalid MFA code."
                        ),
                    }), 400

                user["mfa_last_counter"] = counter

                user[
                    "mfa_enabled"
                ] = False

                user[
                    "mfa_secret"
                ] = ""
                user["mfa_recovery_code_hashes"] = []
                user.pop("mfa_last_counter", None)

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
                ["POST"],
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
