from pathlib import Path

paths = [
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("tools/patch_project_brain_freshness_snapshot_sanitizer.py"),
    Path("tools/patch_freshness_snapshot_readability_sanitizer.py"),
    Path("tools/patch_remaining_answer_freshness_wording.py"),
]

replacements = {
    "Next concrete move / safe move: use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files.":
        "Use the Project Brain freshness snapshot as the context builder source of truth for checkpoint, blocker, next move, fallback priority, recent commits, validation state, and available smoke files as the next safe move.",

    '"Next concrete move / safe move: use the Project Brain freshness snapshot as the "':
        '"Use the Project Brain freshness snapshot as the "',

    '"context builder source of truth for checkpoint, blocker, next move, fallback priority, "':
        '"context builder source of truth for checkpoint, blocker, next move, fallback priority, "',

    '"recent commits, validation state, and available smoke files."':
        '"recent commits, validation state, and available smoke files as the next safe move."',
}

for path in paths:
    if not path.exists():
        print(f"{path}: missing, skipped")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

print("removed duplicate safe-move label at snapshot source")
