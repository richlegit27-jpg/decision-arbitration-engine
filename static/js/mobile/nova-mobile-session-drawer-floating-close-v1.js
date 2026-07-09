(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_FLOATING_CLOSE_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_FLOATING_CLOSE_V1_20260704__ = true;

    const LOG = "[Nova Session Drawer Floating Close V1]";
    const PANEL_ID = "nova-mobile-sessions-panel";
    const BUTTON_ID = "nova-mobile-session-drawer-floating-close-v1";
    const STYLE_ID = "nova-mobile-session-drawer-floating-close-style-v1";

    function panel() {
        return document.getElementById(PANEL_ID);
    }

    function isDrawerOpen() {
        const p = panel();
        if (!p) {
            return false;
        }

        return p.classList.contains("is-open") && getComputedStyle(p).display !== "none";
    }

    function ensureStyle() {
        if (document.getElementById(STYLE_ID)) {
            return;
        }

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
#${BUTTON_ID} {
    position: fixed !important;
    top: max(12px, env(safe-area-inset-top)) !important;
    right: 14px !important;
    z-index: 2147483647 !important;
    min-width: 92px !important;
    height: 48px !important;
    padding: 0 14px !important;
    border-radius: 999px !important;
    border: 2px solid rgba(255,255,255,0.82) !important;
    background: #ffffff !important;
    color: #1f1235 !important;
    font: 900 14px Arial, system-ui, sans-serif !important;
    box-shadow: 0 10px 34px rgba(0,0,0,0.55) !important;
    display: none !important;
    align-items: center !important;
    justify-content: center !important;
    pointer-events: auto !important;
    cursor: pointer !important;
}
#${BUTTON_ID}.is-visible {
    display: inline-flex !important;
}
`;
        document.head.appendChild(style);
    }

    function closeDrawer() {
        if (window.NovaMobileSessionDrawerBridgeV1 && typeof window.NovaMobileSessionDrawerBridgeV1.close === "function") {
            window.NovaMobileSessionDrawerBridgeV1.close();
        } else {
            const p = panel();
            if (p) {
                p.classList.remove("is-open");
                p.style.setProperty("display", "none", "important");
            }
        }

        update();
    }

    function ensureButton() {
        ensureStyle();

        let btn = document.getElementById(BUTTON_ID);

        if (!btn) {
            btn = document.createElement("button");
            btn.id = BUTTON_ID;
            btn.type = "button";
            btn.textContent = "× Close";
            btn.setAttribute("aria-label", "Close sessions drawer");

            btn.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                closeDrawer();
            }, true);

            document.body.appendChild(btn);
        }

        return btn;
    }

    function update() {
        const btn = ensureButton();

        if (isDrawerOpen()) {
            btn.classList.add("is-visible");
            btn.style.setProperty("display", "inline-flex", "important");
        } else {
            btn.classList.remove("is-visible");
            btn.style.setProperty("display", "none", "important");
        }
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && isDrawerOpen()) {
            event.preventDefault();
            closeDrawer();
        }
    }, true);

    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "style"]
    });

    setInterval(update, 500);
    setTimeout(update, 100);
    setTimeout(update, 700);

    window.NovaMobileSessionDrawerFloatingCloseV1 = {
        update: update,
        close: closeDrawer
    };

    console.log(LOG, "installed");
})();
