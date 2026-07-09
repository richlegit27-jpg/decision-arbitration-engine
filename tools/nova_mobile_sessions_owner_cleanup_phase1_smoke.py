from pathlib import Path
import re

template = Path("templates/mobile.html").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

disabled_marker = "NOVA_MOBILE_SESSIONS_OWNER_CLEANUP_PHASE1_20260703"

check("phase1 cleanup marker present", disabled_marker in template)

targets = [
    "nova-mobile-session-restore-override-v4.js",
    "nova-mobile-session-drawer-restore-v5.js",
    "nova-mobile-session-panel-v6.js",
]

for target in targets:
    active_script = re.search(
        r'<script[^>]+src=["\'][^"\']*' + re.escape(target) + r'[^"\']*["\'][^>]*>\s*</script>',
        template,
        re.I,
    )
    check(f"legacy owner script disabled: {target}", active_script is None)
    check(f"legacy owner comment retained: {target}", f"disabled legacy sessions owner: {target}" in template)

check("canonical sessions owner still loaded", "static/js/mobile/nova-mobile-sessions.js" in template)
check("rescue sessions owner still loaded", "nova-mobile-sessions-rescue-final-v1.js" in template)
check("rescue v3 cache bust still loaded", "sessions-rescue-final-v3-body-unhide-20260703" in template)
check("new chat backend creator still loaded", "nova-mobile-new-chat-backend-create-v1.js" in template)

print("")
print("NOVA MOBILE SESSIONS OWNER CLEANUP PHASE 1 SMOKE PASSED")
