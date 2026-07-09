(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_FINAL_OWNER_V2_20260708__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_FINAL_OWNER_V2_20260708__ = true;

    const API = {
        list: "/api/sessions",
        detail: function (id) {
            return "/api/sessions/" + encodeURIComponent(id);
        },
        newSession: "/api/sessions/new",
        rename: "/api/sessions/rename",
        pin: "/api/sessions/pin",
        delete: "/api/sessions/delete"
    };

    const IDS = {
        headerButton: "nova-mobile-sessions-toggle",
        finalButton: "nova-mobile-sessions-final-button-v1",
        panel: "nova-mobile-sessions-final-panel-v1",
        list: "nova-mobile-sessions-final-list-v1",
        status: "nova-mobile-sessions-final-status-v1",
        title: "nova-mobile-sessions-final-title-v1"
    };

    window.NOVA_SESSION_CORE = window.NOVA_SESSION_CORE || {
        activeSessionId: null,
        sessions: [],
        isOpen: false
    };

    function $(id) {
        return document.getElementById(id);
    }

    function jsonFetch(url, options) {
        return fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }, options || {})).then(async function (response) {
            const text = await response.text();
            let data = {};

            try {
                data = text ? JSON.parse(text) : {};
            } catch (error) {
                data = {
                    ok: false,
                    error: text || String(error)
                };
            }

            if (!response.ok || data.ok === false) {
                throw new Error(data.error || ("HTTP " + response.status));
            }

            return data;
        });
    }

    function getSessions(payload) {
        if (!payload) {
            return [];
        }

        if (Array.isArray(payload.sessions)) {
            return payload.sessions;
        }

        if (Array.isArray(payload.items)) {
            return payload.items;
        }

        if (Array.isArray(payload)) {
            return payload;
        }

        return [];
    }

    function normalizeSessionPayload(data, id) {
        const rawSession =
            data && data.session && typeof data.session === "object"
                ? data.session
                : data && typeof data === "object"
                    ? data
                    : {};

        const messages =
            Array.isArray(rawSession.messages)
                ? rawSession.messages
                : Array.isArray(data && data.messages)
                    ? data.messages
                    : [];

        const session = Object.assign({}, rawSession, {
            id: rawSession.id || rawSession.session_id || id,
            session_id: rawSession.session_id || rawSession.id || id,
            messages: messages
        });

        return {
            session_id: id,
            session: session,
            messages: messages
        };
    }

    function setStatus(message) {
        const el = $(IDS.status);

        if (el) {
            el.textContent = message || "";
        }
    }

    function activeIdFromStorage() {
        return (
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            window.novaActiveSessionId ||
            window.NOVA_ACTIVE_SESSION_ID ||
            ""
        );
    }

    function sessionIdFromUrl() {
        try {
            return new URL(window.location.href).searchParams.get("session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function setActiveId(id) {
        if (!id) {
            return;
        }

        localStorage.setItem("nova_mobile_active_session_id", id);
        localStorage.setItem("nova_active_session_id", id);

        window.NOVA_SESSION_CORE.activeSessionId = id;
        window.NOVA_ACTIVE_SESSION_ID = id;
        window.novaActiveSessionId = id;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function forceVisibleButton(button) {
        if (!button) {
            return;
        }

        button.removeAttribute("hidden");
        button.removeAttribute("data-nova-hidden-by-sessions-final");
        button.classList.remove("hidden", "nova-mobile-v10-parked");

        button.style.removeProperty("display");
        button.style.removeProperty("visibility");
        button.style.removeProperty("opacity");
        button.style.removeProperty("pointer-events");

        button.style.setProperty("display", "inline-flex", "important");
        button.style.setProperty("visibility", "visible", "important");
        button.style.setProperty("opacity", "1", "important");
        button.style.setProperty("pointer-events", "auto", "important");
    }

    function removeOldSessionUi() {
        const knownBad = [
            "nova-session-fallback-button-v1",
            "nova-session-fallback-panel-v1",
            "nova-mobile-session-drawer-v2-button",
            "nova-mobile-session-drawer-v2-panel",
            "nova-mobile-sessions-v10-button",
            "nova-mobile-sessions-v10-panel",
            "nova-mobile-session-v10-button",
            "nova-mobile-session-v10-panel",
            "nova-mobile-v10-sessions-panel"
        ];

        knownBad.forEach(function (id) {
            const el = document.getElementById(id);

            if (el) {
                el.remove();
            }
        });

        document.querySelectorAll("button").forEach(function (button) {
            if (
                button.id === IDS.headerButton ||
                button.id === IDS.finalButton ||
                button.closest("#" + IDS.panel)
            ) {
                return;
            }

            const text = [
                button.id || "",
                button.textContent || "",
                button.getAttribute("aria-label") || "",
                button.getAttribute("title") || ""
            ].join(" ");

            if (/session/i.test(text)) {
                button.blur && button.blur();
                button.style.setProperty("display", "none", "important");
                button.dataset.novaHiddenBySessionsFinal = "1";
            }
        });

        forceVisibleButton($(IDS.headerButton));
    }

    function ensureButton() {
        removeOldSessionUi();

        let button = $(IDS.finalButton);

        if (button) {
            return button;
        }

        button = document.createElement("button");
        button.id = IDS.finalButton;
        button.type = "button";
        button.textContent = "Sessions";
        button.setAttribute("aria-label", "Open sessions");

        button.style.cssText = [
            "position:fixed",
            "top:10px",
            "right:10px",
            "z-index:2147483647",
            "height:38px",
            "padding:0 12px",
            "border-radius:999px",
            "border:1px solid rgba(255,255,255,.18)",
            "background:rgba(18,18,24,.96)",
            "color:#fff",
            "font-size:13px",
            "font-weight:700",
            "box-shadow:0 8px 24px rgba(0,0,0,.35)"
        ].join(";");

        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            openPanel();
        });

        document.body.appendChild(button);

        return button;
    }

    function bindHeaderButton() {
        const button = $(IDS.headerButton);

        if (!button) {
            return;
        }

        forceVisibleButton(button);

        button.onclick = function (event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            openPanel();
        };
    }

    function ensurePanel() {
        let panel = $(IDS.panel);

        if (panel) {
            return panel;
        }

        panel = document.createElement("div");
        panel.id = IDS.panel;

        panel.style.cssText = [
            "position:fixed",
            "top:56px",
            "right:10px",
            "left:10px",
            "bottom:84px",
            "z-index:2147483647",
            "display:none",
            "flex-direction:column",
            "background:rgba(14,14,20,.98)",
            "color:#fff",
            "border:1px solid rgba(255,255,255,.14)",
            "border-radius:18px",
            "box-shadow:0 16px 60px rgba(0,0,0,.55)",
            "overflow:hidden",
            "font-family:system-ui,-apple-system,Segoe UI,sans-serif"
        ].join(";");

        panel.innerHTML = [
            '<div style="display:flex;align-items:center;gap:8px;padding:12px;border-bottom:1px solid rgba(255,255,255,.1);">',
            '    <strong id="' + IDS.title + '" style="font-size:15px;flex:1;">Sessions</strong>',
            '    <button type="button" data-nova-action="new" style="height:34px;border-radius:10px;border:0;padding:0 10px;font-weight:800;">New</button>',
            '    <button type="button" data-nova-action="close" style="height:34px;border-radius:10px;border:0;padding:0 10px;font-weight:800;">Close</button>',
            "</div>",
            '<div id="' + IDS.status + '" style="min-height:20px;padding:8px 12px;color:rgba(255,255,255,.72);font-size:12px;"></div>',
            '<div id="' + IDS.list + '" style="overflow:auto;-webkit-overflow-scrolling:touch;padding:8px 10px 14px;"></div>'
        ].join("");

        panel.addEventListener("click", async function (event) {
            const target = event.target.closest("[data-nova-action]");

            if (!target || !panel.contains(target)) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            const action = target.getAttribute("data-nova-action");
            const row = target.closest("[data-session-id]");
            const id = row ? row.getAttribute("data-session-id") : "";

            console.log("[SESSION ACTION]", action, id);

            try {
                if (action === "close") {
                    closePanel();
                    return;
                }

                if (action === "new") {
                    await createNewSession();
                    return;
                }

                if (action === "open" && id) {
                    await openSession(id);
                    return;
                }

                if (action === "rename" && id) {
                    await renameSession(id, row);
                    return;
                }

                if (action === "pin" && id) {
                    await pinSession(id, target.getAttribute("data-pinned") !== "true");
                    return;
                }

                if (action === "delete" && id) {
                    await deleteSession(id, row);
                    return;
                }
            } catch (error) {
                setStatus("Error: " + (error && error.message ? error.message : String(error)));
            }
        });

        document.body.appendChild(panel);

        return panel;
    }

    function sessionRow(session, activeId) {
        const id = String(session.id || session.session_id || "");
        let title = String(session.title || "").trim();

if (!title || /^(new|new chat|chat|untitled|\d+)$/i.test(title)) {
    const count =
        session.message_count ??
        (Array.isArray(session.messages) ? session.messages.length : 0);

    title = count > 0
        ? "Session " + String(session.id || session.session_id || "").slice(-8)
        : "Empty session " + String(session.id || session.session_id || "").slice(-8);
}
        const pinned = !!session.pinned;
        const count = session.message_count ?? (
            Array.isArray(session.messages) ? session.messages.length : 0
        );

        const active = id && id === activeId;

        return [
            '<div data-session-id="' + escapeHtml(id) + '"',
            '     style="border:1px solid ' + (active ? "rgba(255,255,255,.45)" : "rgba(255,255,255,.1)") + ';',
            "            border-radius:14px;",
            "            padding:10px;",
            "            margin:0 0 8px;",
            "            background:" + (active ? "rgba(255,255,255,.12)" : "rgba(255,255,255,.05)") + ';">',
            '    <button type="button" data-nova-action="open"',
            '            style="display:block;width:100%;text-align:left;background:transparent;color:#fff;border:0;padding:0;margin:0 0 8px;font-size:14px;font-weight:800;">',
            "        " + (pinned ? "📌 " : "") + escapeHtml(title),
            "    </button>",
            '    <div style="display:flex;align-items:center;gap:6px;">',
            '        <span style="flex:1;color:rgba(255,255,255,.62);font-size:12px;">' + escapeHtml(id.slice(-8)) + " · " + count + " msgs</span>",
            '        <button type="button" data-nova-action="rename" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">Rename</button>',
            '        <button type="button" data-nova-action="pin" data-pinned="' + (pinned ? "true" : "false") + '" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">' + (pinned ? "Unpin" : "Pin") + "</button>",
            '        <button type="button" data-nova-action="delete" style="border:0;border-radius:9px;padding:7px 9px;font-weight:700;">Delete</button>',
            "    </div>",
            "</div>"
        ].join("");
    }

    async function loadSessions() {
        setStatus("Loading sessions…");

        const data = await jsonFetch(API.list + "?ui_final=" + Date.now(), {
            method: "GET"
        });

        const sessions = getSessions(data);
sessions.sort(function (a, b) {
    const ac = a.message_count ?? (Array.isArray(a.messages) ? a.messages.length : 0);
    const bc = b.message_count ?? (Array.isArray(b.messages) ? b.messages.length : 0);

    if (bc !== ac) {
        return bc - ac;
    }

    return String(b.updated_at || b.created_at || "").localeCompare(
        String(a.updated_at || a.created_at || "")
    );
});
        const activeId = data.active_session_id || activeIdFromStorage();

        window.NOVA_SESSION_CORE.sessions = sessions;

        if (activeId) {
            setActiveId(activeId);
        }

        const list = $(IDS.list);

        if (!list) {
            return sessions;
        }

        if (!sessions.length) {
            list.innerHTML = '<div style="padding:18px;color:rgba(255,255,255,.7);">No sessions found.</div>';
        } else {
            list.innerHTML = sessions.map(function (session) {
                return sessionRow(session, activeId);
            }).join("");
        }

        setStatus(sessions.length + " sessions");

        return sessions;
    }

    async function createNewSession() {
        setStatus("Creating session…");

        const data = await jsonFetch(API.newSession + "?ui_final_new=" + Date.now(), {
            method: "POST",
            body: JSON.stringify({
                title: "New Chat"
            })
        });

        const session = data.session || {};
        const id = session.id || session.session_id || data.session_id || data.active_session_id;

        if (id) {
            setActiveId(id);
        }

        closePanel();

        const url = new URL(window.location.href);
        url.searchParams.set("session_id", id || ("mobile_" + Date.now()));
        history.replaceState({}, "", url.toString());

        if (window.chatContainer) {
            window.chatContainer.innerHTML = "";
        }

        window.NOVA_MESSAGES = [];

        setStatus("New session created");

        return id;
    }

function renderSession(payload) {
    const session = payload.session || {};
    const id = payload.session_id || session.id || session.session_id || "";
    const messages = Array.isArray(payload.messages)
        ? payload.messages
        : Array.isArray(session.messages)
            ? session.messages
            : [];

    const normalizedSession = Object.assign({}, session, {
        id: session.id || id,
        session_id: session.session_id || id,
        messages: messages
    });

    const normalizedPayload = {
        session_id: id,
        session: normalizedSession,
        messages: messages
    };

    console.log("[SESSION RENDER PAYLOAD]", {
        id: id,
        messages: messages.length,
        direct: typeof window.NovaMobileRenderSession === "function",
        chatUI: !!window.NovaMobileChatUI
    });

    if (typeof window.NovaMobileRenderSession === "function") {
        window.NovaMobileRenderSession(normalizedSession, id);
        return;
    }

    if (
        window.NovaMobileChatUI &&
        typeof window.NovaMobileChatUI.renderSessionPayload === "function"
    ) {
        window.NovaMobileChatUI.renderSessionPayload(normalizedPayload, "sessions-owner");
        return;
    }

    window.dispatchEvent(new CustomEvent("nova:session-selected", {
        detail: normalizedPayload
    }));
}

    async function openSession(id) {
        if (!id) {
            return;
        }

        setActiveId(id);
        setStatus("Opening session…");

        const data = await jsonFetch(API.detail(id) + "?ui_final_detail=" + Date.now(), {
            method: "GET"
        });

        const payload = normalizeSessionPayload(data, id);

        console.log("[SESSION DETAIL RESPONSE]", data);
        console.log("[SESSION MESSAGE COUNT]", payload.messages.length);

        renderSession(payload);
        closePanel();

        setStatus("Opened " + id.slice(-8));

        const url = new URL(window.location.href);
        url.searchParams.set("session_id", id);
        history.replaceState({}, "", url.toString());
    }

    async function renameSession(id, row) {
        const current = row
            ? (row.querySelector("[data-nova-action='open']")?.textContent || "")
            : "";

        const title = prompt("Rename session", current.replace(/^📌\s*/, "").trim() || "New Chat");

        if (!title) {
            return;
        }

        setStatus("Renaming…");

        await jsonFetch(API.rename, {
            method: "POST",
            body: JSON.stringify({
                session_id: id,
                title: title
            })
        });

        await loadSessions();

        setStatus("Renamed");
    }

    async function pinSession(id, pinned) {
        setStatus(pinned ? "Pinning…" : "Unpinning…");

        await jsonFetch(API.pin, {
            method: "POST",
            body: JSON.stringify({
                session_id: id,
                pinned: !!pinned
            })
        });

        await loadSessions();

        setStatus(pinned ? "Pinned" : "Unpinned");
    }

    async function deleteSession(id, row) {
        const title = row
            ? (row.querySelector("[data-nova-action='open']")?.textContent || "").trim()
            : id;

        if (!confirm("Delete this session?\n\n" + title)) {
            return;
        }

        setStatus("Deleting…");

        await jsonFetch(API.delete, {
            method: "POST",
            body: JSON.stringify({
                session_id: id
            })
        });

        if (activeIdFromStorage() === id) {
            localStorage.removeItem("nova_mobile_active_session_id");
            localStorage.removeItem("nova_active_session_id");
        }

        await loadSessions();

        setStatus("Deleted");
    }

function openPanel() {
    const panel = ensurePanel();

    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");

    panel.style.setProperty("display", "flex", "important");
    panel.style.setProperty("pointer-events", "auto", "important");
    panel.style.removeProperty("visibility");

    window.NOVA_SESSION_CORE.isOpen = true;

    loadSessions().catch(function (error) {
        setStatus("Error: " + (error && error.message ? error.message : String(error)));
    });
}

function closePanel() {
    const panel = document.getElementById(IDS.panel);

    if (!panel) {
        return;
    }

    const active = document.activeElement;

    if (active && panel.contains(active)) {
        active.blur();
    }

    panel.setAttribute("aria-hidden", "true");
    panel.hidden = true;
    panel.style.setProperty("display", "none", "important");
    panel.style.removeProperty("pointer-events");

    window.NOVA_SESSION_CORE.isOpen = false;
}

    function lockFinalGlobal(name, value) {
        try {
            Object.defineProperty(window, name, {
                value: value,
                writable: false,
                configurable: false,
                enumerable: true
            });
        } catch (error) {
            try {
                window[name] = value;
            } catch (_) {}
        }
    }

    function installFinalSessionGlobals() {
        lockFinalGlobal("NovaMobileOpenSessions", openPanel);
        lockFinalGlobal("NovaMobileCloseSessions", closePanel);
        lockFinalGlobal("NovaMobileReloadSessions", loadSessions);
        lockFinalGlobal("NovaMobileOpenSession", openSession);
    }

    let __novaBooted = false;

    function boot() {
        console.trace("[NOVA BOOT TRACE]");

        if (__novaBooted) {
            return;
        }

        __novaBooted = true;

        console.log("[NOVA] boot running once");

        ensureButton();
        ensurePanel();
        bindHeaderButton();

        loadSessions().catch(function (error) {
            setStatus("Error: " + (error && error.message ? error.message : String(error)));
        });

        const bootSessionId =
            sessionIdFromUrl() ||
            activeIdFromStorage();

        if (bootSessionId) {
            setTimeout(function () {
                console.log("[NOVA BOOT RESTORE SESSION]", bootSessionId);

                openSession(bootSessionId).catch(function (error) {
                    console.warn("[NOVA BOOT RESTORE FAILED]", error);
                    setStatus("Restore failed: " + (error && error.message ? error.message : String(error)));
                });
            }, 200);
        }

        setTimeout(bindHeaderButton, 250);
        setTimeout(bindHeaderButton, 800);
    }

    document.addEventListener("click", function (event) {
        const header = event.target.closest("#" + IDS.headerButton);

        if (!header) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openPanel();
    }, true);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    installFinalSessionGlobals();
})();

// NOVA_MOBILE_SESSIONS_REOPEN_GUARD_20260709
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_REOPEN_GUARD_20260709__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_REOPEN_GUARD_20260709__ = true;

    function findSessionsPanel() {
        return (
            document.getElementById("nova-mobile-sessions-panel") ||
            document.getElementById("nova-clean-session-panel-v1") ||
            document.querySelector("[data-nova-sessions-panel]") ||
            document.querySelector("[id*='session'][role='dialog']") ||
            document.querySelector("[id*='sessions'][role='dialog']")
        );
    }

    function forceShowPanel() {
        const panel = findSessionsPanel();

        if (!panel) {
            return false;
        }

        panel.hidden = false;
        panel.removeAttribute("hidden");
        panel.removeAttribute("inert");
        panel.setAttribute("aria-hidden", "false");

        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("pointer-events", "auto", "important");
        panel.style.setProperty("z-index", "2147483647", "important");

        console.log("[SESSIONS REOPEN GUARD] panel forced visible", {
            id: panel.id,
            children: panel.children.length,
            text: panel.textContent.trim().slice(0, 120)
        });

        return true;
    }

    function isSessionsLauncher(target) {
        const el = target && target.closest
            ? target.closest(
                [
                    "#nova-mobile-sessions-toggle",
                    "#nova-mobile-row-sessions",
                    "#nova-session-fallback-button-v1",
                    "[data-nova-action='sessions']",
                    "[data-nova-action='open-sessions']",
                    "[data-action='sessions']",
                    "button"
                ].join(",")
            )
            : null;

        if (!el) {
            return false;
        }

        const text = (el.textContent || "").trim().toLowerCase();
        const id = (el.id || "").toLowerCase();
        const aria = (el.getAttribute("aria-label") || "").toLowerCase();
        const title = (el.getAttribute("title") || "").toLowerCase();

        return (
            id.includes("session") ||
            aria.includes("session") ||
            title.includes("session") ||
            text === "sessions" ||
            text.includes("sessions")
        );
    }

    document.addEventListener(
        "click",
        function (event) {
            if (!isSessionsLauncher(event.target)) {
                return;
            }

            console.log("[SESSIONS REOPEN GUARD] launcher click captured");

            event.preventDefault();
            event.stopImmediatePropagation();

            try {
                if (typeof window.NovaMobileOpenSessions === "function") {
                    window.NovaMobileOpenSessions();
                }
            } catch (err) {
                console.warn("[SESSIONS REOPEN GUARD] NovaMobileOpenSessions failed", err);
            }

            setTimeout(forceShowPanel, 0);
            setTimeout(forceShowPanel, 80);
            setTimeout(forceShowPanel, 250);
        },
        true
    );

    window.NovaMobileForceShowSessionsPanel20260709 = forceShowPanel;

    console.log("[SESSIONS REOPEN GUARD] installed");
})();

// NOVA_MOBILE_SESSIONS_HARD_REOPEN_FALLBACK_20260709
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_HARD_REOPEN_FALLBACK_20260709__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_HARD_REOPEN_FALLBACK_20260709__ = true;

    const PANEL_ID = "nova-mobile-hard-sessions-panel-20260709";

    function getActiveSessionId() {
        return (
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            new URLSearchParams(location.search).get("session_id") ||
            ""
        );
    }

    function setActiveSessionId(id) {
        if (!id) {
            return;
        }

        localStorage.setItem("nova_mobile_active_session_id", id);
        localStorage.setItem("nova_active_session_id", id);
    }

    function removePanel() {
        const old = document.getElementById(PANEL_ID);

        if (old) {
            old.remove();
        }
    }

    function normalizeSessions(data) {
        if (Array.isArray(data)) {
            return data;
        }

        if (Array.isArray(data.sessions)) {
            return data.sessions;
        }

        if (data.sessions && typeof data.sessions === "object") {
            return Object.values(data.sessions);
        }

        return [];
    }

    function titleForSession(session) {
        return (
            session.title ||
            session.name ||
            session.label ||
            session.id ||
            session.session_id ||
            "Untitled session"
        );
    }

    function idForSession(session) {
        return session.id || session.session_id || "";
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, options || {});

        if (!response.ok) {
            throw new Error("HTTP " + response.status + ": " + await response.text());
        }

        return response.json();
    }

    function renderIntoChat(payload) {
        const session = payload.session || {};
        const id = payload.session_id || session.id || session.session_id || "";
        const messages = Array.isArray(payload.messages)
            ? payload.messages
            : Array.isArray(session.messages)
                ? session.messages
                : [];

        const normalizedSession = Object.assign({}, session, {
            id: session.id || id,
            session_id: session.session_id || id,
            messages: messages
        });

        const normalizedPayload = {
            session_id: id,
            session: normalizedSession,
            messages: messages
        };

        if (typeof window.NovaMobileRenderSession === "function") {
            window.NovaMobileRenderSession(normalizedSession, id);
            return true;
        }

        if (
            window.NovaMobileChatUI &&
            typeof window.NovaMobileChatUI.renderSessionPayload === "function"
        ) {
            window.NovaMobileChatUI.renderSessionPayload(normalizedPayload, "hard-reopen-fallback");
            return true;
        }

        window.dispatchEvent(new CustomEvent("nova:session-selected", {
            detail: normalizedPayload
        }));

        return true;
    }

    async function openSession(id) {
        if (!id) {
            return;
        }

        console.log("[HARD SESSIONS FALLBACK] open", id);

        setActiveSessionId(id);

        const data = await fetchJson("/api/sessions/" + encodeURIComponent(id) + "?hard_reopen=" + Date.now(), {
            method: "GET"
        });

        renderIntoChat(data);

        removePanel();
    }

    async function renameSession(id, currentTitle) {
        const nextTitle = prompt("Rename session:", currentTitle || "");

        if (!nextTitle || !nextTitle.trim()) {
            return;
        }

        const cleanTitle = nextTitle.trim();

        console.log("[HARD SESSIONS FALLBACK] rename", id, cleanTitle);

        await fetchJson("/api/sessions/rename", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: id,
                title: cleanTitle
            })
        });

        await openPanel();
    }

    async function deleteSession(id, title) {
        if (!confirm("Delete this session?\n\n" + (title || id))) {
            return;
        }

        console.log("[HARD SESSIONS FALLBACK] delete", id);

        await fetchJson("/api/sessions/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: id
            })
        });

        await openPanel();
    }

    function makeButton(label, className) {
        const button = document.createElement("button");

        button.type = "button";
        button.textContent = label;
        button.className = className || "";
        button.style.cssText = [
            "border:1px solid rgba(255,255,255,.16)",
            "background:rgba(255,255,255,.08)",
            "color:#fff",
            "border-radius:10px",
            "padding:7px 9px",
            "font-size:12px",
            "line-height:1",
            "cursor:pointer"
        ].join(";");

        return button;
    }

    function renderPanel(sessions) {
        removePanel();

        const activeId = getActiveSessionId();

        const panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-label", "Sessions");

        panel.style.cssText = [
            "position:fixed",
            "top:54px",
            "right:10px",
            "left:10px",
            "bottom:84px",
            "z-index:2147483647",
            "background:rgba(15,15,22,.98)",
            "border:1px solid rgba(255,255,255,.14)",
            "border-radius:18px",
            "box-shadow:0 18px 60px rgba(0,0,0,.45)",
            "padding:12px",
            "overflow:auto",
            "-webkit-overflow-scrolling:touch",
            "color:#fff"
        ].join(";");

        const header = document.createElement("div");
        header.style.cssText = [
            "display:flex",
            "align-items:center",
            "justify-content:space-between",
            "gap:10px",
            "margin-bottom:10px",
            "position:sticky",
            "top:0",
            "background:rgba(15,15,22,.98)",
            "padding-bottom:8px",
            "z-index:2"
        ].join(";");

        const title = document.createElement("div");
        title.textContent = "Sessions";
        title.style.cssText = "font-weight:700;font-size:15px;";

        const close = makeButton("Close");
        close.onclick = removePanel;

        header.appendChild(title);
        header.appendChild(close);
        panel.appendChild(header);

        if (!sessions.length) {
            const empty = document.createElement("div");
            empty.textContent = "No sessions found.";
            empty.style.cssText = "opacity:.75;padding:14px;";
            panel.appendChild(empty);
        }

        sessions.forEach(function (session) {
            const id = idForSession(session);
            const titleText = titleForSession(session);
            const messages = Array.isArray(session.messages)
                ? session.messages.length
                : Number(session.message_count || session.messages_count || 0);

            const row = document.createElement("div");
            row.style.cssText = [
                "display:flex",
                "gap:8px",
                "align-items:center",
                "justify-content:space-between",
                "padding:10px",
                "margin:7px 0",
                "border:1px solid rgba(255,255,255,.10)",
                "border-radius:14px",
                id === activeId ? "background:rgba(128,90,213,.24)" : "background:rgba(255,255,255,.05)"
            ].join(";");

            const open = document.createElement("button");
            open.type = "button";
            open.style.cssText = [
                "flex:1",
                "text-align:left",
                "border:0",
                "background:transparent",
                "color:#fff",
                "padding:4px",
                "cursor:pointer",
                "min-width:0"
            ].join(";");

            open.innerHTML = [
                "<div style='font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>" +
                    titleText.replace(/[&<>"']/g, function (ch) {
                        return {
                            "&": "&amp;",
                            "<": "&lt;",
                            ">": "&gt;",
                            '"': "&quot;",
                            "'": "&#39;"
                        }[ch];
                    }) +
                "</div>",
                "<div style='font-size:11px;opacity:.7;margin-top:3px;'>" +
                    String(messages || 0) +
                    " messages · " +
                    String(id).slice(-6) +
                "</div>"
            ].join("");

            open.onclick = function () {
                openSession(id).catch(function (err) {
                    console.error("[HARD SESSIONS FALLBACK] open failed", err);
                    alert("Open session failed: " + err.message);
                });
            };

            const actions = document.createElement("div");
            actions.style.cssText = "display:flex;gap:6px;flex-shrink:0;";

            const rename = makeButton("Rename");
            rename.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();

                renameSession(id, titleText).catch(function (err) {
                    console.error("[HARD SESSIONS FALLBACK] rename failed", err);
                    alert("Rename failed: " + err.message);
                });
            };

            const del = makeButton("Delete");
            del.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();

                deleteSession(id, titleText).catch(function (err) {
                    console.error("[HARD SESSIONS FALLBACK] delete failed", err);
                    alert("Delete failed: " + err.message);
                });
            };

            actions.appendChild(rename);
            actions.appendChild(del);

            row.appendChild(open);
            row.appendChild(actions);
            panel.appendChild(row);
        });

        document.body.appendChild(panel);

        console.log("[HARD SESSIONS FALLBACK] panel rendered", {
            sessions: sessions.length,
            activeId: activeId
        });
    }

    async function openPanel() {
        console.log("[HARD SESSIONS FALLBACK] open panel");

        const data = await fetchJson("/api/sessions?hard_reopen=" + Date.now(), {
            method: "GET"
        });

        renderPanel(normalizeSessions(data));
    }

    function isSessionsLauncher(target) {
        const el = target && target.closest
            ? target.closest("button,a,[role='button'],[data-nova-action]")
            : null;

        if (!el) {
            return false;
        }

        const haystack = [
            el.id || "",
            el.className || "",
            el.textContent || "",
            el.getAttribute("aria-label") || "",
            el.getAttribute("title") || "",
            el.getAttribute("data-nova-action") || ""
        ].join(" ").toLowerCase();

        return haystack.includes("session");
    }

    document.addEventListener(
        "click",
        function (event) {
            if (!isSessionsLauncher(event.target)) {
                return;
            }

            console.log("[HARD SESSIONS FALLBACK] launcher captured");

            event.preventDefault();
            event.stopImmediatePropagation();

            openPanel().catch(function (err) {
                console.error("[HARD SESSIONS FALLBACK] panel failed", err);
                alert("Sessions failed: " + err.message);
            });
        },
        true
    );

    window.NovaMobileHardOpenSessions20260709 = openPanel;

    console.log("[HARD SESSIONS FALLBACK] installed");
})();