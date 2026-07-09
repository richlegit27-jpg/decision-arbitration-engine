from pathlib import Path

# 1) Fix lowercase stale smoke assertion.
fresh_path = Path("tools/nova_project_brain_freshness_snapshot_smoke.py")
fresh = fresh_path.read_text(encoding="utf-8-sig")

fresh_replacements = {
    '"mission control v1.1"': '"mission control v1.2 / failure interpreter api"',
    '"Mission Control v1.1"': '"Mission Control v1.2 / Failure Interpreter API"',
}

fresh_changed = 0
for old, new in fresh_replacements.items():
    count = fresh.count(old)
    if count:
        fresh = fresh.replace(old, new)
        fresh_changed += count

if fresh_changed:
    fresh_path.write_text(fresh, encoding="utf-8")
    print(f"patched freshness smoke stale v1.1 assertions: {fresh_changed}")


# 2) Fix runtime next-move wording in app.py and chat_service.py without changing encoding.
runtime_files = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
]

runtime_replacements = [
    (
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, and avoiding another app.py guard.",
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, pasted failure interpretation, and avoiding another app.py guard.",
    ),
    (
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, and avoiding another app.py guard.",
        b"Next move: start Project Brain cleanup/consolidation while preserving direct recall, broad Project Brain routing, explicit operator Mission Control prompts, pasted failure interpretation, and avoiding another app.py guard.",
    ),
]

runtime_changed = 0
for path in runtime_files:
    data = path.read_bytes()
    original = data
    file_changed = 0

    for old, new in runtime_replacements:
        count = data.count(old)
        if count:
            data = data.replace(old, new)
            runtime_changed += count
            file_changed += count

    if data != original:
        path.write_bytes(data)
        print(f"patched runtime next-move wording in {path}: {file_changed}")

if fresh_changed == 0 and runtime_changed == 0:
    raise SystemExit("no stale v1.1 or next-move wording found")

print("patched v1.2 state smoke/runtime wording")
