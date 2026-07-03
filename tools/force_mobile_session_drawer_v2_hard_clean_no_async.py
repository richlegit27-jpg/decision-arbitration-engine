from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = r"""
(function () {
    "use strict";

    var VERSION = "20260703-hard-clean-no-async";
    window.__NOVA_SESSION_DRAWER_V2_HARD_CLEAN_NO_ASYNC_20260703__ = VERSION;

    function log() {
        try {
            console.log.apply(console, ["[Nova Session Drawer Hard Clean]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function style() {
        var el = document.getElementById("nova-session-drawer-v2-hard-clean-style");
        if (!el) {
            el = document.createElement("style");
            el.id = "nova-session-drawer-v2-hard-clean-style";
            document.head.appendChild(el);
        }

        el.textContent = [
            "#nova-session-drawer-v2-button{position:fixed!important;left:12px!important;top:10px!important;right:auto!important;bottom:auto!important;z-index:2147483647!important;display:block!important;visibility:visible!important;opacity:1!important;pointer-events:auto!important;background:rgba(139,92,246,.96)!important;color:#fff!important;border:1px solid rgba(255,255,255,.2)!important;border-radius:999px!important;padding:9px 12px!important;font-size:13px!important;font-weight:700!important;transform:none!important;margin:0!important}",
            "#nova-session-drawer-v2-panel{position:fixed!important;left:10px!important;right:10px!important;top:56px!important;bottom:auto!important;max-height:calc(100vh - 70px)!important;overflow-y:auto!important;z-index:2147483646!important;background:rgba(14,14,24,.98)!important;color:#fff!important;border:1px solid rgba(255,255,255,.14)!important;border-radius:16px!important;box-shadow:0 18px 50px rgba(0,0,0,.45)!important;transform:none!important;margin:0!important}",
            "#nova-session-drawer-v2-panel[data-open='true']{display:block!important;visibility:visible!important;opacity:1!important;pointer-events:auto!important}",
            "#nova-session-drawer-v2-panel[data-open='false']{display:none!important;visibility:hidden!important;opacity:0!important;pointer-events:none!important}",
            "#nova-session-drawer-v2-panel *{visibility:visible!important;opacity:1!important}",
            ".nova-session-drawer-v2-empty{padding:12px!important;font-size:13px!important;color:rgba(255,255,255,.78)!important}",
            ".nova-session-drawer-v2-row{display:block!important;width:calc(100% - 16px)!important;margin:8px!important;padding:10px!important;border-radius:12px!important;border:1px solid rgba(255,255,255,.10)!important;background:rgba(255,255,255,.07)!important;color:#fff!important;text-align:left!important}",
            ".nova-session-drawer-v2-title{font-size:14px!important;font-weight:700!important;margin-bottom:4px!important}",
            ".nova-session-drawer-v2-meta{font-size:11px!important;color:rgba(255,255,255,.58)!important;word-break:break-all!important}",
            ".nova-session-drawer-v2-detail{padding:8px!important}",
            ".nova-session-drawer-v2-message{display:block!important;white-space:pre-wrap!important;word-break:break-word!important;border-radius:10px!important;padding:10px!important;margin:8px 0!important;font-size:13px!important;line-height:1.35!important}",
            ".nova-session-drawer-v2-message[data-role='user']{background:rgba(139,92,246,.22)!important}",
            ".nova-session-drawer-v2-message[data-role='assistant']{background:rgba(255,255,255,.10)!important}",
            ".nova-session-drawer-v2-message[data-role='system']{background:rgba(255,255,255,.06)!important}"
        ].join("\n");
    }

    function own() {
        style();

        var button = document.getElementById("nova-session-drawer-v2-button");
        var panel = document.getElementById("nova-session-drawer-v2-panel");

        if (button) {
            button.setAttribute("data-nova-session-drawer-v2", "true");
            button.removeAttribute("hidden");
            button.removeAttribute("aria-hidden");
        }

        if (panel) {
            panel.setAttribute("data-nova-session-drawer-v2", "true");
            panel.removeAttribute("hidden");
            panel.removeAttribute("aria-hidden");

            ["nova-mobile-tools-menu-fixed", "nova-mobile-menu-panel-fixed", "nova-mobile-tools-menu-open", "nova-mobile-menu-panel-open"].forEach(function (name) {
                try { panel.classList.remove(name); } catch (_) {}
            });

            if (panel.getAttribute("data-open") === "true") {
                panel.style.setProperty("display", "block", "important");
                panel.style.setProperty("visibility", "visible", "important");
                panel.style.setProperty("opacity", "1", "important");
                panel.style.setProperty("pointer-events", "auto", "important");
            }
        }
    }

    function fetchJson(url) {
        return fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        }).then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
            return r.json();
        });
    }

    function sessionId(item) {
        return item && String(item.session_id || item.id || item.key || "").trim();
    }

    function sessionsFrom(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.sessions)) return payload.sessions;
        if (payload && payload.data && Array.isArray(payload.data.sessions)) return payload.data.sessions;
        return [];
    }

    function messagesFrom(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.messages)) return payload.messages;
        if (payload && payload.session && Array.isArray(payload.session.messages)) return payload.session.messages;
        if (payload && payload.data && Array.isArray(payload.data.messages)) return payload.data.messages;
        return [];
    }

    function roleOf(m) {
        var r = String((m && (m.role || m.sender || m.type)) || "assistant").toLowerCase();
        if (r.indexOf("user") >= 0) return "user";
        if (r.indexOf("system") >= 0) return "system";
        return "assistant";
    }

    function textOf(m) {
        if (!m) return "";
        if (typeof m === "string") return m;
        return String(m.text || m.content || m.message || m.response || "");
    }

    function hideOldRightButtons() {
        try {
            Array.from(document.querySelectorAll("button,a")).forEach(function (el) {
                if (!el) return;
                if (el.id === "nova-session-drawer-v2-button") return;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) return;

                var text = String(el.textContent || "").trim().toLowerCase();
                var id = String(el.id || "").toLowerCase();
                var klass = String(el.className || "").toLowerCase();

                var looks = text === "sessions" || text === "session" || text.indexOf("sessions") >= 0 || id.indexOf("session") >= 0 || klass.indexOf("session") >= 0;
                if (!looks) return;

                var r = el.getBoundingClientRect();
                if (r.top >= 0 && r.top < 220 && r.right > window.innerWidth - 240) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }

    function ui() {
        style();

        var button = document.getElementById("nova-session-drawer-v2-button");
        var panel = document.getElementById("nova-session-drawer-v2-panel");

        if (!button) {
            button = document.createElement("button");
            button.id = "nova-session-drawer-v2-button";
            button.type = "button";
            button.textContent = "Sessions";
            document.body.appendChild(button);
        }

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "nova-session-drawer-v2-panel";
            panel.setAttribute("data-open", "false");
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Loading sessions...</div>";
            document.body.appendChild(panel);
        }

        button.onclick = function (event) {
            try {
                event.preventDefault();
                event.stopPropagation();
            } catch (_) {}

            var isOpen = panel.getAttribute("data-open") === "true";
            panel.setAttribute("data-open", isOpen ? "false" : "true");

            if (!isOpen) {
                loadSessions();
            }

            setTimeout(own, 0);
            setTimeout(own, 100);
        };

        own();
        hideOldRightButtons();

        return { button: button, panel: panel };
    }

    function renderMessages(id, title, messages) {
        var parts = ui();
        var panel = parts.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "";

        var wrap = document.createElement("div");
        wrap.className = "nova-session-drawer-v2-detail";

        var back = document.createElement("button");
        back.type = "button";
        back.className = "nova-session-drawer-v2-row";
        back.textContent = "← Back to sessions";
        back.onclick = function (event) {
            try {
                event.preventDefault();
                event.stopPropagation();
            } catch (_) {}
            loadSessions();
        };
        wrap.appendChild(back);

        var header = document.createElement("div");
        header.className = "nova-session-drawer-v2-empty";
        header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
        wrap.appendChild(header);

        if (!messages.length) {
            var empty = document.createElement("div");
            empty.className = "nova-session-drawer-v2-message";
            empty.setAttribute("data-role", "system");
            empty.textContent = "No messages in this session.";
            wrap.appendChild(empty);
        }

        messages.forEach(function (m) {
            var row = document.createElement("div");
            row.className = "nova-session-drawer-v2-message";
            row.setAttribute("data-role", roleOf(m));
            row.textContent = textOf(m) || "[empty message]";
            wrap.appendChild(row);
        });

        panel.appendChild(wrap);
        own();

        try { panel.scrollTop = 0; } catch (_) {}
    }

    function openSession(item) {
        var id = sessionId(item);
        if (!id) return;

        var title = item.title || "New Chat";
        var parts = ui();
        var panel = parts.panel;

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        try {
            var url = new URL(window.location.href);
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "session-open-" + Date.now());
            history.replaceState(null, "", url.toString());
        } catch (_) {}

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Opening session...</div>";
        own();

        fetchJson("/api/sessions/" + encodeURIComponent(id)).then(function (detail) {
            var session = detail.session || detail;
            renderMessages(id, session.title || title, messagesFrom(detail));
            log("opened", id);
        }).catch(function (err) {
            panel.setAttribute("data-open", "true");
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session open failed. See console.</div>";
            own();
            log("open failed", err);
        });
    }

    function loadSessions() {
        var parts = ui();
        var button = parts.button;
        var panel = parts.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Loading sessions...</div>";
        own();

        fetchJson("/api/sessions").then(function (payload) {
            var sessions = sessionsFrom(payload);
            button.textContent = "Sessions (" + sessions.length + ")";
            panel.innerHTML = "";

            var head = document.createElement("div");
            head.className = "nova-session-drawer-v2-empty";
            head.textContent = "Sessions: " + sessions.length;
            panel.appendChild(head);

            sessions.forEach(function (item) {
                var id = sessionId(item);
                var title = item.title || "New Chat";
                var count = item.message_count;

                var row = document.createElement("button");
                row.type = "button";
                row.className = "nova-session-drawer-v2-row";

                var titleEl = document.createElement("div");
                titleEl.className = "nova-session-drawer-v2-title";
                titleEl.textContent = title;

                var meta = document.createElement("div");
                meta.className = "nova-session-drawer-v2-meta";
                meta.textContent = (count === undefined || count === null ? "?" : count) + " messages · " + id;

                row.appendChild(titleEl);
                row.appendChild(meta);

                row.onclick = function (event) {
                    try {
                        event.preventDefault();
                        event.stopPropagation();
                    } catch (_) {}
                    openSession(item);
                };

                panel.appendChild(row);
            });

            if (!sessions.length) {
                panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>No sessions returned.</div>";
            }

            own();
            log("sessions", sessions.length);
        }).catch(function (err) {
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session load failed. See console.</div>";
            own();
            log("session load failed", err);
        });
    }

    function boot() {
        ui();

        setInterval(function () {
            own();
            hideOldRightButtons();
        }, 500);

        loadSessions();

        setTimeout(function () {
            var parts = ui();
            var params = new URLSearchParams(window.location.search);
            var id = params.get("session_id");

            if (id) {
                fetchJson("/api/sessions/" + encodeURIComponent(id)).then(function (detail) {
                    var session = detail.session || detail;
                    renderMessages(id, session.title || id, messagesFrom(detail));
                }).catch(function (err) {
                    log("url session failed", err);
                    parts.panel.setAttribute("data-open", "false");
                    own();
                });
            } else {
                parts.panel.setAttribute("data-open", "false");
                own();
            }
        }, 250);

        log("ready", VERSION);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
"""

js_path.write_text(js.strip() + "\n", encoding="utf-8")

app = app_path.read_text(encoding="utf-8")

# Replace every possible drawer script cache version in app.py.
app2 = re.sub(
    r"nova-mobile-session-drawer-v2\.js\?v=[^\"']+",
    "nova-mobile-session-drawer-v2.js?v=20260703-hard-clean-no-async",
    app,
)

if "20260703-hard-clean-no-async" not in app2:
    raise SystemExit("failed to install hard clean cache version in app.py")

app_path.write_text(app2, encoding="utf-8")

print("wrote hard clean no-async drawer")
print("drawer refs in app.py:", app2.count("nova-mobile-session-drawer-v2.js"))
print("hard clean cache refs:", app2.count("20260703-hard-clean-no-async"))
