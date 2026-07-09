from pathlib import Path


TARGETS = [
    Path("data/nova_memory.json"),
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("nova_backend/services/project_brain_mission_control.py"),
    Path("nova_backend/services/project_brain_general_intelligence.py"),
]

REPLACEMENTS = {
    "Decision Engine v1, broad Project Brain routing, and Mission Control v1.2 / Failure Interpreter API are locked":
        "Decision Engine v1, broad Project Brain routing, Mission Control v1.2 / Failure Interpreter API, and Decision Log API route are locked",

    "Mission Control v1.2 / Failure Interpreter API are locked":
        "Mission Control v1.2 / Failure Interpreter API and Decision Log API route are locked",

    "No active Decision Engine blocker is open, no active Mission Control blocker is open, and no active Failure Interpreter blocker is open.":
        "No active Decision Engine blocker is open, no active Mission Control blocker is open, no active Failure Interpreter blocker is open, and no active Decision Log blocker is open.",

    "explicit operator prompts route to Mission Control, answer quality is 100%, and regression now protects the route contracts":
        "explicit operator prompts route to Mission Control, recent-change prompts route to Decision Log, answer quality is 100%, and regression now protects the route contracts",
}

changed = 0

for path in TARGETS:
    if not path.exists():
        continue

    data = path.read_text(encoding="utf-8-sig")
    original = data
    file_changes = 0

    for old, new in REPLACEMENTS.items():
        count = data.count(old)
        if count:
            data = data.replace(old, new)
            file_changes += count
            changed += count

    if data != original:
        path.write_text(data, encoding="utf-8")
        print(f"patched {path}: {file_changes}")

if changed == 0:
    raise SystemExit("no stale Decision Log state wording found")

print(f"patched Decision Log state wording: {changed}")
