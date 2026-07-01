from pathlib import Path

paths = [
    Path("nova_backend/services/project_brain_decision_engine.py"),
    Path("tools/patch_project_brain_decision_engine.py"),
]

for path in paths:
    if not path.exists():
        print(f"{path}: missing, skipped")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        "validation, and avoid-rules before any app.py wiring.",
        "validation, and avoid-rules with no app.py wiring until the service smoke is stable.",
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

print("patched Decision Engine no-app.py-wiring wording contract")
