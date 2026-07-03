from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js_path = ROOT / "static" / "js" / "mobile" / "nova-mobile-session-restore-override-v4.js"

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS", name)

check("override v4 js exists", js_path.exists())

js = js_path.read_text(encoding="utf-8")

check("override v4 marker present", "__NOVA_MOBILE_SESSION_RESTORE_OVERRIDE_V4__" in js)
check("restore function exported", "window.NovaMobileRestoreSession = restoreSession" in js)
check("detail endpoint used", "/api/sessions/" in js)
check("credentials include used", 'credentials: "include"' in js)
check("visible root creator present", "created visible restore root" in js)

wired = False

for rel in ("templates/mobile.html", "templates/index.html"):
    path = ROOT / rel
    if path.exists() and "nova-mobile-session-restore-override-v4.js" in path.read_text(encoding="utf-8"):
        wired = True
        print("PASS wired", rel)

check("override v4 wired into template", wired)

print("")
print("NOVA MOBILE SESSION RESTORE OVERRIDE V4 SMOKE PASSED")
