from pathlib import Path

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")
js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
js = js_path.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("sessions rescue js exists", js_path.exists())
check("sessions rescue marker present", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703" in js)
check("exports rescue object", "NovaMobileSessionsRescueFinal" in js)
check("creates rescue button", "nova-mobile-sessions-rescue-button" in js)
check("creates sessions panel if missing", "nova-mobile-sessions-panel" in js)
check("loads sessions api", 'fetch("/api/sessions"' in js)
check("renders session rows", "nova-sessions-rescue-row" in js)
check("stores active session id", "nova_mobile_active_session_id" in js)
check("template loads rescue final", "nova-mobile-sessions-rescue-final-v1.js" in template)
check("main sessions owner still loaded", "static/js/mobile/nova-mobile-sessions.js" in template)

print("")
print("NOVA MOBILE SESSIONS RESCUE FINAL SMOKE PASSED")
