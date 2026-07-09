(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_SESSION_OWNER_FINAL_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var PANEL_ID = "nova-mobile-session-owner-final-panel-v1";
    var BACKDROP_ID = "nova-mobile-session-owner-final-backdrop-v1";
    var HEADER_BUTTON_ID = "nova-mobile-sessions-toggle";

    function qs(id) {
        return document.getElementById(id);
    }

    function currentSessionId() {
        try {
            return new URLSearchParams(location.search).get("session_id") || localStorage.getItem("nova_mobile_active_session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function removeNode(id) {
        var node = qs(id);

        if (node && node.parentNode) {
            node.parentNode.removeChild(node);
            return true;
        }

        return false;
    }

    function closeDrawer(reason) {
        var closedPanel = removeNode(PANEL_ID);
        var closedBackdrop = removeNode(BACKDROP_ID);

        document.documentElement.classList.remove("nova-mobile-session-owner-open");
        document.body.classList.remove("nova-mobile-session-owner-open");
        document.documentElement.style.overflow = "";
        document.body.style.overflow = "";

        console.log("[Nova Session Owner Final V1] close", {
            reason: reason || "unknown",
            closedPanel: closedPanel,
            closedBackdrop: closedBackdrop
        });

        return closedPanel || closedBackdrop;
    }

    function hideOldLaunchers() {
        [
            "nova-clean-session-launcher-v2"
        ].forEach(function (id) {
            var el = qs(id);

            if (!el) {
                return;
            }

            el.style.display = "none";
            el.style.pointerEvents = "none";
            el.setAttribute("hidden", "hidden");
            el.setAttribute("aria-hidden", "true");
            el.setAttribute("tabindex", "-1");
        });
    }

    function makeButton(text, onClick) {
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.style.border = "1px solid rgba(255,255,255,0.18)";
        button.style.borderRadius = "12px";
        button.style.background = "rgba(255,255,255,0.10)";
        button.style.color = "#fff";
        button.style.padding = "10px 12px";
        button.style.fontSize = "14px";
        button.style.fontWeight = "700";
        button.style.cursor = "pointer";
        button.addEventListener("click", onClick);
        return button;
    }

    function normalizeSessionsPayload(data) {
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

    async function fetchSessions() {
        var response = await fetch("/api/sessions?cache_bust=" + Date.now(), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        var data = await response.json();
        return normalizeSessionsPayload(data);
    }

    async function createNewChat() {
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

            try {
                localStorage.setItem("nova_mobile_active_session_id", id);
            } catch (_) {}

            location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=session-owner-new-" + Date.now();
        } catch (error) {
            console.error("[Nova Session Owner Final V1] new chat failed", error);
            var fallback = "mobile_" + Date.now();
            location.href = "/mobile?session_id=" + encodeURIComponent(fallback) + "&v=session-owner-new-fallback-" + Date.now();
        }
    }

    function switchToSession(id) {
        if (!id) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
        } catch (_) {}

        location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=session-owner-switch-" + Date.now();
    }

    function sessionTitle(session) {
        return String(session.title || session.name || session.id || "New Chat");
    }

    function sessionCount(session) {
        if (typeof session.message_count === "number") {
            return session.message_count;
        }

        if (Array.isArray(session.messages)) {
            return session.messages.length;
        }

        return 0;
    }

    function renderSessionRow(session) {
        var id = String(session.id || session.session_id || "");
        var active = id && id === currentSessionId();

        var row = document.createElement("button");
        row.type = "button";
        row.dataset.sessionId = id;
        row.style.display = "block";
        row.style.width = "100%";
        row.style.textAlign = "left";
        row.style.margin = "0 0 8px 0";
        row.style.padding = "12px";
        row.style.borderRadius = "14px";
        row.style.border = active ? "1px solid rgba(168,85,247,0.95)" : "1px solid rgba(255,255,255,0.12)";
        row.style.background = active ? "rgba(168,85,247,0.22)" : "rgba(255,255,255,0.07)";
        row.style.color = "#fff";
        row.style.cursor = "pointer";

        var title = document.createElement("div");
        title.textContent = (active ? "📌 " : "") + sessionTitle(session);
        title.style.fontSize = "14px";
        title.style.fontWeight = "800";
        title.style.whiteSpace = "nowrap";
        title.style.overflow = "hidden";
        title.style.textOverflow = "ellipsis";

        var meta = document.createElement("div");
        meta.textContent = id + " · " + sessionCount(session) + " messages";
        meta.style.marginTop = "4px";
        meta.style.fontSize = "11px";
        meta.style.opacity = "0.72";
        meta.style.whiteSpace = "nowrap";
        meta.style.overflow = "hidden";
        meta.style.textOverflow = "ellipsis";

        row.appendChild(title);
        row.appendChild(meta);

        row.addEventListener("click", function () {
            switchToSession(id);
        });

        return row;
    }

    async function openDrawer(reason) {
        closeDrawer("replace-before-open");
        hideOldLaunchers();

        document.documentElement.classList.add("nova-mobile-session-owner-open");
        document.body.classList.add("nova-mobile-session-owner-open");
        document.body.style.overflow = "hidden";

        var backdrop = document.createElement("div");
        backdrop.id = BACKDROP_ID;
        backdrop.style.position = "fixed";
        backdrop.style.inset = "0";
        backdrop.style.background = "rgba(0,0,0,0.48)";
        backdrop.style.zIndex = "2147483646";
        backdrop.addEventListener("click", function () {
            closeDrawer("backdrop");
        });

        var panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.style.position = "fixed";
        panel.style.top = "0";
        panel.style.right = "0";
        panel.style.bottom = "0";
        panel.style.width = "min(92vw, 420px)";
        panel.style.background = "rgba(17,17,24,0.98)";
        panel.style.color = "#fff";
        panel.style.zIndex = "2147483647";
        panel.style.boxShadow = "-14px 0 40px rgba(0,0,0,0.45)";
        panel.style.padding = "calc(14px + env(safe-area-inset-top)) 14px calc(14px + env(safe-area-inset-bottom)) 14px";
        panel.style.boxSizing = "border-box";
        panel.style.overflow = "auto";
        panel.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";

        var top = document.createElement("div");
        top.style.display = "flex";
        top.style.alignItems = "center";
        top.style.justifyContent = "space-between";
        top.style.gap = "10px";
        top.style.marginBottom = "12px";

        var title = document.createElement("div");
        title.textContent = "Sessions";
        title.style.fontSize = "20px";
        title.style.fontWeight = "900";

        var close = makeButton("Close", function () {
            closeDrawer("close-button");
        });

        top.appendChild(title);
        top.appendChild(close);

        var actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginBottom = "12px";

        var newChat = makeButton("New Chat", function () {
            createNewChat();
        });

        var refresh = makeButton("Refresh", function () {
            openDrawer("refresh");
        });

        actions.appendChild(newChat);
        actions.appendChild(refresh);

        var list = document.createElement("div");
        list.textContent = "Loading sessions...";
        list.style.opacity = "0.85";

        panel.appendChild(top);
        panel.appendChild(actions);
        panel.appendChild(list);

        document.body.appendChild(backdrop);
        document.body.appendChild(panel);

        try {
            var sessions = await fetchSessions();

            list.textContent = "";

            if (!sessions.length) {
                list.textContent = "No sessions found.";
                return true;
            }

            sessions.forEach(function (session) {
                list.appendChild(renderSessionRow(session));
            });

            console.log("[Nova Session Owner Final V1] opened", {
                reason: reason || "unknown",
                sessions: sessions.length
            });
        } catch (error) {
            console.error("[Nova Session Owner Final V1] session load failed", error);
            list.textContent = "Could not load sessions.";
        }

        return true;
    }

    function bindHeader() {
        var header = qs(HEADER_BUTTON_ID);

        if (!header || header.dataset.novaSessionOwnerFinalBound === "1") {
            return;
        }

        header.dataset.novaSessionOwnerFinalBound = "1";
        header.textContent = "Sessions";
        header.setAttribute("aria-label", "Sessions");

        header.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            openDrawer("header-button");
        }, true);
    }

    document.addEventListener("click", function (event) {
        var target = event.target;

        if (!target || !target.closest) {
            return;
        }

        var header = target.closest("#" + HEADER_BUTTON_ID);

        if (!header) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openDrawer("document-capture");
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeDrawer("escape");
        }
    }, true);

    var observer = new MutationObserver(function () {
        bindHeader();
        hideOldLaunchers();
    });

    try {
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (_) {}

    bindHeader();
    hideOldLaunchers();

    setTimeout(bindHeader, 250);
    setTimeout(bindHeader, 750);
    setTimeout(bindHeader, 1500);

    window.NovaMobileSessionOwnerFinalV1 = {
        open: openDrawer,
        close: closeDrawer,
        bindHeader: bindHeader,
        fetchSessions: fetchSessions
    };

    console.log("[Nova Session Owner Final V1] installed");
})();
