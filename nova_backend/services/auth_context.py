
from flask import session


def get_current_user_id() -> str:
    try:
        user_id = (
            session.get("nova_user_id")
            or session.get("user_id")
            or ""
        )

        return str(user_id).strip()

    except Exception:
        return ""