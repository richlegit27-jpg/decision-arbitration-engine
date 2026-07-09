from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# --- NOVA_SESSION_DETAIL_COMPAT_ROUTES_20260703 ---"

if marker in text:
    print("session detail compat routes already installed")
else:
    addition = r'''

# --- NOVA_SESSION_DETAIL_COMPAT_ROUTES_20260703 ---
try:
    from flask import jsonify as _nova_session_detail_jsonify_20260703
    from flask import request as _nova_session_detail_request_20260703
    from flask import session as _nova_session_detail_flask_session_20260703
    from pathlib import Path as _NovaSessionDetailPath20260703
    import json as _nova_session_detail_json_20260703
    import os as _nova_session_detail_os_20260703

    def _nova_session_detail_auth_ok_20260703():
        try:
            if _nova_session_detail_flask_session_20260703.get("authenticated"):
                return True
            if str(_nova_session_detail_request_20260703.cookies.get("nova_richard_login") or "") == "1":
                return True
        except Exception:
            pass
        return False

    def _nova_session_detail_file_20260703():
        base_dir = _NovaSessionDetailPath20260703(__file__).resolve().parent
        data_dir = _NovaSessionDetailPath20260703(
            _nova_session_detail_os_20260703.environ.get("NOVA_DATA_DIR", str(base_dir / "data"))
        )
        return _NovaSessionDetailPath20260703(
            _nova_session_detail_os_20260703.environ.get(
                "NOVA_SESSIONS_FILE",
                str(data_dir / "nova_sessions.json"),
            )
        )

    def _nova_session_detail_load_all_20260703():
        target = _nova_session_detail_file_20260703()
        if not target.exists():
            return []

        raw = target.read_text(encoding="utf-8")
        payload = _nova_session_detail_json_20260703.loads(raw)

        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            sessions = payload.get("sessions")
            if isinstance(sessions, list):
                return sessions

            if isinstance(sessions, dict):
                out = []
                for sid, value in sessions.items():
                    if isinstance(value, dict):
                        item = dict(value)
                        item.setdefault("id", sid)
                        item.setdefault("session_id", sid)
                        out.append(item)
                return out

            out = []
            for sid, value in payload.items():
                if isinstance(value, dict) and (
                    "messages" in value or "session_id" in value or "id" in value
                ):
                    item = dict(value)
                    item.setdefault("id", sid)
                    item.setdefault("session_id", sid)
                    out.append(item)
            return out

        return []

    def _nova_session_detail_find_20260703(session_id):
        sid = str(session_id or "").strip()
        for item in _nova_session_detail_load_all_20260703():
            if not isinstance(item, dict):
                continue

            candidates = {
                str(item.get("id") or ""),
                str(item.get("session_id") or ""),
                str(item.get("sessionId") or ""),
            }

            if sid in candidates:
                return item

        return None

    def _nova_session_detail_response_20260703(session_id):
        if not _nova_session_detail_auth_ok_20260703():
            return _nova_session_detail_jsonify_20260703({
                "ok": False,
                "error": "Not authenticated.",
            }), 401

        item = _nova_session_detail_find_20260703(session_id)

        if not item:
            return _nova_session_detail_jsonify_20260703({
                "ok": False,
                "error": "Session not found.",
                "session_id": session_id,
                "messages": [],
            }), 404

        messages = item.get("messages")
        if not isinstance(messages, list):
            messages = []

        sid = item.get("id") or item.get("session_id") or session_id

        return _nova_session_detail_jsonify_20260703({
            "ok": True,
            "id": sid,
            "session_id": sid,
            "session": item,
            "messages": messages,
            "message_count": len(messages),
        })

    @app.get("/api/sessions/<path:session_id>")
    def nova_session_detail_compat_20260703(session_id):
        return _nova_session_detail_response_20260703(session_id)

    @app.get("/api/sessions/<path:session_id>/messages")
    def nova_session_messages_compat_20260703(session_id):
        return _nova_session_detail_response_20260703(session_id)

    @app.get("/api/chat/<path:session_id>")
    def nova_chat_session_detail_compat_20260703(session_id):
        return _nova_session_detail_response_20260703(session_id)

    print("[NOVA_SESSION_DETAIL_COMPAT_ROUTES_20260703] installed")
except Exception as _nova_session_detail_compat_error_20260703:
    try:
        print("[NOVA_SESSION_DETAIL_COMPAT_ROUTES_20260703] failed:", _nova_session_detail_compat_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"
    path.write_text(text, encoding="utf-8")
    print("patched session detail compat routes")
