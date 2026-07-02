from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_LIST_TITLE_POLISH_20260702"

if marker in text:
    print("session list title polish already installed")
    raise SystemExit(0)

patch = r'''

# ============================================================
# NOVA_SESSION_LIST_TITLE_POLISH_20260702
# Repair ugly session titles in /api/sessions:
# - "1" / "2" / numeric titles
# - non-empty "New Chat" sessions
# Uses the first meaningful user message as the title.
# Does not change auth, storage location, image generation, or routing.
# ============================================================
try:
    import os as _nova_title_polish_os
    import json as _nova_title_polish_json
    from pathlib import Path as _NovaTitlePolishPath
    from flask import request as _nova_title_polish_request

    def _nova_title_polish_text_20260702(value):
        try:
            value = str(value or "").strip()
            value = " ".join(value.split())
            return value
        except Exception:
            return ""

    def _nova_title_polish_clip_20260702(value):
        value = _nova_title_polish_text_20260702(value)

        if len(value) > 64:
            value = value[:61].rstrip() + "..."

        return value

    def _nova_title_polish_bad_20260702(value, message_count=0):
        value = _nova_title_polish_text_20260702(value)
        low = value.lower()

        if not value:
            return True

        if value.isdigit():
            return True

        if low in ("none", "null", "undefined", "untitled"):
            return True

        # A non-empty New Chat should become the first user message.
        if low == "new chat":
            try:
                return int(message_count or 0) > 0
            except Exception:
                return True

        return False

    def _nova_title_polish_sessions_file_20260702():
        candidates = []

        try:
            env_path = _nova_title_polish_os.environ.get("NOVA_SESSIONS_FILE")
            if env_path:
                candidates.append(_NovaTitlePolishPath(env_path))
        except Exception:
            pass

        try:
            candidates.append(_NovaTitlePolishPath.cwd() / "data" / "nova_sessions.json")
        except Exception:
            pass

        try:
            candidates.append(_NovaTitlePolishPath("data/nova_sessions.json"))
        except Exception:
            pass

        for candidate in candidates:
            try:
                if candidate.exists():
                    return candidate
            except Exception:
                pass

        try:
            return _NovaTitlePolishPath.cwd() / "data" / "nova_sessions.json"
        except Exception:
            return _NovaTitlePolishPath("data/nova_sessions.json")

    def _nova_title_polish_load_store_20260702():
        path = _nova_title_polish_sessions_file_20260702()

        try:
            if not path.exists():
                return path, None

            return path, _nova_title_polish_json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return path, None

    def _nova_title_polish_write_store_20260702(path, store):
        try:
            if path is None or store is None:
                return False

            path.parent.mkdir(parents=True, exist_ok=True)

            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(
                _nova_title_polish_json.dumps(store, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)
            return True
        except Exception as exc:
            try:
                print("[NOVA_SESSION_LIST_TITLE_POLISH_20260702] store write failed:", exc)
            except Exception:
                pass
            return False

    def _nova_title_polish_iter_sessions_20260702(container):
        seen = set()
        result = []

        def add(item):
            try:
                if not isinstance(item, dict):
                    return

                if not ("id" in item or "title" in item or "messages" in item):
                    return

                ident = id(item)
                if ident in seen:
                    return

                seen.add(ident)
                result.append(item)
            except Exception:
                pass

        try:
            if isinstance(container, list):
                for item in container:
                    add(item)

            elif isinstance(container, dict):
                add(container)

                for key in ("sessions", "items"):
                    value = container.get(key)
                    if isinstance(value, list):
                        for item in value:
                            add(item)

                session_obj = container.get("session")
                if isinstance(session_obj, dict):
                    add(session_obj)

                for value in container.values():
                    if isinstance(value, dict):
                        add(value)
        except Exception:
            pass

        return result

    def _nova_title_polish_first_user_text_20260702(session):
        try:
            if not isinstance(session, dict):
                return ""

            messages = session.get("messages")
            if isinstance(messages, list):
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue

                    role = _nova_title_polish_text_20260702(msg.get("role")).lower()
                    if role != "user":
                        continue

                    candidate = (
                        msg.get("text")
                        or msg.get("content")
                        or msg.get("message")
                        or ""
                    )
                    candidate = _nova_title_polish_clip_20260702(candidate)

                    if candidate and not candidate.isdigit():
                        return candidate

            working_state = session.get("working_state")
            if isinstance(working_state, dict):
                candidate = _nova_title_polish_clip_20260702(
                    working_state.get("last_user_message")
                    or working_state.get("active_task")
                    or working_state.get("checkpoint")
                    or ""
                )

                if candidate and not candidate.isdigit():
                    return candidate
        except Exception:
            pass

        return ""

    def _nova_title_polish_make_title_20260702(session, fallback_session=None):
        try:
            candidate = _nova_title_polish_first_user_text_20260702(session)

            if not candidate and isinstance(fallback_session, dict):
                candidate = _nova_title_polish_first_user_text_20260702(fallback_session)

            if candidate:
                return candidate

            current = _nova_title_polish_clip_20260702(
                session.get("title") if isinstance(session, dict) else ""
            )

            if current and not _nova_title_polish_bad_20260702(current, 0):
                return current

            return "New Chat"
        except Exception:
            return "New Chat"

    def _nova_title_polish_store_index_20260702(store):
        index = {}

        try:
            for item in _nova_title_polish_iter_sessions_20260702(store):
                sid = _nova_title_polish_text_20260702(item.get("id"))
                if sid:
                    index[sid] = item
        except Exception:
            pass

        return index

    def _nova_title_polish_repair_sessions_20260702(sessions, store_index=None):
        changed = False

        try:
            if store_index is None:
                store_index = {}

            for item in sessions:
                if not isinstance(item, dict):
                    continue

                try:
                    message_count = int(item.get("message_count") or 0)
                except Exception:
                    message_count = 0

                current_title = item.get("title")

                if not _nova_title_polish_bad_20260702(current_title, message_count):
                    continue

                sid = _nova_title_polish_text_20260702(item.get("id"))
                fallback = store_index.get(sid)

                new_title = _nova_title_polish_make_title_20260702(item, fallback)

                if new_title and new_title != current_title:
                    item["title"] = new_title
                    changed = True
        except Exception:
            pass

        return changed

    def _nova_session_list_title_polish_20260702(response):
        try:
            req_path = _nova_title_polish_request.path.rstrip("/")

            if not (
                req_path == "/api/sessions"
                or req_path == "/api/chat"
                or req_path.startswith("/api/sessions/")
            ):
                return response

            if getattr(response, "status_code", 200) >= 400:
                return response

            payload = response.get_json(silent=True)
            if not isinstance(payload, dict):
                return response

            store_path, store = _nova_title_polish_load_store_20260702()
            store_index = _nova_title_polish_store_index_20260702(store)

            payload_sessions = []
            try:
                if isinstance(payload.get("sessions"), list):
                    payload_sessions.extend(payload.get("sessions"))
                if isinstance(payload.get("items"), list):
                    payload_sessions.extend(payload.get("items"))
                if isinstance(payload.get("session"), dict):
                    payload_sessions.append(payload.get("session"))
            except Exception:
                pass

            store_sessions = _nova_title_polish_iter_sessions_20260702(store)

            store_changed = _nova_title_polish_repair_sessions_20260702(store_sessions, store_index)
            payload_changed = _nova_title_polish_repair_sessions_20260702(payload_sessions, store_index)

            if store_changed:
                _nova_title_polish_write_store_20260702(store_path, store)

            if payload_changed:
                try:
                    debug = payload.get("debug")
                    if not isinstance(debug, dict):
                        debug = {}
                    debug["session_list_title_polish"] = True
                    payload["debug"] = debug
                except Exception:
                    pass

                body = _nova_title_polish_json.dumps(payload, ensure_ascii=False)
                response.set_data(body)
                response.mimetype = "application/json"

                try:
                    response.headers["Content-Length"] = str(len(body.encode("utf-8")))
                except Exception:
                    pass

            return response
        except Exception as exc:
            try:
                print("[NOVA_SESSION_LIST_TITLE_POLISH_20260702] failed:", exc)
            except Exception:
                pass
            return response

    try:
        _nova_title_polish_after_funcs_20260702 = app.after_request_funcs.setdefault(None, [])
        _nova_title_polish_after_funcs_20260702.insert(0, _nova_session_list_title_polish_20260702)
        print("[NOVA_SESSION_LIST_TITLE_POLISH_20260702] installed")
    except Exception as _nova_title_polish_install_error_20260702:
        try:
            print("[NOVA_SESSION_LIST_TITLE_POLISH_20260702] install failed:", _nova_title_polish_install_error_20260702)
        except Exception:
            pass

except Exception as _nova_title_polish_error_20260702:
    try:
        print("[NOVA_SESSION_LIST_TITLE_POLISH_20260702] outer failed:", _nova_title_polish_error_20260702)
    except Exception:
        pass
'''

insert_anchor = 'if __name__ == "__main__":'

if insert_anchor in text:
    text = text.replace(insert_anchor, patch + "\n\n" + insert_anchor, 1)
else:
    text = text.rstrip() + "\n" + patch + "\n"

path.write_text(text, encoding="utf-8")
print("patched session list title polish")
