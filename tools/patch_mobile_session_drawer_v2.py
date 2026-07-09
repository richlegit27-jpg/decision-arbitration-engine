from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")
js_path.parent.mkdir(parents=True, exist_ok=True)

js = r"""
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_V2_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_V2_20260703__ = true;

    function log() {
        try { console.log("[Nova Session Drawer V2]", ...arguments); } catch (_) {}
    }

    function cssEscapeText(value) {
        if (value === null || value === undefined) return "";
        if (typeof value === "string") return value;
        if (typeof value === "number" || typeof value === "boolean") return String(value);

        if (typeof value === "object") {
            if (typeof value.text === "string") return value.text;
            if (typeof value.content === "string") return value.content;
            if (typeof value.message === "string") return value.message;
            try { return JSON.stringify(value, null, 2); } catch (_) { return String(value); }
        }

        return String(value);
    }

    function sessionId(item) {
        return item && (item.id || item.session_id || item.sessionId || "");
    }

    function normalizeSessions(payload) {
        if (Array.isArray(payload)) return payload;
        if (payload && Array.isArray(payload.sessions)) return payload.sessions;

        if (payload && payload.sessions && typeof payload.sessions === "object") {
            return Object.keys(payload.sessions).map(function (key) {
                const item = payload.sessions[key] || {};
                item.id = item.id || item.session_id || key;
                item.session_id = item.session_id || item.id || key;
                return item;
            });
        }

        return [];
    }

    function normalizeMessages(payload) {
        if (payload && Array.isArray(payload.messages)) return payload.messages;
        if (payload && payload.session && Array.isArray(payload.session.messages)) return payload.session.messages;
        if (payload && payload.data && Array.isArray(payload.data.messages)) return payload.data.messages;
        if (Array.isArray(payload)) return payload;
        return [];
    }

    function messageRole(message) {
        const raw = String((message && (message.role || message.sender || message.type || message.author)) || "assistant").toLowerCase();
        if (raw.includes("user") || raw.includes("human")) return "user";
        if (raw.includes("system")) return "system";
        return "assistant";
    }

    function messageText(message) {
        if (!message) return "";
        if (typeof message === "string") return message;

        return cssEscapeText(
            message.text ||
            message.content ||
            message.message ||
            message.assistant_message ||
            message.user_message ||
            message.response ||
            message.answer ||
            message
        );
    }

    async function fetchJson(url) {
        const res = await fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });

        const text = await res.text();

        if (!res.ok) {
            throw new Error(url + " -> " + res.status + " " + text.slice(0, 250));
        }

        return JSON.parse(text);
    }

    function installStyles() {
        if (document.getElementById("nova-session-drawer-v2-style")) return;

        const style = document.createElement("style");
        style.id = "nova-session-drawer-v2-style";
        style.textContent = `
            #nova-mobile-sessions-panel,
            section#nova-mobile-sessions-panel,
            .nova-mobile-tools-menu-fixed.nova-mobile-menu-panel-fixed {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            #nova-session-drawer-v2-button {
                position: fixed !important;
                left: 12px !important;
                bottom: 92px !important;
                z-index: 2147483647 !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                background: #7c3aed !important;
                color: #fff !important;
                border: 1px solid rgba(255,255,255,0.25) !important;
                border-radius: 999px !important;
                padding: 12px 16px !important;
                font-size: 14px !important;
                font-weight: 900 !important;
                box-shadow: 0 12px 36px rgba(0,0,0,0.55) !important;
            }

            #nova-session-drawer-v2-panel {
                position: fixed !important;
                left: 8px !important;
                right: 8px !important;
                top: 58px !important;
                bottom: 92px !important;
                z-index: 2147483646 !important;
                display: none !important;
                background: rgba(10,10,16,0.98) !important;
                color: #fff !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                border-radius: 18px !important;
                padding: 12px !important;
                overflow-y: auto !important;
                -webkit-overflow-scrolling: touch !important;
                box-shadow: 0 20px 70px rgba(0,0,0,0.65) !important;
            }

            #nova-session-drawer-v2-panel[data-open="true"] {
                display: block !important;
            }

            .nova-session-drawer-v2-row {
                display: block !important;
                width: 100% !important;
                text-align: left !important;
                background: rgba(255,255,255,0.08) !important;
                color: #fff !important;
                border: 1px solid rgba(255,255,255,0.11) !important;
                border-radius: 13px !important;
                padding: 11px !important;
                margin: 8px 0 !important;
                cursor: pointer !important;
            }

            .nova-session-drawer-v2-title {
                font-size: 14px !important;
                font-weight: 900 !important;
                line-height: 1.25 !important;
                margin-bottom: 4px !important;
            }

            .nova-session-drawer-v2-meta {
                font-size: 11px !important;
                opacity: 0.70 !important;
                overflow-wrap: anywhere !important;
            }

            #nova-session-drawer-v2-messages {
                margin: 70px 10px 120px 10px !important;
                padding: 8px 0 !important;
            }

            .nova-session-drawer-v2-message {
                white-space: pre-wrap !important;
                border-radius: 14px !important;
                padding: 11px 12px !important;
                margin: 9px 0 !important;
                line-height: 1.36 !important;
                font-size: 14px !important;
                color: #fff !important;
                border: 1px solid rgba(255,255,255,0.10) !important;
            }

            .nova-session-drawer-v2-message[data-role="user"] {
                background: rgba(124,58,237,0.35) !important;
                margin-left: 22px !important;
            }

            .nova-session-drawer-v2-message[data-role="assistant"] {
                background: rgba(255,255,255,0.08) !important;
                margin-right: 22px !important;
            }

            .nova-session-drawer-v2-message[data-role="system"] {
                background: rgba(255,255,255,0.04) !important;
                font-size: 12px !important;
                opacity: 0.78 !important;
            }

            .nova-session-drawer-v2-empty {
                padding: 12px !important;
                opacity: 0.75 !important;
                font-size: 13px !important;
            }
        `;
        document.head.appendChild(style);
    }

    function hideOldSessionButtons() {
        try {
            const nodes = Array.from(document.querySelectorAll("button, a, [role='button']"));

            nodes.forEach(function (el) {
                if (!el || el.id === "nova-session-drawer-v2-button") return;
                if (el.closest("#nova-session-drawer-v2-panel")) return;

                const text = String(el.textContent || el.getAttribute("aria-label") || el.title || "").trim().toLowerCase();
                const id = String(el.id || "").toLowerCase();
                const klass = String(el.className || "").toLowerCase();

                const looksLikeOldSession =
                    text === "sessions" ||
                    text === "session" ||
                    text.includes("sessions") ||
                    id.includes("session") ||
                    klass.includes("session");

                const nearTopRight = (function () {
                    try {
                        const r = el.getBoundingClientRect();
                        return r.top < 120 && r.right > window.innerWidth - 180;
                    } catch (_) {
                        return false;
                    }
                })();

                if (looksLikeOldSession && nearTopRight) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                }
            });
        } catch (_) {}
    }

    function ensureUi() {
        installStyles();
        hideOldSessionButtons();

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
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Loading sessions...</div>";
            document.body.appendChild(panel);
        }

        button.onclick = function () {
            const open = panel.getAttribute("data-open") === "true";
            panel.setAttribute("data-open", open ? "false" : "true");
            if (!open) loadSessions();
        };

        return { button, panel };
    }

    function messageContainer() {
        let container = document.getElementById("nova-session-drawer-v2-messages");
        if (!container) {
            container = document.createElement("div");
            container.id = "nova-session-drawer-v2-messages";
            document.body.appendChild(container);
        }
        return container;
    }

    function renderMessages(id, title, messages) {
        const container = messageContainer();
        container.innerHTML = "";

        const header = document.createElement("div");
        header.className = "nova-session-drawer-v2-message";
        header.setAttribute("data-role", "system");
        header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
        container.appendChild(header);

        if (!messages.length) {
            const empty = document.createElement("div");
            empty.className = "nova-session-drawer-v2-message";
            empty.setAttribute("data-role", "system");
            empty.textContent = "No messages in this session.";
            container.appendChild(empty);
        }

        messages.forEach(function (message) {
            const row = document.createElement("div");
            row.className = "nova-session-drawer-v2-message";
            row.setAttribute("data-role", messageRole(message));
            row.textContent = messageText(message) || "[empty message]";
            container.appendChild(row);
        });

        try {
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (_) {
            window.scrollTo(0, 0);
        }
    }

    async function openSession(item) {
        const id = sessionId(item);
        if (!id) return;

        const title = item.title || "New Chat";

        try {
            localStorage.setItem("nova_mobile_active_session_id", id);
            localStorage.setItem("nova_active_session_id", id);
        } catch (_) {}

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", id);
            url.searchParams.set("v", "session-drawer-v2-" + Date.now());
            history.replaceState(null, "", url.toString());
        } catch (_) {}

        const panel = document.getElementById("nova-session-drawer-v2-panel");
        if (panel) panel.setAttribute("data-open", "false");

        renderMessages(id, title, []);

        try {
            const detail = await fetchJson("/api/sessions/" + encodeURIComponent(id));
            const messages = normalizeMessages(detail);
            renderMessages(id, title, messages);
            log("opened", id, messages.length);
        } catch (err) {
            log("open failed", err);
        }
    }

    async function loadSessions() {
        const ui = ensureUi();
        const panel = ui.panel;

        panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Loading sessions...</div>";

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
                row.onclick = function () { openSession(item); };

                panel.appendChild(row);
            });

            if (!sessions.length) {
                panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>No sessions returned.</div>";
            }

            log("sessions", sessions.length);
        } catch (err) {
            panel.innerHTML = "<div class='nova-session-drawer-v2-empty'>Session load failed. See console.</div>";
            log("session load failed", err);
        }
    }

    async function boot() {
        ensureUi();
        setInterval(hideOldSessionButtons, 1000);

        await loadSessions();

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

        log("ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
"""

js_path.write_text(js, encoding="utf-8")

app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

marker = "# --- NOVA_MOBILE_SESSION_DRAWER_V2_INJECT_20260703 ---"

if marker not in text:
    block = r'''

# --- NOVA_MOBILE_SESSION_DRAWER_V2_INJECT_20260703 ---
try:
    from flask import request as _nmsdv2_request

    @app.after_request
    def _nmsdv2_inject_after_request_20260703(response):
        try:
            if _nmsdv2_request.path not in ("/mobile", "/mobile/"):
                return response

            content_type = str(response.headers.get("Content-Type") or "")
            if "text/html" not in content_type:
                return response

            html = response.get_data(as_text=True)

            if "nova-mobile-session-drawer-v2.js" in html:
                return response

            script = '<script src="/static/js/mobile/nova-mobile-session-drawer-v2.js?v=20260703-drawer-v2"></script>'

            lower = html.lower()
            idx = lower.rfind("</body>")

            if idx >= 0:
                html = html[:idx] + "\n" + script + "\n" + html[idx:]
            else:
                html = html + "\n" + script + "\n"

            response.set_data(html)
            response.headers["Content-Length"] = str(len(response.get_data()))
        except Exception as exc:
            try:
                print("[NOVA_MOBILE_SESSION_DRAWER_V2_INJECT_20260703] failed:", exc)
            except Exception:
                pass

        return response

    print("[NOVA_MOBILE_SESSION_DRAWER_V2_INJECT_20260703] installed")
except Exception as _nmsdv2_error_20260703:
    try:
        print("[NOVA_MOBILE_SESSION_DRAWER_V2_INJECT_20260703] failed:", _nmsdv2_error_20260703)
    except Exception:
        pass
'''
    anchor = 'if __name__ == "__main__":'
    idx = text.rfind(anchor)
    if idx >= 0:
        text = text[:idx] + block + "\n" + text[idx:]
    else:
        text = text.rstrip() + block + "\n"

    app_path.write_text(text, encoding="utf-8")
    print("patched app.py injector")
else:
    print("app.py injector already installed")

print("wrote", js_path)
