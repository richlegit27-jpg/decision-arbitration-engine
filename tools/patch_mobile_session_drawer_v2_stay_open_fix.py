from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = js_path.read_text(encoding="utf-8")

def replace_function(src, name, replacement):
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

safe_hide = r'''function hideOldSessionButtons() {
        try {
            Array.from(document.querySelectorAll("button, a")).forEach(function (el) {
                if (!el) return;

                if (
                    el.id === "nova-session-drawer-v2-button" ||
                    el.id === "nova-session-drawer-v2-panel" ||
                    el.id === "nova-session-drawer-v2-messages" ||
                    el.getAttribute("data-nova-session-drawer-v2") === "true" ||
                    (el.closest && el.closest("#nova-session-drawer-v2-panel, #nova-session-drawer-v2-messages"))
                ) {
                    return;
                }

                const text = String(el.textContent || "").trim().toLowerCase();
                const id = String(el.id || "").toLowerCase();
                const klass = String(el.className || "").toLowerCase();

                const looksLikeOldSession =
                    text === "sessions" ||
                    text === "session" ||
                    text.includes("sessions") ||
                    id.includes("session") ||
                    klass.includes("session");

                if (!looksLikeOldSession) return;

                const r = el.getBoundingClientRect();
                const nearTopRight = r.top >= 0 && r.top < 220 && r.right > window.innerWidth - 240;

                if (nearTopRight) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }'''

js = replace_function(js, "hideOldSessionButtons", safe_hide)

marker = "NOVA_SESSION_DRAWER_V2_STAY_OPEN_FIX_20260703"
if marker not in js:
    stay_open = r'''

// NOVA_SESSION_DRAWER_V2_STAY_OPEN_FIX_20260703
(function () {
    "use strict";

    if (window.__NOVA_SESSION_DRAWER_V2_STAY_OPEN_FIX_20260703__) {
        return;
    }
    window.__NOVA_SESSION_DRAWER_V2_STAY_OPEN_FIX_20260703__ = true;

    function keepDrawerStable() {
        try {
            const button = document.getElementById("nova-session-drawer-v2-button");
            const panel = document.getElementById("nova-session-drawer-v2-panel");
            const messages = document.getElementById("nova-session-drawer-v2-messages");

            if (button) {
                button.setAttribute("data-nova-session-drawer-v2", "true");
                button.style.setProperty("position", "fixed", "important");
                button.style.setProperty("left", "12px", "important");
                button.style.setProperty("right", "auto", "important");
                button.style.setProperty("top", "10px", "important");
                button.style.setProperty("bottom", "auto", "important");
                button.style.setProperty("z-index", "2147483647", "important");
                button.style.setProperty("display", "block", "important");
                button.style.setProperty("visibility", "visible", "important");
                button.style.setProperty("pointer-events", "auto", "important");
                button.style.setProperty("transform", "none", "important");
                button.style.setProperty("margin", "0", "important");
            }

            if (panel) {
                panel.setAttribute("data-nova-session-drawer-v2", "true");
                panel.style.setProperty("position", "fixed", "important");
                panel.style.setProperty("left", "10px", "important");
                panel.style.setProperty("right", "10px", "important");
                panel.style.setProperty("top", "56px", "important");
                panel.style.setProperty("bottom", "auto", "important");
                panel.style.setProperty("max-height", "calc(100vh - 70px)", "important");
                panel.style.setProperty("overflow-y", "auto", "important");
                panel.style.setProperty("z-index", "2147483646", "important");
                panel.style.setProperty("transform", "none", "important");
                panel.style.setProperty("margin", "0", "important");
                panel.style.setProperty("pointer-events", "auto", "important");

                if (panel.getAttribute("data-open") === "true") {
                    panel.style.setProperty("display", "block", "important");
                    panel.style.setProperty("visibility", "visible", "important");
                    panel.style.setProperty("opacity", "1", "important");
                }
            }

            if (messages) {
                messages.setAttribute("data-nova-session-drawer-v2", "true");
            }
        } catch (_) {}
    }

    keepDrawerStable();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", keepDrawerStable);
    }

    document.addEventListener("click", function () {
        setTimeout(keepDrawerStable, 0);
        setTimeout(keepDrawerStable, 100);
        setTimeout(keepDrawerStable, 500);
        setTimeout(keepDrawerStable, 1200);
    }, true);

    setInterval(keepDrawerStable, 500);
})();
'''
    js = js.rstrip() + "\n" + stay_open + "\n"

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
    'nova-mobile-session-drawer-v2.js?v=20260703-stay-open-fix',
    app,
)
if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")
app_path.write_text(app2, encoding="utf-8")

print("patched drawer stay-open fix")
