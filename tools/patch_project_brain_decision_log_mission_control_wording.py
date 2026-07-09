from pathlib import Path
import re


TARGETS = [
    Path("app.py"),
    Path("nova_backend/services/chat_service.py"),
    Path("nova_backend/services/project_brain_freshness_snapshot.py"),
    Path("nova_backend/services/project_brain_mission_control.py"),
    Path("nova_backend/services/project_brain_general_intelligence.py"),
]

changed = 0

plain_replacements = {
    "explicit operator prompts route to Mission Control, answer quality is 100%":
        "explicit operator prompts route to Mission Control, recent-change prompts route to Decision Log, answer quality is 100%",

    "explicit operator prompts route to Mission Control, answer quality is 100%, and regression now protects the route contracts":
        "explicit operator prompts route to Mission Control, recent-change prompts route to Decision Log, answer quality is 100%, and regression now protects the route contracts",
}

for path in TARGETS:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8-sig")
    original = text
    file_changes = 0

    for old, new in plain_replacements.items():
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            file_changes += count
            changed += count

    # Flexible fallback for wrapped/variant Mission Control wording.
    pattern = re.compile(
        r"explicit operator prompts route to Mission Control,\s*"
        r"(?!recent-change prompts route to Decision Log,\s*)"
        r"answer quality is 100%",
        re.IGNORECASE,
    )
    text, count = pattern.subn(
        "explicit operator prompts route to Mission Control, recent-change prompts route to Decision Log, answer quality is 100%",
        text,
    )
    if count:
        file_changes += count
        changed += count

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"patched {path}: {file_changes}")

if changed == 0:
    raise SystemExit("no stale Mission Control Decision Log route wording found")

print(f"patched Mission Control Decision Log route wording: {changed}")
