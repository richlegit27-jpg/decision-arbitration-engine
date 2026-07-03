import json
from pathlib import Path

candidates = [
    Path("data/nova_sessions.json"),
    Path("data_container_backup/nova_sessions.json"),
]

candidates.extend(sorted(Path("nova_backups").glob("**/nova_sessions.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10])

def extract_sessions(data):
    if isinstance(data, dict):
        if isinstance(data.get("sessions"), list):
            return data["sessions"]
        return [v for v in data.values() if isinstance(v, dict)]
    if isinstance(data, list):
        return data
    return []

def msg_count(s):
    if not isinstance(s, dict):
        return 0
    if isinstance(s.get("messages"), list):
        return len(s["messages"])
    try:
        return int(s.get("message_count") or 0)
    except Exception:
        return 0

for path in candidates:
    print("")
    print("=" * 90)
    print(path)
    print("exists:", path.exists())

    if not path.exists():
        continue

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace") or "{}")
    except Exception as exc:
        print("load_error:", exc)
        continue

    sessions = extract_sessions(data)
    nonempty = [s for s in sessions if msg_count(s) > 0]
    pinned = [s for s in sessions if isinstance(s, dict) and s.get("pinned")]

    print("sessions:", len(sessions))
    print("nonempty:", len(nonempty))
    print("pinned:", len(pinned))

    for s in sessions[:8]:
        if not isinstance(s, dict):
            continue
        print({
            "id": s.get("id") or s.get("session_id"),
            "title": s.get("title"),
            "messages": msg_count(s),
            "pinned": s.get("pinned"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
        })
