from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

path = Path("data/nova_sessions.json")
backup_dir = Path("data/session_reset_backups")
backup_dir.mkdir(parents=True, exist_ok=True)

if path.exists():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"nova_sessions_before_clean_reset_{stamp}.json"
    shutil.copy2(path, backup_path)
    print(f"BACKUP: {backup_path}")
else:
    backup_path = None
    print("BACKUP: no existing data/nova_sessions.json found")

now = datetime.now(timezone.utc).isoformat()
sid = "session_clean_start_" + uuid4().hex[:24]

clean_session = {
    "id": sid,
    "title": "Clean Start",
    "messages": [],
    "message_count": 0,
    "pinned": False,
    "meta": {
        "manual_title": True,
        "title_locked": True,
        "clean_reset": True
    },
    "manual_title": True,
    "title_locked": True,
    "created_at": now,
    "updated_at": now,
    "working_state": {
        "active_task": "",
        "checkpoint": "",
        "current_bug": "",
        "current_file": "",
        "last_success": "",
        "next_move": "",
        "updated_at": ""
    },
    "execution_state": None,
    "active_execution": None
}

root = {}
if path.exists():
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        root = {}

if isinstance(root, dict) and isinstance(root.get("sessions"), list):
    new_root = dict(root)
    new_root["active_session_id"] = sid
    new_root["sessions"] = [clean_session]
elif isinstance(root, dict) and isinstance(root.get("sessions"), dict):
    new_root = dict(root)
    new_root["active_session_id"] = sid
    new_root["sessions"] = {sid: clean_session}
elif isinstance(root, list):
    new_root = [clean_session]
else:
    new_root = {
        "active_session_id": sid,
        "sessions": {
            sid: clean_session
        }
    }

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(new_root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"CLEAN_SESSION_ID: {sid}")
print(f"WROTE: {path}")
