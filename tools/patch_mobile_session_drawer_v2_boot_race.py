from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = js_path.read_text(encoding="utf-8")

def replace_function(src, name, replacement):
    start = src.find("async function " + name + "(")
    if start < 0:
        start = src.find("function " + name + "(")
    if start < 0:
        raise SystemExit("missing function " + name)

    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("missing opening brace for " + name)

    depth = 0
    end = None
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise SystemExit("missing closing brace for " + name)

    return src[:start] + replacement + src[end:]

new_boot = r'''async function boot() {
        ensureUi();

        let drawerTouchedByUser = false;

        document.addEventListener("click", function (event) {
            try {
                const target = event.target;
                if (
                    target &&
                    target.closest &&
                    target.closest("#nova-session-drawer-v2-button, #nova-session-drawer-v2-panel")
                ) {
                    drawerTouchedByUser = true;
                    window.__NOVA_SESSION_DRAWER_V2_USER_TOUCHED_20260703__ = true;
                }
            } catch (_) {}
        }, true);

        setInterval(function () {
            installStyles();
            ownDrawerVisibility();
            hideOldSessionButtons();
        }, 500);

        try {
            await loadSessions();
            const ui = ensureUi();
            const params = new URLSearchParams(window.location.search);
            const id = params.get("session_id");

            if (!id && !drawerTouchedByUser && !window.__NOVA_SESSION_DRAWER_V2_USER_TOUCHED_20260703__) {
                ui.panel.setAttribute("data-open", "false");
                ownDrawerVisibility();
            }
        } catch (_) {}

        const params = new URLSearchParams(window.location.search);
        const id = params.get("session_id");

        if (id) {
            try {
                const detail = await fetchJson("/api/sessions/" + encodeURIComponent(id));
                const session = detail.session || detail;
                renderMessages(id, session.title || id, normalizeMessages(detail));
            } catch (err) {
                log("url session failed", err);
            }
        }

        log("ready", VERSION);
    }'''

js = replace_function(js, "boot", new_boot)

marker = "NOVA_SESSION_DRAWER_V2_BOOT_RACE_FIX_20260703"
if marker not in js:
    js = js.rstrip() + r'''

// NOVA_SESSION_DRAWER_V2_BOOT_RACE_FIX_20260703
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

                setTimeout(function () {
                    const panel = document.getElementById("nova-session-drawer-v2-panel");
                    if (panel && window.__NOVA_SESSION_DRAWER_V2_USER_TOUCHED_20260703__) {
                        panel.setAttribute("data-open", "true");
                        panel.style.setProperty("display", "block", "important");
                        panel.style.setProperty("visibility", "visible", "important");
                        panel.style.setProperty("opacity", "1", "important");
                        panel.style.setProperty("pointer-events", "auto", "important");
                    }
                }, 650);
            }
        } catch (_) {}
    }, true);
})();
''' + "\n"

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r"nova-mobile-session-drawer-v2\.js\?v=[^\"']+",
    "nova-mobile-session-drawer-v2.js?v=20260703-clean-replace-2-racefix",
    app,
)

if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")

app_path.write_text(app2, encoding="utf-8")

print("patched drawer boot race")
