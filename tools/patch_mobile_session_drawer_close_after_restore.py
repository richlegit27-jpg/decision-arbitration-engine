from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
js = js_path.read_text(encoding="utf-8")

old = '''renderSessionToMainChat(id, session.title || title, restoredMessages);'''

new = '''renderSessionToMainChat(id, session.title || title, restoredMessages);

            try {
                var uiAfterRestore = getUi();
                uiAfterRestore.panel.setAttribute("data-open", "false");
                ownDrawer();
            } catch (_) {}'''

if old not in js:
    raise SystemExit("main chat restore call not found")

js = js.replace(old, new, 1)
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
        "nova-mobile-session-drawer-v2.js?v=20260703-stable-no-jitter-5-close-after-restore",
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("updated", path)

print("patched drawer close after main restore")
