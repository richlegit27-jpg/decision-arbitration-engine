from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = ROOT / "static" / "js" / "mobile" / "nova-mobile-session-panel-v6.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("panel v6 exists", js.exists())

text = js.read_text(encoding="utf-8")

check("panel marker present", "__NOVA_MOBILE_SESSION_PANEL_V6__" in text)
check("opens exported panel", "NovaMobileSessionPanelV6" in text)
check("loads sessions", "/api/sessions" in text)
check("uses restore function", "NovaMobileRestoreSession" in text)
check("credentials include", 'credentials: "include"' in text)

wired = False
for rel in ("templates/mobile.html", "templates/index.html"):
    path = ROOT / rel
    if path.exists() and "nova-mobile-session-panel-v6.js" in path.read_text(encoding="utf-8"):
        wired = True
        print("PASS wired", rel)

check("panel v6 wired", wired)

print("")
print("NOVA MOBILE SESSION PANEL V6 SMOKE PASSED")
