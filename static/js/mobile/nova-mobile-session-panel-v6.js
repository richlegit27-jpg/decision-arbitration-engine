(function () {
    "use strict";

    const VERSION = "mobile-session-panel-v6";
    window.__NOVA_MOBILE_SESSION_PANEL_V6__ = true;

    function log() {
        try { console.log("[NOVA MOBILE SESSION PANEL V6]", ...arguments); } catch (_) {}
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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

    function ensurePanel() {
        let panel = document.getElementById("nova-mobile-session-panel-v6");

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-mobile-session-panel-v6";
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
                <button id="nova-mobile-session-panel-v6-close" style="border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.08);color:white;border-radius:999px;padding:8px 12px;">Close</button>
            </div>
            <div id="nova-mobile-session-panel-v6-list" style="overflow:auto;-webkit-overflow-scrolling:touch;padding:10px;display:flex;flex-direction:column;gap:8px;"></div>
        `;

        document.body.appendChild(panel);

        panel.querySelector("#nova-mobile-session-panel-v6-close").addEventListener("click", function () {
            panel.style.display = "none";
        });

        return panel;
    }

    async function renderPanel() {
        const panel = ensurePanel();
        const list = panel.querySelector("#nova-mobile-session-panel-v6-list");

        panel.style.display = "flex";
        list.innerHTML = `<div style="padding:12px;color:rgba(255,255,255,0.75);">Loading sessions...</div>`;

        const sessions = (await loadSessions()).map(normalizeSession).filter(s => s.id);

        if (!sessions.length) {
            list.innerHTML = `<div style="padding:12px;color:rgba(255,255,255,0.75);">No sessions found.</div>`;
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

            button.addEventListener("click", async function () {
                if (typeof window.NovaMobileRestoreSession !== "function") {
                    console.warn("[NOVA MOBILE SESSION PANEL V6] NovaMobileRestoreSession missing");
                    return;
                }

                log("restoring", session.id);

                const restored = await window.NovaMobileRestoreSession(session.id);
                log("restored", restored && restored.id, restored && restored.messages && restored.messages.length);

                panel.style.display = "none";
            });

            list.appendChild(button);
        }
    }

    function wireButtons() {
        document.addEventListener("click", function (event) {
            const node = event.target && event.target.closest
                ? event.target.closest("button, a, [role='button']")
                : null;

            if (!node) {
                return;
            }

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
                renderPanel();
            }
        }, true);
    }

    window.NovaMobileSessionPanelV6 = {
        version: VERSION,
        open: renderPanel,
        loadSessions: loadSessions
    };

    wireButtons();
    log("active", VERSION);
})();
