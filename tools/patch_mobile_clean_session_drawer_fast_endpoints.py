from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

old = '''        const candidates = [
            {
                url: "/api/sessions/" + safeId + "/" + action,
                body: payload || {}
            },
            {
                url: "/api/sessions/" + action,
                body: body
            },
            {
                url: "/api/sessions/" + safeId,
                body: Object.assign({ action: action }, body)
            }
        ];
'''

new = '''        const candidates = [
            {
                url: "/api/sessions/" + action,
                body: body
            },
            {
                url: "/api/sessions/" + safeId + "/" + action,
                body: payload || {}
            },
            {
                url: "/api/sessions/" + safeId,
                body: Object.assign({ action: action }, body)
            }
        ];
'''

if old not in text:
    raise SystemExit("Could not find candidate endpoint block.")

text = text.replace(old, new, 1)
text = text.replace(
    'const MARK = "NOVA_MOBILE_CLEAN_SESSION_DRAWER_V3_20260704";',
    'const MARK = "NOVA_MOBILE_CLEAN_SESSION_DRAWER_V3_FAST_ENDPOINTS_20260704";',
    1
)
text = text.replace(
    'version: "clean-v3-actions"',
    'version: "clean-v3-fast-endpoints"',
    1
)
text = text.replace(
    'console.error("[Nova Clean Sessions V3] installed");',
    'console.error("[Nova Clean Sessions V3 Fast Endpoints] installed");',
    1
)

path.write_text(text, encoding="utf-8")
print("Reordered clean session drawer action endpoints.")
