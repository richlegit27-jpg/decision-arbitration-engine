from pathlib import Path
import re

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

marker = "NOVA_MOBILE_SESSIONS_OWNER_CLEANUP_PHASE2_INLINE_PANEL_20260703"

check("phase2 inline panel cleanup marker present", marker in template)

bad_active_block = (
    "function forceHide(panel)" in template
    and "function forceShow(panel, topOrBottom)" in template
    and "nova-mobile-sessions-panel" in template
    and 'setProperty("display", "none", "important")' in template
)

check("legacy inline forceHide/forceShow block removed", not bad_active_block)

check("phase1 cleanup still present", "NOVA_MOBILE_SESSIONS_OWNER_CLEANUP_PHASE1_20260703" in template)
check("canonical sessions owner still loaded", "static/js/mobile/nova-mobile-sessions.js" in template)
check("rescue sessions owner still loaded", "nova-mobile-sessions-rescue-final-v1.js" in template)
check("rescue v3 cache bust still loaded", "sessions-rescue-final-v3-body-unhide-20260703" in template)
check("new chat backend creator still loaded", "nova-mobile-new-chat-backend-create-v1.js" in template)

print("")
print("NOVA MOBILE SESSIONS OWNER CLEANUP PHASE 2 INLINE PANEL SMOKE PASSED")
