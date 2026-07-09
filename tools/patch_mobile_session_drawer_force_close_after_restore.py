from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
js = js_path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_DRAWER_V2_FORCE_CLOSE_AFTER_RESTORE_20260703"

if marker not in js:
    anchor = "    window.NovaSessionDrawerV2Stable = {"
    if anchor not in js:
        raise SystemExit("missing public api anchor")

    block = r'''
    // NOVA_SESSION_DRAWER_V2_FORCE_CLOSE_AFTER_RESTORE_20260703
    function closeDrawerAfterRestore() {
        try {
            var panel = document.getElementById("nova-session-drawer-v2-panel");
            if (!panel) return;

            panel.setAttribute("data-open", "false");
            panel.style.setProperty("display", "none", "important");
            panel.style.setProperty("visibility", "hidden", "important");
            panel.style.setProperty("opacity", "0", "important");
            panel.style.setProperty("pointer-events", "none", "important");
        } catch (_) {}
    }

'''
    js = js.replace(anchor, block + anchor, 1)

old = '''renderSessionToMainChat(id, session.title || title, restoredMessages);

            try {
                var uiAfterRestore = getUi();
                uiAfterRestore.panel.setAttribute("data-open", "false");
                ownDrawer();
            } catch (_) {}'''

new = '''renderSessionToMainChat(id, session.title || title, restoredMessages);

            closeDrawerAfterRestore();
            setTimeout(closeDrawerAfterRestore, 50);
            setTimeout(closeDrawerAfterRestore, 250);
            setTimeout(closeDrawerAfterRestore, 750);'''

if old in js:
    js = js.replace(old, new, 1)
else:
    old2 = '''renderSessionToMainChat(id, session.title || title, restoredMessages);'''
    if old2 not in js:
        raise SystemExit("main chat restore call not found")
    js = js.replace(old2, old2 + "\n\n            closeDrawerAfterRestore();\n            setTimeout(closeDrawerAfterRestore, 50);\n            setTimeout(closeDrawerAfterRestore, 250);\n            setTimeout(closeDrawerAfterRestore, 750);", 1)

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

targets = [
    Path("app.py"),
    Path("templates/index.html"),
    Path("templates/mobile.html"),
]

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
        "nova-mobile-session-drawer-v2.js?v=20260703-stable-no-jitter-6-force-close-after-restore",
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("updated", path)

print("patched force close after restore")
