(function () {
    "use strict";

    const VERSION = "mobile-session-restore-override-v4";
    window.__NOVA_MOBILE_SESSION_RESTORE_OVERRIDE_V4__ = true;

    function log() {
        try { console.log("[NOVA MOBILE RESTORE OVERRIDE V4]", ...arguments); } catch (_) {}
    }

    function warn() {
        try { console.warn("[NOVA MOBILE RESTORE OVERRIDE V4]", ...arguments); } catch (_) {}
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function roleOf(message) {
        const raw = String(
            message && (message.role || message.sender || message.author || message.type || "")
        ).toLowerCase();

        if (raw.includes("user") || raw === "human") {
            return "user";
        }

        return "assistant";
    }

    function textOf(message) {
        if (!message) return "";

        const direct = [
            message.text,
            message.content,
            message.message,
            message.body,
            message.reply,
            message.response,
            message.output
        ];

        for (const item of direct) {
            if (typeof item === "string" && item.trim()) {
                return item;
            }
        }

        if (Array.isArray(message.content)) {
            return message.content.map(function (part) {
                if (typeof part === "string") return part;
                if (part && typeof part.text === "string") return part.text;
                return "";
            }).filter(Boolean).join("\n");
        }

        return "";
    }

    function messagesOf(payload) {
        const candidates = [
            payload && payload.messages,
            payload && payload.session && payload.session.messages,
            payload && payload.data && payload.data.messages,
            payload && payload.result && payload.result.messages
        ];

        for (const item of candidates) {
            if (Array.isArray(item)) {
                return item;
            }
        }

        return [];
    }

    function sessionOf(payload, fallbackId) {
        const session = payload && payload.session ? payload.session : payload || {};
        return {
            id: String(session.id || session.session_id || payload.session_id || payload.id || fallbackId || ""),
            title: String(session.title || session.name || payload.title || fallbackId || "Session"),
            messages: messagesOf(payload)
        };
    }

    function existingRoot() {
        const selectors = [
            "#nova-mobile-restored-session-messages",
            "[data-nova-chat-messages]",
            "[data-chat-messages]",
            "#nova-mobile-messages",
            "#mobile-chat-messages",
            "#chat-messages",
            "#messages",
            ".nova-mobile-messages",
            ".mobile-chat-messages",
            ".chat-messages",
            ".messages",
            "[role='log']"
        ];

        for (const selector of selectors) {
            const node = document.querySelector(selector);
            if (node) {
                return node;
            }
        }

        return null;
    }

    function makeRoot() {
        let root = document.getElementById("nova-mobile-restored-session-messages");

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = "nova-mobile-restored-session-messages";
        root.className = "nova-mobile-restored-session-messages nova-mobile-messages chat-messages";
        root.setAttribute("data-nova-chat-messages", "true");
        root.setAttribute("data-restore-override-v4", "true");

        root.style.cssText = [
            "box-sizing:border-box",
            "width:100%",
            "min-height:45vh",
            "max-height:calc(100vh - 170px)",
            "overflow-y:auto",
            "-webkit-overflow-scrolling:touch",
            "padding:12px",
            "display:flex",
            "flex-direction:column",
            "gap:10px"
        ].join(";");

        const textarea = document.querySelector("textarea");
        const composer = textarea && textarea.closest
            ? textarea.closest("form, footer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer")
            : null;

        if (composer && composer.parentNode) {
            composer.parentNode.insertBefore(root, composer);
        } else {
            (document.querySelector("main") || document.body).appendChild(root);
        }

        log("created visible restore root", root);
        return root;
    }

    function render(messages) {
        const root = existingRoot() || makeRoot();

        root.innerHTML = "";

        for (const message of messages) {
            const role = roleOf(message);
            const text = textOf(message);

            const row = document.createElement("div");
            row.className = "nova-mobile-message message " + role;
            row.setAttribute("data-role", role);
            row.style.cssText = [
                "box-sizing:border-box",
                "max-width:92%",
                "padding:10px 12px",
                "border-radius:14px",
                "white-space:normal",
                "word-break:break-word",
                "align-self:" + (role === "user" ? "flex-end" : "flex-start"),
                "background:" + (role === "user" ? "rgba(120,90,255,0.24)" : "rgba(255,255,255,0.10)"),
                "border:1px solid rgba(255,255,255,0.12)",
                "color:inherit"
            ].join(";");

            row.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
            root.appendChild(row);
        }

        try { root.scrollTop = root.scrollHeight; } catch (_) {}
        return root;
    }

    function updateActive(session) {
        if (!session || !session.id) return;

        try { localStorage.setItem("nova_mobile_active_session_id", session.id); } catch (_) {}
        try { localStorage.setItem("nova_active_session_id", session.id); } catch (_) {}

        window.novaMobileActiveSessionId = session.id;
        window.activeSessionId = session.id;
        window.currentSessionId = session.id;

        const title = "Session: " + (session.title || session.id) + " · " + session.id.slice(-6);

        document.querySelectorAll(
            "[data-session-title], [data-nova-session-title], #nova-session-title, #mobile-session-title, #session-title, .nova-session-title, .session-title"
        ).forEach(function (node) {
            node.textContent = title;
        });
    }

    async function restoreSession(id) {
        const sessionId = String(id || "").trim();

        if (!sessionId) {
            warn("missing session id");
            return null;
        }

        const response = await fetch("/api/sessions/" + encodeURIComponent(sessionId), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });

        const payload = await response.json();

        if (!response.ok || payload.ok === false) {
            warn("session detail failed", response.status, payload);
            return null;
        }

        const session = sessionOf(payload, sessionId);
        render(session.messages);
        updateActive(session);

        log("restored", session.id, "messages", session.messages.length);
        return session;
    }

    document.addEventListener("click", function (event) {
        const item = event.target && event.target.closest
            ? event.target.closest("[data-session-id], [data-id], .session-item, .nova-session-item, .mobile-session-item")
            : null;

        if (!item) return;

        const text = String(item.textContent || "").toLowerCase();
        if (text.includes("new chat")) return;

        const id = String(
            item.getAttribute("data-session-id") ||
            item.getAttribute("data-id") ||
            item.dataset.sessionId ||
            item.dataset.id ||
            ""
        ).trim();

        if (!id || id.length < 3) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        restoreSession(id);
    }, true);

    window.NovaMobileRestoreSession = restoreSession;
    window.NovaMobileSessionRestoreOverrideV4 = {
        version: VERSION,
        restoreSession: restoreSession,
        render: render
    };


    function loadSessionPanelV6FromV4() {
        if (window.__NOVA_MOBILE_SESSION_PANEL_V6__) {
            return;
        }

        if (document.querySelector("script[data-nova-session-panel-v6-loader='true']")) {
            return;
        }

        const script = document.createElement("script");
        script.src = "/static/js/mobile/nova-mobile-session-panel-v9.js?v=v9-new-file";
        script.async = false;
        script.setAttribute("data-nova-session-panel-v6-loader", "true");

        script.onload = function () {
            try {
                console.log("[NOVA MOBILE RESTORE OVERRIDE V4] loaded session panel v6");
            } catch (_) {}
        };

        script.onerror = function () {
            try {
                console.warn("[NOVA MOBILE RESTORE OVERRIDE V4] failed to load session panel v6");
            } catch (_) {}
        };

        document.head.appendChild(script);
    }

    loadSessionPanelV6FromV4();

    log("active", VERSION);
})();

