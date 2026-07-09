from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702"

if marker in text:
    print("backend new chat owner inheritance already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702
# Backend guard: New Chat/session responses must not become anonymous
# when there is a known authenticated owner in the existing session file.
# Fills missing user_id/username on response payloads and session store.
# ============================================================
try:
    import os as _nova_owner_os
    import json as _nova_owner_json
    from pathlib import Path as _NovaOwnerPath
    from flask import request as _nova_owner_request

    def _nova_owner_nonempty_20260702(value):
        try:
            value = str(value or "").strip()
            return value if value else ""
        except Exception:
            return ""

    def _nova_owner_sessions_file_20260702():
        candidates = []

        try:
            env_path = _nova_owner_os.environ.get("NOVA_SESSIONS_FILE")
            if env_path:
                candidates.append(_NovaOwnerPath(env_path))
        except Exception:
            pass

        try:
            candidates.append(_NovaOwnerPath.cwd() / "data" / "nova_sessions.json")
        except Exception:
            pass

        try:
            candidates.append(_NovaOwnerPath("data/nova_sessions.json"))
        except Exception:
            pass

        for candidate in candidates:
            try:
                if candidate and candidate.exists():
                    return candidate
            except Exception:
                pass

        try:
            return _NovaOwnerPath.cwd() / "data" / "nova_sessions.json"
        except Exception:
            return _NovaOwnerPath("data/nova_sessions.json")

    def _nova_owner_load_store_20260702():
        path = _nova_owner_sessions_file_20260702()

        try:
            if not path.exists():
                return path, None
            return path, _nova_owner_json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return path, None

    def _nova_owner_write_store_20260702(path, store):
        try:
            if not path or store is None:
                return False

            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(_nova_owner_json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
            return True
        except Exception as exc:
            try:
                print("[NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702] write failed:", exc)
            except Exception:
                pass
            return False

    def _nova_owner_session_lists_20260702(container):
        lists = []

        try:
            if isinstance(container, list):
                lists.append(container)

            elif isinstance(container, dict):
                for key in ("sessions", "items", "messages"):
                    value = container.get(key)
                    if isinstance(value, list):
                        lists.append(value)

                # Some older stores are dicts keyed by session id.
                dict_values = []
                for value in container.values():
                    if isinstance(value, dict) and (
                        "id" in value or "title" in value or "messages" in value
                    ):
                        dict_values.append(value)

                if dict_values:
                    lists.append(dict_values)
        except Exception:
            pass

        return lists

    def _nova_owner_find_known_owner_20260702(*containers):
        owners = []

        def consider(item):
            try:
                if not isinstance(item, dict):
                    return

                user_id = _nova_owner_nonempty_20260702(item.get("user_id"))
                username = _nova_owner_nonempty_20260702(item.get("username"))

                meta = item.get("meta")
                if isinstance(meta, dict):
                    user_id = user_id or _nova_owner_nonempty_20260702(meta.get("user_id"))
                    username = username or _nova_owner_nonempty_20260702(meta.get("username"))

                if user_id or username:
                    owners.append((user_id, username))
            except Exception:
                pass

        for container in containers:
            try:
                if isinstance(container, dict):
                    consider(container)

                    session_obj = container.get("session")
                    if isinstance(session_obj, dict):
                        consider(session_obj)

                    assistant_message = container.get("assistant_message")
                    if isinstance(assistant_message, dict):
                        consider(assistant_message)

                for session_list in _nova_owner_session_lists_20260702(container):
                    for item in session_list:
                        consider(item)
            except Exception:
                pass

        # Prefer a complete owner.
        for user_id, username in reversed(owners):
            if user_id and username:
                return user_id, username

        # Otherwise allow partial owner.
        for user_id, username in reversed(owners):
            if user_id or username:
                return user_id, username

        return "", ""

    def _nova_owner_apply_to_item_20260702(item, user_id, username):
        try:
            if not isinstance(item, dict):
                return False

            changed = False

            if user_id and not _nova_owner_nonempty_20260702(item.get("user_id")):
                item["user_id"] = user_id
                changed = True

            if username and not _nova_owner_nonempty_20260702(item.get("username")):
                item["username"] = username
                changed = True

            return changed
        except Exception:
            return False

    def _nova_owner_apply_to_payload_20260702(payload, user_id, username):
        changed = False

        try:
            if not isinstance(payload, dict):
                return False

            changed = _nova_owner_apply_to_item_20260702(payload, user_id, username) or changed

            session_obj = payload.get("session")
            if isinstance(session_obj, dict):
                changed = _nova_owner_apply_to_item_20260702(session_obj, user_id, username) or changed

            for key in ("sessions", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    for item in value:
                        changed = _nova_owner_apply_to_item_20260702(item, user_id, username) or changed

            return changed
        except Exception:
            return changed

    def _nova_owner_apply_to_store_20260702(store, user_id, username):
        changed = False

        try:
            if not store:
                return False

            for session_list in _nova_owner_session_lists_20260702(store):
                for item in session_list:
                    if isinstance(item, dict):
                        # Only fill sessions that are currently anonymous.
                        if not _nova_owner_nonempty_20260702(item.get("user_id")) and not _nova_owner_nonempty_20260702(item.get("username")):
                            changed = _nova_owner_apply_to_item_20260702(item, user_id, username) or changed

            return changed
        except Exception:
            return changed

    def _nova_backend_new_chat_owner_inheritance_20260702(response):
        try:
            path = _nova_owner_request.path.rstrip("/")

            if not (
                path == "/api/sessions"
                or path == "/api/chat"
                or path.startswith("/api/sessions/")
            ):
                return response

            if getattr(response, "status_code", 200) >= 400:
                return response

            payload = response.get_json(silent=True)
            if not isinstance(payload, dict):
                return response

            store_path, store = _nova_owner_load_store_20260702()
            user_id, username = _nova_owner_find_known_owner_20260702(payload, store)

            if not user_id and not username:
                return response

            payload_changed = _nova_owner_apply_to_payload_20260702(payload, user_id, username)
            store_changed = _nova_owner_apply_to_store_20260702(store, user_id, username)

            if store_changed:
                _nova_owner_write_store_20260702(store_path, store)

            if payload_changed:
                try:
                    debug = payload.get("debug")
                    if not isinstance(debug, dict):
                        debug = {}
                    debug["backend_new_chat_owner_inheritance"] = True
                    debug["owner_user_id_present"] = bool(user_id)
                    debug["owner_username_present"] = bool(username)
                    payload["debug"] = debug
                except Exception:
                    pass

                body = _nova_owner_json.dumps(payload, ensure_ascii=False)
                response.set_data(body)
                response.mimetype = "application/json"

                try:
                    response.headers["Content-Length"] = str(len(body.encode("utf-8")))
                except Exception:
                    pass

            return response
        except Exception as exc:
            try:
                print("[NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702] failed:", exc)
            except Exception:
                pass
            return response

    app.after_request(_nova_backend_new_chat_owner_inheritance_20260702)
    print("[NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702] installed")

except Exception as _nova_backend_new_chat_owner_error_20260702:
    try:
        print("[NOVA_BACKEND_NEW_CHAT_OWNER_INHERITANCE_20260702] outer failed:", _nova_backend_new_chat_owner_error_20260702)
    except Exception:
        pass
'''

insert_anchor = 'if __name__ == "__main__":'

if insert_anchor in text:
    text = text.replace(insert_anchor, patch + "\n\n" + insert_anchor, 1)
else:
    text = text.rstrip() + "\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
print("patched backend new chat owner inheritance")
