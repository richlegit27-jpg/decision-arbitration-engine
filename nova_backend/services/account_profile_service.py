import json
from pathlib import Path

from flask import jsonify
from nova_backend.services.auth_context import get_current_user_id


class AccountProfileService:

    def __init__(self, users_path=None):
        self.users_path = (
            Path(users_path)
            if users_path is not None
            else Path(__file__).resolve().parents[2]
            / "data"
            / "nova_auth_users.json"
        )

    def get_profile(self):
        user_id = str(get_current_user_id() or "").strip()
        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Authentication is required to view account details.",
            }), 401

        try:
            users_data = json.loads(
                self.users_path.read_text(encoding="utf-8")
            )
            user = next(
                (
                    item
                    for item in users_data.get("users", [])
                    if str(item.get("id") or "") == user_id
                ),
                None,
            )
        except Exception:
            user = None

        if not user:
            return jsonify({
                "ok": False,
                "error": "Authenticated account was not found.",
            }), 401

        username = str(user.get("username") or "").strip()

        try:
            from nova_backend.services.billing_service import get_account

            billing = get_account(username=username, user_id=user_id)

        except Exception:
            return jsonify({
                "ok": False,
                "error": "Account billing details are temporarily unavailable.",
            }), 503

        return jsonify({
            "ok": True,
            "username": username,
            "plan": billing.get("plan", "free"),
            "credits": billing.get("credits", 0),
            "monthly_credits": billing.get("monthly_credits", 0),
            "created_at": billing.get("created_at", ""),
        })
