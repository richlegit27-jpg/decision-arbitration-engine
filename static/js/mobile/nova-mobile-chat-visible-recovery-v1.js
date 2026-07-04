(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_V1_20260703";

    if (window.__NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_V1_20260703__ = true;

    function chatRoot() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-messages") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages")
        );
    }

    function textOf(value) {
        return String(value || "").trim();
    }

    function messageText(message) {
        if (!message) return "";
        return textOf(
            message.text ||
            message.content ||
            message.body ||
            message.message ||
            message.value ||
            ""
        );
    }

    function roleOf(message, fallback) {
        const raw = textOf(
            message && (
                message.role ||
                message.sender ||
                message.type ||
                message.author
            )
        ).toLowerCase();

        if (raw.includes("assistant") || raw.includes("bot") || raw.includes("ai")) {
            return "assistant";
        }

        if (raw.includes("user") || raw.includes("human")) {
            return "user";
        }

        return fallback || "assistant";
    }

    function ensureStyles() {
        if (document.getElementById("nova-mobile-chat-visible-recovery-style-v1")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "nova-mobile-chat-visible-recovery-style-v1";
        style.textContent = `
            #mobileChatMessages {
                display: flex !important;
                flex-direction: column !important;
                gap: 10px !important;
                color: #f8fafc !important;
            }

            .nova-mobile-visible-message-v1 {
                max-width: 88% !important;
                padding: 10px 12px !important;
                border-radius: 16px !important;
                white-space: pre-wrap !important;
                overflow-wrap: anywhere !important;
                line-height: 1.42 !important;
                font-size: 14px !important;
                box-sizing: border-box !important;
                color: #f8fafc !important;
            }

            .nova-mobile-visible-message-v1[data-role="user"] {
                align-self: flex-end !important;
                background: rgba(168, 85, 247, 0.32) !important;
                border: 1px solid rgba(216, 180, 254, 0.28) !important;
            }

            .nova-mobile-visible-message-v1[data-role="assistant"] {
                align-self: flex-start !important;
                background: rgba(255, 255, 255, 0.08) !important;
                border: 1px solid rgba(255, 255, 255, 0.12) !important;
            }
        `;
        document.head.appendChild(style);
    }

    function appendMessage(role, text, id) {
        const root = chatRoot();
        text = textOf(text);

        if (!root || !text) return false;

        ensureStyles();

        const key = id || (role + ":" + text.slice(0, 120));

        const existingSameText = Array.from(root.querySelectorAll(".nova-mobile-visible-message-v1"))
            .some(function (el) {
                return el.dataset.role === (role || "assistant") &&
                    String(el.textContent || "").trim() === text;
            });

        if (existingSameText) {
            return true;
        }

        if (root.querySelector(`[data-nova-visible-key="${CSS.escape(key)}"]`)) {
            return true;
        }

        const bubble = document.createElement("div");
        bubble.className = "nova-mobile-visible-message-v1";
        bubble.dataset.role = role || "assistant";
        bubble.dataset.novaVisibleKey = key;
        bubble.textContent = text;

        root.appendChild(bubble);

        try {
            root.scrollTop = root.scrollHeight;
        } catch (_) {}

        return true;
    }

    function renderPayload(payload) {
        if (!payload || typeof payload !== "object") return false;

        let rendered = false;

        const sessionMessages =
            payload.session && Array.isArray(payload.session.messages)
                ? payload.session.messages
                : [];

        if (sessionMessages.length) {
            sessionMessages.forEach(function (message, index) {
                rendered = appendMessage(
                    roleOf(message, index % 2 ? "assistant" : "user"),
                    messageText(message),
                    message.id || ""
                ) || rendered;
            });
        }

        if (rendered) {
            return true;
        }

        const assistant =
            payload.assistant_message ||
            payload.assistant ||
            payload.message_out ||
            null;

        if (assistant) {
            rendered = appendMessage(
                roleOf(assistant, "assistant"),
                messageText(assistant),
                assistant.id || ""
            ) || rendered;
        }

        const text = textOf(payload.text || payload.response || payload.answer);
        if (text) {
            rendered = appendMessage("assistant", text, payload.id || "") || rendered;
        }

        return rendered;
    }

    async function loadCurrentSession() {
        const params = new URLSearchParams(window.location.search);
        const sid =
            params.get("session_id") ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            "";

        if (!sid) return;

        try {
            const response = await fetch("/api/sessions/" + encodeURIComponent(sid), {
                method: "GET",
                headers: { "Accept": "application/json" },
                cache: "no-store",
                credentials: "include"
            });

            if (!response.ok) return;

            const payload = await response.json();
            renderPayload(payload);
        } catch (_) {}
    }

    function patchFetch() {
        if (window.__NovaMobileChatVisibleRecoveryFetchPatchedV1) return;
        window.__NovaMobileChatVisibleRecoveryFetchPatchedV1 = true;

        const originalFetch = window.fetch;
        if (typeof originalFetch !== "function") return;

        window.fetch = async function novaVisibleFetch(input, init) {
            const response = await originalFetch.apply(this, arguments);

            try {
                const url = String(input && input.url ? input.url : input || "");
                const method = String(
                    (init && init.method) ||
                    (input && input.method) ||
                    "GET"
                ).toUpperCase();

                if (method === "POST" && url.includes("/api/chat")) {
                    response.clone().json().then(renderPayload).catch(function () {});
                }
            } catch (_) {}

            return response;
        };
    }

    function boot() {
        ensureStyles();
        patchFetch();
        loadCurrentSession();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }

    setTimeout(loadCurrentSession, 500);
    setTimeout(loadCurrentSession, 1500);

    window.NovaMobileChatVisibleRecoveryV1 = {
        renderPayload,
        loadCurrentSession,
        appendMessage
    };

    console.log("[" + MARK + "] ready");
})();

