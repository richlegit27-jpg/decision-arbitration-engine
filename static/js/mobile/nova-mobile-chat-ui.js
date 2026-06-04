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

        if (role !== "system") {
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
        const bubble =
            appendMessage("assistant", "");

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

})();