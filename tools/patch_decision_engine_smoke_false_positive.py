from pathlib import Path

paths = [
    Path("tools/nova_project_brain_decision_engine_smoke.py"),
    Path("tools/patch_project_brain_decision_engine.py"),
]

for path in paths:
    if not path.exists():
        print(f"{path}: missing, skipped")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        '        avoided_terms=[\n            "execute all",\n            "memory write",\n        ],',
        '        avoided_terms=[\n            "execute all",\n            "save this memory",\n        ],',
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

print("patched Decision Engine smoke avoided-term false positive")
