from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703"
script = '    <script src="/static/js/mobile/nova-mobile-sessions-close-final-v1.js?v=sessions-close-final-v1-20260703"></script>'

if marker in text or "nova-mobile-sessions-close-final-v1.js" in text:
    print("sessions close final already wired")
    raise SystemExit(0)

anchors = [
    '    <script src="/static/js/mobile/nova-mobile-close-layout-reset-v1.js?v=close-layout-reset-v1-20260703"></script>',
    '<script src="/static/js/mobile/nova-mobile-close-layout-reset-v1.js?v=close-layout-reset-v1-20260703"></script>',
    '<script src="/static/js/mobile/nova-mobile-sessions.js"></script>',
]

for anchor in anchors:
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + script, 1)
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        print("wired sessions close final after:", anchor)
        raise SystemExit(0)

raise SystemExit("could not find sessions close wiring anchor")
