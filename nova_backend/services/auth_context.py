
from flask import session


def project_api_auth_required(path: str, user_id: str = "") -> bool:
    normalized_path = str(path or "").strip()
    is_project_api = (
        normalized_path == "/api/projects"
        or normalized_path.startswith("/api/projects/")
    )
    return is_project_api and not str(user_id or "").strip()


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
