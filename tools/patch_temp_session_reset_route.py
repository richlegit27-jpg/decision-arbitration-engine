from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_TEMP_SESSION_RESET_ROUTE_20260704"

if marker in text:
    print("Reset route already installed.")
else:
    route = r'''

# NOVA_TEMP_SESSION_RESET_ROUTE_20260704
@app.post("/api/admin/reset-sessions-clean-start")
def nova_temp_reset_sessions_clean_start_20260704():
    from datetime import datetime, timezone
    from pathlib import Path
    from uuid import uuid4
    import json
    import shutil

    token = (request.headers.get("X-Nova-Reset-Token") or "").strip()
    expected = (os.environ.get("NOVA_RESET_TOKEN") or "richard-clean-reset-20260704").strip()

    if token != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    data_dir = Path(os.environ.get("NOVA_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    sessions_path = data_dir / "nova_sessions.json"
    backup_dir = data_dir / "session_reset_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if sessions_path.exists():
        backup_path = backup_dir / f"nova_sessions_before_admin_clean_reset_{stamp}.json"
        shutil.copy2(sessions_path, backup_path)
    else:
        backup_path = None

    sid = "session_clean_start_" + uuid4().hex[:24]

    clean_session = {
        "id": sid,
        "title": "Clean Start",
        "messages": [],
        "message_count": 0,
        "session_attachments": [],
        "working_state": {
            "active_task": "",
            "current_file": "",
            "current_bug": "",
            "last_success": "",
            "next_move": "",
            "checkpoint": "",
            "updated_at": ""
        },
        "active_execution": None,
        "execution_state": None,
        "pinned": True,
        "created_at": now,
        "updated_at": now,
        "manual_title": True,
        "title_locked": True,
        "meta": {
            "manual_title": True,
            "title_locked": True,
            "clean_reset": True,
            "source": "admin_reset_route"
        }
    }

    payload = {
        "active_session_id": sid,
        "sessions": [clean_session]
    }

    sessions_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    return jsonify({
        "ok": True,
        "active_session_id": sid,
        "session_id": sid,
        "count": 1,
        "backup_path": str(backup_path) if backup_path else None,
        "sessions_path": str(sessions_path)
    })
'''

    insert_at = text.rfind('if __name__ == "__main__"')
    if insert_at == -1:
        insert_at = len(text)

    text = text[:insert_at] + route + "\n\n" + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    print("Installed reset route.")
