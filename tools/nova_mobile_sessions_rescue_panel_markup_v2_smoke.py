from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
js = js_path.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("rescue js exists", js_path.exists())
check("panel markup v2 marker present", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V2_PANEL_MARKUP_20260703" in js)
check("ensurePanelMarkup function present", "function ensurePanelMarkup(panel)" in js)
check("existing panel gets markup", "ensurePanelMarkup(panel);" in js)
check("rescue list forced into panel", "nova-mobile-sessions-rescue-list" in js)
check("rescue close forced into panel", "nova-sessions-rescue-close" in js)
check("loadSessions can find rescue list", "var list = $(\"nova-mobile-sessions-rescue-list\");" in js)
check("openPanel still loads sessions", "loadSessions();" in js)

print("")
print("NOVA MOBILE SESSIONS RESCUE PANEL MARKUP V2 SMOKE PASSED")
