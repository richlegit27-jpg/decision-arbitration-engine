from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

old = "/static/js/mobile/nova-mobile-sessions-rescue-final-v1.js?v=sessions-rescue-final-v1-20260703"
new = "/static/js/mobile/nova-mobile-sessions-rescue-final-v1.js?v=sessions-rescue-final-v2-panel-markup-20260703"

if new in text:
    print("sessions rescue v2 cache bust already installed")
    raise SystemExit(0)

if old not in text:
    raise SystemExit("old sessions rescue script URL not found")

text = text.replace(old, new, 1)
path.write_text(text.rstrip() + "\n", encoding="utf-8")

print("patched mobile rescue cache bust to v2")
