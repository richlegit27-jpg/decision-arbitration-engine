from pathlib import Path

paths = [
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("tools/patch_project_brain_freshness_snapshot_sanitizer.py"),
]

for path in paths:
    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        '"and fres current blocker",',
        '"and fres",\n'
        '            "and fres current blocker",\n'
        '            "next concrete move / safe move: next concrete move / safe move",\n'
        '            "current safe direction: next concrete move",',
    )

    text = text.replace(
        '["Project Brain", "freshness"],',
        '["Project Brain", "freshness snapshot"],',
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

print("broadened Project Brain freshness snapshot sanitizer malformed-fragment checks")
