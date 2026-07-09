from pathlib import Path

path = Path("nova_backend/services/project_brain_freshness_snapshot.py")
text = path.read_text(encoding="utf-8")

old = '''    next_move = (
        "Use the Project Brain freshness snapshot as the source of truth for current checkpoint, blocker, "
        "next concrete move / safe move, latest commits, and available smoke files."
    )
'''

new = '''    next_move = (
        "Use the Project Brain freshness snapshot as the context builder source of truth for current "
        "checkpoint, blocker, next concrete move / safe move, latest commits, and available smoke files."
    )
'''

if old not in text:
    raise SystemExit("snapshot next_move text not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched freshness snapshot to include exact context builder term")
