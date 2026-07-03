from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js_path = ROOT / "static" / "js" / "mobile" / "nova-mobile-session-restore-lock.js"
js = js_path.read_text(encoding="utf-8")

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS", name)

check("restore lock exists", js_path.exists())
check("base marker present", "__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__" in js)
check("emergency root v3 marker present", "__NOVA_MOBILE_SESSION_RESTORE_EMERGENCY_ROOT_V3__" in js)
check("emergency root creator present", "createEmergencyChatRoot" in js)
check("clear render uses emergency root", "root = createEmergencyChatRoot()" in js)
check("restore endpoint still used", "/api/sessions/" in js)
check("credentials include still used", 'credentials: "include"' in js or 'credentials = "include"' in js)

wired = False
cache_busted = False

for rel in ("templates/mobile.html", "templates/index.html"):
    path = ROOT / rel
    if not path.exists():
        continue

    html = path.read_text(encoding="utf-8")

    if "nova-mobile-session-restore-lock.js" in html:
        wired = True
        print("PASS wired", rel)

    if "session-restore-dom-root-v3" in html:
        cache_busted = True
        print("PASS cache busted", rel)

check("restore lock wired into mobile template", wired)
check("restore lock cache busted to v3", cache_busted)

print("")
print("NOVA MOBILE SESSION RESTORE EMERGENCY ROOT V3 SMOKE PASSED")
