(function () {
    "use strict";

    function appendMessage(role, text) {
        if (!window.chatContainer) return null;

        const emptyState =
            window.chatContainer.querySelector(
                ".nova-mobile-empty-state"
            );

        if (emptyState) {
            emptyState.remove();
        }

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "mobile-chat-message " + role;

        const content =
            document.createElement("div");

        content.className =
            "mobile-message-content";

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
            window.NovaMobileBridge &&
            typeof window.NovaMobileBridge.scrollBottom === "function"
        ) {
            window.NovaMobileBridge.scrollBottom();
        }

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

                if (
                    typeof window.saveCurrentMessages === "function"
                ) {
                    window.saveCurrentMessages();
                }
            }, 0);
        }

        return wrapper;
    }

    function createThinkingBubble(label) {
let bubble = appendMessage("assistant", "");

if (!bubble && window.__NOVA_SESSION_RENDERING__) {
    return null;
}


        if (!bubble) return null;

        bubble.classList.add(
            "mobile-thinking-bubble"
        );

        const content =
            bubble.querySelector(
                ".mobile-message-content"
            );

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
        if (!bubble) return;

        const content =
            bubble.querySelector(
                ".mobile-message-content"
            );

        bubble.classList.add(
            "mobile-thinking-bubble"
        );

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
                window.NovaMobileBridge.enhanceCodeBlocks(
                    bubble
                );
            }
        }

        if (
            window.NovaMobileBridge &&
            typeof window.NovaMobileBridge.scrollBottom === "function"
        ) {
            window.NovaMobileBridge.scrollBottom();
        }
    }

    window.NovaMobileChatUI = {
        appendMessage,
        createThinkingBubble,
        updateThinkingBubble
    };

window.addEventListener("nova:session-selected", function (event) {
    const sessionId = event.detail?.session_id;
    const session = event.detail?.session || event.detail;

    console.log("[CHAT UI RESTORE DEBUG]", event.detail, session);

    if (!sessionId) return;

    window.__NOVA_SESSION_RENDERING__ = true;

    if (window.chatContainer) {
        window.chatContainer.innerHTML = "";
    }

    window.NOVA_MESSAGES = [];

    const messages =
        session?.messages ||
        event.detail?.messages ||
        [];

    console.log("[CHAT UI MESSAGES]", messages.length, messages);

    window.NOVA_MESSAGES = messages;

    if (Array.isArray(messages)) {
        messages.forEach(msg => {
            appendMessage(
                msg.role,
                msg.content ?? msg.text ?? ""
            );
        });
    }

    setTimeout(() => {
        window.__NOVA_SESSION_RENDERING__ = false;
    }, 0);
});

})();

