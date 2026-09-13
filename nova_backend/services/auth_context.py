from flask import session


def get_current_user_id() -> str:
    try:
        user_id = (
            session.get("nova_user_id")
            or session.get("user_id")
            or ""
        )

        user_id = str(user_id).strip()

        if user_id:
            return user_id

        # Local Nova mode uses the default owner when
        # no authenticated session exists.
        return "default"

    except Exception:
        return "default"