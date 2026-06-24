
(function () {
    "use strict";

    const MARKER = "[NOVA_MOBILE_VISIBLE_SESSIONS_FALLBACK_20260623]";
    const PANEL_ID = "nova-mobile-visible-sessions-fallback-panel";

    function log() {
        try {
            console.log.apply(console, [MARKER].concat([].slice.call(arguments)));
        } catch (e) {}
    }

    function textOf(value) {
        return String(value == null ? "" : value);
    }

    function sessionIdOf(item) {
        if (!item || typeof item !== "object") return "";
        return textOf(item.id || item.session_id || "").trim();
    }

    function messageTextOf(msg) {
        if (!msg || typeof msg !== "object") return "";
        return textOf(msg.content || msg.text || msg.message || msg.body || "").trim();
    }

    function messageRoleOf(msg) {
        if (!msg || typeof msg !== "object") return "assistant";
        const role = textOf(msg.role || msg.type || "").toLowerCase().trim();
        return role === "user" ? "user" : "assistant";
    }

    function ensurePanel() {
        let panel = document.getElementById(PANEL_ID);

        if (panel) return panel;

        panel = document.createElement("div");
        panel.id = PANEL_ID;
        panel.innerHTML = `
            <div class="nova-visible-sessions-head">
                <strong>Sessions</strong>
                <button type="button" data-nova-visible-sessions-refresh>Refresh</button>
                <button type="button" data-nova-visible-sessions-close>?</button>
            </div>
            <div class="nova-visible-sessions-body" data-nova-visible-sessions-body>
                Loading sessions...
            </div>
        `;

        document.body.appendChild(panel);

        const style = document.createElement("style");
        style.id = "nova-mobile-visible-sessions-fallback-style";
        style.textContent = `
            #${PANEL_ID} {
                position: fixed;
                left: 12px;
                right: 12px;
                top: 76px;
                bottom: 86px;
                z-index: 2147483000;
                display: none;
                overflow: hidden;
                border: 1px solid rgba(168, 85, 247, 0.45);
                border-radius: 18px;
                background: rgba(12, 10, 18, 0.98);
                color: #f7f0ff;
                box-shadow: 0 18px 60px rgba(0, 0, 0, 0.55);
            }

            #${PANEL_ID}.open {
                display: flex;
                flex-direction: column;
            }

            #${PANEL_ID} .nova-visible-sessions-head {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 12px;
                border-bottom: 1px solid rgba(168, 85, 247, 0.25);
            }

            #${PANEL_ID} .nova-visible-sessions-head strong {
                flex: 1;
                font-size: 15px;
            }

            #${PANEL_ID} button {
                border: 1px solid rgba(168, 85, 247, 0.38);
                border-radius: 12px;
                background: rgba(168, 85, 247, 0.18);
                color: #f7f0ff;
                padding: 8px 10px;
                font-weight: 700;
            }

            #${PANEL_ID} .nova-visible-sessions-body {
                overflow: auto;
                padding: 10px;
                -webkit-overflow-scrolling: touch;
            }

            #${PANEL_ID} .nova-visible-session-card {
                width: 100%;
                display: block;
                text-align: left;
                margin: 0 0 10px;
                padding: 12px;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.055);
            }

            #${PANEL_ID} .nova-visible-session-title {
                font-size: 14px;
                font-weight: 800;
                margin-bottom: 5px;
            }

            #${PANEL_ID} .nova-visible-session-meta {
                font-size: 12px;
                opacity: 0.78;
                word-break: break-all;
            }
        `;

        if (!document.getElementById(style.id)) {
            document.head.appendChild(style);
        }

        panel.querySelector("[data-nova-visible-sessions-close]").addEventListener("click", () => {
            panel.classList.remove("open");
        });

        panel.querySelector("[data-nova-visible-sessions-refresh]").addEventListener("click", () => {
            loadSessions();
        });

        return panel;
    }

    function findChatContainer() {
        return document.querySelector("#messages")
            || document.querySelector("#chat")
            || document.querySelector(".messages")
            || document.querySelector(".chat-messages")
            || document.querySelector("[data-chat-messages]")
            || document.querySelector("main")
            || document.body;
    }

    function renderMessages(session) {
        const messages = Array.isArray(session && session.messages) ? session.messages : [];
        const chat = findChatContainer();

        if (!chat) return;

        let fallback = document.getElementById("nova-mobile-visible-session-render");

        if (!fallback) {
            fallback = document.createElement("div");
            fallback.id = "nova-mobile-visible-session-render";
            chat.appendChild(fallback);
        }

        fallback.innerHTML = "";

        messages.forEach((msg) => {
            const role = messageRoleOf(msg);
            const content = messageTextOf(msg);

            if (!content) return;

            const bubble = document.createElement("div");
            bubble.className = "message " + role + " nova-visible-session-message";
            bubble.textContent = content;
            fallback.appendChild(bubble);
        });

        try {
            chat.scrollTop = chat.scrollHeight;
        } catch (e) {}
    }

    async function openSession(sessionId) {
        if (!sessionId) return;

        const panel = ensurePanel();
        const body = panel.querySelector("[data-nova-visible-sessions-body]");

        if (body) {
            body.innerHTML = "Opening session...";
        }

        const res = await fetch("/api/sessions/" + encodeURIComponent(sessionId), {
            credentials: "include"
        });

        const data = await res.json();
        const session = data && data.session;

        if (!data || !data.ok || !session) {
            if (body) body.innerHTML = "Could not open session.";
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
        } catch (e) {}

        try {
            window.activeSessionId = sessionId;
            window.NovaActiveSessionId = sessionId;
            window.NOVA_ACTIVE_SESSION_ID = sessionId;
        } catch (e) {}

        renderMessages(session);
        panel.classList.remove("open");

        log("opened visible session", sessionId, "messages:", Array.isArray(session.messages) ? session.messages.length : 0);
    }

    async function loadSessions() {
        const panel = ensurePanel();
        const body = panel.querySelector("[data-nova-visible-sessions-body]");

        panel.classList.add("open");

        if (body) {
            body.innerHTML = "Loading sessions...";
        }

        try {
            const res = await fetch("/api/sessions", {
                credentials: "include"
            });

            const data = await res.json();
            const items = Array.isArray(data.items)
                ? data.items
                : Array.isArray(data.sessions)
                    ? data.sessions
                    : [];

            if (!items.length) {
                if (body) body.innerHTML = "No sessions found for this account yet.";
                log("loaded empty sessions list");
                return;
            }

            if (body) {
                body.innerHTML = "";
            }

            items.forEach((item) => {
                const sid = sessionIdOf(item);

                if (!sid) return;

                const card = document.createElement("button");
                card.type = "button";
                card.className = "nova-visible-session-card";
                card.innerHTML = `
                    <div class="nova-visible-session-title"></div>
                    <div class="nova-visible-session-meta"></div>
                `;

                const title = card.querySelector(".nova-visible-session-title");
                const meta = card.querySelector(".nova-visible-session-meta");

                title.textContent = textOf(item.title || "New Chat");
                meta.textContent = sid + " ? messages: " + textOf(item.message_count || (Array.isArray(item.messages) ? item.messages.length : 0));

                card.addEventListener("click", () => openSession(sid));

                if (body) {
                    body.appendChild(card);
                }
            });

            log("loaded visible sessions", items.length);
        } catch (err) {
            if (body) {
                body.innerHTML = "Failed to load sessions.";
            }

            log("load failed", err);
        }
    }

    function wireButtons() {
        const candidates = Array.from(document.querySelectorAll("button, a, [role='button']"));

        candidates.forEach((el) => {
            const label = textOf(el.textContent || el.getAttribute("aria-label") || el.title || "").toLowerCase();

            if (!label.includes("session") && !label.includes("history")) {
                return;
            }

            if (el.dataset.novaVisibleSessionsWired === "1") {
                return;
            }

            el.dataset.novaVisibleSessionsWired = "1";

            el.addEventListener("click", function () {
                setTimeout(loadSessions, 50);
            }, true);
        });
    }

    window.NovaMobileVisibleSessionsFallback = {
        open: loadSessions,
        refresh: loadSessions,
        openSession: openSession
    };

    document.addEventListener("DOMContentLoaded", () => {
        ensurePanel();
        wireButtons();
        setTimeout(wireButtons, 500);
        setTimeout(wireButtons, 1500);
    });

    setInterval(wireButtons, 2000);

    log("ready");
})();
