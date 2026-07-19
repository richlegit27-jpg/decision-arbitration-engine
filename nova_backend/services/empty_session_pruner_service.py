import json
from pathlib import Path


data_dir = Path(__file__).resolve().parents[2] / "data"
sessions_path = data_dir / "nova_sessions.json"


def load_store():
    try:
        if not sessions_path.exists():
            return {
                "active_session_id": "",
                "sessions": [],
            }

        data = json.loads(
            sessions_path.read_text(
                encoding="utf-8-sig"
            )
        )

        if not isinstance(data, dict):
            return {
                "active_session_id": "",
                "sessions": [],
            }

        if not isinstance(data.get("sessions"), list):
            data["sessions"] = []

        data.setdefault(
            "active_session_id",
            ""
        )

        return data

    except Exception:
        return {
            "active_session_id": "",
            "sessions": [],
        }


def save_store(store):
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

        tmp.replace(
            sessions_path
        )

        return True

    except Exception:
        return False

def is_empty_new_chat(item):
    if not isinstance(item, dict):
        return False

    title = str(item.get("title") or "").strip().lower()
    messages = item.get("messages")

    if title not in ("", "new chat"):
        return False

    if isinstance(messages, list) and len(messages) > 0:
        return False

    if item.get("pinned"):
        return False

    active_execution = item.get("active_execution")
    if active_execution not in (None, {}, [], ""):
        return False

    working_state = item.get("working_state")
    if isinstance(working_state, dict):
        meaningful = [
            str(working_state.get("active_task") or "").strip(),
            str(working_state.get("checkpoint") or "").strip(),
            str(working_state.get("current_bug") or "").strip(),
            str(working_state.get("current_file") or "").strip(),
            str(working_state.get("last_success") or "").strip(),
            str(working_state.get("next_move") or "").strip(),
        ]

        if any(meaningful):
            return False

    return True


def owner_key(item):
    user_id = str(item.get("user_id") or "").strip()
    username = str(item.get("username") or "").strip().lower()

    return user_id or username or "legacy_unowned"


def sort_key(item):
    return str(
        item.get("updated_at")
        or item.get("created_at")
        or ""
    )


def prune_empty_new_chat_spam():
    store = load_store()
    sessions = store.get("sessions", [])

    if not isinstance(sessions, list):
        return 0

    empty_by_owner = {}

    for item in sessions:
        if is_empty_new_chat(item):
            empty_by_owner.setdefault(
                owner_key(item),
                [],
            ).append(item)

    keep_ids = set()
    remove_ids = set()

    for key, items in empty_by_owner.items():
        if not items:
            continue

        newest = sorted(
            items,
            key=sort_key,
            reverse=True,
        )[0]

        keep_ids.add(
            str(newest.get("id") or "")
        )

        for old in items:
            old_id = str(old.get("id") or "")

            if old_id and old_id != str(newest.get("id") or ""):
                remove_ids.add(old_id)

    valid_ids = [
        str(item.get("id") or "")
        for item in sessions
        if isinstance(item, dict)
        and str(item.get("id") or "")
    ]

    old_active = str(
        store.get("active_session_id") or ""
    )

    if old_active and old_active not in set(valid_ids):
        store["active_session_id"] = (
            valid_ids[0]
            if valid_ids
            else ""
        )

        save_store(store)
        return 0

    if not remove_ids:
        return 0

    new_sessions = [
        item
        for item in sessions
        if not (
            isinstance(item, dict)
            and str(item.get("id") or "") in remove_ids
        )
    ]

    if old_active in remove_ids:
        preferred = ""

        for item in new_sessions:
            if str(item.get("id") or "") in keep_ids:
                preferred = str(item.get("id") or "")
                break

        if not preferred and new_sessions:
            preferred = str(new_sessions[0].get("id") or "")

        store["active_session_id"] = preferred

    store["sessions"] = new_sessions
    save_store(store)

    return len(remove_ids)

def install(app):
    from flask import request

    @app.after_request
    def nova_prune_empty_session_spam_after_request_20260610(response):
        path = str(request.path or "")

        if request.method != "GET" and path in (
            "/api/sessions/new",
            "/api/sessions/switch",
            "/api/sessions/rename",
            "/api/sessions/pin",
            "/api/sessions/delete",
        ):
            return response

        if (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
            or path == "/mobile"
        ):
            removed = prune_empty_new_chat_spam()

            if removed:
                try:
                    app.logger.info(
                        "[Nova Session Spam Pruner] removed %s duplicate empty New Chat sessions",
                        removed,
                    )
                except Exception:
                    pass

        return response
    from flask import request

    @app.after_request
    def nova_prune_empty_session_spam_after_request_20260610(response):
        path = str(request.path or "")

        if request.method != "GET" and path in (
            "/api/sessions/new",
            "/api/sessions/switch",
            "/api/sessions/rename",
            "/api/sessions/pin",
            "/api/sessions/delete",
        ):
            return response

        if (
            path.startswith("/api/sessions")
            or path.startswith("/api/chat")
            or path.startswith("/api/chat/stream")
            or path == "/mobile"
        ):
            removed = prune_empty_new_chat_spam()

            if removed:
                try:
                    app.logger.info(
                        "[Nova Session Spam Pruner] removed %s duplicate empty New Chat sessions",
                        removed,
                    )
                except Exception:
                    pass

        return response