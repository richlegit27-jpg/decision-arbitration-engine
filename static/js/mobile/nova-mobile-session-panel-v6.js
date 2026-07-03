(function () {
    "use strict";

    const VERSION = "mobile-session-panel-v7";
    window.__NOVA_MOBILE_SESSION_PANEL_V7__ = true;
    window.__NOVA_MOBILE_SESSION_PANEL_V6__ = true;

    const ACTIVE_KEYS = [
        "nova_mobile_active_session_id",
        "nova_active_session_id",
        "active_session_id",
        "session_id"
    ];

    function log() {
        try { console.log("[NOVA MOBILE SESSION PANEL V7]", ...arguments); } catch (_) {}
    }

    function warn() {
        try { console.warn("[NOVA MOBILE SESSION PANEL V7]", ...arguments); } catch (_) {}
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getActiveSessionId() {
        for (const key of ACTIVE_KEYS) {
            try {
                const value = String(localStorage.getItem(key) || "").trim();
                if (value) return value;
            } catch (_) {}
        }

        const globals = [
            window.novaMobileActiveSessionId,
            window.activeSessionId,
            window.currentSessionId,
            window.NOVA_ACTIVE_SESSION_ID
        ];

        for (const value of globals) {
            const id = String(value || "").trim();
            if (id) return id;
        }

        return "";
    }

    function setActiveSessionId(id) {
        const sessionId = String(id || "").trim();
        if (!sessionId) return "";

        for (const key of ACTIVE_KEYS) {
            try { localStorage.setItem(key, sessionId); } catch (_) {}
        }

        window.novaMobileActiveSessionId = sessionId;
        window.activeSessionId = sessionId;
        window.currentSessionId = sessionId;
        window.NOVA_ACTIVE_SESSION_ID = sessionId;

        return sessionId;
    }

    function ensureActiveSessionId() {
        let id = getActiveSessionId();

        if (!id) {
            id = "mobile_session_" + Date.now();
            setActiveSessionId(id);
            log("created active session", id);
        }

        return id;
    }

    function installChatSessionSaveGuard() {
        if (window.__NOVA_MOBILE_CHAT_SESSION_SAVE_GUARD_V7__) {
            return;
        }

        window.__NOVA_MOBILE_CHAT_SESSION_SAVE_GUARD_V7__ = true;

        const originalFetch = window.fetch;
        if (typeof originalFetch !== "function") {
            return;
        }

        window.fetch = async function novaMobileSessionPanelV7Fetch(input, init) {
            const url = typeof input === "string"
                ? input
                : input && input.url
                    ? input.url
                    : "";

            if (!url.includes("/api/chat")) {
                return originalFetch.call(this, input, init);
            }

            const nextInit = Object.assign({}, init || {});
            nextInit.credentials = "include";

            const method = String(nextInit.method || "GET").toUpperCase();

            if (method === "POST" && typeof nextInit.body === "string") {
                try {
                    const payload = JSON.parse(nextInit.body);
                    const existing = String(payload.session_id || payload.sessionId || "").trim();
                    const sessionId = existing || ensureActiveSessionId();

                    payload.session_id = sessionId;
                    payload.sessionId = sessionId;

                    setActiveSessionId(sessionId);
                    nextInit.body = JSON.stringify(payload);

                    log("forced /api/chat session_id", sessionId);
                } catch (_) {}
            }

            return originalFetch.call(this, input, nextInit);
        };

        log("chat session save guard active");
    }

    async function loadSessions() {
        const response = await fetch("/api/sessions", {
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });

        const payload = await response.json();
        return payload.sessions || payload.items || payload.data || payload.results || [];
    }

    function normalizeSession(session) {
        const id = String(session.id || session.session_id || session.key || "").trim();
        const title = String(session.title || session.name || session.label || id || "Session").trim();
        const count = session.message_count || session.messages_count || session.count || (Array.isArray(session.messages) ? session.messages.length : "");

        return { id, title, count };
    }

    function closePanel() {
        const panel = document.getElementById("nova-mobile-session-panel-v6");

        if (panel) {
            panel.style.display = "none";
            panel.setAttribute("aria-hidden", "true");
        }

        document.body.classList.remove("nova-session-panel-open");

        log("panel closed");
    }

    function ensurePanel() {
        let panel = document.getElementById("nova-mobile-session-panel-v6");

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-mobile-session-panel-v6";
        panel.setAttribute("aria-hidden", "true");
        panel.style.cssText = [
            "position:fixed",
            "inset:0",
            "z-index:999998",
            "background:rgba(8,8,14,0.96)",
            "color:white",
            "display:none",
            "flex-direction:column",
            "font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        ].join(";");

        panel.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,0.14);">
                <strong>Sessions</strong>
                <button type="button" id="nova-mobile-session-panel-v6-close" style="border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.08);color:white;border-radius:999px;padding:8px 12px;">Close</button>
            </div>
            <div id="nova-mobile-session-panel-v6-list" style="overflow:auto;-webkit-overflow-scrolling:touch;padding:10px;display:flex;flex-direction:column;gap:8px;"></div>
        `;

        document.body.appendChild(panel);

        panel.addEventListener("click", function (event) {
            if (event.target === panel) {
                event.preventDefault();
                event.stopPropagation();
                closePanel();
            }
        }, true);

        const close = panel.querySelector("#nova-mobile-session-panel-v6-close");
        if (close) {
            close.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                closePanel();
            }, true);

            close.addEventListener("touchend", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                closePanel();
            }, true);
        }

        return panel;
    }

    async function openPanel() {
        const panel = ensurePanel();
        const list = panel.querySelector("#nova-mobile-session-panel-v6-list");

        panel.style.display = "flex";
        panel.setAttribute("aria-hidden", "false");
        document.body.classList.add("nova-session-panel-open");

        list.innerHTML = `<div style="padding:12px;color:rgba(255,255,255,0.75);">Loading sessions...</div>`;

        const sessions = (await loadSessions()).map(normalizeSession).filter(s => s.id);

        if (!sessions.length) {
            list.innerHTML = `<div style="padding:12px;color:rgba(255,255,255,0.75);">No sessions found yet. Send a message first.</div>`;
            return;
        }

        list.innerHTML = "";

        for (const session of sessions) {
            const button = document.createElement("button");
            button.type = "button";
            button.setAttribute("data-session-id", session.id);
            button.style.cssText = [
                "width:100%",
                "text-align:left",
                "border:1px solid rgba(255,255,255,0.14)",
                "background:rgba(255,255,255,0.07)",
                "color:white",
                "border-radius:14px",
                "padding:12px",
                "display:block"
            ].join(";");

            button.innerHTML = `
                <div style="font-weight:700;margin-bottom:4px;">${escapeHtml(session.title)}</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.65);">${escapeHtml(session.id)}${session.count !== "" ? " · " + escapeHtml(session.count) + " messages" : ""}</div>
            `;

            button.addEventListener("click", async function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                if (typeof window.NovaMobileRestoreSession !== "function") {
                    warn("NovaMobileRestoreSession missing");
                    return;
                }

                setActiveSessionId(session.id);
                log("restoring", session.id);

                try {
                    const restored = await window.NovaMobileRestoreSession(session.id);
                    log("restored", restored && restored.id, restored && restored.messages && restored.messages.length);
                } finally {
                    closePanel();
                }
            }, true);

            list.appendChild(button);
        }
    }

    function wireSessionButtons() {
        document.addEventListener("click", function (event) {
            const node = event.target && event.target.closest
                ? event.target.closest("button, a, [role='button']")
                : null;

            if (!node) return;

            const raw = (
                String(node.id || "") + " " +
                String(node.className || "") + " " +
                String(node.getAttribute("data-action") || "") + " " +
                String(node.textContent || "")
            ).toLowerCase();

            if (
                raw.includes("session") ||
                raw.includes("history") ||
                raw.includes("chat list") ||
                raw.includes("chats")
            ) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                openPanel();
            }
        }, true);

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closePanel();
            }
        }, true);
    }

    installChatSessionSaveGuard();
    wireSessionButtons();

    window.NovaMobileSessionPanelV6 = {
        version: VERSION,
        open: openPanel,
        close: closePanel,
        loadSessions: loadSessions,
        getActiveSessionId: getActiveSessionId,
        setActiveSessionId: setActiveSessionId
    };

    window.NovaMobileSessionPanelV7 = window.NovaMobileSessionPanelV6;

    log("active", VERSION);
})();
