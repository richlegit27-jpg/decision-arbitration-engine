from pathlib import Path

changed = 0

# Fix snapshot source next_move wording.
snapshot_path = Path("nova_backend/services/project_brain_freshness_snapshot.py")
snapshot = snapshot_path.read_text(encoding="utf-8-sig")

snapshot_replacements = {
    "Mission Control v1.1 behavior":
        "Mission Control v1.2 / Failure Interpreter API behavior",

    "explicit operator Mission Control prompts, and consolidate":
        "explicit operator Mission Control prompts, pasted failure interpretation, and consolidate",

    "explicit operator Mission Control prompts, and avoiding another app.py guard.":
        "explicit operator Mission Control prompts, pasted failure interpretation, and avoiding another app.py guard.",
}

snapshot_count = 0
for old, new in snapshot_replacements.items():
    count = snapshot.count(old)
    if count:
        snapshot = snapshot.replace(old, new)
        snapshot_count += count
        changed += count

if snapshot_count:
    snapshot_path.write_text(snapshot, encoding="utf-8")
    print(f"patched snapshot source wording: {snapshot_count}")


# Fix live next-move runtime wording without changing encoding.
runtime_files = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
]

runtime_replacements = [
    (
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, and avoiding another app.py guard.",
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, pasted failure interpretation, and avoiding another app.py guard.",
    ),
    (
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, and avoiding another app.py guard.",
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, pasted failure interpretation, and avoiding another app.py guard.",
    ),
]

for path in runtime_files:
    if not path.exists():
        continue

    data = path.read_bytes()
    original = data
    file_count = 0

    for old, new in runtime_replacements:
        count = data.count(old)
        if count:
            data = data.replace(old, new)
            file_count += count
            changed += count

    if data != original:
        path.write_bytes(data)
        print(f"patched runtime wording in {path}: {file_count}")

if changed == 0:
    raise SystemExit("no stale Failure Interpreter API state/runtime wording found")

print(f"patched Failure Interpreter API state/runtime wording: {changed}")
