from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "static/js/mobile/nova-mobile-close-layout-reset-v1.js"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

text = script.read_text(encoding="utf-8")

check("close layout reset script exists", script.exists())
check("marker present", "NOVA_MOBILE_CLOSE_LAYOUT_RESET_V1_20260703" in text)
check("removes open classes", "OPEN_CLASSES" in text and "classList.remove" in text)
check("resets transforms", "style.transform" in text and "style.left" in text)
check("close target detector", "isCloseTarget" in text)
check("click listener installed", 'addEventListener("click"' in text)
check("escape listener installed", 'addEventListener("keydown"' in text)

wired = False
for rel in ["templates/mobile.html", "templates/index.html", "templates/index-mobile.html"]:
    path = ROOT / rel
    if path.exists() and "nova-mobile-close-layout-reset-v1.js" in path.read_text(encoding="utf-8", errors="replace"):
        print("PASS wired", rel)
        wired = True

check("wired into at least one template", wired)

print("")
print("NOVA MOBILE CLOSE LAYOUT RESET SMOKE PASSED")
