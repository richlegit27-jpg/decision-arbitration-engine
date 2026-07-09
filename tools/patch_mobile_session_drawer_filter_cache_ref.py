from pathlib import Path
import re

VERSION = "20260703-stable-no-jitter-2-session-filter"
targets = [
    Path("app.py"),
    Path("templates/index.html"),
    Path("templates/mobile.html"),
]

changed = []

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    # Replace any drawer v2 cache param, no matter what old value it has.
    new_text = re.sub(
        r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
        "nova-mobile-session-drawer-v2.js?v=" + VERSION,
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        changed.append(str(path))

print("changed refs:", changed)

if not changed:
    raise SystemExit("No drawer refs changed. Need to inspect app.py/template script injection manually.")
