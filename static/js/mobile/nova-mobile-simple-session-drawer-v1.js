(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_SIMPLE_SESSION_DRAWER_V1_20260704";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    function getSessionId(item) {
        return item && (item.id || item.session_id || item.sessionId || "");
    }

    function getCurrentSessionId() {
        try {
            return (
                new URLSearchParams(location.search).get("session_id") ||
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("active_session_id") ||
                ""
            );
        } catch (_) {
            return "";
        }
    }

    function setCurrentSessionId(sessionId) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (_) {}
    }

    function openSession(sessionId) {
        if (!sessionId) {
            return;
        }

        setCurrentSessionId(sessionId);
        location.href = "/mobile?session_id=" + encodeURIComponent(sessionId) + "&v=simple-session-open-" + Date.now();
    }

    function makeButton() {
        let btn = document.getElementById("nova-simple-sessions-button-v1");

        if (btn) {
            return btn;
        }

        btn = document.createElement("button");
        btn.id = "nova-simple-sessions-button-v1";
        btn.type = "button";
        btn.textContent = "Sessions";
        btn.style.cssText = [
            "position:fixed",
            "left:10px",
            "top:10px",
            "z-index:2147483647",
            "border:1px solid rgba(255,255,255,.25)",
            "background:#17171c",
            "color:white",
            "border-radius:999px",
            "padding:10px 14px",
            "font:600 14px system-ui,-apple-system,Segoe UI,sans-serif",
            "box-shadow:0 8px 24px rgba(0,0,0,.35)"
        ].join(";");

        btn.addEventListener("click", function () {
            renderDrawer();
        });

        document.body.appendChild(btn);
        return btn;
    }

    function makePanel() {
        let panel = document.getElementById("nova-simple-sessions-panel-v1");

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = "nova-simple-sessions-panel-v1";
        panel.style.cssText = [
            "position:fixed",
            "left:10px",
            "right:10px",
            "top:56px",
            "max-height:70vh",
            "overflow:auto",
            "z-index:2147483647",
            "background:#101014",
            "color:white",
            "border:1px solid rgba(255,255,255,.18)",
            "border-radius:16px",
            "box-shadow:0 18px 60px rgba(0,0,0,.55)",
            "padding:12px",
            "display:none",
            "font:14px system-ui,-apple-system,Segoe UI,sans-serif"
        ].join(";");

        document.body.appendChild(panel);
        return panel;
    }

    function closePanel() {
        const panel = document.getElementById("nova-simple-sessions-panel-v1");
        if (panel) {
            panel.style.display = "none";
        }
    }

    async function fetchSessions() {
        const res = await fetch("/api/sessions?simple_drawer=" + Date.now(), {
            credentials: "include",
            cache: "no-store"
        });

        const data = await res.json();

        return {
            activeSessionId: data.active_session_id || "",
            sessions: data.sessions || data.items || []
        };
    }

    async function renderDrawer() {
        const panel = makePanel();

        panel.style.display = "block";
        panel.innerHTML = "<div style='padding:10px;'>Loading sessions...</div>";

        try {
            const data = await fetchSessions();
            const currentId = getCurrentSessionId() || data.activeSessionId;

            const header = document.createElement("div");
            header.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px;";

            const title = document.createElement("div");
            title.textContent = "Sessions";
            title.style.cssText = "font-weight:800;font-size:16px;";

            const close = document.createElement("button");
            close.type = "button";
            close.textContent = "Close";
            close.style.cssText = "background:#24242b;color:white;border:1px solid rgba(255,255,255,.2);border-radius:10px;padding:8px 10px;";
            close.addEventListener("click", closePanel);

            header.appendChild(title);
            header.appendChild(close);

            const list = document.createElement("div");
            list.style.cssText = "display:flex;flex-direction:column;gap:8px;";

            data.sessions.forEach(function (session) {
                const sessionId = getSessionId(session);
                const isActive = sessionId === currentId;
                const row = document.createElement("button");

                row.type = "button";
                row.style.cssText = [
                    "width:100%",
                    "text-align:left",
                    "border-radius:14px",
                    "border:1px solid " + (isActive ? "rgba(140,120,255,.85)" : "rgba(255,255,255,.14)"),
                    "background:" + (isActive ? "#27213f" : "#18181f"),
                    "color:white",
                    "padding:12px",
                    "display:block"
                ].join(";");

                const name = session.title || "New Chat";
                const count = session.message_count || 0;
                const pin = session.pinned ? " · pinned" : "";
                const active = isActive ? " · active" : "";

                row.innerHTML =
                    "<div style='font-weight:750;margin-bottom:4px;'>" + escapeHtml(name) + "</div>" +
                    "<div style='opacity:.75;font-size:12px;'>" + escapeHtml(sessionId) + "</div>" +
                    "<div style='opacity:.75;font-size:12px;margin-top:4px;'>" + count + " messages" + pin + active + "</div>";

                row.addEventListener("click", function () {
                    openSession(sessionId);
                });

                list.appendChild(row);
            });

            panel.innerHTML = "";
            panel.appendChild(header);

            if (!data.sessions.length) {
                const empty = document.createElement("div");
                empty.textContent = "No sessions returned.";
                empty.style.cssText = "opacity:.75;padding:10px;";
                panel.appendChild(empty);
            } else {
                panel.appendChild(list);
            }

            console.error("[Nova Simple Sessions] rendered", {
                count: data.sessions.length,
                activeSessionId: data.activeSessionId,
                currentId: currentId
            });
        } catch (err) {
            panel.innerHTML = "<div style='padding:10px;color:#ffb4b4;'>Failed to load sessions.</div>";
            console.error("[Nova Simple Sessions] failed", err);
        }
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    window.NovaMobileSimpleSessionDrawerV1 = {
        renderDrawer: renderDrawer,
        openSession: openSession
    };

    function boot() {
        makeButton();
        console.error("[Nova Simple Sessions] installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
