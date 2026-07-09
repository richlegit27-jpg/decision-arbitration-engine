from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "static/js/mobile/nova-mobile-new-chat-backend-create-v1.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

text = script.read_text(encoding="utf-8")

check("new chat backend create script exists", script.exists())
check("marker present", "NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V1_20260703" in text)
check("posts sessions new", "/api/sessions/new" in text)
check("uses credentials include", 'credentials: "include"' in text)
check("extracts session id", "extractSessionId" in text)
check("saves mobile active session", "nova_mobile_active_session_id" in text)
check("opens mobile with session id", "session_id=" in text)
check("captures new chat click", "document.addEventListener" in text and "click" in text)
check("stops old handlers", "stopImmediatePropagation" in text)

wired = False
for rel in ["templates/mobile.html", "templates/index.html", "templates/index-mobile.html"]:
    path = ROOT / rel
    if path.exists() and "nova-mobile-new-chat-backend-create-v1.js" in path.read_text(encoding="utf-8", errors="replace"):
        print("PASS wired", rel)
        wired = True

check("wired into at least one template", wired)

print("")
print("NOVA MOBILE NEW CHAT BACKEND CREATE SMOKE PASSED")
