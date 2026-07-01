from pathlib import Path

files = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
]

replacements = [
    (
        b"Current task: Decision Engine v1 and broad Project Brain routing are locked.\\n",
        b"Current task: Decision Engine v1, broad Project Brain routing, and Mission Control v1.1 are locked.\\n",
    ),
    (
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, and avoiding another app.py guard.",
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, and avoiding another app.py guard.",
    ),
]

total = 0

for path in files:
    if not path.exists():
        continue

    data = path.read_bytes()
    original = data
    file_total = 0

    for old, new in replacements:
        count = data.count(old)
        if count:
            data = data.replace(old, new)
            file_total += count
            total += count

    if data != original:
        path.write_bytes(data)
        print(f"patched {path}: {file_total} replacement(s)")

if total == 0:
    raise SystemExit("no stale next-move runtime wording found")

print(f"patched runtime next-move Mission Control v1.1 wording: {total}")
