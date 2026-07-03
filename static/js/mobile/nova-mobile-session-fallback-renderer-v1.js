
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_FALLBACK_RENDERER_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_FALLBACK_RENDERER_V1_20260703__ = true;

    const VERSION = "fallback-session-renderer-v1-20260703";

    function log() {
        try {
            console.log("[Nova Session Fallback]", ...arguments);
        } catch (_) {}
    }

    function escapeText(value) {
        if (value === null || value === undefined) {
            return "";
        }

        if (typeof value === "string") {
            return value;
        }

        if (typeof value === "number" || typeof value === "boolean") {
            return String(value);
        }

        if (typeof value === "object") {
            if (typeof value.text === "string") {
                return value.text;
            }

            if (typeof value.content === "string") {
                return value.content;
            }

            if (typeof value.message === "string") {
                return value.message;
            }

            try {
                return JSON.stringify(value, null, 2);
            } catch (_) {
                return String(value);
            }
        }

        return String(value);
    }

    function getSessionId(item) {
        return item && (item.id || item.session_id || item.sessionId || item.uuid || "");
    }

    function getMessageRole(message) {
        const raw = String(
            (message && (message.role || message.sender || message.type || message.author)) || "assistant"
        ).toLowerCase();

        if (raw.includes("user") || raw.includes("human")) {
            return "user";
        }

        if (raw.includes("system")) {
            return "system";
        }

        return "assistant";
    }

    function getMessageText(message) {
        if (!message) {
            return "";
        }

        if (typeof message === "string") {
            return message;
        }

        return escapeText(
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

    function normalizeSessions(payload) {
        if (Array.isArray(payload)) {
            return payload;
        }

        if (payload && Array.isArray(payload.sessions)) {
            return payload.sessions;
        }

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
        if (!payload) {
            return [];
        }

        if (Array.isArray(payload.messages)) {
            return payload.messages;
        }

        if (payload.session && Array.isArray(payload.session.messages)) {
            return payload.session.messages;
        }

        if (payload.data && Array.isArray(payload.data.messages)) {
            return payload.data.messages;
        }

        if (Array.isArray(payload)) {
            return payload;
        }

        return [];
    }

    async function fetchJson(url) {
        const res = await fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        const text = await res.text();

        if (!res.ok) {
            throw new Error(url + " -> " + res.status + " " + text.slice(0, 200));
        }

        try {
            return JSON.parse(text);
        } catch (err) {
            throw new Error(url + " returned non-JSON: " + text.slice(0, 200));
        }
    }

    function ensureStyles() {
        if (document.getElementById("nova-session-fallback-style-v1")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "nova-session-fallback-style-v1";
        style.textContent = `
            #nova-session-fallback-button-v1 {
                position: fixed;
                top: 10px;
                left: 10px;
                z-index: 2147483000;
                border: 1px solid rgba(255,255,255,0.20);
                background: rgba(20, 20, 28, 0.94);
                color: #fff;
                border-radius: 999px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
                box-shadow: 0 8px 30px rgba(0,0,0,0.35);
            }

            #nova-session-fallback-panel-v1 {
                position: fixed;
                top: 54px;
                left: 10px;
                width: min(92vw, 390px);
                max-height: 74vh;
                overflow: auto;
                z-index: 2147483000;
                background: rgba(14, 14, 20, 0.98);
                color: #fff;
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 16px;
                box-shadow: 0 18px 60px rgba(0,0,0,0.55);
                padding: 10px;
                display: none;
                -webkit-overflow-scrolling: touch;
            }

            #nova-session-fallback-panel-v1[data-open="true"] {
                display: block;
            }

            .nova-session-fallback-row-v1 {
                width: 100%;
                display: block;
                text-align: left;
                background: rgba(255,255,255,0.07);
                color: #fff;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
                padding: 10px;
                margin: 7px 0;
                cursor: pointer;
            }

            .nova-session-fallback-row-v1:hover {
                background: rgba(255,255,255,0.12);
            }

            .nova-session-fallback-title-v1 {
                font-size: 13px;
                font-weight: 800;
                line-height: 1.25;
                margin-bottom: 4px;
            }

            .nova-session-fallback-meta-v1 {
                font-size: 11px;
                opacity: 0.72;
            }

            #nova-session-fallback-messages-v1 {
                margin: 70px 10px 110px 10px;
                padding: 8px 0;
            }

            .nova-session-fallback-message-v1 {
                white-space: pre-wrap;
                border-radius: 14px;
                padding: 11px 12px;
                margin: 9px 0;
                line-height: 1.36;
                font-size: 14px;
                color: #fff;
                border: 1px solid rgba(255,255,255,0.10);
            }

            .nova-session-fallback-message-v1[data-role="user"] {
                background: rgba(98, 80, 255, 0.28);
                margin-left: 24px;
            }

            .nova-session-fallback-message-v1[data-role="assistant"] {
                background: rgba(255,255,255,0.08);
                margin-right: 24px;
            }

            .nova-session-fallback-message-v1[data-role="system"] {
                background: rgba(255,255,255,0.04);
                font-size: 12px;
                opacity: 0.75;
            }

            .nova-session-fallback-empty-v1 {
                opacity: 0.75;
                font-size: 13px;
                padding: 12px;
            }
        `;
        document.head.appendChild(style);
    }

    function ensureButtonAndPanel() {
        ensureStyles();

        let button = document.getElementById("nova-session-fallback-button-v1");
        let panel = document.getElementById("nova-session-fallback-panel-v1");

        if (!button) {
            button = document.createElement("button");
            button.id = "nova-session-fallback-button-v1";
            button.type = "button";
            button.textContent = "Sessions";
            document.body.appendChild(button);
        }

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "nova-session-fallback-panel-v1";
            panel.innerHTML = "<div class='nova-session-fallback-empty-v1'>Loading sessions...</div>";
            document.body.appendChild(panel);
        }

        button.onclick = function () {
            const open = panel.getAttribute("data-open") === "true";
            panel.setAttribute("data-open", open ? "false" : "true");

            if (!open) {
                loadSessions();
            }
        };

        return { button, panel };
    }

    function getExistingMessageContainer() {
        const selectors = [
            "#messages",
            "#chat-messages",
            "#chatMessages",
            "#message-list",
            "#nova-messages",
            "#nova-chat-messages",
            ".messages",
            ".chat-messages",
            ".nova-messages",
            ".nova-chat-messages",
            "[data-chat-messages]",
            "[data-nova-messages]"
        ];

        for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (el) {
                return el;
            }
        }

        return null;
    }

    function ensureMessageContainer() {
        let existing = getExistingMessageContainer();

        if (existing) {
            return existing;
        }

        let fallback = document.getElementById("nova-session-fallback-messages-v1");

        if (!fallback) {
            fallback = document.createElement("div");
            fallback.id = "nova-session-fallback-messages-v1";
            document.body.appendChild(fallback);
        }

        return fallback;
    }

    function renderMessages(sessionId, title, messages) {
        const container = ensureMessageContainer();

        container.innerHTML = "";

        const header = document.createElement("div");
        header.className = "nova-session-fallback-message-v1";
        header.setAttribute("data-role", "system");
        header.textContent = "Session: " + (title || sessionId || "New Chat") + " · " + messages.length + " messages";
        container.appendChild(header);

        if (!messages.length) {
            const empty = document.createElement("div");
            empty.className = "nova-session-fallback-message-v1";
            empty.setAttribute("data-role", "system");
            empty.textContent = "No messages in this session.";
            container.appendChild(empty);
        }

        messages.forEach(function (message) {
            const role = getMessageRole(message);
            const text = getMessageText(message);

            const row = document.createElement("div");
            row.className = "nova-session-fallback-message-v1";
            row.setAttribute("data-role", role);
            row.textContent = text || "[empty message]";
            container.appendChild(row);
        });

        try {
            window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
        } catch (_) {
            window.scrollTo(0, document.body.scrollHeight);
        }
    }

    async function openSession(item) {
        const sessionId = getSessionId(item);

        if (!sessionId) {
            return;
        }

        const title = item.title || "New Chat";

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
        } catch (_) {}

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            url.searchParams.set("v", "session-fallback-" + Date.now());
            history.replaceState(null, "", url.toString());
        } catch (_) {}

        const panel = document.getElementById("nova-session-fallback-panel-v1");
        if (panel) {
            panel.setAttribute("data-open", "false");
        }

        const container = ensureMessageContainer();
        container.innerHTML = "";
        const loading = document.createElement("div");
        loading.className = "nova-session-fallback-message-v1";
        loading.setAttribute("data-role", "system");
        loading.textContent = "Loading session...";
        container.appendChild(loading);

        try {
            const detail = await fetchJson("/api/sessions/" + encodeURIComponent(sessionId));
            const messages = normalizeMessages(detail);
            renderMessages(sessionId, title, messages);
            log("opened session", sessionId, messages.length);
        } catch (err) {
            renderMessages(sessionId, title, []);
            log("open session failed", err);
        }
    }

    async function loadSessions() {
        const ui = ensureButtonAndPanel();
        const panel = ui.panel;

        panel.innerHTML = "<div class='nova-session-fallback-empty-v1'>Loading sessions...</div>";

        try {
            const payload = await fetchJson("/api/sessions");
            const sessions = normalizeSessions(payload);

            panel.innerHTML = "";

            const header = document.createElement("div");
            header.className = "nova-session-fallback-empty-v1";
            header.textContent = "Sessions: " + sessions.length;
            panel.appendChild(header);

            sessions.forEach(function (item) {
                const sessionId = getSessionId(item);
                const title = item.title || "New Chat";
                const count = item.message_count;
                const row = document.createElement("button");
                row.type = "button";
                row.className = "nova-session-fallback-row-v1";

                const titleEl = document.createElement("div");
                titleEl.className = "nova-session-fallback-title-v1";
                titleEl.textContent = title;

                const meta = document.createElement("div");
                meta.className = "nova-session-fallback-meta-v1";
                meta.textContent = (count === undefined || count === null ? "?" : count) + " messages · " + sessionId;

                row.appendChild(titleEl);
                row.appendChild(meta);
                row.onclick = function () {
                    openSession(item);
                };

                panel.appendChild(row);
            });

            if (!sessions.length) {
                panel.innerHTML = "<div class='nova-session-fallback-empty-v1'>No sessions returned.</div>";
            }

            log("rendered sessions", sessions.length);
        } catch (err) {
            panel.innerHTML = "<div class='nova-session-fallback-empty-v1'>Session load failed. Check console.</div>";
            log("load sessions failed", err);
        }
    }

    async function boot() {
        ensureButtonAndPanel();

        const params = new URLSearchParams(window.location.search);
        const urlSession = params.get("session_id");

        if (urlSession) {
            try {
                const detail = await fetchJson("/api/sessions/" + encodeURIComponent(urlSession));
                const session = detail.session || detail;
                const messages = normalizeMessages(detail);
                renderMessages(urlSession, session.title || urlSession, messages);
            } catch (err) {
                log("url session load failed", err);
            }
        }

        loadSessions();
        log("ready", VERSION);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
