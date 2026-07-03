from pathlib import Path

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")
js_path = Path("static/js/mobile/nova-mobile-sessions-close-final-v1.js")
js = js_path.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("sessions close final js exists", js_path.exists())
check("sessions close final marker present", "NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703" in js)
check("exports NovaMobileCloseSessionsFinal", "NovaMobileCloseSessionsFinal" in js)
check("exports NovaMobileCloseSessions", "NovaMobileCloseSessions" in js)
check("exports NovaCloseMobileSessions", "NovaCloseMobileSessions" in js)
check("hard close hides sessions panel", 'display", "none", "important"' in js)
check("hard close keeps composer visible", "nova-mobile-composer" in js)
check("click capture installed", 'document.addEventListener("click"' in js)
check("escape close installed", 'event.key === "Escape"' in js)
check("template loads sessions close final", "nova-mobile-sessions-close-final-v1.js" in template)
check("main sessions owner still loaded", "static/js/mobile/nova-mobile-sessions.js" in template)
check("close reset still loaded", "nova-mobile-close-layout-reset-v1.js" in template)

print("")
print("NOVA MOBILE SESSIONS CLOSE FINAL SMOKE PASSED")
