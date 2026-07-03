from pathlib import Path
import re

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_OWNER_CLEANUP_PHASE2_INLINE_PANEL_20260703"

if marker in text:
    print("sessions owner cleanup phase 2 already installed")
    raise SystemExit(0)

pattern = re.compile(
    r'<script>\s*'
    r'\(function\s*\(\)\s*\{\s*'
    r'"use strict";'
    r'(?P<body>.*?)'
    r'\}\)\(\);\s*'
    r'</script>',
    re.S,
)

matches = []
for match in pattern.finditer(text):
    block = match.group(0)
    if (
        "function forceHide(panel)" in block
        and "function forceShow(panel, topOrBottom)" in block
        and "nova-mobile-sessions-panel" in block
        and 'setProperty("display", "none", "important")' in block
        and 'setAttribute("aria-hidden"' in block
    ):
        matches.append(match)

if len(matches) != 1:
    raise SystemExit(f"expected exactly 1 inline sessions panel owner block, found {len(matches)}")

match = matches[0]
replacement = (
    "<!-- "
    + marker
    + ": disabled legacy inline sessions panel forceHide/forceShow owner "
    + "-->\n"
)

text = text[:match.start()] + replacement + text[match.end():]
path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("disabled inline sessions panel owner block")
print("start index:", match.start())
print("end index:", match.end())
