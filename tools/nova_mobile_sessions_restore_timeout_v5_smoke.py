from pathlib import Path

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")
js = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("restore timeout v5 marker present", "NOVA_MOBILE_SESSIONS_RESTORE_TIMEOUT_V5_20260703" in js)
check("restore timeout v5 export present", "NovaMobileSessionRestoreV5" in js)
check("abort controller timeout present", "AbortController" in js)
check("detail timeout ms present", "DETAIL_TIMEOUT_MS = 4500" in js)
check("api chat preferred first", '"/api/chat/" + encoded' in js)
check("api sessions fallback present", '"/api/sessions/" + encoded' in js)
check("sessions list fallback present", '"/api/sessions"' in js)
check("v4 restore overridden", "window.NovaMobileSessionRestoreV4.restore = restore" in js)
check("v5 last written", "window.NovaMobileSessionRestoreV5.last = last" in js)
check("v4 last written", "window.NovaMobileSessionRestoreV4.last = last" in js)
check("cache bust present", "sessions-restore-timeout-v5-20260703" in template)

print("")
print("NOVA MOBILE SESSIONS RESTORE TIMEOUT V5 SMOKE PASSED")
