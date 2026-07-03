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


    // NOVA_SESSION_DRAWER_V2_REAL_SESSION_FILTER_20260703
    function showDebugSessions() {
        try {
            var params = new URLSearchParams(window.location.search);
            if (
                params.get("debug_sessions") === "1" ||
                params.get("show_debug_sessions") === "1" ||
                params.get("dev_sessions") === "1"
            ) {
                return true;
            }

            return localStorage.getItem("nova_show_debug_sessions") === "1";
        } catch (_) {
            return false;
        }
    }

    function isDebugSession(item) {
        var id = sessionId(item).toLowerCase();
        var title = String((item && item.title) || "").toLowerCase();
        var combined = id + " " + title;

        return (
            id.indexOf("regression_") === 0 ||
            id.indexOf("test_") === 0 ||
            id.indexOf("smoke_") === 0 ||
            id.indexOf("duplicate_") === 0 ||
            id.indexOf("debug_") === 0 ||
            id.indexOf("api_check_") === 0 ||
            combined.indexOf("regression") >= 0 ||
            combined.indexOf("smoke") >= 0 ||
            combined.indexOf("duplicate_api_check") >= 0 ||
            combined.indexOf("api check") >= 0
        );
    }

    function shouldShowSessionInDrawer(item) {
        if (!item) return false;

        var id = sessionId(item);
        if (!id) return false;

        if (isDebugSession(item) && !showDebugSessions()) {
            return false;
        }

        return true;
    }

    function sessionKind(item) {
        var id = sessionId(item).toLowerCase();

        if (id.indexOf("mobile_") === 0) return "Mobile";
        if (id.indexOf("session_") === 0) return "Legacy";
        if (id.indexOf("regression_") === 0) return "Regression";
        if (id.indexOf("test_") === 0) return "Test";
        if (id.indexOf("smoke_") === 0) return "Smoke";

        return "Session";
    }

    function sessionSortRank(item) {
        var kind = sessionKind(item);

        if (kind === "Mobile") return 0;
        if (kind === "Legacy") return 1;
        if (kind === "Session") return 2;
        return 9;
    }

    function compareDrawerSessions(a, b) {
        var ar = sessionSortRank(a);
        var br = sessionSortRank(b);

        if (ar !== br) return ar - br;

        var at = String((a && (a.updated_at || a.created_at || a.last_updated)) || "");
        var bt = String((b && (b.updated_at || b.created_at || b.last_updated)) || "");

        return bt.localeCompare(at);
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


    // NOVA_SESSION_DRAWER_V2_MAIN_CHAT_RESTORE_20260703
    function installMainChatRestoreStyle() {
        try {
            var style = document.getElementById("nova-session-drawer-v2-main-chat-restore-style");
            if (!style) {
                style = document.createElement("style");
                style.id = "nova-session-drawer-v2-main-chat-restore-style";
                document.head.appendChild(style);
            }

            style.textContent = [
                ".nova-session-main-restore-header{margin:58px 10px 10px 10px!important;padding:10px 12px!important;border-radius:12px!important;background:rgba(139,92,246,.16)!important;color:#fff!important;border:1px solid rgba(139,92,246,.28)!important;font-size:13px!important}",
                ".nova-session-main-restore-message{margin:8px 10px!important;padding:10px 12px!important;border-radius:12px!important;color:#fff!important;white-space:pre-wrap!important;word-break:break-word!important;font-size:14px!important;line-height:1.38!important}",
                ".nova-session-main-restore-message[data-role='user']{background:rgba(139,92,246,.26)!important}",
                ".nova-session-main-restore-message[data-role='assistant']{background:rgba(255,255,255,.09)!important}",
                ".nova-session-main-restore-message[data-role='system']{background:rgba(255,255,255,.06)!important;color:rgba(255,255,255,.75)!important}"
            ].join("\\n");
        } catch (_) {}
    }

    function findMainChatContainer() {
        var selectors = [
            "#nova-mobile-chat-messages",
            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#chat-messages",
            "#messages",
            "[data-nova-mobile-messages]",
            ".nova-mobile-chat-messages",
            ".nova-mobile-messages",
            ".chat-messages",
            ".messages"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            try {
                var nodes = Array.from(document.querySelectorAll(selectors[i]));
                for (var j = 0; j < nodes.length; j += 1) {
                    var el = nodes[j];
                    if (!el) continue;
                    if (el.id === "nova-session-drawer-v2-panel") continue;
                    if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                    if (el.tagName && ["INPUT", "TEXTAREA", "BUTTON"].indexOf(el.tagName.toUpperCase()) >= 0) continue;

                    var rect = el.getBoundingClientRect();
                    if (rect.width > 80 && rect.height >= 0) {
                        return el;
                    }
                }
            } catch (_) {}
        }

        var fallback = document.getElementById("nova-session-main-restore-fallback");
        if (!fallback) {
            fallback = document.createElement("div");
            fallback.id = "nova-session-main-restore-fallback";
            fallback.setAttribute("data-nova-mobile-messages", "true");

            var drawer = document.getElementById("nova-session-drawer-v2-panel");
            if (drawer && drawer.parentNode) {
                drawer.parentNode.insertBefore(fallback, drawer);
            } else {
                document.body.appendChild(fallback);
            }
        }

        return fallback;
    }

    function renderSessionToMainChat(id, title, messages) {
        try {
            installMainChatRestoreStyle();

            var container = findMainChatContainer();
            if (!container) return false;

            container.innerHTML = "";
            container.setAttribute("data-nova-restored-session-id", id);

            var header = document.createElement("div");
            header.className = "nova-session-main-restore-header";
            header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
            container.appendChild(header);

            if (!messages.length) {
                var empty = document.createElement("div");
                empty.className = "nova-session-main-restore-message";
                empty.setAttribute("data-role", "system");
                empty.textContent = "No messages in this session.";
                container.appendChild(empty);
            }

            messages.forEach(function (message) {
                var row = document.createElement("div");
                row.className = "nova-session-main-restore-message";
                row.setAttribute("data-role", roleOf(message));
                row.textContent = textOf(message) || "[empty message]";
                container.appendChild(row);
            });

            try {
                container.scrollTop = container.scrollHeight;
            } catch (_) {}

            try {
                window.scrollTo({ top: 0, behavior: "smooth" });
            } catch (_) {
                window.scrollTo(0, 0);
            }

            return true;
        } catch (err) {
            log("main chat restore failed", err);
            return false;
        }
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
            var restoredMessages = messagesFrom(detail);
            renderMessages(id, session.title || title, restoredMessages);
            renderSessionToMainChat(id, session.title || title, restoredMessages);

            closeDrawerAfterRestore();
            setTimeout(closeDrawerAfterRestore, 50);
            setTimeout(closeDrawerAfterRestore, 250);
            setTimeout(closeDrawerAfterRestore, 750);
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
            var allSessions = sessionsFrom(payload);
            var sessions = allSessions.filter(shouldShowSessionInDrawer).sort(compareDrawerSessions);
            var hiddenDebugCount = allSessions.length - sessions.length;
            button.textContent = "Sessions (" + sessions.length + ")";
            panel.innerHTML = "";

            var head = document.createElement("div");
            head.className = "nova-session-drawer-v2-empty";
            head.textContent = "Sessions: " + sessions.length + (hiddenDebugCount ? " · hidden tests: " + hiddenDebugCount : "");
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
                meta.textContent = sessionKind(item) + " · " + (count === undefined || count === null ? "?" : count) + " messages · " + id;

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


    // NOVA_SESSION_DRAWER_V2_FORCE_CLOSE_AFTER_RESTORE_20260703
    function closeDrawerAfterRestore() {
        try {
            var panel = document.getElementById("nova-session-drawer-v2-panel");
            if (!panel) return;

            panel.setAttribute("data-open", "false");
            panel.style.setProperty("display", "none", "important");
            panel.style.setProperty("visibility", "hidden", "important");
            panel.style.setProperty("opacity", "0", "important");
            panel.style.setProperty("pointer-events", "none", "important");
        } catch (_) {}
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
