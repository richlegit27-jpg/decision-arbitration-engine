from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
panel = ROOT / "static/js/mobile/nova-mobile-session-panel-v6.js"
loader = ROOT / "static/js/mobile/nova-mobile-session-restore-override-v4.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

panel_text = panel.read_text(encoding="utf-8")
loader_text = loader.read_text(encoding="utf-8")

check("new chat session v8 marker present", "NOVA_MOBILE_NEW_CHAT_SESSION_V8_20260703" in panel_text)
check("new chat creates fresh mobile session id", '"mobile_session_" + Date.now()' in panel_text)
check("new chat sets localStorage active id", "localStorage.setItem(key, sessionId)" in panel_text)
check("new chat clears visible chat", "clearVisibleChat" in panel_text)
check("new chat blocks old handlers", "stopImmediatePropagation" in panel_text)
check("new chat detects new chat buttons", "new chat" in panel_text and "new session" in panel_text)
check("new chat helper exported", "NovaMobileNewChatSessionV8" in panel_text)
check("v4 loader cache bumped", "new-chat-session-v8" in loader_text)

print("")
print("NOVA MOBILE NEW CHAT SESSION V8 SMOKE PASSED")
