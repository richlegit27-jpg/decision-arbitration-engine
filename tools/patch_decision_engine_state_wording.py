from pathlib import Path

path = Path("nova_backend/services/chat_service.py")
text = path.read_text(encoding="utf-8")

replacements = {
    "Current task: Project Brain answer freshness v2.\\n":
        "Current task: Decision Engine v1 and broad Project Brain routing are locked.\\n",

    "Next move: fix the `what's next?` route so it uses project context instead of generic chat fallback, ":
        "Next move: start Project Brain cleanup/consolidation while preserving direct recall, ",

    "then keep next move, blocker, fallback priority, and safe move answers fresh through the context-builder path.":
        "broad Project Brain routing, and avoiding another app.py guard.",
}

changed = 0
for old, new in replacements.items():
    count = text.count(old)
    if count:
        text = text.replace(old, new)
        changed += count
        print(f"patched {count} occurrence(s): {old}")

if changed == 0:
    raise SystemExit("no matching stale chat_service wording found")

path.write_text(text, encoding="utf-8")
print(f"patched chat_service wording replacements: {changed}")
