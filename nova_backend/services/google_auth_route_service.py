import json
import secrets
from pathlib import Path

from flask import jsonify, redirect, session


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

            self.users_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                ),
                encoding="utf-8",
            )

        def find_email(email):

            for user in load_users().get(
                "users",
                [],
            ):
                if user.get(
                    "email"
                ) == email:
                    return user

            return None

        @self.app.route(
            "/api/auth/google",
            methods=["GET"],
        )
        def google_login():

            return google.authorize_redirect(
                "/api/auth/google/callback"
            )


        @self.app.route(
            "/api/auth/google/callback",
            methods=["GET"],
        )
        def google_callback():

            token = google.authorize_access_token()

            profile = google.parse_id_token(
                token
            )

            email = profile.get(
                "email",
                "",
            )

            name = profile.get(
                "name"
            ) or email.split(
                "@",
                1,
            )[0]

            user = find_email(
                email
            )

            if not user:

                data = load_users()

                user = {
                    "id": (
                        "user_"
                        + secrets.token_hex(12)
                    ),
                    "username": name,
                    "email": email,
                    "auth_provider": "google",
                    "plan": "free",
                    "credits": 100000,
                    "subscription_status": "inactive",
                }

                data["users"].append(
                    user
                )

                save_users(
                    data
                )


            session["nova_user_id"] = user["id"]
            session["authenticated"] = True
            session["auth_mode"] = "google"


            return jsonify({
                "ok": True,
                "authenticated": True,
                "user": user,
            })


        print(
            "[GOOGLE AUTH ROUTES] installed"
        )