from pathlib import Path

paths = [
    Path("tools/nova_project_answer_readability_smoke.py"),
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("tools/patch_project_brain_freshness_snapshot_sanitizer.py"),
    Path("tools/patch_freshness_snapshot_readability_sanitizer.py"),
]

for path in paths:
    if not path.exists():
        print(f"{path}: missing, skipped")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        '"and fres",\n',
        ''
    )

    text = text.replace(
        '"and fres",\r\n',
        ''
    )

    if '"and fres current blocker"' not in text and "BAD_TERMS" in text:
        text = text.replace(
            '"text: Current Nova project state",',
            '"and fres Current blocker",\n    "text: Current Nova project state",'
        )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"{path}: patched")
    else:
        print(f"{path}: no change")

print("removed overbroad readability/sanitizer false-positive term")
