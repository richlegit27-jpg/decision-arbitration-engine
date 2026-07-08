(function () {
    "use strict";

    var MARK = "NOVA_MOBILE_SESSION_DRAWER_SINGLE_OWNER_20260705";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_SINGLE_OWNER_20260705__ = true;

    var isOpen = false;
    var loading = false;

    function log() {
        try {
            console.log.apply(console, ["[" + MARK + "]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function ensureStyle() {
        if (document.getElementById("nova-mobile-session-drawer-single-owner-style")) {
            return;
        }

        var style = document.createElement("style");
        style.id = "nova-mobile-session-drawer-single-owner-style";
        style.textContent = [
            "#nova-session-drawer-v2-panel{position:fixed!important;top:0!important;right:0!important;bottom:0!important;width:min(88vw,360px)!important;background:#11111a!important;color:#fff!important;z-index:999999!important;box-shadow:-12px 0 30px rgba(0,0,0,.55)!important;display:none!important;flex-direction:column!important;border-left:1px solid rgba(168,85,247,.35)!important;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important}",
            "#nova-session-drawer-v2-panel.nova-open{display:flex!important}",
            "#nova-session-drawer-v2-header{display:flex!important;align-items:center!important;justify-content:space-between!important;padding:14px!important;border-bottom:1px solid rgba(255,255,255,.10)!important}",
            "#nova-session-drawer-v2-title{font-size:15px!important;font-weight:700!important}",
            "#nova-session-drawer-v2-close{border:0!important;border-radius:10px!important;background:rgba(255,255,255,.10)!important;color:#fff!important;padding:8px 10px!important}",
            "#nova-session-drawer-v2-list{overflow:auto!important;padding:10px!important;display:flex!important;flex-direction:column!important;gap:8px!important}",
            ".nova-session-drawer-row{border:1px solid rgba(255,255,255,.10)!important;border-radius:12px!important;background:rgba(255,255,255,.06)!important;color:#fff!important;padding:10px!important;text-align:left!important;display:block!important;width:100%!important}",
            ".nova-session-drawer-row-title{font-size:13px!important;font-weight:700!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}",
            ".nova-session-drawer-row-meta{font-size:11px!important;opacity:.70!important;margin-top:3px!important}"
        ].join("\n");

        document.head.appendChild(style);
    }

    function getPanel() {
        ensureStyle();

        var panel = document.getElementById("nova-session-drawer-v2-panel");

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "nova-session-drawer-v2-panel";
            panel.setAttribute("role", "dialog");
            panel.setAttribute("aria-label", "Sessions");

            panel.innerHTML = [
                '<div id="nova-session-drawer-v2-header">',
                '  <div id="nova-session-drawer-v2-title">Sessions</div>',
                '  <button id="nova-session-drawer-v2-close" type="button">Close</button>',
                '</div>',
                '<div id="nova-session-drawer-v2-list">Loading sessions...</div>'
            ].join("");

            document.body.appendChild(panel);
        }

var close = document.getElementById("nova-session-drawer-v2-close");

if (close) {
    close.onclick = closeDrawer;
}

        return panel;
    }

    function normalizeSessions(data) {
        if (Array.isArray(data)) return data;

        if (data && Array.isArray(data.sessions)) return data.sessions;
        if (data && Array.isArray(data.items)) return data.items;
        if (data && data.data && Array.isArray(data.data.sessions)) return data.data.sessions;
        if (data && data.session && typeof data.session === "object") return [data.session];

        return [];
    }

    function sessionIdOf(session) {
        return String(
            session.id ||
            session.session_id ||
            session.sid ||
            ""
        );
    }

    function sessionTitleOf(session) {
        return String(
            session.title ||
            session.name ||
            session.label ||
            sessionIdOf(session).slice(-8) ||
            "Untitled session"
        );
    }

    function sessionMetaOf(session) {
        var parts = [];

        if (typeof session.message_count !== "undefined") {
            parts.push(session.message_count + " messages");
        }

        if (session.updated_at) {
            parts.push(String(session.updated_at).replace("T", " ").slice(0, 19));
        }

        var id = sessionIdOf(session);
        if (id) {
            parts.push(id.slice(-8));
        }

        return parts.join(" · ");
    }

    async function fetchSessions() {
        var response = await fetch("/api/sessions", {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        var raw = await response.text();

        if (!response.ok) {
            throw new Error("HTTP " + response.status + ": " + raw.slice(0, 500));
        }

        try {
            return JSON.parse(raw);
        } catch (_) {
            return {};
        }
    }

    function renderSessions(sessions) {
        var list = document.getElementById("nova-session-drawer-v2-list");
        if (!list) return;

        list.innerHTML = "";

        if (!sessions.length) {
            list.textContent = "No sessions found.";
            return;
        }

        sessions.forEach(function (session) {
            var sid = sessionIdOf(session);
            if (!sid) return;

            var row = document.createElement("button");
            row.type = "button";
            row.className = "nova-session-drawer-row";
            row.setAttribute("data-nova-session-id", sid);

            row.innerHTML = [
                '<div class="nova-session-drawer-row-title"></div>',
                '<div class="nova-session-drawer-row-meta"></div>'
            ].join("");

            row.querySelector(".nova-session-drawer-row-title").textContent = sessionTitleOf(session);
            row.querySelector(".nova-session-drawer-row-meta").textContent = sessionMetaOf(session);

row.addEventListener("click", function (event) {
    try {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    } catch (_) {}

    try {
        localStorage.setItem("nova_mobile_active_session_id", sid);
        localStorage.setItem("nova_active_session_id", sid);
    } catch (_) {}

    if (
        window.NovaMobileRestoreSession &&
        typeof window.NovaMobileRestoreSession.restore === "function"
    ) {
        console.log("[SESSION CLICK] restoring", sid);

window.NovaMobileRestoreSession.restore(sid);
        return;
    }

location.href = "/mobile?session_id=" + encodeURIComponent(sid) + "&v=session-open-" + Date.now();

            }, true);

            list.appendChild(row);
        });
    }

    async function refreshSessions() {
        if (loading) return;

        loading = true;

        var list = document.getElementById("nova-session-drawer-v2-list");
        if (list) {
            list.textContent = "Loading sessions...";
        }

        try {
            var data = await fetchSessions();
            var sessions = normalizeSessions(data);
            renderSessions(sessions);
            log("sessions loaded", sessions.length);
        } catch (error) {
            console.error("[" + MARK + "] sessions failed", error);
            if (list) {
                list.textContent = "Sessions failed: " + (error && error.message ? error.message : String(error));
            }
        } finally {
            loading = false;
        }
    }

function openDrawer(event) {
    var panel = getPanel();

    panel.classList.add("nova-open");
    panel.style.setProperty("display", "flex", "important");

    refreshSessions();
}

function closeDrawer(event) {
    var panel = getPanel();

    if (!panel) return;

    panel.classList.remove("nova-open");
    panel.style.removeProperty("display");
    panel.style.setProperty("display", "none", "important");

    console.log("[SESSION] drawer closed");
}

function toggleDrawer(event) {
    var panel = document.getElementById("nova-session-drawer-v2-panel");

    var currentlyOpen = !!(
        panel &&
        panel.classList.contains("nova-open") &&
        getComputedStyle(panel).display !== "none"
    );

    if (currentlyOpen) {
        closeDrawer(event);
    } else {
        openDrawer(event);
    }
}

    function isSessionButton(el) {
        if (!el) return false;

        if (el.closest && el.closest("#nova-session-drawer-v2-panel")) {
            return false;
        }

        var text = String(el.innerText || el.textContent || "").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var klass = String(el.className || "").toLowerCase();
        var aria = String(el.getAttribute("aria-label") || "").toLowerCase();
        var title = String(el.getAttribute("title") || "").toLowerCase();

        var haystack = [text, id, klass, aria, title].join(" ");

        if (haystack.indexOf("new chat") >= 0) return false;
        if (haystack.indexOf("rename") >= 0) return false;
        if (haystack.indexOf("delete") >= 0) return false;
        if (haystack.indexOf("pin") >= 0) return false;
        if (haystack.indexOf("send") >= 0) return false;
        if (haystack.indexOf("attach") >= 0) return false;

        return (
            text === "sessions" ||
            text === "session" ||
            id === "nova-mobile-sessions-toggle" ||
            haystack.indexOf("sessions-toggle") >= 0 ||
            haystack.indexOf("session drawer") >= 0
        );
    }

    function bindButtons() {
        var count = 0;

        Array.from(document.querySelectorAll("button, a, [role='button']")).forEach(function (el) {
            if (!isSessionButton(el)) return;

            count += 1;

            if (el.dataset.novaSessionDrawerSingleOwner === "1") return;

            el.dataset.novaSessionDrawerSingleOwner = "1";
            el.addEventListener("click", toggleDrawer);

            try {
                el.disabled = false;
                el.removeAttribute("disabled");
                el.style.pointerEvents = "auto";
            } catch (_) {}
        });

        return count;
    }

document.addEventListener("click", function (event) {
    return;
}, true);

    function boot() {
        getPanel();
        var count = bindButtons();
        log("ready", { bound: count });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }

    setTimeout(boot, 250);
    setTimeout(boot, 900);
    setTimeout(boot, 1800);

    var observer = new MutationObserver(boot);
    observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
    });

    window.NovaMobileSessionDrawerOwnerV1 = {
        version: MARK,
        open: openDrawer,
        close: closeDrawer,
        toggle: toggleDrawer,
        refresh: refreshSessions,
        bindButtons: bindButtons
    };
})();
