from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "static/js/mobile/nova-mobile-url-session-authority-v1.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

text = script.read_text(encoding="utf-8")

check("url session authority script exists", script.exists())
check("marker present", "NOVA_MOBILE_URL_SESSION_AUTHORITY_V1_20260703" in text)
check("reads session_id from url", 'get("session_id")' in text)
check("writes mobile active session", "nova_mobile_active_session_id" in text)
check("strips new param", 'searchParams.delete("new")' in text)
check("patches fetch", "window.fetch" in text and "/api/chat" in text)
check("forces api chat session id", "data.session_id = sessionId" in text)

wired = False
for rel in ["templates/mobile.html", "templates/index.html", "templates/index-mobile.html"]:
    path = ROOT / rel
    if path.exists() and "nova-mobile-url-session-authority-v1.js" in path.read_text(encoding="utf-8", errors="replace"):
        print("PASS wired", rel)
        wired = True

check("wired into at least one template", wired)

print("")
print("NOVA MOBILE URL SESSION AUTHORITY SMOKE PASSED")
