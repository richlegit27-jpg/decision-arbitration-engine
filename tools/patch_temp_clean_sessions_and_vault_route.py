from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_TEMP_CLEAN_SESSIONS_AND_VAULT_ROUTE_20260704"

if marker in text:
    print("Temp clean sessions+vault route already installed.")
else:
    route = r'''

# NOVA_TEMP_CLEAN_SESSIONS_AND_VAULT_ROUTE_20260704_BEGIN
@app.post("/api/admin/clean-sessions-and-vault")
def nova_temp_clean_sessions_and_vault_20260704():
    from datetime import datetime, timezone
    from pathlib import Path
    from uuid import uuid4
    import json
    import os
    import shutil

    token = (request.headers.get("X-Nova-Reset-Token") or "").strip()
    expected = (os.environ.get("NOVA_RESET_TOKEN") or "richard-clean-reset-20260704").strip()

    if token != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    now = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
            "source": "temp_clean_sessions_and_vault_route"
        }
    }

    payload = {
        "active_session_id": sid,
        "sessions": [clean_session]
    }

    candidates = []

    try:
        candidates.append(Path(SESSIONS_FILE))
    except Exception:
        pass

    base = Path(__file__).resolve().parent
    candidates.append(base / "data" / "nova_sessions.json")
    candidates.append(Path.cwd() / "data" / "nova_sessions.json")
    candidates.append(Path("/app/data/nova_sessions.json"))

    env_sessions = (os.environ.get("NOVA_SESSIONS_FILE") or "").strip()
    if env_sessions:
        candidates.append(Path(env_sessions))

    env_data = (os.environ.get("NOVA_DATA_DIR") or "").strip()
    if env_data:
        candidates.append(Path(env_data) / "nova_sessions.json")

    written = []
    backed_up = []
    errors = []

    seen = set()

    for sessions_path in candidates:
        try:
            key = str(sessions_path)
            if key in seen:
                continue
            seen.add(key)

            data_dir = sessions_path.parent
            data_dir.mkdir(parents=True, exist_ok=True)

            backup_dir = data_dir / "session_reset_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            targets = [
                sessions_path,
                data_dir / "nova_sessions.richard_restore_vault_20260703.json",
            ]

            for target_path in targets:
                try:
                    if target_path.exists():
                        backup_path = backup_dir / f"{target_path.name}.before_clean_{stamp}.json"
                        shutil.copy2(target_path, backup_path)
                        backed_up.append(str(backup_path))

                    target_path.write_text(
                        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8"
                    )
                    written.append(str(target_path))
                except Exception as inner_exc:
                    errors.append(f"{target_path}: {inner_exc}")

        except Exception as exc:
            errors.append(f"{sessions_path}: {exc}")

    return jsonify({
        "ok": True,
        "active_session_id": sid,
        "session_id": sid,
        "count": 1,
        "written": written,
        "backed_up": backed_up,
        "errors": errors
    })
# NOVA_TEMP_CLEAN_SESSIONS_AND_VAULT_ROUTE_20260704_END
'''

    insert_at = text.rfind('if __name__ == "__main__"')
    if insert_at == -1:
        insert_at = len(text)

    text = text[:insert_at] + route + "\n\n" + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    print("Installed temp clean sessions+vault route.")
