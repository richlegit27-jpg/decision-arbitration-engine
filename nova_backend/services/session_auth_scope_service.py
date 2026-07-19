import json
from pathlib import Path
from flask import session


BASE_DIR = Path(__file__).resolve().parents[2]

data_dir = BASE_DIR / "data"
sessions_path = data_dir / "nova_sessions.json"
users_path = data_dir / "nova_auth_users.json"


def load_json(path, fallback):
    try:
        if not path.exists():
            return fallback

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return data if isinstance(data, type(fallback)) else fallback

    except Exception:
        return fallback


def write_sessions_store(store):
    try:
        data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        tmp = sessions_path.with_suffix(
            sessions_path.suffix + ".tmp"
        )

        tmp.write_text(
            json.dumps(
                store,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        tmp.replace(sessions_path)
        return True

    except Exception:
        return False


def current_auth_user():
    uid = session.get("nova_user_id")

    if not uid:
        return None

    users_data = load_json(
        users_path,
        {"users": []},
    )

    users = (
        users_data.get("users", [])
        if isinstance(users_data, dict)
        else []
    )

    for user in users:
        if not isinstance(user, dict):
            continue

        if str(user.get("id") or "") == str(uid):
            return {
                "id": str(user.get("id") or ""),
                "username": str(user.get("username") or ""),
                "email": str(user.get("email") or ""),
            }

    return {
        "id": str(uid),
        "username": "",
        "email": "",
    }


def is_unowned(item):
    if not isinstance(item, dict):
        return False

    return (
        not str(item.get("user_id") or "").strip()
        and not str(item.get("username") or "").strip()
    )


def is_visible_to_user(item, user):
    if not isinstance(item, dict):
        return False

    if not user:
        return False

    item_user_id = str(item.get("user_id") or "").strip()
    item_username = str(item.get("username") or "").strip().lower()

    if not item_user_id and not item_username:
        return False

    if item_user_id and item_user_id == str(user.get("id") or ""):
        return True

    if item_username and item_username == str(user.get("username") or "").strip().lower():
        return True

    return False


def claim_session(item, user):
    if not isinstance(item, dict) or not user:
        return False

    changed = False

    if not str(item.get("user_id") or "").strip():
        item["user_id"] = str(user.get("id") or "")
        changed = True

    if not str(item.get("username") or "").strip():
        item["username"] = str(user.get("username") or "")
        changed = True

    meta = item.get("meta")

    if not isinstance(meta, dict):
        meta = {}
        item["meta"] = meta
        changed = True

    if not str(meta.get("owner_source") or "").strip():
        meta["owner_source"] = "local_auth"
        changed = True

    return changed


def normalize_store_for_user(user):
    store = load_json(
        sessions_path,
        {
            "active_session_id": "",
            "sessions": [],
        },
    )

    if not isinstance(store, dict):
        store = {
            "active_session_id": "",
            "sessions": [],
        }

    sessions = store.get("sessions", [])

    if not isinstance(sessions, list):
        sessions = []

    changed = False

    visible = [
        item
        for item in sessions
        if is_visible_to_user(item, user)
    ]

    active_id = str(
        store.get("active_session_id")
        or ""
    ).strip()

    visible_ids = {
        str(item.get("id") or "")
        for item in visible
        if isinstance(item, dict)
    }

    if active_id not in visible_ids:
        new_active = (
            str(visible[0].get("id") or "").strip()
            if visible
            else ""
        )

        if store.get("active_session_id") != new_active:
            store["active_session_id"] = new_active
            changed = True

    store["sessions"] = sessions

    if changed:
        write_sessions_store(store)

    return store, visible

class SessionAuthScopeService:

    def install(self, app):
        from flask import request, g

        @app.before_request
        def nova_session_auth_scope_before_request_20260610():
            path = str(request.path or "")

            if not (
                path.startswith("/api/sessions")
                or path.startswith("/api/chat")
                or path.startswith("/api/chat/stream")
            ):
                return None

            user = current_auth_user()

            g.nova_auth_user = user

            normalize_store_for_user(user)

            return None

        @app.after_request
        def nova_session_auth_scope_after_request_20260610(response):
            try:
                data = response.get_json(silent=True)

                if (
                    isinstance(data, dict)
                    and data.get("skip_session_auth_scope_filter")
                ):
                    return response

            except Exception:
                pass

            path = str(request.path or "")

            if not path.startswith("/api/sessions"):
                return response

            if response.headers.get("X-Nova-Slim-Sessions") == "1":
                return response

            if request.method != "GET" and path in (
                "/api/sessions/new",
                "/api/sessions/switch",
                "/api/sessions/rename",
                "/api/sessions/pin",
                "/api/sessions/delete",
            ):
                return response

            user = (
                getattr(g, "nova_auth_user", None)
                or current_auth_user()
            )

            store, visible = normalize_store_for_user(user)

            try:
                payload = response.get_json(silent=True)
            except Exception:
                payload = None

            if not isinstance(payload, dict):
                return response

            visible_ids = {
                str(item.get("id") or "")
                for item in visible
                if isinstance(item, dict)
            }

            if isinstance(payload.get("sessions"), list):
                payload["sessions"] = [
                    item
                    for item in payload["sessions"]
                    if (
                        isinstance(item, dict)
                        and str(item.get("id") or "") in visible_ids
                    )
                ]

                response.set_data(
                    json.dumps(payload)
                )
                response.headers["Content-Type"] = "application/json"

            return response