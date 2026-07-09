from pathlib import Path

path = Path("nova_backend/services/project_brain_context_builder.py")
text = path.read_text(encoding="utf-8")

old = '''        f"Next concrete move: {context.next_move} "
        "Validation: run the context-builder smoke, project-state memory API smoke, general-intelligence smoke, "
'''

new = '''        f"Next concrete move: {context.next_move} "
        "Safe validation: run the context-builder smoke, project-state memory API smoke, general-intelligence smoke, "
'''

if old not in text:
    raise SystemExit("target practical validation text not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched practical Project Brain answer to include safe validation")
