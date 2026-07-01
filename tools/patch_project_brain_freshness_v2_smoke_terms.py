from pathlib import Path

path = Path("nova_backend/services/project_brain_context_builder.py")
text = path.read_text(encoding="utf-8")

old = '''    blocker = (
        "The current blocker is Project Brain freshness v2: the context-builder path is protected, "
        "but the builder still needs a cleaner source-of-truth model so checkpoint, blocker, next move, "
        "recent commits, and validation state can update without another wording patch."
    )
'''

new = '''    blocker = (
        "The current blocker is Project Brain answer freshness v2: fallback-route priority and the "
        "context-builder path are protected, but the builder still needs a cleaner source-of-truth model "
        "so checkpoint, blocker, next move, recent commits, and validation state can update without another "
        "wording patch."
    )
'''

if old not in text:
    raise SystemExit("freshness v2 blocker text not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched Freshness v2 blocker terms: answer freshness + fallback")
