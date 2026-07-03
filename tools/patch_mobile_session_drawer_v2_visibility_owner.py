from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = js_path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_DRAWER_V2_VISIBILITY_OWNER_20260703"

if marker not in js:
    block = r'''

// NOVA_SESSION_DRAWER_V2_VISIBILITY_OWNER_20260703
(function () {
    "use strict";

    if (window.__NOVA_SESSION_DRAWER_V2_VISIBILITY_OWNER_20260703__) {
        return;
    }
    window.__NOVA_SESSION_DRAWER_V2_VISIBILITY_OWNER_20260703__ = true;

    const BAD_PANEL_CLASSES = [
        "nova-mobile-tools-menu-fixed",
        "nova-mobile-menu-panel-fixed",
        "nova-mobile-tools-menu-open",
        "nova-mobile-menu-panel-open"
    ];

    function installVisibilityOwnerStyle() {
        try {
            let style = document.getElementById("nova-session-drawer-v2-visibility-owner-style");
            if (!style) {
                style = document.createElement("style");
                style.id = "nova-session-drawer-v2-visibility-owner-style";
                document.head.appendChild(style);
            }

            style.textContent = `
#nova-session-drawer-v2-button {
    position: fixed !important;
    left: 12px !important;
    right: auto !important;
    top: 10px !important;
    bottom: auto !important;
    z-index: 2147483647 !important;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    transform: none !important;
    margin: 0 !important;
}

#nova-session-drawer-v2-panel {
    position: fixed !important;
    left: 10px !important;
    right: 10px !important;
    top: 56px !important;
    bottom: auto !important;
    max-height: calc(100vh - 70px) !important;
    overflow-y: auto !important;
    z-index: 2147483646 !important;
    transform: none !important;
    margin: 0 !important;
}

#nova-session-drawer-v2-panel[data-open="true"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}

#nova-session-drawer-v2-panel[data-open="false"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

#nova-session-drawer-v2-panel[data-open="true"].nova-mobile-tools-menu-fixed,
#nova-session-drawer-v2-panel[data-open="true"].nova-mobile-menu-panel-fixed,
#nova-session-drawer-v2-panel[data-open="true"].nova-mobile-tools-menu-open,
#nova-session-drawer-v2-panel[data-open="true"].nova-mobile-menu-panel-open {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
`;
        } catch (_) {}
    }

    function ownDrawerVisibility() {
        try {
            installVisibilityOwnerStyle();

            const button = document.getElementById("nova-session-drawer-v2-button");
            const panel = document.getElementById("nova-session-drawer-v2-panel");
            const messages = document.getElementById("nova-session-drawer-v2-messages");

            if (button) {
                button.setAttribute("data-nova-session-drawer-v2", "true");
                button.removeAttribute("hidden");
                button.removeAttribute("aria-hidden");
                button.style.setProperty("position", "fixed", "important");
                button.style.setProperty("left", "12px", "important");
                button.style.setProperty("right", "auto", "important");
                button.style.setProperty("top", "10px", "important");
                button.style.setProperty("bottom", "auto", "important");
                button.style.setProperty("z-index", "2147483647", "important");
                button.style.setProperty("display", "block", "important");
                button.style.setProperty("visibility", "visible", "important");
                button.style.setProperty("opacity", "1", "important");
                button.style.setProperty("pointer-events", "auto", "important");
                button.style.setProperty("transform", "none", "important");
                button.style.setProperty("margin", "0", "important");
            }

            if (panel) {
                panel.setAttribute("data-nova-session-drawer-v2", "true");
                panel.removeAttribute("hidden");
                panel.removeAttribute("aria-hidden");

                BAD_PANEL_CLASSES.forEach(function (name) {
                    try {
                        panel.classList.remove(name);
                    } catch (_) {}
                });

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

                if (panel.getAttribute("data-open") === "true") {
                    panel.style.setProperty("display", "block", "important");
                    panel.style.setProperty("visibility", "visible", "important");
                    panel.style.setProperty("opacity", "1", "important");
                    panel.style.setProperty("pointer-events", "auto", "important");
                }
            }

            if (messages) {
                messages.setAttribute("data-nova-session-drawer-v2", "true");
                messages.removeAttribute("hidden");
                messages.removeAttribute("aria-hidden");
            }
        } catch (_) {}
    }

    function observeDrawer() {
        try {
            const panel = document.getElementById("nova-session-drawer-v2-panel");
            if (!panel || panel.__novaSessionDrawerVisibilityObserver20260703) {
                return;
            }

            panel.__novaSessionDrawerVisibilityObserver20260703 = true;

            const observer = new MutationObserver(function () {
                setTimeout(ownDrawerVisibility, 0);
            });

            observer.observe(panel, {
                attributes: true,
                attributeFilter: ["class", "style", "data-open", "hidden", "aria-hidden"]
            });
        } catch (_) {}
    }

    function tick() {
        ownDrawerVisibility();
        observeDrawer();
    }

    tick();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", tick);
    }

    document.addEventListener("click", function () {
        setTimeout(tick, 0);
        setTimeout(tick, 50);
        setTimeout(tick, 250);
        setTimeout(tick, 750);
        setTimeout(tick, 1500);
    }, true);

    setInterval(tick, 250);
})();
'''
    js = js.rstrip() + "\n" + block + "\n"
else:
    print("visibility owner already installed")

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
    'nova-mobile-session-drawer-v2.js?v=20260703-visibility-owner',
    app,
)
if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")

app_path.write_text(app2, encoding="utf-8")

print("patched drawer visibility owner")
