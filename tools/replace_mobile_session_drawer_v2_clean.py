from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
app_path = Path("app.py")

js = r'''
(function () {
    "use strict";

    const VERSION = "20260703-clean-replace-1";

    if (window.__NOVA_SESSION_DRAWER_V2_CLEAN_REPLACE_20260703__) {
        return;
    }

    window.__NOVA_SESSION_DRAWER_V2_CLEAN_REPLACE_20260703__ = VERSION;

    function log() {
        try {
            console.log.apply(console, ["[Nova Session Drawer V2 Clean]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function installStyles() {
        let style = document.getElementById("nova-session-drawer-v2-style");
        if (!style) {
            style = document.createElement("style");
            style.id = "nova-session-drawer-v2-style";
            document.head.appendChild(style);
        }

        style.textContent = [
            "#nova-session-drawer-v2-button {",
            "    position: fixed !important;",
            "    left: 12px !important;",
            "    right: auto !important;",
            "    top: 10px !important;",
            "    bottom: auto !important;",
            "    z-index: 2147483647 !important;",
            "    display: block !important;",
            "    visibility: visible !important;",
            "    opacity: 1 !important;",
            "    pointer-events: auto !important;",
            "    transform: none !important;",
            "    margin: 0 !important;",
            "    padding: 9px 12px !important;",
            "    border-radius: 999px !important;",
            "    border: 1px solid rgba(255,255,255,0.18) !important;",
            "    background: rgba(139,92,246,0.96) !important;",
            "    color: #fff !important;",
            "    font-size: 13px !important;",
            "    font-weight: 700 !important;",
            "}",
            "",
            "#nova-session-drawer-v2-panel {",
            "    position: fixed !important;",
            "    left: 10px !important;",
            "    right: 10px !important;",
            "    top: 56px !important;",
            "    bottom: auto !important;",
            "    max-height: calc(100vh - 70px) !important;",
            "    overflow-y: auto !important;",
            "    z-index: 2147483646 !important;",
            "    transform: none !important;",
            "    margin: 0 !important;",
            "    border-radius: 16px !important;",
            "    border: 1px solid rgba(255,255,255,0.14) !important;",
            "    background: rgba(14,14,24,0.98) !important;",
            "    color: #fff !important;",
            "    box-shadow: 0 18px 50px rgba(0,0,0,0.45) !important;",
            "}",
            "",
            "#nova-session-drawer-v2-panel[data-open='true'] {",
            "    display: block !important;",
            "    visibility: visible !important;",
            "    opacity: 1 !important;",
            "    pointer-events: auto !important;",
            "}",
            "",
            "#nova-session-drawer-v2-panel[data-open='false'] {",
            "    display: none !important;",
            "    visibility: hidden !important;",
            "    opacity: 0 !important;",
            "    pointer-events: none !important;",
            "}",
            "",
            "#nova-session-drawer-v2-panel * {",
            "    visibility: visible !important;",
            "    opacity: 1 !important;",
            "}",
            "",
            ".nova-session-drawer-v2-empty {",
            "    padding: 12px !important;",
            "    font-size: 13px !important;",
            "    color: rgba(255,255,255,0.78) !important;",
            "}",
            "",
            ".nova-session-drawer-v2-row {",
            "    display: block !important;",
            "    width: calc(100% - 16px) !important;",
            "    margin: 8px !important;",
            "    padding: 10px !important;",
            "    border-radius: 12px !important;",
            "    border: 1px solid rgba(255,255,255,0.10) !important;",
            "    background: rgba(255,255,255,0.07) !important;",
            "    color: #fff !important;",
            "    text-align: left !important;",
            "}",
            "",
            ".nova-session-drawer-v2-title {",
            "    font-size: 14px !important;",
            "    font-weight: 700 !important;",
            "    margin-bottom: 4px !important;",
            "}",
            "",
            ".nova-session-drawer-v2-meta {",
            "    font-size: 11px !important;",
            "    color: rgba(255,255,255,0.58) !important;",
            "    word-break: break-all !important;",
            "}",
            "",
            ".nova-session-drawer-v2-detail {",
            "    padding: 8px !important;",
            "}",
            "",
            ".nova-session-drawer-v2-message {",
            "    display: block !important;",
            "    white-space: pre-wrap !important;",
            "    word-break: break-word !important;",
            "    border-radius: 10px !important;",
            "    padding: 10px !important;",
            "    margin: 8px 0 !important;",
            "    font-size: 13px !important;",
            "    line-height: 1.35 !important;",
            "}",
            "",
            ".nova-session-drawer-v2-message[data-role='user'] {",
            "    background: rgba(139, 92, 246, 0.22) !important;",
            "}",
            "",
            ".nova-session-drawer-v2-message[data-role='assistant'] {",
            "    background: rgba(255, 255, 255, 0.10) !important;",
            "}",
            "",
            ".nova-session-drawer-v2-message[data-role='system'] {",
            "    background: rgba(255, 255, 255, 0.06) !important;",
            "}"
        ].join("\n");
    }

    function ownDrawerVisibility() {
        try {
            const button = document.getElementById("nova-session-drawer-v2-button");
            const panel = document.getElementById("nova-session-drawer-v2-panel");

            if (button) {
                button.setAttribute("data-nova-session-drawer-v2", "true");
                button.removeAttribute("hidden");
                button.removeAttribute("aria-hidden");
                button.style.setProperty("display", "block", "important");
                button.style.setProperty("visibility", "visible", "important");
                button.style.setProperty("opacity", "1", "important");
                button.style.setProperty("top", "10px", "important");
                button.style.setProperty("left", "12px", "important");
                button.style.setProperty("position", "fixed", "important");
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

                panel.style.setProperty("position", "fixed", "important");
                panel.style.setProperty("left", "10px", "important");
                panel.style.setProperty("right", "10px", "important");
                panel.style.setProperty("top", "56px", "important");

                if (panel.getAttribute("data-open") === "true") {
                    panel.style.setProperty("display", "block", "important");
                    panel.style.setProperty("visibility", "visible", "important");
                    panel.style.setProperty("opacity", "1", "important");
                    panel.style.setProperty("pointer-events", "auto", "important");
                }
            }
        } catch (_) {}
    }

    function hideOldSessionButtons() {
        try {
            Array.from(document.querySelectorAll("button, a")).forEach(function (el) {
                if (!el) return;
                if (el.id === "nova-session-drawer-v2-button") return;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) return;

                const text = String(el.textContent || "").trim().toLowerCase();
                const id = String(el.id || "").toLowerCase();
                const klass = String(el.className || "").toLowerCase();

                const looksSession =
                    text === "sessions" ||
                    text === "session" ||
                    text.includes("sessions") ||
                    id.includes("session") ||
                    klass.includes("session");

                if (!looksSession) return;

                const r = el.getBoundingClientRect();
                const nearTopRight = r.top >= 0 && r.top < 220 && r.right > window.innerWidth - 240;

                if (nearTopRight) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, Object.assign({
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        }, options || {}));

        if (!response.ok) {
            throw new Error("HTTP " + response.status + " for " + url);
        }

        return await response.json();
    }

    function sessionId(item) {
        return item && String(item.session_id || item.id || item.key || "").trim();
    }

    function normalizeSessions(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.sessions)) return payload.sessions;
        if (payload && payload.data && Array.isArray(payload.data.sessions)) return payload.data.sessions;
        return [];
    }

    function normalizeMessages(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.messages)) return payload.messages;
        if (payload && payload.session && Array.isArray(payload.session.messages)) return payload.session.messages;
        if (payload && payload.data && Array.isArray(payload.data.messages)) return payload.data.messages;
        return [];
    }

    function messageRole(message) {
        const role = String((message && (message.role || message.sender || message.type)) || "assistant").toLowerCase();
        if (role.includes("user")) return "user";
        if (role.includes("system")) return "system";
        return "assistant";
    }

    function messageText(message) {
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

    function ensureUi() {
        installStyles();

        let button = document.getElementById("nova-session-drawer-v2-button");
        let panel = document.getElementById("nova-session-drawer-v2-panel");

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
            panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">Loading sessions...</div>";
            document.body.appendChild(panel);
        }

        button.onclick = function (event) {
            try {
                event.preventDefault();
                event.stopPropagation();
            } catch (_) {}

            const open = panel.getAttribute("data-open") === "true";
            panel.setAttribute("data-open", open ? "false" : "true");

            if (!open) {
                loadSessions();
            }

            setTimeout(ownDrawerVisibility, 0);
            setTimeout(ownDrawerVisibility, 100);
        };

        ownDrawerVisibility();
        hideOldSessionButtons();

        return { button: button, panel: panel };
    }

    function renderMessages(id, title, messages) {
        const ui = ensureUi();
        const panel = ui.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "";

        const wrap = document.createElement("div");
        wrap.className = "nova-session-drawer-v2-detail";

        const back = document.createElement("button");
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

        const header = document.createElement("div");
        header.className = "nova-session-drawer-v2-empty";
        header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
        wrap.appendChild(header);

        if (!messages.length) {
            const empty = document.createElement("div");
            empty.className = "nova-session-drawer-v2-message";
            empty.setAttribute("data-role", "system");
            empty.textContent = "No messages in this session.";
            wrap.appendChild(empty);
        }

        messages.forEach(function (message) {
            const row = document.createElement("div");
            row.className = "nova-session-drawer-v2-message";
            row.setAttribute("data-role", messageRole(message));
            row.textContent = messageText(message) || "[empty message]";
            wrap.appendChild(row);
        });

        panel.appendChild(wrap);
        ownDrawerVisibility();

        try {
            panel.scrollTop = 0;
        } catch (_) {}
    }

    async function openSession(item) {
        const id = sessionId(item);
        if (!id) return;

        const title = item.title || "New Chat";
        const ui = ensureUi();
        const panel = ui.panel;

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "session-open-" + Date.now());
            history.replaceState(null, "", url.toString());
        } catch (_) {}

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">Opening session...</div>";
        ownDrawerVisibility();

        try {
            const detail = await fetchJson("/api/sessions/" + encodeURIComponent(id));
            const session = detail.session || detail;
            const messages = normalizeMessages(detail);
            renderMessages(id, session.title || title, messages);
            log("opened", id, messages.length);
        } catch (err) {
            panel.setAttribute("data-open", "true");
            panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">Session open failed. See console.</div>";
            ownDrawerVisibility();
            log("open failed", err);
        }
    }

    async function loadSessions() {
        const ui = ensureUi();
        const panel = ui.panel;

        panel.setAttribute("data-open", "true");
        panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">Loading sessions...</div>";
        ownDrawerVisibility();

        try {
            const payload = await fetchJson("/api/sessions");
            const sessions = normalizeSessions(payload);

            ui.button.textContent = "Sessions (" + sessions.length + ")";
            panel.innerHTML = "";

            const head = document.createElement("div");
            head.className = "nova-session-drawer-v2-empty";
            head.textContent = "Sessions: " + sessions.length;
            panel.appendChild(head);

            sessions.forEach(function (item) {
                const id = sessionId(item);
                const title = item.title || "New Chat";
                const count = item.message_count;

                const row = document.createElement("button");
                row.type = "button";
                row.className = "nova-session-drawer-v2-row";

                const titleEl = document.createElement("div");
                titleEl.className = "nova-session-drawer-v2-title";
                titleEl.textContent = title;

                const meta = document.createElement("div");
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
                panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">No sessions returned.</div>";
            }

            ownDrawerVisibility();
            log("sessions", sessions.length);
        } catch (err) {
            panel.innerHTML = "<div class=\"nova-session-drawer-v2-empty\">Session load failed. See console.</div>";
            ownDrawerVisibility();
            log("session load failed", err);
        }
    }

    async function boot() {
        ensureUi();

        setInterval(function () {
            installStyles();
            ownDrawerVisibility();
            hideOldSessionButtons();
        }, 500);

        try {
            await loadSessions();
            const ui = ensureUi();
            ui.panel.setAttribute("data-open", "false");
            ownDrawerVisibility();
        } catch (_) {}

        const params = new URLSearchParams(window.location.search);
        const id = params.get("session_id");

        if (id) {
            try {
                const detail = await fetchJson("/api/sessions/" + encodeURIComponent(id));
                const session = detail.session || detail;
                renderMessages(id, session.title || id, normalizeMessages(detail));
            } catch (err) {
                log("url session failed", err);
            }
        }

        log("ready", VERSION);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
'''

js_path.write_text(js.strip() + "\n", encoding="utf-8")

app = app_path.read_text(encoding="utf-8")
app2 = re.sub(
    r"nova-mobile-session-drawer-v2\.js\?v=[^\"']+",
    "nova-mobile-session-drawer-v2.js?v=20260703-clean-replace-1",
    app,
)

if app2 == app:
    raise SystemExit("drawer script cache string not found in app.py")

app_path.write_text(app2, encoding="utf-8")

print("replaced drawer js cleanly")
