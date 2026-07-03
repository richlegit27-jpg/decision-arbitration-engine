/* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function addStyle() {
        if ($("nova-mobile-sessions-rescue-style")) return;

        var style = document.createElement("style");
        style.id = "nova-mobile-sessions-rescue-style";
        style.textContent = `
            #nova-mobile-sessions-rescue-button {
                position: fixed !important;
                top: 10px !important;
                right: 10px !important;
                z-index: 2147483600 !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                min-height: 36px !important;
                padding: 8px 12px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                background: rgba(20,20,28,0.92) !important;
                color: #fff !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                line-height: 1 !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
            }

            #nova-mobile-sessions-panel {
                position: fixed !important;
                inset: 0 !important;
                z-index: 2147483500 !important;
                background: rgba(8,8,12,0.98) !important;
                color: #fff !important;
                padding: 14px !important;
                box-sizing: border-box !important;
                overflow: auto !important;
            }

            #nova-mobile-sessions-panel.hidden {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            .nova-sessions-rescue-header {
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 12px !important;
                margin-bottom: 12px !important;
            }

            .nova-sessions-rescue-title {
                font-size: 18px !important;
                font-weight: 800 !important;
            }

            .nova-sessions-rescue-close {
                min-height: 36px !important;
                padding: 8px 12px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                background: rgba(255,255,255,0.08) !important;
                color: #fff !important;
                font-weight: 700 !important;
            }

            .nova-sessions-rescue-row {
                width: 100% !important;
                display: block !important;
                text-align: left !important;
                margin: 8px 0 !important;
                padding: 12px !important;
                border-radius: 14px !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                background: rgba(255,255,255,0.06) !important;
                color: #fff !important;
            }

            .nova-sessions-rescue-row strong {
                display: block !important;
                font-size: 14px !important;
                margin-bottom: 4px !important;
            }

            .nova-sessions-rescue-row span {
                display: block !important;
                opacity: 0.72 !important;
                font-size: 12px !important;
            }
        `;
        document.head.appendChild(style);
    }

    function showMainLayout() {
        var shell = document.querySelector(".mobile-shell");
        var messages = $("mobileChatMessages");
        var composer = $("nova-mobile-composer");

        [shell, messages, composer].forEach(function (el) {
            if (!el) return;
            el.style.removeProperty("height");
            el.style.removeProperty("max-height");
            el.style.removeProperty("min-height");
            el.style.removeProperty("overflow");
            el.style.removeProperty("transform");
        });

        if (messages) {
            messages.style.setProperty("display", "block", "important");
            messages.style.setProperty("visibility", "visible", "important");
            messages.style.setProperty("opacity", "1", "important");
            messages.style.setProperty("pointer-events", "auto", "important");
        }

        if (composer) {
            composer.style.setProperty("display", "flex", "important");
            composer.style.setProperty("visibility", "visible", "important");
            composer.style.setProperty("opacity", "1", "important");
            composer.style.setProperty("pointer-events", "auto", "important");
        }
    }

    function getPanel() {
        var panel = $("nova-mobile-sessions-panel") ||
            document.querySelector(".nova-mobile-sessions-panel") ||
            document.querySelector("[data-nova-sessions-panel='true']");

        if (panel) {
            if (!panel.id) panel.id = "nova-mobile-sessions-panel";
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-mobile-sessions-panel";
        panel.className = "hidden";
        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("data-nova-sessions-panel", "true");
        panel.innerHTML = `
            <div class="nova-sessions-rescue-header">
                <div class="nova-sessions-rescue-title">Sessions</div>
                <button type="button" class="nova-sessions-rescue-close" data-action="close-sessions">Close</button>
            </div>
            <div id="nova-mobile-sessions-rescue-list">Loading sessions...</div>
        `;
        document.body.appendChild(panel);
        return panel;
    }

    function closePanel() {
        var panel = getPanel();

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("data-nova-sessions-open", "false");
        panel.dataset.novaSessionsOpen = "false";
        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");
        panel.style.setProperty("pointer-events", "none", "important");

        document.documentElement.classList.remove("nova-mobile-sessions-open", "nova-sessions-open", "sessions-open");
        if (document.body) {
            document.body.classList.remove("nova-mobile-sessions-open", "nova-sessions-open", "sessions-open");
        }

        showMainLayout();
    }

    function normalizeSessions(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.sessions)) return payload.sessions;
        if (payload && Array.isArray(payload.items)) return payload.items;
        if (payload && payload.data && Array.isArray(payload.data.sessions)) return payload.data.sessions;
        return [];
    }

    function renderSessions(sessions) {
        var list = $("nova-mobile-sessions-rescue-list");
        if (!list) return;

        if (!sessions.length) {
            list.textContent = "No sessions found from /api/sessions.";
            return;
        }

        list.innerHTML = "";

        sessions.forEach(function (session) {
            var id = session.id || session.session_id || session.key || "";
            var title = session.title || session.name || session.label || id || "Untitled session";
            var updated = session.updated_at || session.modified_at || session.created_at || "";

            var row = document.createElement("button");
            row.type = "button";
            row.className = "nova-sessions-rescue-row";
            row.innerHTML = "<strong></strong><span></span>";
            row.querySelector("strong").textContent = title;
            row.querySelector("span").textContent = id ? (updated ? id + " · " + updated : id) : updated;

            row.addEventListener("click", function () {
                if (!id) return;

                try {
                    localStorage.setItem("nova_mobile_active_session_id", id);
                    localStorage.setItem("nova_active_session_id", id);
                } catch (e) {}

                if (window.NovaMobileSessionPanelV6 && typeof window.NovaMobileSessionPanelV6.switchSession === "function") {
                    window.NovaMobileSessionPanelV6.switchSession(id);
                    closePanel();
                    return;
                }

                if (typeof window.NovaMobileSwitchSession === "function") {
                    window.NovaMobileSwitchSession(id);
                    closePanel();
                    return;
                }

                window.location.href = "/mobile?session_id=" + encodeURIComponent(id);
            });

            list.appendChild(row);
        });
    }

    function loadSessions() {
        var list = $("nova-mobile-sessions-rescue-list");
        if (list) list.textContent = "Loading sessions...";

        fetch("/api/sessions", {
            method: "GET",
            credentials: "include",
            cache: "no-store"
        })
        .then(function (response) {
            return response.json();
        })
        .then(function (payload) {
            renderSessions(normalizeSessions(payload));
        })
        .catch(function (error) {
            if (list) {
                list.textContent = "Could not load sessions: " + (error && error.message ? error.message : error);
            }
        });
    }

    function openPanel() {
        addStyle();

        var panel = getPanel();

        panel.classList.remove("hidden");
        panel.setAttribute("aria-hidden", "false");
        panel.setAttribute("data-nova-sessions-open", "true");
        panel.dataset.novaSessionsOpen = "true";
        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("pointer-events", "auto", "important");

        document.documentElement.classList.add("nova-mobile-sessions-open");
        if (document.body) {
            document.body.classList.add("nova-mobile-sessions-open");
        }

        loadSessions();
    }

    function findExistingButton() {
        return $("nova-mobile-sessions-button") ||
            $("mobileSessionsButton") ||
            $("nova-sessions-button") ||
            document.querySelector("[data-action='sessions']") ||
            document.querySelector("[data-mobile-action='sessions']") ||
            document.querySelector("[aria-label='Sessions']") ||
            document.querySelector("[title='Sessions']");
    }

    function ensureButton() {
        addStyle();

        var button = findExistingButton();

        if (!button) {
            button = document.createElement("button");
            button.type = "button";
            button.id = "nova-mobile-sessions-rescue-button";
            button.textContent = "Sessions";
            button.setAttribute("aria-label", "Sessions");
            document.body.appendChild(button);
        } else {
            button.id = button.id || "nova-mobile-sessions-rescue-button";
            button.style.setProperty("display", "inline-flex", "important");
            button.style.setProperty("visibility", "visible", "important");
            button.style.setProperty("opacity", "1", "important");
            button.style.setProperty("pointer-events", "auto", "important");
        }

        if (button.dataset.novaSessionsRescueWired === "1") return button;

        button.dataset.novaSessionsRescueWired = "1";
        button.removeAttribute("onclick");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
            openPanel();
            return false;
        }, true);

        return button;
    }

    document.addEventListener("click", function (event) {
        var target = event.target && event.target.closest
            ? event.target.closest("[data-action='close-sessions'], .nova-sessions-rescue-close")
            : null;

        if (!target) return;

        event.preventDefault();
        event.stopPropagation();
        if (event.stopImmediatePropagation) {
            event.stopImmediatePropagation();
        }

        closePanel();
        return false;
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closePanel();
        }
    }, true);

    window.NovaMobileSessionsRescueFinal = {
        ensureButton: ensureButton,
        open: openPanel,
        close: closePanel,
        reload: loadSessions
    };

    function boot() {
        ensureButton();
        closePanel();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    setInterval(ensureButton, 1500);

    console.log("[NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V1_20260703] ready");
})();
