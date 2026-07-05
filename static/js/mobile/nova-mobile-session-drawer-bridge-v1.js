(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_BRIDGE_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_BRIDGE_V1_20260704__ = true;

    const LOG = "[Nova Session Drawer Bridge V1]";
    const DRAWER_ID = "nova-mobile-sessions-panel";
    const STYLE_ID = "nova-mobile-session-drawer-bridge-style-v1";

    function currentSessionId() {
        return new URLSearchParams(location.search).get("session_id") || "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function blurIfFocused(el) {
        try {
            if (el && (document.activeElement === el || el.contains(document.activeElement))) {
                document.activeElement.blur();
            }
        } catch (_) {}
    }

    function hideOldLaunchers() {
        [
            "nova-standalone-sessions-button-v5",
            "nova-visible-sessions-launcher-final"
        ].forEach(function (id) {
            const el = document.getElementById(id);
            if (!el) {
                return;
            }

            blurIfFocused(el);

            el.style.setProperty("display", "none", "important");
            el.style.setProperty("pointer-events", "none", "important");
            el.style.setProperty("visibility", "hidden", "important");
            el.setAttribute("tabindex", "-1");

            try {
                el.inert = true;
            } catch (_) {}
        });
    }

    function ensureStyle() {
        if (document.getElementById(STYLE_ID)) {
            return;
        }

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
#nova-mobile-sessions-panel.nova-session-drawer-bridge {
    position: fixed !important;
    top: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: min(92vw, 380px) !important;
    max-width: 380px !important;
    z-index: 2147483646 !important;
    display: none !important;
    flex-direction: column !important;
    box-sizing: border-box !important;
    padding: 68px 14px 14px 14px !important;
    background: rgba(15, 10, 28, 0.98) !important;
    color: #f7f2ff !important;
    border-left: 1px solid rgba(255,255,255,0.16) !important;
    box-shadow: -18px 0 50px rgba(0,0,0,0.45) !important;
    overflow: hidden !important;
    opacity: 1 !important;
    transform: none !important;
    visibility: visible !important;
}
#nova-mobile-sessions-panel.nova-session-drawer-bridge.is-open {
    display: flex !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-head {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    margin-bottom: 12px !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-title {
    font: 900 18px Arial, system-ui, sans-serif !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-close {
    position: fixed !important;
    top: max(12px, env(safe-area-inset-top)) !important;
    right: 14px !important;
    z-index: 2147483647 !important;
    min-width: 100px !important;
    height: 48px !important;
    padding: 0 16px !important;
    border-radius: 999px !important;
    border: 2px solid rgba(255,255,255,0.9) !important;
    background: #ffffff !important;
    color: #1f1235 !important;
    font: 900 14px Arial, system-ui, sans-serif !important;
    box-shadow: 0 10px 34px rgba(0,0,0,0.55) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    pointer-events: auto !important;
    cursor: pointer !important;
    opacity: 1 !important;
    visibility: visible !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-body {
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
    padding-bottom: 20px !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-row {
    width: 100% !important;
    display: block !important;
    text-align: left !important;
    box-sizing: border-box !important;
    margin: 8px 0 !important;
    padding: 12px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.07) !important;
    color: #f7f2ff !important;
    cursor: pointer !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-row.is-active {
    border-color: rgba(168,85,247,0.85) !important;
    background: rgba(124,58,237,0.28) !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-row-title {
    font: 900 14px Arial, system-ui, sans-serif !important;
    margin-bottom: 4px !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-row-meta {
    font: 700 11px Arial, system-ui, sans-serif !important;
    opacity: 0.72 !important;
}
#nova-mobile-sessions-panel .nova-session-bridge-empty,
#nova-mobile-sessions-panel .nova-session-bridge-loading {
    padding: 16px !important;
    opacity: 0.75 !important;
    font: 800 13px Arial, system-ui, sans-serif !important;
}
`;
        document.head.appendChild(style);
    }

    function ensureDrawer() {
        ensureStyle();

        let drawer = document.getElementById(DRAWER_ID);

        if (!drawer) {
            drawer = document.createElement("aside");
            drawer.id = DRAWER_ID;
            document.body.appendChild(drawer);
        }

        blurIfFocused(drawer);

        drawer.className = "nova-session-drawer-bridge";
        drawer.removeAttribute("hidden");
        drawer.removeAttribute("aria-hidden");
        drawer.style.removeProperty("opacity");
        drawer.style.removeProperty("transform");
        drawer.style.setProperty("visibility", "visible", "important");

        return drawer;
    }

    function closeDrawer() {
        const drawer = ensureDrawer();

        blurIfFocused(drawer);

        drawer.classList.remove("is-open");
        drawer.style.setProperty("display", "none", "important");

        console.log(LOG, "closed");
    }

    function openDrawer() {
        hideOldLaunchers();

        const drawer = ensureDrawer();

        drawer.innerHTML = `
            <div class="nova-session-bridge-head">
                <div class="nova-session-bridge-title">Sessions</div>
                <button type="button" class="nova-session-bridge-close" aria-label="Close sessions">× Close</button>
            </div>
            <div class="nova-session-bridge-body">
                <div class="nova-session-bridge-loading">Loading sessions...</div>
            </div>
        `;

        drawer.classList.add("is-open");
        drawer.style.setProperty("display", "flex", "important");

        const close = drawer.querySelector(".nova-session-bridge-close");
        if (close) {
            close.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                closeDrawer();
            }, true);

            try {
                close.focus({ preventScroll: true });
            } catch (_) {}
        }

        loadSessions(drawer);
    }

    async function loadSessions(drawer) {
        const body = drawer.querySelector(".nova-session-bridge-body");
        const active = currentSessionId();

        try {
            const r = await fetch("/api/sessions?v=" + Date.now(), {
                credentials: "include",
                cache: "no-store"
            });

            const data = await r.json();
            const sessions = data.sessions || data.items || [];

            if (!sessions.length) {
                body.innerHTML = `<div class="nova-session-bridge-empty">No sessions found.</div>`;
                return;
            }

            body.innerHTML = sessions.map(function (session) {
                const sid = session.id || "";
                const title = session.title || "Untitled session";
                const count = session.message_count ?? (session.messages ? session.messages.length : 0);
                const activeClass = sid === active ? " is-active" : "";

                return `
                    <button
                        type="button"
                        class="nova-session-bridge-row${activeClass}"
                        data-nova-session-id="${escapeHtml(sid)}"
                    >
                        <div class="nova-session-bridge-row-title">${escapeHtml(title)}</div>
                        <div class="nova-session-bridge-row-meta">${escapeHtml(count)} messages · ${escapeHtml(sid.slice(-8))}</div>
                    </button>
                `;
            }).join("");

            body.querySelectorAll("[data-nova-session-id]").forEach(function (row) {
                row.addEventListener("click", function (event) {
                    const sid = row.getAttribute("data-nova-session-id");

                    if (!sid || sid === active) {
                        return;
                    }

                    event.preventDefault();
                    event.stopPropagation();

                    try {
                        localStorage.setItem("nova_mobile_active_session_id", sid);
                        sessionStorage.setItem("nova_mobile_active_session_id", sid);
                    } catch (_) {}

                    console.log(LOG, "switching", { from: active, to: sid });

                    location.href = "/mobile?session_id=" + encodeURIComponent(sid) + "&v=session-drawer-bridge-" + Date.now();
                });
            });

            console.log(LOG, "rendered sessions", sessions.length);
        } catch (e) {
            console.error(LOG, "failed to load sessions", e);
            body.innerHTML = `<div class="nova-session-bridge-empty">Failed to load sessions.</div>`;
        }
    }

    document.addEventListener("click", function (event) {
        const closeButton = event.target && event.target.closest
            ? event.target.closest(".nova-session-bridge-close")
            : null;

        if (closeButton) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            closeDrawer();
            return;
        }

        const headerButton = event.target && event.target.closest
            ? event.target.closest("#nova-mobile-sessions-toggle")
            : null;

        if (!headerButton) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openDrawer();
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            const drawer = document.getElementById(DRAWER_ID);
            if (drawer && drawer.classList.contains("is-open")) {
                event.preventDefault();
                closeDrawer();
            }
        }
    }, true);

    hideOldLaunchers();
    setTimeout(hideOldLaunchers, 500);
    setTimeout(hideOldLaunchers, 1500);


    function removeLegacySessionLaunchers() {
        function removeOne(el) {
            if (!el) {
                return;
            }

            try {
                if (document.activeElement === el || el.contains(document.activeElement)) {
                    document.activeElement.blur();
                }
            } catch (_) {}

            try {
                el.inert = true;
            } catch (_) {}

            try {
                el.remove();
            } catch (_) {
                el.style.setProperty("display", "none", "important");
                el.style.setProperty("visibility", "hidden", "important");
                el.style.setProperty("pointer-events", "none", "important");
                el.setAttribute("tabindex", "-1");
            }
        }

        [
            "nova-visible-sessions-launcher-final",
            "nova-standalone-sessions-button-v5",
            "nova-standalone-sessions-drawer-v5"
        ].forEach(function (id) {
            removeOne(document.getElementById(id));
        });

        document.querySelectorAll("button, [role='button']").forEach(function (el) {
            if (!el) {
                return;
            }

            if (el.id === "nova-mobile-sessions-toggle") {
                return;
            }

            if (el.closest && el.closest("#nova-mobile-sessions-panel")) {
                return;
            }

            const text = String(el.textContent || "").replace(/\s+/g, " ").trim();

            if (text !== "☰ Sessions" && text !== "Sessions") {
                return;
            }

            let fixed = false;

            try {
                fixed = getComputedStyle(el).position === "fixed";
            } catch (_) {}

            if (fixed) {
                removeOne(el);
            }
        });
    }

    removeLegacySessionLaunchers();
    setTimeout(removeLegacySessionLaunchers, 50);
    setTimeout(removeLegacySessionLaunchers, 250);
    setTimeout(removeLegacySessionLaunchers, 750);
    setInterval(removeLegacySessionLaunchers, 400);

    try {
        new MutationObserver(removeLegacySessionLaunchers).observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (_) {}

    window.NovaMobileSessionDrawerBridgeV1 = {
        open: openDrawer,
        close: closeDrawer
    };

    console.log(LOG, "installed");
})();

