from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "static/js/mobile/nova-mobile-send-dedupe-guard-v1.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

text = script.read_text(encoding="utf-8")

check("send dedupe script exists", script.exists())
check("marker present", "NOVA_MOBILE_SEND_DEDUPE_GUARD_V1_20260703" in text)
check("click guarded", 'addEventListener("click"' in text)
check("submit guarded", 'addEventListener("submit"' in text)
check("enter guarded", 'addEventListener("keydown"' in text)
check("stop immediate propagation used", "stopImmediatePropagation" in text)
check("same text lock used", "sameText" in text and "SEND_LOCK_MS" in text)

wired = False
for rel in ["templates/mobile.html", "templates/index.html", "templates/index-mobile.html"]:
    path = ROOT / rel
    if path.exists() and "nova-mobile-send-dedupe-guard-v1.js" in path.read_text(encoding="utf-8", errors="replace"):
        print("PASS wired", rel)
        wired = True

check("wired into at least one template", wired)

print("")
print("NOVA MOBILE SEND DEDUPE GUARD SMOKE PASSED")
