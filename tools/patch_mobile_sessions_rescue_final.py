from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "nova-mobile-sessions-rescue-final-v1.js"
script = '    <script src="/static/js/mobile/nova-mobile-sessions-rescue-final-v1.js?v=sessions-rescue-final-v1-20260703"></script>'

if marker in text:
    print("sessions rescue final already wired")
    raise SystemExit(0)

anchors = [
    '    <script src="/static/js/mobile/nova-mobile-sessions-close-final-v1.js?v=sessions-close-final-v1-20260703"></script>',
    '<script src="/static/js/mobile/nova-mobile-sessions-close-final-v1.js?v=sessions-close-final-v1-20260703"></script>',
    '    <script src="/static/js/mobile/nova-mobile-close-layout-reset-v1.js?v=close-layout-reset-v1-20260703"></script>',
    '<script src="/static/js/mobile/nova-mobile-close-layout-reset-v1.js?v=close-layout-reset-v1-20260703"></script>',
    '    <script src="/static/js/mobile/nova-mobile-sessions.js"></script>',
    '<script src="/static/js/mobile/nova-mobile-sessions.js"></script>',
]

for anchor in anchors:
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + script, 1)
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        print("wired sessions rescue final after:", anchor)
        raise SystemExit(0)

raise SystemExit("could not find sessions rescue wiring anchor")
