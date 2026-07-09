from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

bad_strings = [
    "function showMobileMemoryButton() {\n    ...\n}",
    "[Nova Mobile Memory Button Fix]",
    "[Nova Restore Real Mobile Menu Buttons]",
    "[Nova Force Real Mobile Menu DOM]",
    "NOVA_MOBILE_HIDE_TOP_BRAND_SIGN_20260624",
    "#nova-mobile-copy-chat,\n#nova-mobile-export-chat",
]

for bad in bad_strings:
    check("removed bad raw tail: " + bad[:60], bad not in text)

check("raw tail garbage marker present", "NOVA_MOBILE_REMOVE_RAW_TAIL_GARBAGE_20260703" in text)
check("sessions panel still exists", 'id="nova-mobile-sessions-panel"' in text)
check("main sessions owner still loaded", "static/js/mobile/nova-mobile-sessions.js" in text)
check("close reset still loaded", "nova-mobile-close-layout-reset-v1.js" in text)
check("menu panel scroll fix still present", "NOVA_MOBILE_MENU_PANEL_SCROLL_FIX_20260623" in text)

print("")
print("NOVA MOBILE RAW TAIL GARBAGE SMOKE PASSED")
