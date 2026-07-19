import json
from pathlib import Path

from flask import jsonify, session


class AccountProfileService:

    def get_profile(self):
        username = ""

        try:
            user_id = session.get("nova_user_id")

            if user_id:
                users_path = (
                    Path("data")
                    / "nova_auth_users.json"
                )

                if users_path.exists():
                    users_data = json.loads(
                        users_path.read_text(
                            encoding="utf-8"
                        )
                    )

                    for user in users_data.get("users", []):
                        if user.get("id") == user_id:
                            username = str(
                                user.get("username") or ""
                            ).strip()
                            break

        except Exception:
            pass

        if not username:
            username = str(
                session.get("username") or ""
            ).strip()

        if not username:
            username = "richard"

        try:
            from nova_backend.services.billing_service import get_account

            billing = get_account(username)

        except Exception:
            billing = {
                "plan": "free",
                "credits": 0,
                "monthly_credits": 0,
                "created_at": "",
            }

        return jsonify({
            "ok": True,
            "username": username,
            "plan": billing.get("plan", "free"),
            "credits": billing.get("credits", 0),
            "monthly_credits": billing.get("monthly_credits", 0),
            "created_at": billing.get("created_at", ""),
        })