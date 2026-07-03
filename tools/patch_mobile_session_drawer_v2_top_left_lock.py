from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
text = js_path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_DRAWER_V2_TOPLEFT_LOCK_20260703"

if marker not in text:
    lock = r'''

// NOVA_SESSION_DRAWER_V2_TOPLEFT_LOCK_20260703
(function () {
    "use strict";

    if (window.__NOVA_SESSION_DRAWER_V2_TOPLEFT_LOCK_20260703__) {
        return;
    }
    window.__NOVA_SESSION_DRAWER_V2_TOPLEFT_LOCK_20260703__ = true;

    function forceDrawerTopLeft() {
        try {
            const button = document.getElementById("nova-session-drawer-v2-button");
            const panel = document.getElementById("nova-session-drawer-v2-panel");

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
            }

            Array.from(document.querySelectorAll("button, a")).forEach(function (el) {
                if (!el) return;
                if (el.id === "nova-session-drawer-v2-button") return;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel, #nova-session-drawer-v2-messages")) return;

                const text = String(el.textContent || "").trim().toLowerCase();
                const id = String(el.id || "").toLowerCase();
                const klass = String(el.className || "").toLowerCase();

                const looksLikeSession =
                    text === "sessions" ||
                    text === "session" ||
                    text.includes("sessions") ||
                    id.includes("session") ||
                    klass.includes("session");

                if (!looksLikeSession) return;

                const r = el.getBoundingClientRect();
                const nearRightSide = r.right > window.innerWidth - 240;
                const nearTopHalf = r.top >= 0 && r.top < 360;

                if (nearRightSide && nearTopHalf) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }

    forceDrawerTopLeft();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", forceDrawerTopLeft);
    }

    setTimeout(forceDrawerTopLeft, 100);
    setTimeout(forceDrawerTopLeft, 500);
    setTimeout(forceDrawerTopLeft, 1500);
    setInterval(forceDrawerTopLeft, 1000);
})();
'''
    text = text.rstrip() + "\n" + lock + "\n"
    js_path.write_text(text, encoding="utf-8")
    print("added top-left lock")
else:
    print("top-left lock already installed")

print("patched", js_path)
