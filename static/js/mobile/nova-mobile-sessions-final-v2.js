(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_SESSIONS_FINAL_V2_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var PANEL_ID = "nova-mobile-sessions-final-panel-v2";
    var BACKDROP_ID = "nova-mobile-sessions-final-backdrop-v2";
    var HEADER_BUTTON_ID = "nova-mobile-sessions-toggle";

    function byId(id) {
        return document.getElementById(id);
    }

    function activeSessionId() {
        try {
            return new URLSearchParams(location.search).get("session_id") ||
                localStorage.getItem("nova_mobile_active_session_id") ||
                "";
        } catch (_) {
            return "";
        }
    }

    function closeSessions(reason) {
        var panel = byId(PANEL_ID);
        var backdrop = byId(BACKDROP_ID);

        if (panel) {
            panel.remove();
        }

        if (backdrop) {
            backdrop.remove();
        }

        document.body.style.overflow = "";
        document.documentElement.style.overflow = "";

        console.log("[Nova Mobile Sessions Final V2] close", reason || "unknown");

        return !!(panel || backdrop);
    }

    function normalizeSessions(data) {
        if (Array.isArray(data)) {
            return data;
        }

        if (Array.isArray(data && data.sessions)) {
            return data.sessions;
        }

        if (Array.isArray(data && data.items)) {
            return data.items;
        }

        if (Array.isArray(data && data.result && data.result.sessions)) {
            return data.result.sessions;
        }

        return [];
    }

    async function loadSessions() {
        var response = await fetch("/api/sessions?cache_bust=" + Date.now(), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        var data = await response.json();

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || "Could not load sessions");
        }

        return normalizeSessions(data);
    }

    function goToSession(id, reason) {
        if (!id) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
        } catch (_) {}

        location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=sessions-final-v2-" + encodeURIComponent(reason || "switch") + "-" + Date.now();
    }

    async function newChat() {
        try {
            var response = await fetch("/api/sessions/new", {
                method: "POST",
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({})
            });

            var data = await response.json();

            var id =
                data.session_id ||
                data.id ||
                (data.session && data.session.id) ||
                (data.result && data.result.id) ||
                "";

            if (!id) {
                id = "mobile_" + Date.now();
            }

            goToSession(id, "new-chat");
        } catch (error) {
            console.error("[Nova Mobile Sessions Final V2] new chat failed", error);
            goToSession("mobile_" + Date.now(), "new-chat-fallback");
        }
    }

    function makeButton(label, handler) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = label;
        btn.style.border = "1px solid rgba(255,255,255,0.18)";
        btn.style.borderRadius = "12px";
        btn.style.background = "rgba(255,255,255,0.10)";
        btn.style.color = "#fff";
        btn.style.padding = "10px 12px";
        btn.style.fontWeight = "800";
        btn.style.fontSize = "14px";
        btn.style.cursor = "pointer";
        btn.addEventListener("click", handler);
        return btn;
    }

    function sessionId(session) {
        return String(session.id || session.session_id || "");
    }

    function sessionTitle(session) {
        return String(session.title || session.name || sessionId(session) || "New Chat");
    }

    function sessionMessageCount(session) {
        if (typeof session.message_count === "number") {
            return session.message_count;
        }

        if (Array.isArray(session.messages)) {
            return session.messages.length;
        }

        return 0;
    }

    function renderRow(session) {
        var id = sessionId(session);
        var active = id && id === activeSessionId();

        var row = document.createElement("button");
        row.type = "button";
        row.style.display = "block";
        row.style.width = "100%";
        row.style.textAlign = "left";
        row.style.margin = "0 0 8px 0";
        row.style.padding = "12px";
        row.style.borderRadius = "14px";
        row.style.border = active ? "1px solid rgba(168,85,247,0.95)" : "1px solid rgba(255,255,255,0.14)";
        row.style.background = active ? "rgba(168,85,247,0.24)" : "rgba(255,255,255,0.07)";
        row.style.color = "#fff";
        row.style.cursor = "pointer";

        var title = document.createElement("div");
        title.textContent = (active ? "📌 " : "") + sessionTitle(session);
        title.style.fontSize = "14px";
        title.style.fontWeight = "900";
        title.style.whiteSpace = "nowrap";
        title.style.overflow = "hidden";
        title.style.textOverflow = "ellipsis";

        var meta = document.createElement("div");
        meta.textContent = id + " · " + sessionMessageCount(session) + " messages";
        meta.style.marginTop = "4px";
        meta.style.fontSize = "11px";
        meta.style.opacity = "0.72";
        meta.style.whiteSpace = "nowrap";
        meta.style.overflow = "hidden";
        meta.style.textOverflow = "ellipsis";

        row.appendChild(title);
        row.appendChild(meta);

        row.addEventListener("click", function () {
            goToSession(id, "switch");
        });

        return row;
    }

    function removeKnownOldPanels() {
        [
            "nova-session-switch-restore-panel-v1",
            "nova-mobile-sessions-final-panel-v1",
            "nova-mobile-sessions-final-backdrop-v1",
            "nova-mobile-session-owner-final-panel-v1",
            "nova-mobile-session-owner-final-backdrop-v1"
        ].forEach(function (id) {
            var el = byId(id);

            if (el) {
                el.remove();
            }
        });
    }

    async function openSessions(reason) {
        closeSessions("replace-before-open");
        removeKnownOldPanels();

        document.body.style.overflow = "hidden";

        var backdrop = document.createElement("div");
        backdrop.id = BACKDROP_ID;
        backdrop.style.position = "fixed";
        backdrop.style.inset = "0";
        backdrop.style.background = "rgba(0,0,0,0.52)";
        backdrop.style.zIndex = "2147483646";
        backdrop.addEventListener("click", function () {
            closeSessions("backdrop");
        });

        var panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.style.position = "fixed";
        panel.style.top = "0";
        panel.style.right = "0";
        panel.style.bottom = "0";
        panel.style.width = "min(92vw, 420px)";
        panel.style.background = "rgba(16,16,24,0.98)";
        panel.style.color = "#fff";
        panel.style.zIndex = "2147483647";
        panel.style.boxShadow = "-18px 0 44px rgba(0,0,0,0.45)";
        panel.style.padding = "calc(14px + env(safe-area-inset-top)) 14px calc(14px + env(safe-area-inset-bottom)) 14px";
        panel.style.boxSizing = "border-box";
        panel.style.overflow = "auto";
        panel.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";

        var top = document.createElement("div");
        top.style.display = "flex";
        top.style.alignItems = "center";
        top.style.justifyContent = "space-between";
        top.style.gap = "12px";
        top.style.marginBottom = "12px";

        var heading = document.createElement("div");
        heading.textContent = "Sessions";
        heading.style.fontSize = "20px";
        heading.style.fontWeight = "950";

        top.appendChild(heading);
        top.appendChild(makeButton("Close", function () {
            closeSessions("close-button");
        }));

        var actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginBottom = "12px";

        actions.appendChild(makeButton("New Chat", newChat));
        actions.appendChild(makeButton("Refresh", function () {
            openSessions("refresh");
        }));

        var list = document.createElement("div");
        list.textContent = "Loading sessions...";
        list.style.opacity = "0.85";

        panel.appendChild(top);
        panel.appendChild(actions);
        panel.appendChild(list);

        document.body.appendChild(backdrop);
        document.body.appendChild(panel);

        try {
            var sessions = await loadSessions();

            list.textContent = "";

            if (!sessions.length) {
                list.textContent = "No sessions found.";
                return true;
            }

            sessions.forEach(function (session) {
                list.appendChild(renderRow(session));
            });

            console.log("[Nova Mobile Sessions Final V2] open", {
                reason: reason || "unknown",
                sessions: sessions.length
            });

            return true;
        } catch (error) {
            console.error("[Nova Mobile Sessions Final V2] load failed", error);
            list.textContent = "Could not load sessions.";
            return false;
        }
    }

    function bindHeader() {
        var header = byId(HEADER_BUTTON_ID);

        if (!header) {
            return false;
        }

        if (header.textContent.trim() !== "Sessions") {
            header.textContent = "Sessions";
        }

        if (header.getAttribute("aria-label") !== "Sessions") {
            header.setAttribute("aria-label", "Sessions");
        }

        if (header.dataset.novaMobileSessionsFinalV2Bound === "1") {
            return true;
        }

        header.dataset.novaMobileSessionsFinalV2Bound = "1";

        header.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            openSessions("header");
        }, true);

        return true;
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeSessions("escape");
        }
    }, true);

    closeSessions("boot-cleanup");
    removeKnownOldPanels();
    bindHeader();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindHeader, { once: true });
    }

    setTimeout(bindHeader, 250);
    setTimeout(bindHeader, 1000);
    setTimeout(bindHeader, 2500);

    window.NovaMobileSessionsFinalV2 = {
        open: openSessions,
        close: closeSessions,
        loadSessions: loadSessions,
        bindHeader: bindHeader,
        activeSessionId: activeSessionId
    };

    console.log("[Nova Mobile Sessions Final V2] installed");
})();

