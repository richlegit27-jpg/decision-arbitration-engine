from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_RICHARD_SESSION_STORE_IMPORT_ROUTE_20260703"

if marker in text:
    print("session import route already installed")
    raise SystemExit(0)

addition = r'''


# ============================================================
# NOVA_RICHARD_SESSION_STORE_IMPORT_ROUTE_20260703
# Temporary authenticated import route for restoring local session history
# into Railway /app/data/nova_sessions.json.
# Requires logged-in local-auth username richard plus explicit confirmation.
# ============================================================
try:
    import json as _nova_import_json
    from pathlib import Path as _NovaImportPath
    from flask import request as _nova_import_request
    from flask import jsonify as _nova_import_jsonify
    from flask import session as _nova_import_flask_session

    def _nova_import_current_user_20260703():
        try:
            base_dir = _NovaImportPath(__file__).resolve().parent
            users_path = base_dir / "data" / "nova_auth_users.json"
            uid = str(_nova_import_flask_session.get("nova_user_id") or "").strip()

            if not uid or not users_path.exists():
                return None

            users_data = _nova_import_json.loads(users_path.read_text(encoding="utf-8"))
            for item in users_data.get("users", []):
                if isinstance(item, dict) and str(item.get("id") or "") == uid:
                    return {
                        "id": str(item.get("id") or ""),
                        "username": str(item.get("username") or ""),
                        "email": str(item.get("email") or ""),
                    }
        except Exception:
            return None

        return None

    def _nova_import_session_id_20260703(item):
        if not isinstance(item, dict):
            return ""
        return str(item.get("id") or item.get("session_id") or "").strip()

    def _nova_import_session_lists_20260703(store):
        if isinstance(store, dict):
            value = store.get("sessions")
            if isinstance(value, list):
                return value
            value = store.get("items")
            if isinstance(value, list):
                return value
        if isinstance(store, list):
            return store
        return []

    def _nova_import_message_count_20260703(item):
        try:
            messages = item.get("messages")
            if isinstance(messages, list):
                return len(messages)
            return int(item.get("message_count") or 0)
        except Exception:
            return 0

    @app.post("/api/admin/session-store/import")
    def nova_richard_session_store_import_20260703():
        user = _nova_import_current_user_20260703()

        if not user or str(user.get("username") or "").strip().lower() != "richard":
            return _nova_import_jsonify({
                "ok": False,
                "error": "Not authorized.",
            }), 403

        payload = _nova_import_request.get_json(silent=True) or {}

        if payload.get("confirm") != "I_UNDERSTAND_IMPORT_LOCAL_NOVA_SESSIONS":
            return _nova_import_jsonify({
                "ok": False,
                "error": "Missing confirmation.",
            }), 400

        incoming_store = payload.get("store")
        incoming_sessions = _nova_import_session_lists_20260703(incoming_store)

        if not incoming_sessions:
            return _nova_import_jsonify({
                "ok": False,
                "error": "No sessions found in uploaded store.",
            }), 400

        base_dir = _NovaImportPath(__file__).resolve().parent
        sessions_path = base_dir / "data" / "nova_sessions.json"
        sessions_path.parent.mkdir(parents=True, exist_ok=True)

        if sessions_path.exists():
            try:
                current_store = _nova_import_json.loads(sessions_path.read_text(encoding="utf-8"))
            except Exception:
                current_store = {"active_session_id": "", "sessions": []}
        else:
            current_store = {"active_session_id": "", "sessions": []}

        if isinstance(current_store, list):
            current_store = {"active_session_id": "", "sessions": current_store}
        if not isinstance(current_store, dict):
            current_store = {"active_session_id": "", "sessions": []}
        if not isinstance(current_store.get("sessions"), list):
            current_store["sessions"] = []

        current_sessions = current_store["sessions"]
        by_id = {}

        for item in current_sessions:
            sid = _nova_import_session_id_20260703(item)
            if sid:
                by_id[sid] = item

        imported = 0
        updated = 0
        skipped = 0

        for item in incoming_sessions:
            if not isinstance(item, dict):
                skipped += 1
                continue

            sid = _nova_import_session_id_20260703(item)
            if not sid:
                skipped += 1
                continue

            cloned = _nova_import_json.loads(_nova_import_json.dumps(item, ensure_ascii=False))

            meta = cloned.get("meta")
            if not isinstance(meta, dict):
                meta = {}
                cloned["meta"] = meta

            old_user_id = str(cloned.get("user_id") or "").strip()
            old_username = str(cloned.get("username") or "").strip()

            if old_user_id and old_user_id != user["id"]:
                meta.setdefault("previous_owner_user_id", old_user_id)
            if old_username and old_username.lower() != "richard":
                meta.setdefault("previous_owner_username", old_username)

            cloned["user_id"] = user["id"]
            cloned["username"] = "richard"
            meta["owner_source"] = "session_store_import_20260703"

            if sid in by_id:
                existing_count = _nova_import_message_count_20260703(by_id[sid])
                incoming_count = _nova_import_message_count_20260703(cloned)

                if incoming_count >= existing_count:
                    index = current_sessions.index(by_id[sid])
                    current_sessions[index] = cloned
                    by_id[sid] = cloned
                    updated += 1
                else:
                    skipped += 1
            else:
                current_sessions.append(cloned)
                by_id[sid] = cloned
                imported += 1

        current_sessions.sort(
            key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
            reverse=True
        )

        if current_sessions and not str(current_store.get("active_session_id") or "").strip():
            current_store["active_session_id"] = _nova_import_session_id_20260703(current_sessions[0])

        sessions_path.write_text(
            _nova_import_json.dumps(current_store, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return _nova_import_jsonify({
            "ok": True,
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total_sessions": len(current_sessions),
            "sessions_with_messages": sum(1 for item in current_sessions if _nova_import_message_count_20260703(item) > 0),
            "path": str(sessions_path),
        })

except Exception as _nova_import_error_20260703:
    try:
        print("[NOVA_RICHARD_SESSION_STORE_IMPORT_ROUTE_20260703] install failed:", _nova_import_error_20260703)
    except Exception:
        pass
'''

text = text.rstrip() + addition + "\n"
path.write_text(text, encoding="utf-8")
print("patched:", path)
