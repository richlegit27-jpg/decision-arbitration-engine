from flask import session


def get_current_user_id() -> str:
    try:
        return str(
            session.get("nova_user_id")
            or session.get("user_id")
            or ""
        ).strip()
    except Exception:
        return ""