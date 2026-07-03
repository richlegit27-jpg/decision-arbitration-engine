from pathlib import Path
import re

drawer_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
newchat_path = Path("static/js/mobile/nova-mobile-new-chat-backend-create-v1.js")

DRAWER_VERSION = "20260703-stable-no-jitter-1"
NEWCHAT_VERSION = "backend-create-v2-no-auto-run-20260703b"

drawer_js = r'''
(function () {
    "use strict";

    var VERSION = "20260703-stable-no-jitter-1";
    window.__NOVA_SESSION_DRAWER_V2_STABLE_NO_JITTER_20260703__ = VERSION;

    function log() {
        try {
            console.log.apply(console, ["[Nova Session Drawer Stable]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function installStyle() {
        var style = document.getElementById("nova-session-drawer-v2-stable-style");
        if (!style) {
            style = document.createElement("style");
            style.id = "nova-session-drawer-v2-stable-style";
            document.head.appendChild(style);
        }

        style.textContent = [
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

    function ownDrawer() {
        installStyle();

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

            [
                "nova-mobile-tools-menu-fixed",
                "nova-mobile-menu-panel-fixed",
                "nova-mobile-tools-menu-open",
                "nova-mobile-menu-panel-open"
            ].forEach(function (klass) {
                try {
                    panel.classList.remove(klass);
                } catch (_) {}
            });
        }
    }

    function fetchJson(url) {
        return fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("HTTP " + response.status + " for " + url);
            }
            return response.json();
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

    function roleOf(message) {
        var role = String((message && (message.role || message.sender || message.type)) || "assistant").toLowerCase();
        if (role.indexOf("user") >= 0) return "user";
        if (role.indexOf("system") >= 0) return "system";
        return "assistant";
    }

    function textOf(message) {
        if (!message) return "";
        if (typeof message === "string") return message;
        return String(
            message.text ||
            message.content ||
            message.message ||
            message.response ||
            message.assistant_message ||
            ""
        );
    }

    function hideOldRightSessionButtons() {
        try {
            Array.from(document.querySelectorAll("button,a")).forEach(function (el) {
                if (!el) return;
                if (el.id === "nova-session-drawer-v2-button") return;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) return;

                var text = String(el.textContent || "").trim().toLowerCase();
                var id = String(el.id || "").toLowerCase();
                var klass = String(el.className || "").toLowerCase();

                var looksSession =
                    text === "sessions" ||
                    text === "session" ||
                    text.indexOf("sessions") >= 0 ||
                    id.indexOf("session") >= 0 ||
                    klass.indexOf("session") >= 0;

                if (!looksSession) return;

                var r = el.getBoundingClientRect();
                if (r.top >= 0 && r.top < 220 && r.right > window.innerWidth - 240) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }

    function getUi() {
        installStyle();

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
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Tap Sessions to load chats.</div>";
            document.body.appendChild(panel);
        }

        button.onclick = function (event) {
            try {
                event.preventDefault();
                event.stopPropagation();
            } catch (_) {}

            var isOpen = panel.getAttribute("data-open") === "true";

            if (isOpen) {
                panel.setAttribute("data-open", "false");
                ownDrawer();
                return;
            }

            panel.setAttribute("data-open", "true");
            loadSessions();
            ownDrawer();
        };

        ownDrawer();

        return { button: button, panel: panel };
    }

    function renderMessages(id, title, messages) {
        var ui = getUi();
        var panel = ui.panel;

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

        messages.forEach(function (message) {
            var row = document.createElement("div");
            row.className = "nova-session-drawer-v2-message";
            row.setAttribute("data-role", roleOf(message));
            row.textContent = textOf(message) || "[empty message]";
            wrap.appendChild(row);
        });

        panel.appendChild(wrap);
        ownDrawer();

        try {
            panel.scrollTop = 0;
        } catch (_) {}
    }

    function openSession(item) {
        var id = sessionId(item);
        if (!id) return;

        var title = item.title || "New Chat";
        var ui = getUi();
        var panel = ui.panel;

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
        ownDrawer();

        fetchJson("/api/sessions/" + encodeURIComponent(id)).then(function (detail) {
            var session = detail.session || detail;
            renderMessages(id, session.title || title, messagesFrom(detail));
            log("opened", id);
        }).catch(function (err) {
            panel.setAttribute("data-open", "true");
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session open failed. See console.</div>";
            ownDrawer();
            log("open failed", err);
        });
    }

    function loadSessions() {
        var ui = getUi();
        var button = ui.button;
        var panel = ui.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Loading sessions...</div>";
        ownDrawer();

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

            ownDrawer();
            log("sessions", sessions.length);
        }).catch(function (err) {
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session load failed. See console.</div>";
            ownDrawer();
            log("session load failed", err);
        });
    }

    function boot() {
        getUi();

        setTimeout(hideOldRightSessionButtons, 100);
        setTimeout(hideOldRightSessionButtons, 700);

        var params = new URLSearchParams(window.location.search);
        var id = params.get("session_id");

        if (id) {
            fetchJson("/api/sessions/" + encodeURIComponent(id)).then(function (detail) {
                var session = detail.session || detail;
                renderMessages(id, session.title || id, messagesFrom(detail));
            }).catch(function (err) {
                log("url session failed", err);
            });
        }

        log("ready", VERSION);
    }

    window.NovaSessionDrawerV2Stable = {
        version: VERSION,
        loadSessions: loadSessions,
        openSession: openSession
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
'''

newchat_js = r'''
(function () {
    "use strict";

    var VERSION = "backend-create-v2-no-auto-run-20260703b";
    window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_NO_AUTO_RUN_20260703__ = VERSION;

    var inFlight = false;
    var lastRunAt = 0;

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile New Chat Backend Create V2]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function extractSessionId(payload) {
        if (!payload) return "";

        return String(
            payload.session_id ||
            payload.id ||
            payload.active_session_id ||
            (payload.session && (payload.session.session_id || payload.session.id)) ||
            (payload.data && (payload.data.session_id || payload.data.id || payload.data.active_session_id)) ||
            ""
        ).trim();
    }

    function createBackendSession() {
        return fetch("/api/sessions/new", {
            method: "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                source: "mobile_new_chat_backend_create_v2",
                title: "New Chat"
            })
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("Session create HTTP " + response.status);
            }
            return response.json();
        }).then(function (payload) {
            var id = extractSessionId(payload);

            if (!id) {
                throw new Error("Session create returned no usable id: " + JSON.stringify(payload).slice(0, 600));
            }

            return { id: id, payload: payload };
        });
    }

    function clearVisibleChat() {
        try {
            [
                "#messages",
                "#chat-messages",
                "#nova-chat-messages",
                "#nova-mobile-messages",
                ".messages",
                ".chat-messages",
                ".nova-mobile-messages"
            ].forEach(function (selector) {
                document.querySelectorAll(selector).forEach(function (el) {
                    if (el && el.id !== "nova-session-drawer-v2-panel") {
                        el.innerHTML = "";
                    }
                });
            });
        } catch (_) {}
    }

    function goToSession(id) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        clearVisibleChat();

        try {
            var url = new URL(window.location.href);
            url.pathname = "/mobile";
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "new-chat-backend-create-v2-" + Date.now());
            window.location.href = url.toString();
        } catch (_) {
            window.location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=new-chat-backend-create-v2-" + Date.now();
        }
    }

    function runNewChatFlow(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        var now = Date.now();

        if (inFlight || now - lastRunAt < 1500) {
            log("ignored duplicate new-chat request");
            return;
        }

        inFlight = true;
        lastRunAt = now;

        createBackendSession().then(function (result) {
            log("created", result.id);
            goToSession(result.id);
        }).catch(function (err) {
            log("failed once", err);
        }).finally(function () {
            setTimeout(function () {
                inFlight = false;
            }, 1000);
        });
    }

    function looksLikeNewChatButton(el) {
        if (!el) return false;

        var text = String(el.textContent || "").trim().toLowerCase();
        var aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        var title = String(el.getAttribute("title") || "").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var klass = String(el.className || "").toLowerCase();

        var haystack = [text, aria, title, id, klass].join(" ");

        if (haystack.indexOf("session") >= 0 && haystack.indexOf("new") < 0) {
            return false;
        }

        return (
            haystack.indexOf("new chat") >= 0 ||
            haystack.indexOf("new-chat") >= 0 ||
            haystack.indexOf("start new") >= 0 ||
            haystack === "+" ||
            text === "+"
        );
    }

    function installClickCapture() {
        if (window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_CLICK_CAPTURE_INSTALLED_20260703__) {
            return;
        }

        window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V2_CLICK_CAPTURE_INSTALLED_20260703__ = true;

        document.addEventListener("click", function (event) {
            try {
                var target = event.target;
                var button = target && target.closest && target.closest("button, a, [role='button']");
                if (!button) return;

                if (button.closest && button.closest("#nova-session-drawer-v2-panel")) {
                    return;
                }

                if (!looksLikeNewChatButton(button)) {
                    return;
                }

                runNewChatFlow(event);
            } catch (err) {
                log("click capture failed", err);
            }
        }, true);
    }

    installClickCapture();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installClickCapture);
    }

    window.NovaMobileNewChatBackendCreateV2 = {
        version: VERSION,
        run: runNewChatFlow
    };

    log("ready", VERSION);
})();
'''

drawer_path.write_text(drawer_js.strip() + "\n", encoding="utf-8")
newchat_path.write_text(newchat_js.strip() + "\n", encoding="utf-8")

script_ref_patterns = [
    (
        re.compile(r"nova-mobile-session-drawer-v2\.js\?v=[^\"'<>\\s]+"),
        "nova-mobile-session-drawer-v2.js?v=" + DRAWER_VERSION
    ),
    (
        re.compile(r"nova-mobile-new-chat-backend-create-v1\.js\?v=[^\"'<>\\s]+"),
        "nova-mobile-new-chat-backend-create-v1.js?v=" + NEWCHAT_VERSION
    ),
]

updated = []

for path in Path(".").rglob("*"):
    if ".git" in path.parts:
        continue
    if path.suffix.lower() not in (".py", ".html", ".js"):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        continue

    new_text = text
    for pattern, replacement in script_ref_patterns:
        new_text = pattern.sub(replacement, new_text)

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        updated.append(str(path))

print("wrote stable drawer:", drawer_path)
print("wrote no-auto new chat:", newchat_path)
print("updated script refs:")
for item in updated:
    print(" -", item)
