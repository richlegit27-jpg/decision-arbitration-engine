(function () {
    "use strict";

    const VERSION = "session-restore-lock-dom-root-v3";
    window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;
    window.__NOVA_MOBILE_SESSION_RESTORE_DOM_ROOT_V2__ = true;
    window.__NOVA_MOBILE_SESSION_RESTORE_EMERGENCY_ROOT_V3__ = true;
    window.__NOVA_MOBILE_SESSION_RESTORE_DOM_ROOT_V2__ = true;

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

    function isVisibleNode(node) {
        if (!node || !node.getBoundingClientRect) {
            return false;
        }

        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle ? window.getComputedStyle(node) : null;

        if (style && (style.display === "none" || style.visibility === "hidden")) {
            return false;
        }

        return rect.width > 40 && rect.height > 40;
    }

    function isBadChatRootCandidate(node) {
        if (!node) {
            return true;
        }

        const raw = (
            String(node.id || "") + " " +
            String(node.className || "") + " " +
            String(node.getAttribute("role") || "") + " " +
            String(node.getAttribute("aria-label") || "") + " " +
            String(node.getAttribute("data-action") || "")
        ).toLowerCase();

        return (
            raw.includes("composer") ||
            raw.includes("input") ||
            raw.includes("textarea") ||
            raw.includes("prompt") ||
            raw.includes("button") ||
            raw.includes("toolbar") ||
            raw.includes("drawer") ||
            raw.includes("session-list") ||
            raw.includes("sessions-list") ||
            raw.includes("auth") ||
            raw.includes("panel") ||
            raw.includes("menu") ||
            raw.includes("nav") ||
            raw.includes("header") ||
            raw.includes("footer") ||
            raw.includes("modal")
        );
    }

    function scoreChatRootCandidate(node) {
        if (!node || isBadChatRootCandidate(node) || !isVisibleNode(node)) {
            return -9999;
        }

        const raw = (
            String(node.id || "") + " " +
            String(node.className || "") + " " +
            String(node.getAttribute("role") || "") + " " +
            String(node.getAttribute("aria-live") || "") + " " +
            String(node.getAttribute("data-nova-chat-messages") || "") + " " +
            String(node.getAttribute("data-chat-messages") || "") + " " +
            String(node.getAttribute("data-messages") || "")
        ).toLowerCase();

        let score = 0;

        if (raw.includes("message")) score += 80;
        if (raw.includes("messages")) score += 90;
        if (raw.includes("chat")) score += 70;
        if (raw.includes("conversation")) score += 70;
        if (raw.includes("thread")) score += 65;
        if (raw.includes("feed")) score += 55;
        if (raw.includes("history")) score += 55;
        if (raw.includes("log")) score += 45;
        if (raw.includes("stream")) score += 45;
        if (raw.includes("nova")) score += 20;
        if (raw.includes("mobile")) score += 20;
        if (raw.includes("aria-live")) score += 35;
        if (node.getAttribute("role") === "log") score += 90;

        try {
            const rect = node.getBoundingClientRect();
            if (rect.height > 120) score += 20;
            if (rect.height > 250) score += 25;
            if (node.scrollHeight > rect.height + 20) score += 20;
        } catch (_) {}

        const messageChildren = node.querySelectorAll(
            ".message, .nova-message, .nova-mobile-message, .chat-message, .assistant, .user, [data-role], [data-message-id], [data-nova-message]"
        ).length;

        score += Math.min(messageChildren * 20, 160);

        return score;
    }

    function createFallbackChatRoot() {
        let root = document.getElementById("nova-mobile-restored-session-messages");

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = "nova-mobile-restored-session-messages";
        root.className = "nova-mobile-restored-session-messages nova-mobile-messages chat-messages";
        root.setAttribute("data-nova-chat-messages", "true");
        root.setAttribute("data-session-restore-fallback", "true");
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

        const composer = document.querySelector(
            "#composer, #mobile-composer, #nova-composer, #nova-mobile-composer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer, form textarea, textarea"
        );

        const anchor = composer && composer.closest
            ? composer.closest("form, footer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer")
            : null;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(root, anchor);
        } else {
            const main = document.querySelector("main") || document.body;
            main.appendChild(root);
        }

        log("created fallback chat root", root);
        return root;
    }

    function findChatRoot() {
        const selectors = [
            "[data-nova-chat-messages]",
            "[data-chat-messages]",
            "[data-messages]",
            "[data-nova-messages]",
            "[data-chat-root]",
            "[data-thread]",
            "[role='log']",
            "[aria-live='polite']",
            "[aria-live='assertive']",

            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#mobile-chat-messages",
            "#chat-messages",
            "#messages",
            "#message-list",
            "#messages-list",
            "#messageList",
            "#chat-history",
            "#chat-log",
            "#chat-feed",
            "#conversation",
            "#conversation-feed",
            "#conversation-log",
            "#thread",
            "#chat-thread",
            "#nova-thread",
            "#nova-chat-thread",
            "#nova-chat-feed",
            "#mobile-chat-feed",
            "#nova-mobile-chat-feed",
            "#nova-chat-window",
            "#mobile-chat-window",
            "#nova-mobile-chat",
            "#nova-mobile-chat-area",
            "#mobile-chat",
            "#mobile-chat-area",

            ".nova-mobile-messages",
            ".nova-chat-messages",
            ".mobile-chat-messages",
            ".chat-messages",
            ".messages",
            ".message-list",
            ".messages-list",
            ".chat-history",
            ".chat-log",
            ".chat-feed",
            ".conversation",
            ".conversation-feed",
            ".conversation-log",
            ".thread",
            ".chat-thread",
            ".nova-thread",
            ".nova-chat-thread",
            ".nova-chat-feed",
            ".mobile-chat-feed",
            ".nova-mobile-chat-feed",
            ".nova-chat-window",
            ".mobile-chat-window",
            ".nova-mobile-chat",
            ".nova-mobile-chat-area",
            ".mobile-chat",
            ".mobile-chat-area"
        ];

        for (const selector of selectors) {
            const nodes = Array.from(document.querySelectorAll(selector));
            const best = nodes
                .map(function (node) {
                    return {
                        node: node,
                        score: scoreChatRootCandidate(node)
                    };
                })
                .filter(function (item) {
                    return item.score > 0;
                })
                .sort(function (a, b) {
                    return b.score - a.score;
                })[0];

            if (best && best.node) {
                best.node.setAttribute("data-nova-chat-messages", "true");
                log("found chat root by selector", selector, "score", best.score, best.node);
                return best.node;
            }
        }

        const broadNodes = Array.from(document.querySelectorAll("main, section, article, div, ul, ol"));
        const bestBroad = broadNodes
            .map(function (node) {
                return {
                    node: node,
                    score: scoreChatRootCandidate(node)
                };
            })
            .filter(function (item) {
                return item.score > 40;
            })
            .sort(function (a, b) {
                return b.score - a.score;
            })[0];

        if (bestBroad && bestBroad.node) {
            bestBroad.node.setAttribute("data-nova-chat-messages", "true");
            log("found chat root by DOM scoring", "score", bestBroad.score, bestBroad.node);
            return bestBroad.node;
        }

        return createFallbackChatRoot();
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


    function createEmergencyChatRoot() {
        let root = document.getElementById("nova-mobile-restored-session-messages");

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = "nova-mobile-restored-session-messages";
        root.className = "nova-mobile-restored-session-messages nova-mobile-messages chat-messages";
        root.setAttribute("data-nova-chat-messages", "true");
        root.setAttribute("data-session-restore-emergency-root", "true");
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

        const composer = document.querySelector(
            "#composer, #mobile-composer, #nova-composer, #nova-mobile-composer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer, form textarea, textarea"
        );

        const anchor = composer && composer.closest
            ? composer.closest("form, footer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer")
            : null;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(root, anchor);
        } else {
            const main = document.querySelector("main") || document.body;
            main.appendChild(root);
        }

        log("created emergency chat root", root);
        return root;
    }

    function clearAndRenderMessages(messages) {
        let root = findChatRoot();

        if (!root) {
            root = createEmergencyChatRoot();
        }

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

    const id = String(node.id || "").toLowerCase();
    const cls = String(node.className || "").toLowerCase();
    const action = String(node.getAttribute("data-action") || "").toLowerCase();
    const role = String(node.getAttribute("data-role") || "").toLowerCase();

    return (
        id.includes("new-chat") ||
        id.includes("newchat") ||
        cls.includes("new-chat") ||
        cls.includes("newchat") ||
        action === "new-chat" ||
        role === "new-chat"
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
