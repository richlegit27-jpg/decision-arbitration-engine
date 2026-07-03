from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_REMOVE_RAW_TAIL_GARBAGE_20260703"
if marker in text:
    print("raw tail garbage patch already installed")
    raise SystemExit(0)

end_marker = "<!-- NOVA_MOBILE_MENU_PANEL_SCROLL_FIX_20260623 -->"
end = text.find(end_marker)
if end == -1:
    raise SystemExit("could not find end marker: " + end_marker)

start_candidates = [
    '\n@media (max-width: 900px) {\n    a[href="/logout"],',
    '\n@media (max-width: 900px) { a[href="/logout"],',
    '\n(function() {\n    "use strict";\n\n    function showMobileMemoryButton()',
    '\n(function () {\n    "use strict";\n\n    function restoreRealMobileMenuButtons()',
    '\n#nova-mobile-copy-chat,\n#nova-mobile-export-chat',
]

starts = []
for needle in start_candidates:
    idx = text.find(needle)
    if idx != -1 and idx < end:
        starts.append(idx)

if not starts:
    raise SystemExit("could not find raw tail garbage start before menu panel scroll fix")

start = min(starts)
removed = text[start:end]

replacement = f'''
<!-- {marker}
     Removed malformed legacy mobile tail blocks that leaked raw JS/CSS into the page.
     Sessions panel remains owned by static/js/mobile/nova-mobile-sessions.js.
-->
'''

text = text[:start] + replacement + text[end:]
path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("removed raw tail garbage chars:", len(removed))
print("patched:", path)
