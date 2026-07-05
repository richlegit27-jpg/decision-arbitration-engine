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

    function hideOldLaunchers() {
        [
            "nova-standalone-sessions-button-v5",
            "nova-visible-sessions-launcher-final"
        ].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                try {
                    if (document.activeElement === el || el.contains(document.activeElement)) {
                        document.activeElement.blur();
                    }
                } catch (_) {}

                el.style.setProperty("display", "none", "important");
                el.style.setProperty("pointer-events", "none", "important");
                el.setAttribute("aria-hidden", "true");
            }
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
    padding: 62px 14px 14px 14px !important;
    background: rgba(15, 10, 28, 0.98) !important;
    color: #f7f2ff !important;
    border-left: 1px solid rgba(255,255,255,0.16) !important;
    box-shadow: -18px 0 50px rgba(0,0,0,0.45) !important;
    overflow: hidden !important;
    opacity: 1 !important;
    transform: none !important;
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
    min-width: 96px !important;
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

        drawer.className = "nova-session-drawer-bridge";
        drawer.removeAttribute("hidden");
        drawer.style.removeProperty("opacity");
        drawer.style.removeProperty("transform");

        return drawer;
    }

    function closeDrawer() {
        const drawer = ensureDrawer();
        drawer.classList.remove("is-open");
        drawer.style.setProperty("display", "none", "important");
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
                closeDrawer();
            });
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

    hideOldLaunchers();
    setTimeout(hideOldLaunchers, 500);
    setTimeout(hideOldLaunchers, 1500);

    window.NovaMobileSessionDrawerBridgeV1 = {
        open: openDrawer,
        close: closeDrawer
    };

    console.log(LOG, "installed");
})();


