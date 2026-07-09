from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703"

if marker in text:
    print("token import route already installed")
else:
    addition = r'''

# === NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703 ===
# TEMPORARY REPAIR ROUTE. Remove after old sessions are imported.
try:
    @app.route("/api/admin/session-store/import-token", methods=["POST"])
    def nova_session_store_import_token_20260703():
        import json
        import os
        import shutil
        from datetime import datetime, timezone
        from pathlib import Path
        from flask import request, jsonify

        expected_token = os.environ.get("NOVA_SESSION_IMPORT_TOKEN", "richard-import-20260703")
        provided_token = request.headers.get("X-Nova-Import-Token", "")

        if provided_token != expected_token:
            return jsonify({
                "ok": False,
                "error": "Bad import token.",
            }), 403

        raw = request.get_data(as_text=True) or ""
        if not raw.strip():
            return jsonify({
                "ok": False,
                "error": "Empty request body.",
            }), 400

        try:
            payload = json.loads(raw)
        except Exception as exc:
            return jsonify({
                "ok": False,
                "error": "Invalid JSON.",
                "detail": str(exc),
            }), 400

        def rewrite_owner(value):
            if isinstance(value, list):
                return [rewrite_owner(item) for item in value]

            if isinstance(value, dict):
                out = {}
                for key, item in value.items():
                    lk = str(key).lower()

                    if lk in ("owner", "owner_name"):
                        if item in (None, "", "joe", "Joe", "JOE", "blank"):
                            out[key] = "richard"
                        else:
                            out[key] = item
                    elif lk in ("owner_id", "user_id"):
                        if item in (None, "", "joe", "Joe", "JOE", "blank", "user_joe"):
                            out[key] = "user_richard_stable_local_login"
                        else:
                            out[key] = item
                    else:
                        out[key] = rewrite_owner(item)

                return out

            return value

        payload = rewrite_owner(payload)

        def session_count(value):
            if isinstance(value, list):
                return len(value)

            if isinstance(value, dict):
                sessions = value.get("sessions")
                if isinstance(sessions, list):
                    return len(sessions)
                if isinstance(sessions, dict):
                    return len(sessions)

                dict_session_values = [
                    item for item in value.values()
                    if isinstance(item, dict) and (
                        "messages" in item or "session_id" in item or "id" in item
                    )
                ]
                if dict_session_values:
                    return len(dict_session_values)

            return 0

        base_dir = Path(__file__).resolve().parent
        data_dir = Path(os.environ.get("NOVA_DATA_DIR", str(base_dir / "data")))
        data_dir.mkdir(parents=True, exist_ok=True)

        target = data_dir / "nova_sessions.json"

        backup_path = None
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = data_dir / f"nova_sessions.before_import_{stamp}.json"
            shutil.copy2(target, backup_path)

        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return jsonify({
            "ok": True,
            "imported_count": session_count(payload),
            "target": str(target),
            "backup": str(backup_path) if backup_path else None,
            "mode": "replace",
        })

    print("[NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703] installed")
except Exception as _nova_session_import_token_error_20260703:
    try:
        print("[NOVA_SESSION_IMPORT_TOKEN_ROUTE_20260703] failed:", _nova_session_import_token_error_20260703)
    except Exception:
        pass
'''
    text = text.rstrip() + addition + "\n"
    path.write_text(text, encoding="utf-8")
    print("patched token import route:", path)
