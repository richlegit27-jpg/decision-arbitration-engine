from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_OWNER_CLEANUP_PHASE1_20260703"

if marker in text:
    print("sessions owner cleanup phase 1 already installed")
    raise SystemExit(0)

targets = [
    "nova-mobile-session-restore-override-v4.js",
    "nova-mobile-session-drawer-restore-v5.js",
    "nova-mobile-session-panel-v6.js",
]

removed = []

for target in targets:
    pattern = re.compile(
        r'^[ \t]*<script[^>\n]*' + re.escape(target) + r'[^>\n]*>\s*</script>[ \t]*\n?',
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))
    if not matches:
        print("not found:", target)
        continue

    for match in reversed(matches):
        removed.append(target)
        replacement = f'    <!-- {marker}: disabled legacy sessions owner: {target} -->\n'
        text = text[:match.start()] + replacement + text[match.end():]

path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("disabled legacy session owner scripts:", len(removed))
for item in removed:
    print("-", item)
