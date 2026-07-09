(function () {
    "use strict";

    function appendMessage(role, text) {
        if (!window.chatContainer) {
            return null;
        }

        const emptyState = window.chatContainer.querySelector(
            ".nova-mobile-empty-state"
        );

        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement("div");
        wrapper.className = "mobile-chat-message " + role;

        const content = document.createElement("div");
        content.className = "mobile-message-content";

        if (role === "assistant") {
            content.innerHTML =
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.renderMarkdown === "function"
                    ? window.NovaMobileBridge.renderMarkdown(text || "")
                    : text || "";
        } else {
            content.textContent = text || "";
        }

        wrapper.appendChild(content);
        window.chatContainer.appendChild(wrapper);

        if (
            role !== "system" &&
            !window.__NOVA_SESSION_RENDERING__ &&
            !window.__NOVA_SUPPRESS_SAVE
        ) {
            setTimeout(function () {
                if (
                    window.NovaMobileBridge &&
                    typeof window.NovaMobileBridge.saveCurrentMessages === "function"
                ) {
                    window.NovaMobileBridge.saveCurrentMessages();
                    return;
                }

                if (typeof window.saveCurrentMessages === "function") {
                    window.saveCurrentMessages();
                }
            }, 0);
        }

        return wrapper;
    }

    function createThinkingBubble(label) {
        const bubble = appendMessage("assistant", "");

        if (!bubble && window.__NOVA_SESSION_RENDERING__) {
            return null;
        }

        if (!bubble) {
            return null;
        }

        bubble.classList.add("mobile-thinking-bubble");

        const content = bubble.querySelector(".mobile-message-content");

        if (content) {
            content.innerHTML = `
                <span class="nova-typing-label">${label || "Nova is thinking"}</span>
                <span class="nova-typing-dots">
                    <span></span><span></span><span></span>
                </span>
            `;
        }

        return bubble;
    }

    function updateThinkingBubble(bubble, text) {
        if (!bubble) {
            return;
        }

        const content = bubble.querySelector(".mobile-message-content");

        bubble.classList.add("mobile-thinking-bubble");

        if (content) {
            content.innerHTML =
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.renderMarkdown === "function"
                    ? window.NovaMobileBridge.renderMarkdown(text || "")
                    : text || "";

            if (
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.enhanceCodeBlocks === "function"
            ) {
                window.NovaMobileBridge.enhanceCodeBlocks(bubble);
            }
        }

        if (
            window.NovaMobileBridge &&
            typeof window.NovaMobileBridge.scrollBottom === "function"
        ) {
            window.NovaMobileBridge.scrollBottom();
        }
    }

    function renderSessionPayload(payload, reason) {
        const detail = payload || {};

        const session =
            detail.session && typeof detail.session === "object"
                ? detail.session
                : detail;

        const sessionId =
            detail.session_id ||
            session.id ||
            session.session_id ||
            "";

        const messages =
            Array.isArray(detail.messages)
                ? detail.messages
                : Array.isArray(session.messages)
                    ? session.messages
                    : [];

        console.log("[CHAT UI DIRECT RESTORE]", {
            reason: reason || "unknown",
            session_id: sessionId,
            messages: messages.length
        });

        const resolvedChatContainer =
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-chat") ||
            document.getElementById("chat-container") ||
            document.getElementById("chatContainer") ||
            document.querySelector("[data-nova-chat-container]") ||
            document.querySelector(".nova-mobile-chat") ||
            document.querySelector(".chat-container") ||
            window.chatContainer;

        if (!resolvedChatContainer || !document.body.contains(resolvedChatContainer)) {
            console.warn("[CHAT UI DIRECT RESTORE] missing visible chatContainer", {
                oldExists: !!window.chatContainer,
                oldConnected: !!window.chatContainer?.isConnected
            });

            return false;
        }

        window.chatContainer = resolvedChatContainer;

        window.__NOVA_SESSION_RENDERING__ = true;
        window.__NOVA_SUPPRESS_SAVE = true;

        window.chatContainer.innerHTML = "";
        window.NOVA_MESSAGES = messages.slice();

        let renderedCount = 0;

        messages.forEach(function (msg, index) {
            try {
                appendMessage(
                    msg.role || "assistant",
                    msg.content ?? msg.text ?? ""
                );

                renderedCount += 1;
            } catch (err) {
                console.error("[CHAT UI DIRECT RESTORE APPEND FAILED]", {
                    index: index,
                    role: msg && msg.role,
                    text: String((msg && (msg.content ?? msg.text)) || "").slice(0, 120),
                    error: err
                });
            }
        });

        console.log("[CHAT UI DIRECT RESTORE DONE]", {
            session_id: sessionId,
            messages: messages.length,
            rendered: renderedCount,
            children: window.chatContainer ? window.chatContainer.children.length : null,
            text: window.chatContainer ? window.chatContainer.textContent.trim().slice(0, 200) : ""
        });

        try {
            if (
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.scrollBottom === "function"
            ) {
                window.NovaMobileBridge.scrollBottom(true);
            }
        } catch (err) {
            console.warn("[CHAT UI DIRECT RESTORE SCROLL FAILED]", err);
        }

        console.log("[CHAT UI DIRECT RESTORE AFTER SCROLL]");

        setTimeout(function () {
            window.__NOVA_SESSION_RENDERING__ = false;
            window.__NOVA_SUPPRESS_SAVE = false;
        }, 250);

        return true;
    }

    window.NovaMobileChatUI = {
        appendMessage: appendMessage,
        createThinkingBubble: createThinkingBubble,
        updateThinkingBubble: updateThinkingBubble,
        renderSessionPayload: renderSessionPayload
    };

    window.NovaMobileRenderSession = function (session, sessionId) {
        return renderSessionPayload(
            {
                session_id: sessionId || session?.id || session?.session_id || "",
                session: session || {},
                messages: Array.isArray(session?.messages) ? session.messages : []
            },
            "direct-call"
        );
    };

    window.addEventListener("nova:session-selected", function (event) {
        console.log("[CHAT UI LISTENER FIRED]", event.detail);
        return renderSessionPayload(event.detail || {}, "event");
    });
})();
