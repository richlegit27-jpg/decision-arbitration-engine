(function () {
    "use strict";

    const VERSION = "session-restore-lock-20260702";
    window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;

    const ACTIVE_SESSION_KEYS = [
        "nova_mobile_active_session_id",
        "nova_active_session_id",
        "active_session_id",
        "session_id"
    ];

    function log() {
        try {
            console.log("[NOVA MOBILE SESSION RESTORE LOCK]", ...arguments);
        } catch (_) {}
    }

    function warn() {
        try {
            console.warn("[NOVA MOBILE SESSION RESTORE LOCK]", ...arguments);
        } catch (_) {}
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function normalizeRole(message) {
        const raw = String(
            message && (
                message.role ||
                message.sender ||
                message.author ||
                message.type ||
                ""
            )
        ).toLowerCase();

        if (raw.includes("user") || raw === "human") {
            return "user";
        }

        if (
            raw.includes("assistant") ||
            raw.includes("nova") ||
            raw.includes("bot") ||
            raw.includes("ai")
        ) {
            return "assistant";
        }

        return "assistant";
    }

    function normalizeText(message) {
        if (!message) {
            return "";
        }

        const candidates = [
            message.text,
            message.content,
            message.message,
            message.body,
            message.reply,
            message.response,
            message.output,
            message.value
        ];

        for (const candidate of candidates) {
            if (typeof candidate === "string" && candidate.trim()) {
                return candidate;
            }
        }

        if (message.assistant_message) {
            return normalizeText(message.assistant_message);
        }

        if (message.user_message) {
            return normalizeText(message.user_message);
        }

        if (Array.isArray(message.content)) {
            return message.content
                .map(function (part) {
                    if (typeof part === "string") {
                        return part;
                    }
                    if (part && typeof part.text === "string") {
                        return part.text;
                    }
                    return "";
                })
                .filter(Boolean)
                .join("\n");
        }

        return "";
    }

    function normalizeMessages(payload) {
        const candidates = [
            payload && payload.messages,
            payload && payload.session && payload.session.messages,
            payload && payload.data && payload.data.messages,
            payload && payload.result && payload.result.messages
        ];

        for (const candidate of candidates) {
            if (Array.isArray(candidate)) {
                return candidate;
            }
        }

        return [];
    }

    function normalizeSession(payload, fallbackId) {
        const session = (
            payload && payload.session ||
            payload && payload.data && payload.data.session ||
            payload && payload.result && payload.result.session ||
            payload ||
            {}
        );

        const id = String(
            session.id ||
            session.session_id ||
            payload.session_id ||
            payload.id ||
            fallbackId ||
            ""
        ).trim();

        const title = String(
            session.title ||
            session.name ||
            session.label ||
            payload.title ||
            id ||
            "Session"
        ).trim();

        return {
            id: id,
            title: title,
            messages: normalizeMessages(payload)
        };
    }

    function findChatRoot() {
        const selectors = [
            "[data-nova-chat-messages]",
            "[data-chat-messages]",
            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#mobile-chat-messages",
            "#chat-messages",
            "#messages",
            ".nova-mobile-messages",
            ".chat-messages",
            ".messages"
        ];

        for (const selector of selectors) {
            const node = document.querySelector(selector);
            if (node) {
                return node;
            }
        }

        return null;
    }

    function renderMessage(message) {
        const role = normalizeRole(message);
        const text = normalizeText(message);

        const row = document.createElement("div");
        row.className = "nova-mobile-message message " + role;
        row.setAttribute("data-role", role);

        const bubble = document.createElement("div");
        bubble.className = "nova-mobile-message-bubble bubble " + role;
        bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");

        row.appendChild(bubble);
        return row;
    }

    function clearAndRenderMessages(messages) {
        const root = findChatRoot();

        if (!root) {
            warn("chat root not found; cannot render restored messages");
            return false;
        }

        root.innerHTML = "";

        for (const message of messages) {
            root.appendChild(renderMessage(message));
        }

        try {
            root.scrollTop = root.scrollHeight;
        } catch (_) {}

        return true;
    }

    function updateActiveSessionState(session) {
        if (!session || !session.id) {
            return;
        }

        for (const key of ACTIVE_SESSION_KEYS) {
            try {
                localStorage.setItem(key, session.id);
            } catch (_) {}
        }

        window.novaMobileActiveSessionId = session.id;
        window.activeSessionId = session.id;
        window.currentSessionId = session.id;
        window.NOVA_ACTIVE_SESSION_ID = session.id;

        const titleText = session.title
            ? "Session: " + session.title + " · " + session.id.slice(-6)
            : "Session: " + session.id.slice(-6);

        const titleSelectors = [
            "[data-session-title]",
            "[data-nova-session-title]",
            "#nova-session-title",
            "#mobile-session-title",
            "#session-title",
            ".nova-session-title",
            ".session-title"
        ];

        for (const selector of titleSelectors) {
            document.querySelectorAll(selector).forEach(function (node) {
                node.textContent = titleText;
            });
        }

        document.querySelectorAll("[data-session-id], [data-id]").forEach(function (node) {
            const nodeId = (
                node.getAttribute("data-session-id") ||
                node.getAttribute("data-id") ||
                ""
            ).trim();

            if (nodeId === session.id) {
                node.classList.add("active", "is-active");
                node.setAttribute("aria-current", "true");
            } else {
                node.classList.remove("active", "is-active");
                node.removeAttribute("aria-current");
            }
        });

        try {
            window.dispatchEvent(new CustomEvent("nova:mobile-session-restored", {
                detail: {
                    session_id: session.id,
                    title: session.title,
                    count: session.messages.length
                }
            }));
        } catch (_) {}
    }

    async function restoreSession(sessionId) {
        const id = String(sessionId || "").trim();

        if (!id) {
            warn("restore skipped; missing session id");
            return null;
        }

        const response = await fetch("/api/sessions/" + encodeURIComponent(id), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error("session detail failed HTTP " + response.status);
        }

        const payload = await response.json();
        const session = normalizeSession(payload, id);

        if (!session.id) {
            session.id = id;
        }

        clearAndRenderMessages(session.messages);
        updateActiveSessionState(session);

        log("restored", session.id, "messages", session.messages.length);
        return session;
    }

    function looksLikeNewChat(node) {
        if (!node) {
            return false;
        }

        const text = String(node.textContent || "").toLowerCase();
        const id = String(node.id || "").toLowerCase();
        const cls = String(node.className || "").toLowerCase();
        const action = String(node.getAttribute("data-action") || "").toLowerCase();

        return (
            text.includes("new chat") ||
            id.includes("new-chat") ||
            id.includes("newchat") ||
            cls.includes("new-chat") ||
            cls.includes("newchat") ||
            action.includes("new")
        );
    }

    function findSessionClickTarget(startNode) {
        if (!startNode || !startNode.closest) {
            return null;
        }

        const sessionRoot = startNode.closest(
            "[data-session-list], [data-nova-session-list], #session-list, #sessions-list, #nova-session-list, #sessionsPanel, #sessionDrawer, .session-list, .sessions-list, .session-drawer, .sessions-drawer"
        );

        const item = startNode.closest(
            "[data-session-id], [data-id], .session-item, .nova-session-item, .mobile-session-item, li, button, a"
        );

        if (!item) {
            return null;
        }

        if (!sessionRoot && !String(item.className || "").toLowerCase().includes("session")) {
            return null;
        }

        if (looksLikeNewChat(item)) {
            return null;
        }

        const id = String(
            item.getAttribute("data-session-id") ||
            item.getAttribute("data-id") ||
            item.dataset.sessionId ||
            item.dataset.id ||
            ""
        ).trim();

        if (!id || id.length < 3) {
            return null;
        }

        return {
            node: item,
            id: id
        };
    }

    function installSessionClickCapture() {
        document.addEventListener("click", function (event) {
            const target = findSessionClickTarget(event.target);

            if (!target) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            restoreSession(target.id).catch(function (error) {
                warn("restore failed", target.id, error && error.message ? error.message : error);
            });
        }, true);
    }

    function installNewChatDebounce() {
        let lastNewChatAt = 0;

        document.addEventListener("click", function (event) {
            const node = event.target && event.target.closest
                ? event.target.closest("button, a, [role='button'], [data-action]")
                : null;

            if (!looksLikeNewChat(node)) {
                return;
            }

            const now = Date.now();

            if (now - lastNewChatAt < 1500) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                log("blocked duplicate New Chat click");
                return;
            }

            lastNewChatAt = now;
        }, true);
    }

    function installFetchCredentialGuard() {
        if (window.__NOVA_MOBILE_SESSION_RESTORE_FETCH_GUARD_20260702__) {
            return;
        }

        window.__NOVA_MOBILE_SESSION_RESTORE_FETCH_GUARD_20260702__ = true;

        const originalFetch = window.fetch;
        if (typeof originalFetch !== "function") {
            return;
        }

        window.fetch = function novaMobileSessionRestoreFetch(input, init) {
            const url = typeof input === "string"
                ? input
                : input && input.url
                    ? input.url
                    : "";

            if (
                url.includes("/api/sessions/") ||
                url.endsWith("/api/sessions") ||
                url.includes("/api/sessions/new")
            ) {
                const nextInit = Object.assign({}, init || {});
                nextInit.credentials = "include";
                return originalFetch.call(this, input, nextInit);
            }

            return originalFetch.call(this, input, init);
        };
    }

    function install() {
        installFetchCredentialGuard();
        installSessionClickCapture();
        installNewChatDebounce();

        window.NovaMobileRestoreSession = restoreSession;
        window.NovaMobileSessionRestoreLock = {
            version: VERSION,
            restoreSession: restoreSession,
            renderMessages: clearAndRenderMessages,
            active: true
        };

        log("active", VERSION);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", install, { once: true });
    } else {
        install();
    }
})();
