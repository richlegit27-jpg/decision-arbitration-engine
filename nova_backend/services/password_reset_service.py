import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt


class PasswordResetService:

    def __init__(
        self,
        app,
        request,
        jsonify,
    ):
        self.app = app
        self.request = request
        self.jsonify = jsonify

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

        self.resets_path = (
            self.data_dir
            / "nova_password_resets.json"
        )

        self.reset_expiry_minutes = 30

    def _load_json(
        self,
        path,
        default,
    ):
        if not path.exists():
            return default

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            return (
                data
                if isinstance(data, type(default))
                else default
            )

        except Exception:
            return default

    def _save_json(
        self,
        path,
        data,
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        temp_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temp_path.replace(path)

    def _load_users(self):
        data = self._load_json(
            self.users_path,
            {"users": []},
        )

        if not isinstance(
            data.get("users"),
            list,
        ):
            data["users"] = []

        return data

    def _save_users(
        self,
        data,
    ):
        self._save_json(
            self.users_path,
            data,
        )

    def _load_resets(self):
        data = self._load_json(
            self.resets_path,
            {"resets": []},
        )

        if not isinstance(
            data.get("resets"),
            list,
        ):
            data["resets"] = []

        return data

    def _save_resets(
        self,
        data,
    ):
        self._save_json(
            self.resets_path,
            data,
        )

    def _hash_token(
        self,
        token,
    ):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    def _utc_now(self):
        return datetime.now(
            timezone.utc
        )

    def _parse_time(
        self,
        value,
    ):
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except Exception:
            return None

    def _clean_expired_resets(
        self,
        resets,
    ):
        now = self._utc_now()

        active = []

        for record in resets:

            expires_at = self._parse_time(
                record.get("expires_at")
            )

            if not expires_at:
                continue

            if expires_at <= now:
                continue

            if record.get("used_at"):
                continue

            active.append(record)

        return active

    def _find_user_by_email(
        self,
        email,
    ):
        normalized = str(
            email or ""
        ).strip().lower()

        if not normalized:
            return None, None

        users_data = self._load_users()

        for user in users_data["users"]:

            user_email = str(
                user.get("email")
                or ""
            ).strip().lower()

            if (
                user_email
                and user_email == normalized
            ):
                return user, users_data

        return None, users_data

    def request_reset(
        self,
        email,
    ):
        normalized_email = str(
            email or ""
        ).strip().lower()

        if not normalized_email:
            return None

        user, _ = self._find_user_by_email(
            normalized_email
        )

        if not user:
            return None

        token = secrets.token_urlsafe(48)

        now = self._utc_now()

        expires_at = (
            now
            + timedelta(
                minutes=self.reset_expiry_minutes
            )
        )

        resets_data = self._load_resets()

        active_resets = self._clean_expired_resets(
            resets_data["resets"]
        )

        user_id = str(
            user.get("id")
            or ""
        )

        active_resets = [
            record
            for record in active_resets
            if str(
                record.get("user_id")
                or ""
            ) != user_id
        ]

        active_resets.append(
            {
                "id": secrets.token_hex(16),
                "user_id": user_id,
                "email": normalized_email,
                "token_hash": self._hash_token(
                    token
                ),
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "used_at": None,
            }
        )

        resets_data["resets"] = active_resets

        self._save_resets(
            resets_data
        )

        return token

    def reset_password(
        self,
        token,
        new_password,
    ):
        token = str(
            token or ""
        ).strip()

        new_password = str(
            new_password or ""
        )

        if not token:
            return (
                False,
                "Invalid or expired reset link.",
            )

        if len(new_password) < 8:
            return (
                False,
                "Password must be at least 8 characters.",
            )

        token_hash = self._hash_token(
            token
        )

        resets_data = self._load_resets()

        active_resets = self._clean_expired_resets(
            resets_data["resets"]
        )

        reset_record = None

        for record in active_resets:

            if secrets.compare_digest(
                str(
                    record.get("token_hash")
                    or ""
                ),
                token_hash,
            ):
                reset_record = record
                break

        if not reset_record:
            resets_data["resets"] = active_resets

            self._save_resets(
                resets_data
            )

            return (
                False,
                "Invalid or expired reset link.",
            )

        user_id = str(
            reset_record.get("user_id")
            or ""
        )

        users_data = self._load_users()

        target_user = None

        for user in users_data["users"]:

            if str(
                user.get("id")
                or ""
            ) == user_id:

                target_user = user
                break

        if not target_user:

            resets_data["resets"] = [
                record
                for record in active_resets
                if record is not reset_record
            ]

            self._save_resets(
                resets_data
            )

            return (
                False,
                "Account not found.",
            )

        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        now = self._utc_now()

        target_user["password_hash"] = (
            password_hash
        )

        target_user.pop(
            "salt",
            None,
        )

        target_user["password_changed_at"] = (
            now.isoformat()
        )

        self._save_users(
            users_data
        )

        resets_data["resets"] = [
            record
            for record in active_resets
            if str(
                record.get("user_id")
                or ""
            ) != user_id
        ]

        self._save_resets(
            resets_data
        )

        return (
            True,
            "Password reset successfully.",
        )

    def install_routes(self):

        app = self.app
        request = self.request
        jsonify = self.jsonify

        existing_rules = {
            str(rule.rule)
            for rule in app.url_map.iter_rules()
        }

        if "/api/auth/forgot-password" not in existing_rules:

            @app.post(
                "/api/auth/forgot-password"
            )
            def nova_forgot_password():

                payload = (
                    request.get_json(
                        silent=True
                    )
                    or {}
                )

                email = str(
                    payload.get("email")
                    or ""
                ).strip().lower()

                if not email:
                    return jsonify(
                        {
                            "ok": False,
                            "error": (
                                "Email is required."
                            ),
                        }
                    ), 400

                token = self.request_reset(
                    email
                )

                response = {
                    "ok": True,
                    "message": (
                        "If an account exists for "
                        "that email, a password reset "
                        "link has been sent."
                    ),
                }

                if token:

                    response[
                        "reset_token"
                    ] = token

                    response[
                        "reset_url"
                    ] = (
                        "/reset-password?token="
                        + token
                    )

                return jsonify(
                    response
                )

        if "/api/auth/reset-password" not in existing_rules:

            @app.post(
                "/api/auth/reset-password"
            )
            def nova_reset_password():

                payload = (
                    request.get_json(
                        silent=True
                    )
                    or {}
                )

                token = payload.get("token")

                new_password = (
                    payload.get("new_password")
                )

                ok, message = (
                    self.reset_password(
                        token,
                        new_password,
                    )
                )

                if not ok:

                    return jsonify(
                        {
                            "ok": False,
                            "error": message,
                        }
                    ), 400

                return jsonify(
                    {
                        "ok": True,
                        "message": message,
                    }
                )