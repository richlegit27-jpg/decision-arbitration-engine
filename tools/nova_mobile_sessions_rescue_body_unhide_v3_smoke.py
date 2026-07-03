from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
template_path = Path("templates/mobile.html")

js = js_path.read_text(encoding="utf-8", errors="replace")
template = template_path.read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("body unhide v3 marker present", "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V3_BODY_UNHIDE_20260703" in js)
check("restoreBodyVisibility function present", "function restoreBodyVisibility(reason)" in js)
check("body hidden attribute removed", 'body.removeAttribute("hidden")' in js)
check("body aria-hidden removed", 'body.removeAttribute("aria-hidden")' in js)
check("body display restored", 'body.style.setProperty("display", "block", "important")' in js)
check("panel hidden attribute removed on close/open", 'panel.removeAttribute("hidden")' in js)
check("focused close button blurred before hiding panel", "document.activeElement.blur()" in js)
check("interval keeps body restored", 'restoreBodyVisibility("interval")' in js)
check("template uses v3 cache bust", "sessions-rescue-final-v3-body-unhide-20260703" in template)

print("")
print("NOVA MOBILE SESSIONS RESCUE BODY UNHIDE V3 SMOKE PASSED")
