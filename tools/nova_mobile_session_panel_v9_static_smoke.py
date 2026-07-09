from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
panel = ROOT / "static/js/mobile/nova-mobile-session-panel-v9.js"
loader = ROOT / "static/js/mobile/nova-mobile-session-restore-override-v4.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

panel_text = panel.read_text(encoding="utf-8")
loader_text = loader.read_text(encoding="utf-8")

check("panel v9 file exists", panel.exists())
check("panel v9 has v8 marker", "NOVA_MOBILE_NEW_CHAT_SESSION_V8_20260703" in panel_text)
check("panel v9 has url boot marker", "NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703" in panel_text)
check("panel v9 exports active helper", "NovaMobileNewChatSessionV8" in panel_text)
check("panel v9 exposes get active", "getActiveSessionId" in panel_text)
check("v4 loader points to panel v9", "nova-mobile-session-panel-v9.js" in loader_text)
check("v4 loader cache is v9 new file", "v9-new-file" in loader_text)

print("")
print("NOVA MOBILE SESSION PANEL V9 STATIC SMOKE PASSED")
