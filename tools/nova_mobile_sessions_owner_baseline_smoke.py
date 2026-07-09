from pathlib import Path

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")
rescue = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("main sessions owner loaded", "static/js/mobile/nova-mobile-sessions.js" in template)
check("rescue sessions owner loaded", "nova-mobile-sessions-rescue-final-v1.js" in template)
check("rescue v3 cache bust loaded", "sessions-rescue-final-v3-body-unhide-20260703" in template)

check("rescue has v1 marker", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703" in rescue)
check("rescue has v2 panel markup marker", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V2_PANEL_MARKUP_20260703" in rescue)
check("rescue has v3 body unhide marker", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V3_BODY_UNHIDE_20260703" in rescue)

check("rescue restores body hidden attr", 'body.removeAttribute("hidden")' in rescue)
check("rescue restores body aria hidden", 'body.removeAttribute("aria-hidden")' in rescue)
check("rescue forces sessions list markup", "ensurePanelMarkup(panel)" in rescue)
check("rescue loads /api/sessions", 'fetch("/api/sessions"' in rescue)

print("")
print("NOVA MOBILE SESSIONS OWNER BASELINE SMOKE PASSED")
