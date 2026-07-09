from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# --- NOVA_RICHARD_ALL_SESSIONS_LIST_BRIDGE_20260703 ---"

if marker in text:
    print("Richard all sessions list bridge already installed")
else:
    addition = r'''

# --- NOVA_RICHARD_ALL_SESSIONS_LIST_BRIDGE_20260703 ---
try:
    from flask import request as _nova_all_sessions_request_20260703
    from flask import session as _nova_all_sessions_flask_session_20260703
    from flask import jsonify as _nova_all_sessions_jsonify_20260703
    from pathlib import Path as _NovaAllSessionsPath20260703
    import json as _nova_all_sessions_json_20260703
    import os as _nova_all_sessions_os_20260703

    def _nova_all_sessions_is_richard_20260703():
        try:
            if str(_nova_all_sessions_request_20260703.cookies.get("nova_richard_login") or "") == "1":
                return True

            username = str(_nova_all_sessions_flask_session_20260703.get("username") or "").strip().lower()
            authed = bool(_nova_all_sessions_flask_session_20260703.get("authenticated"))
            return authed and username == "richard"
        except Exception:
            return False

    def _nova_all_sessions_file_20260703():
        base_dir = _NovaAllSessionsPath20260703(__file__).resolve().parent
        data_dir = _NovaAllSessionsPath20260703(
            _nova_all_sessions_os_20260703.environ.get("NOVA_DATA_DIR", str(base_dir / "data"))
        )
        return _NovaAllSessionsPath20260703(
            _nova_all_sessions_os_20260703.environ.get(
                "NOVA_SESSIONS_FILE",
                str(data_dir / "nova_sessions.json"),
            )
        )

    def _nova_all_sessions_load_raw_20260703():
        target = _nova_all_sessions_file_20260703()
        if not target.exists():
            return []

        payload = _nova_all_sessions_json_20260703.loads(target.read_text(encoding="utf-8"))

        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            sessions = payload.get("sessions")

            if isinstance(sessions, list):
                return sessions

            if isinstance(sessions, dict):
                out = []
                for sid, item in sessions.items():
                    if isinstance(item, dict):
                        copied = dict(item)
                        copied.setdefault("id", sid)
                        copied.setdefault("session_id", sid)
                        out.append(copied)
                return out

            out = []
            for sid, item in payload.items():
                if isinstance(item, dict) and (
                    "messages" in item or "id" in item or "session_id" in item
                ):
                    copied = dict(item)
                    copied.setdefault("id", sid)
                    copied.setdefault("session_id", sid)
                    out.append(copied)
            return out

        return []

    def _nova_all_sessions_visible_20260703():
        rows = []

        for item in _nova_all_sessions_load_raw_20260703():
            if not isinstance(item, dict):
                continue

            sid = item.get("id") or item.get("session_id") or item.get("sessionId")
            if not sid:
                continue

            title = str(item.get("title") or "").strip()
            messages = item.get("messages")
            message_count = len(messages) if isinstance(messages, list) else 0

            # Hide only truly empty inactive New Chat shells.
            if message_count <= 0 and title.lower() in ("", "new chat", "untitled"):
                continue

            copied = dict(item)
            copied["id"] = str(sid)
            copied["session_id"] = str(sid)
            copied["title"] = title or "New Chat"
            copied["message_count"] = message_count
            rows.append(copied)

        rows.sort(
            key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""),
            reverse=True,
        )

        return rows

    _nova_sessions_list_wrapped_20260703 = False

    for _nova_rule_20260703 in list(app.url_map.iter_rules()):
        if str(_nova_rule_20260703) == "/api/sessions":
            _nova_endpoint_20260703 = _nova_rule_20260703.endpoint
            _nova_original_sessions_list_20260703 = app.view_functions.get(_nova_endpoint_20260703)

            if _nova_original_sessions_list_20260703 and not getattr(
                _nova_original_sessions_list_20260703,
                "_nova_richard_all_sessions_list_bridge_20260703",
                False,
            ):
                def _nova_richard_all_sessions_list_bridge_20260703(*args, **kwargs):
                    if _nova_all_sessions_is_richard_20260703():
                        return _nova_all_sessions_jsonify_20260703(_nova_all_sessions_visible_20260703())

                    return _nova_original_sessions_list_20260703(*args, **kwargs)

                _nova_richard_all_sessions_list_bridge_20260703._nova_richard_all_sessions_list_bridge_20260703 = True
                app.view_functions[_nova_endpoint_20260703] = _nova_richard_all_sessions_list_bridge_20260703
                _nova_sessions_list_wrapped_20260703 = True

            break

    print("[NOVA_RICHARD_ALL_SESSIONS_LIST_BRIDGE_20260703] installed", _nova_sessions_list_wrapped_20260703)
except Exception as _nova_all_sessions_bridge_error_20260703:
    try:
        print("[NOVA_RICHARD_ALL_SESSIONS_LIST_BRIDGE_20260703] failed:", _nova_all_sessions_bridge_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"
    path.write_text(text, encoding="utf-8")
    print("patched Richard all sessions list bridge")
