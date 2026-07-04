(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_OWNER_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_OWNER_V1_20260703__ = true;

    var VERSION = "session-drawer-owner-v1-20260703";
    var state = {
        open: false,
        sessions: [],
        activeSessionId: null,
        loading: false
    };

    function isValidSessionId(value) {
        var text;

        if (!value) {
            return false;
        }

        text = String(value).trim();

        if (
            !text ||
            text === "null" ||
            text === "undefined" ||
            text.indexOf("=") === 0 ||
            text.indexOf(" ") >= 0
        ) {
            return false;
        }

        return (
            text.indexOf("session_") === 0 ||
            text.indexOf("mobile_") === 0 ||
            text.indexOf("debug_") === 0 ||
            text.indexOf("regression_") === 0
        );
    }

    function getSessionId(session) {
        if (!session) {
            return null;
        }

        return session.session_id || session.id || null;
    }

    function getSessionTitle(session) {
        var id;

        if (!session) {
            return "New Chat";
        }

        id = getSessionId(session);

        return (
            session.title ||
            session.name ||
            session.label ||
            (id ? "Session " + String(id).slice(-6) : "New Chat")
        );
    }

    function getMessageCount(session) {
        if (!session) {
            return 0;
        }

        if (typeof session.message_count === "number") {
            return session.message_count;
        }

        if (Array.isArray(session.messages)) {
            return session.messages.length;
        }

        return 0;
    }

    function getStoredSessionId() {
        try {
            return (
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("active_session_id")
            );
        } catch (err) {
            return null;
        }
    }

    function saveSessionId(sessionId) {
        if (!isValidSessionId(sessionId)) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.removeItem("active_session_id");
        } catch (err) {
            console.warn("[Nova Session Drawer Owner] localStorage save failed", err);
        }

        window.NovaMobileActiveSessionId = sessionId;
        state.activeSessionId = sessionId;
    }

    function setUrlSessionId(sessionId) {
        var url;

        if (!isValidSessionId(sessionId)) {
            return;
        }

        try {
            url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            window.history.replaceState(null, "", url.pathname + url.search + url.hash);
        } catch (err) {
            console.warn("[Nova Session Drawer Owner] URL update failed", err);
        }
    }

    function sleep(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    async function fetchJson(url, options) {
        var response;
        var text;
        var data;

        response = await fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }, options || {}));

        text = await response.text();

        try {
            data = text ? JSON.parse(text) : {};
        } catch (err) {
            data = {
                ok: false,
                error: text || response.statusText
            };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || response.statusText || ("HTTP " + response.status));
        }

        return data;
    }

    async function tryJson(calls) {
        var i;
        var lastError;

        for (i = 0; i < calls.length; i += 1) {
            try {
                return await fetchJson(calls[i].url, calls[i].options);
            } catch (err) {
                lastError = err;
            }
        }

        throw lastError || new Error("Request failed");
    }

    function injectStyles() {
        var style;

        if (document.getElementById("nova-session-drawer-owner-style-v1")) {
            return;
        }

        style = document.createElement("style");
        style.id = "nova-session-drawer-owner-style-v1";
        style.textContent = [
            "#nova-session-drawer-owner-button-v1 { position: fixed; left: 10px; top: 10px; z-index: 2147483000; min-height: 36px; padding: 8px 11px; border: 1px solid rgba(255,255,255,.16); border-radius: 999px; background: rgba(20,20,28,.92); color: #fff; font: 600 13px system-ui, -apple-system, Segoe UI, sans-serif; box-shadow: 0 8px 20px rgba(0,0,0,.28); }",
            "#nova-session-drawer-owner-backdrop-v1 { position: fixed; inset: 0; z-index: 2147483001; background: rgba(0,0,0,.42); display: none; }",
            "#nova-session-drawer-owner-backdrop-v1[data-open='true'] { display: block; }",
            "#nova-session-drawer-owner-panel-v1 { position: absolute; left: 0; top: 0; width: min(390px, 92vw); height: 100%; background: #12121a; color: #fff; box-shadow: 12px 0 28px rgba(0,0,0,.38); display: flex; flex-direction: column; }",
            "#nova-session-drawer-owner-header-v1 { display: flex; align-items: center; gap: 8px; padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,.10); }",
            "#nova-session-drawer-owner-title-v1 { font: 700 16px system-ui, -apple-system, Segoe UI, sans-serif; flex: 1; }",
            "#nova-session-drawer-owner-close-v1, #nova-session-drawer-owner-new-v1 { border: 1px solid rgba(255,255,255,.14); border-radius: 10px; background: rgba(255,255,255,.08); color: #fff; min-height: 34px; padding: 7px 10px; font: 600 13px system-ui, -apple-system, Segoe UI, sans-serif; }",
            "#nova-session-drawer-owner-body-v1 { overflow: auto; -webkit-overflow-scrolling: touch; padding: 8px; }",
            ".nova-session-drawer-row-v1 { border: 1px solid rgba(255,255,255,.10); border-radius: 14px; background: rgba(255,255,255,.045); padding: 10px; margin: 8px 0; }",
            ".nova-session-drawer-row-v1[data-active='true'] { outline: 2px solid rgba(155,100,255,.75); background: rgba(155,100,255,.14); }",
            ".nova-session-drawer-main-v1 { display: flex; gap: 8px; align-items: flex-start; }",
            ".nova-session-drawer-open-v1 { flex: 1; text-align: left; border: 0; background: transparent; color: inherit; padding: 0; }",
            ".nova-session-drawer-title-v1 { font: 700 14px system-ui, -apple-system, Segoe UI, sans-serif; line-height: 1.25; }",
            ".nova-session-drawer-meta-v1 { margin-top: 4px; opacity: .72; font: 12px system-ui, -apple-system, Segoe UI, sans-serif; }",
            ".nova-session-drawer-actions-v1 { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 9px; }",
            ".nova-session-drawer-actions-v1 button { border: 1px solid rgba(255,255,255,.12); border-radius: 10px; background: rgba(255,255,255,.07); color: #fff; padding: 6px 8px; font: 600 12px system-ui, -apple-system, Segoe UI, sans-serif; }",
            ".nova-session-drawer-empty-v1, .nova-session-drawer-loading-v1, .nova-session-drawer-error-v1 { padding: 18px 12px; opacity: .82; font: 14px system-ui, -apple-system, Segoe UI, sans-serif; }",
            ".nova-session-drawer-error-v1 { color: #ffb4b4; }"
        ].join("\n");

        document.head.appendChild(style);
    }

    function createButton() {
        var button;

        button = document.getElementById("nova-session-drawer-owner-button-v1");

        if (button) {
            return button;
        }

        button = document.createElement("button");
        button.id = "nova-session-drawer-owner-button-v1";
        button.type = "button";
        button.textContent = "☰ Sessions";
        button.setAttribute("aria-label", "Open sessions");
        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            openDrawer();
        });

        document.body.appendChild(button);
        return button;
    }

    function createDrawer() {
        var backdrop;
        var panel;
        var header;
        var title;
        var newButton;
        var closeButton;
        var body;

        backdrop = document.getElementById("nova-session-drawer-owner-backdrop-v1");

        if (backdrop) {
            return backdrop;
        }

        backdrop = document.createElement("div");
        backdrop.id = "nova-session-drawer-owner-backdrop-v1";
        backdrop.setAttribute("data-open", "false");

        panel = document.createElement("div");
        panel.id = "nova-session-drawer-owner-panel-v1";
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-label", "Sessions");

        header = document.createElement("div");
        header.id = "nova-session-drawer-owner-header-v1";

        title = document.createElement("div");
        title.id = "nova-session-drawer-owner-title-v1";
        title.textContent = "Sessions";

        newButton = document.createElement("button");
        newButton.id = "nova-session-drawer-owner-new-v1";
        newButton.type = "button";
        newButton.textContent = "New";

        closeButton = document.createElement("button");
        closeButton.id = "nova-session-drawer-owner-close-v1";
        closeButton.type = "button";
        closeButton.textContent = "Close";

        body = document.createElement("div");
        body.id = "nova-session-drawer-owner-body-v1";

        header.appendChild(title);
        header.appendChild(newButton);
        header.appendChild(closeButton);
        panel.appendChild(header);
        panel.appendChild(body);
        backdrop.appendChild(panel);
        document.body.appendChild(backdrop);

        closeButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            closeDrawer();
        });

        newButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            createNewSession();
        });

        backdrop.addEventListener("click", function (event) {
            if (event.target === backdrop) {
                closeDrawer();
            }
        });

        body.addEventListener("click", onBodyClick);

        return backdrop;
    }

    function isLegacySessionControl(node) {
        var text;

        if (!node || node.id === "nova-session-drawer-owner-button-v1") {
            return false;
        }

        if (node.closest && node.closest("#nova-session-drawer-owner-backdrop-v1")) {
            return false;
        }

        text = [
            node.id || "",
            node.className || "",
            node.getAttribute ? (node.getAttribute("aria-label") || "") : "",
            node.getAttribute ? (node.getAttribute("title") || "") : "",
            node.textContent || ""
        ].join(" ").toLowerCase();

        if (text.indexOf("nova-session-drawer-owner") >= 0) {
            return false;
        }

        if (text.indexOf("new chat") >= 0) {
            return false;
        }

        return (
            text.indexOf("session") >= 0 ||
            text.indexOf("sessions") >= 0 ||
            text.indexOf("history") >= 0 ||
            text.indexOf("nova-session-fallback-button") >= 0
        );
    }

    function hideLegacySessionControls() {
        var nodes;
        var i;

        nodes = Array.prototype.slice.call(
            document.querySelectorAll("button, a, [role='button']")
        );

        for (i = 0; i < nodes.length; i += 1) {
            if (isLegacySessionControl(nodes[i])) {
                nodes[i].setAttribute("data-nova-hidden-by-session-owner", "true");
                nodes[i].style.display = "none";
                nodes[i].style.pointerEvents = "none";
            }
        }
    }

    function getBody() {
        createDrawer();
        return document.getElementById("nova-session-drawer-owner-body-v1");
    }

    function renderLoading() {
        var body = getBody();
        body.innerHTML = '<div class="nova-session-drawer-loading-v1">Loading sessions…</div>';
    }

    function renderError(message) {
        var body = getBody();
        body.innerHTML = '<div class="nova-session-drawer-error-v1">' + escapeHtml(message || "Session drawer failed.") + '</div>';
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function renderSessions() {
        var body;
        var html;
        var i;
        var session;
        var id;
        var title;
        var count;
        var active;
        var pinned;

        body = getBody();

        if (!state.sessions.length) {
            body.innerHTML = '<div class="nova-session-drawer-empty-v1">No sessions found.</div>';
            return;
        }

        html = "";

        for (i = 0; i < state.sessions.length; i += 1) {
            session = state.sessions[i];
            id = getSessionId(session);

            if (!isValidSessionId(id)) {
                continue;
            }

            title = getSessionTitle(session);
            count = getMessageCount(session);
            active = id === state.activeSessionId;
            pinned = !!(session.pinned || session.pin || session.is_pinned);

            html += [
                '<div class="nova-session-drawer-row-v1" data-session-id="' + escapeHtml(id) + '" data-active="' + (active ? "true" : "false") + '">',
                    '<div class="nova-session-drawer-main-v1">',
                        '<button type="button" class="nova-session-drawer-open-v1" data-action="open">',
                            '<div class="nova-session-drawer-title-v1">' + escapeHtml(pinned ? "📌 " + title : title) + '</div>',
                            '<div class="nova-session-drawer-meta-v1">' + escapeHtml(String(count)) + ' messages · ' + escapeHtml(String(id).slice(-8)) + '</div>',
                        '</button>',
                    '</div>',
                    '<div class="nova-session-drawer-actions-v1">',
                        '<button type="button" data-action="open">Open</button>',
                        '<button type="button" data-action="rename">Rename</button>',
                        '<button type="button" data-action="pin">' + escapeHtml(pinned ? "Unpin" : "Pin") + '</button>',
                        '<button type="button" data-action="delete">Delete</button>',
                    '</div>',
                '</div>'
            ].join("");
        }

        body.innerHTML = html || '<div class="nova-session-drawer-empty-v1">No valid sessions found.</div>';
    }

    async function waitForRecoveryRenderer() {
        var i;

        for (i = 0; i < 40; i += 1) {
            if (
                window.NovaMobileChatVisibleRecoveryV1 &&
                typeof window.NovaMobileChatVisibleRecoveryV1.renderPayload === "function"
            ) {
                return window.NovaMobileChatVisibleRecoveryV1;
            }

            await sleep(50);
        }

        return null;
    }

    async function renderSessionPayload(sessionId) {
        var payload;
        var renderer;

        payload = await fetchJson(
            "/api/sessions/" + encodeURIComponent(sessionId) + "?cache_bust=" + Date.now(),
            {
                method: "GET"
            }
        );

        renderer = await waitForRecoveryRenderer();

        if (renderer && payload && payload.session) {
            renderer.renderPayload(payload);
        }
    }

    async function loadSessions() {
        var list;
        var active;
        var stored;

        state.loading = true;
        renderLoading();

        list = await fetchJson("/api/sessions?cache_bust=" + Date.now(), {
            method: "GET"
        });

        stored = getStoredSessionId();
        active = list.active_session_id || window.NovaMobileActiveSessionId || stored;

        if (!isValidSessionId(active)) {
            active = stored;
        }

        state.sessions = Array.isArray(list.sessions) ? list.sessions : [];
        state.activeSessionId = isValidSessionId(active) ? String(active).trim() : null;
        state.loading = false;

        renderSessions();
    }

    async function openDrawer() {
        var backdrop;

        injectStyles();
        createButton();
        backdrop = createDrawer();

        state.open = true;
        backdrop.setAttribute("data-open", "true");

        try {
            await loadSessions();
        } catch (err) {
            console.error("[Nova Session Drawer Owner] load failed", err);
            renderError(err.message || "Could not load sessions.");
        }
    }

    function closeDrawer() {
        var backdrop;

        backdrop = document.getElementById("nova-session-drawer-owner-backdrop-v1");

        state.open = false;

        if (backdrop) {
            backdrop.setAttribute("data-open", "false");
        }
    }

    async function openSession(sessionId) {
        if (!isValidSessionId(sessionId)) {
            return;
        }

        await tryJson([
            {
                url: "/api/sessions/" + encodeURIComponent(sessionId) + "/switch",
                options: {
                    method: "POST",
                    body: JSON.stringify({})
                }
            },
            {
                url: "/api/sessions/switch",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        session_id: sessionId
                    })
                }
            },
            {
                url: "/api/sessions/switch",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        id: sessionId
                    })
                }
            }
        ]).catch(function () {
            return {
                ok: true,
                local_only: true
            };
        });

        saveSessionId(sessionId);
        setUrlSessionId(sessionId);
        await renderSessionPayload(sessionId);
        closeDrawer();

        window.dispatchEvent(
            new CustomEvent("nova-mobile-session-opened", {
                detail: {
                    session_id: sessionId,
                    version: VERSION
                }
            })
        );

        console.log("[Nova Session Drawer Owner] opened", sessionId);
    }

    async function renameSession(sessionId) {
        var current;
        var nextTitle;

        current = state.sessions.find(function (session) {
            return getSessionId(session) === sessionId;
        });

        nextTitle = window.prompt("Rename session:", getSessionTitle(current));

        if (!nextTitle || !nextTitle.trim()) {
            return;
        }

        nextTitle = nextTitle.trim();

        await tryJson([
            {
                url: "/api/sessions/" + encodeURIComponent(sessionId) + "/rename",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        title: nextTitle
                    })
                }
            },
            {
                url: "/api/sessions/rename",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        session_id: sessionId,
                        title: nextTitle
                    })
                }
            }
        ]);

        await loadSessions();
    }

    async function pinSession(sessionId) {
        var current;
        var pinned;

        current = state.sessions.find(function (session) {
            return getSessionId(session) === sessionId;
        });

        pinned = !!(current && (current.pinned || current.pin || current.is_pinned));

        await tryJson([
            {
                url: "/api/sessions/" + encodeURIComponent(sessionId) + "/pin",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        pinned: !pinned
                    })
                }
            },
            {
                url: "/api/sessions/pin",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        session_id: sessionId,
                        pinned: !pinned
                    })
                }
            }
        ]);

        await loadSessions();
    }

    async function deleteSession(sessionId) {
        var nextSession;

        if (!window.confirm("Delete this session?")) {
            return;
        }

        await tryJson([
            {
                url: "/api/sessions/" + encodeURIComponent(sessionId) + "/delete",
                options: {
                    method: "POST",
                    body: JSON.stringify({})
                }
            },
            {
                url: "/api/sessions/delete",
                options: {
                    method: "POST",
                    body: JSON.stringify({
                        session_id: sessionId
                    })
                }
            },
            {
                url: "/api/sessions/" + encodeURIComponent(sessionId),
                options: {
                    method: "DELETE"
                }
            }
        ]);

        await loadSessions();

        if (state.activeSessionId === sessionId && state.sessions.length) {
            nextSession = state.sessions.find(function (session) {
                return isValidSessionId(getSessionId(session));
            });

            if (nextSession) {
                await openSession(getSessionId(nextSession));
            }
        }
    }

    async function createNewSession() {
        var result;
        var sessionId;

        result = await tryJson([
            {
                url: "/api/sessions/new",
                options: {
                    method: "POST",
                    body: JSON.stringify({})
                }
            },
            {
                url: "/api/sessions",
                options: {
                    method: "POST",
                    body: JSON.stringify({})
                }
            }
        ]);

        sessionId =
            result.session_id ||
            result.id ||
            getSessionId(result.session) ||
            getSessionId(result);

        if (isValidSessionId(sessionId)) {
            saveSessionId(sessionId);
            setUrlSessionId(sessionId);
            await renderSessionPayload(sessionId).catch(function () {});
            closeDrawer();
            return;
        }

        await loadSessions();
    }

    async function onBodyClick(event) {
        var button;
        var row;
        var action;
        var sessionId;

        button = event.target.closest("button[data-action]");

        if (!button) {
            return;
        }

        row = button.closest(".nova-session-drawer-row-v1");

        if (!row) {
            return;
        }

        action = button.getAttribute("data-action");
        sessionId = row.getAttribute("data-session-id");

        event.preventDefault();
        event.stopPropagation();

        try {
            if (action === "open") {
                await openSession(sessionId);
            } else if (action === "rename") {
                await renameSession(sessionId);
            } else if (action === "pin") {
                await pinSession(sessionId);
            } else if (action === "delete") {
                await deleteSession(sessionId);
            }
        } catch (err) {
            console.error("[Nova Session Drawer Owner] action failed", action, err);
            renderError(err.message || "Session action failed.");
        }
    }

    function boot() {
        injectStyles();
        createButton();
        createDrawer();
        hideLegacySessionControls();

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeDrawer();
            }
        });

        try {
            new MutationObserver(function () {
                hideLegacySessionControls();
                createButton();
            }).observe(document.body, {
                childList: true,
                subtree: true
            });
        } catch (err) {
            setInterval(function () {
                hideLegacySessionControls();
                createButton();
            }, 1500);
        }

        console.log("[Nova Session Drawer Owner] ready", VERSION);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileSessionDrawerOwnerV1 = {
        version: VERSION,
        open: openDrawer,
        close: closeDrawer,
        reload: loadSessions,
        openSession: openSession
    };
}());
