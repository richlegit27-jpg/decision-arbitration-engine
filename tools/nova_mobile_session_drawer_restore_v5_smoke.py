from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js_path = ROOT / "static" / "js" / "mobile" / "nova-mobile-session-drawer-restore-v5.js"

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS", name)

check("drawer restore v5 exists", js_path.exists())

js = js_path.read_text(encoding="utf-8")

check("drawer v5 marker present", "__NOVA_MOBILE_SESSION_DRAWER_RESTORE_V5__" in js)
check("uses NovaMobileRestoreSession", "NovaMobileRestoreSession" in js)
check("loads session list", "/api/sessions" in js)
check("credentials include used", 'credentials: "include"' in js)
check("click capture installed", 'document.addEventListener("click"' in js)
check("touch capture installed", 'document.addEventListener("touchend"' in js)
check("text fallback resolver present", "resolveByText" in js)

wired = False

for rel in ("templates/mobile.html", "templates/index.html"):
    path = ROOT / rel
    if path.exists() and "nova-mobile-session-drawer-restore-v5.js" in path.read_text(encoding="utf-8"):
        wired = True
        print("PASS wired", rel)

check("drawer restore v5 wired into template", wired)

print("")
print("NOVA MOBILE SESSION DRAWER RESTORE V5 SMOKE PASSED")
