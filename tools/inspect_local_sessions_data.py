import json
from pathlib import Path

path = Path("data/nova_sessions.json")
print("exists:", path.exists())

if not path.exists():
    raise SystemExit(0)

data = json.loads(path.read_text(encoding="utf-8", errors="replace"))

if isinstance(data, dict):
    if "sessions" in data and isinstance(data["sessions"], list):
        sessions = data["sessions"]
    else:
        sessions = list(data.values())
elif isinstance(data, list):
    sessions = data
else:
    sessions = []

print("local session count:", len(sessions))

for s in sessions[:20]:
    if not isinstance(s, dict):
        continue

    messages = s.get("messages") or []

    print({
        "id": s.get("id") or s.get("session_id"),
        "title": s.get("title"),
        "messages": len(messages) if isinstance(messages, list) else None,
        "created_at": s.get("created_at"),
        "updated_at": s.get("updated_at"),
    })
