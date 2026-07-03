from pathlib import Path

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")
js = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("real restore v4 marker present", "NOVA_MOBILE_SESSIONS_RESTORE_REAL_BACKEND_V4_20260703" in js)
check("real restore export present", "NovaMobileSessionRestoreV4" in js)
check("findSessionRecord present", "function findSessionRecord(data, sessionId)" in js)
check("data.sessions pool present", "data.sessions" in js)
check("session id match present", "candidate.id === sessionId" in js)
check("messages picked from matching record", "record.messages" in js)
check("api sessions detail fetch present", '"/api/sessions/" + encoded' in js)
check("api chat fallback fetch present", '"/api/chat/" + encoded' in js)
check("active id localStorage present", "nova_mobile_active_session_id" in js)
check("click capture present", 'document.addEventListener("click"' in js)
check("cache bust present", "sessions-real-restore-v4-20260703" in template)

print("")
print("NOVA MOBILE SESSIONS REAL RESTORE V4 SMOKE PASSED")
