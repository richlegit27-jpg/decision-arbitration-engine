from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = js_path.read_text(encoding="utf-8")

old_interval = '''        setInterval(function () {
            installStyles();
            ownDrawerVisibility();
            hideOldSessionButtons();
        }, 500);'''

new_stable = '''        function stabilitySweep() {
            try {
                installStyles();
                ownDrawerVisibility();
                hideOldSessionButtons();
            } catch (_) {}
        }

        stabilitySweep();
        setTimeout(stabilitySweep, 100);
        setTimeout(stabilitySweep, 500);
        setTimeout(stabilitySweep, 1500);

        window.addEventListener("resize", stabilitySweep);
        document.addEventListener("visibilitychange", stabilitySweep);'''

if old_interval in js:
    js = js.replace(old_interval, new_stable, 1)
else:
    print("old 500ms interval not found; continuing")

marker = "// NOVA_SESSION_DRAWER_V2_BOOT_RACE_FIX_20260703"
idx = js.find(marker)

if idx >= 0:
    js = js[:idx].rstrip() + r'''

// NOVA_SESSION_DRAWER_V2_BOOT_RACE_FIX_20260703
// Reduced to a passive marker. The old emergency click timer forced panel visibility
// after every click and could cause page jitter/reflow.
(function () {
    "use strict";
    window.__NOVA_SESSION_DRAWER_V2_BOOT_RACE_FIX_20260703__ = true;

    document.addEventListener("click", function (event) {
        try {
            const target = event.target;
            if (
                target &&
                target.closest &&
                target.closest("#nova-session-drawer-v2-button, #nova-session-drawer-v2-panel")
            ) {
                window.__NOVA_SESSION_DRAWER_V2_USER_TOUCHED_20260703__ = true;
            }
        } catch (_) {}
    }, true);
})();
''' + "\n"

# Remove any leftover raw 500ms style-force interval if duplicated.
js = js.replace('setInterval(keepDrawerStable, 500);', 'setTimeout(keepDrawerStable, 500);')
js = js.replace('setInterval(tick, 250);', 'setTimeout(tick, 250);')
js = js.replace('setInterval(forceDrawerTopLeft, 1000);', 'setTimeout(forceDrawerTopLeft, 1000);')

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r"nova-mobile-session-drawer-v2\.js\?v=[^\"']+",
    "nova-mobile-session-drawer-v2.js?v=20260703-clean-replace-3-dejitter",
    app,
)

if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")

app_path.write_text(app2, encoding="utf-8")

print("patched drawer dejitter")
