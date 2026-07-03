from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
mobile = ROOT / "templates" / "mobile.html"
text = mobile.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("legacy sessions owner removed", "NOVA_MOBILE_UNIQUE_FINAL_SESSIONS_PANEL_OWNER_20260625" not in text)
check("broken session variable removed", "window.switchSession(session.id)" not in text)
check("main sessions panel still exists", 'id="nova-mobile-sessions-panel"' in text)
check("sessions core still referenced somewhere", "nova-mobile-sessions" in text)
check("close layout reset still wired", "nova-mobile-close-layout-reset-v1.js" in text)

print("")
print("NOVA REMOVE LEGACY MOBILE SESSIONS OWNER SMOKE PASSED")
