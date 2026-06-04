(function () {
    "use strict";

    const chatContainer =
        document.getElementById(
            "mobileChatMessages"
        );

    const inputEl =
        document.getElementById(
            "nova-mobile-input"
        );

    const sendBtn =
        document.getElementById(
            "nova-mobile-send"
        );

    const stopGenerationBtn =
        document.getElementById(
            "nova-mobile-stop-generation"
        );

    const statusDot =
        document.querySelector(
            ".mobile-status"
        );

    window.chatContainer = chatContainer;
    window.inputEl = inputEl;

    function setGeneratingState(state) {
        const isGenerating = !!state;

        document.body.classList.toggle(
            "nova-mobile-thinking",
            isGenerating
        );

        if (sendBtn) {
            sendBtn.disabled =
                isGenerating;
        }

        if (stopGenerationBtn) {
            stopGenerationBtn.disabled = false;

            stopGenerationBtn.textContent =
                "Stop";

            if (isGenerating) {
                stopGenerationBtn.style.display =
                    "flex";

                stopGenerationBtn.classList.add(
                    "is-visible"
                );
            } else {
                stopGenerationBtn.style.display =
                    "none";

                stopGenerationBtn.classList.remove(
                    "is-visible"
                );
            }
        }

        document.body.classList.toggle(
            "mobile-generating",
            isGenerating
        );
    }

    function setConnectionState(state) {
        if (!statusDot) return;

        statusDot.classList.remove(
            "mobile-status-idle",
            "mobile-status-working",
            "mobile-status-error"
        );

        statusDot.classList.add(
            state === "working"
                ? "mobile-status-working"
                : state === "error"
                  ? "mobile-status-error"
                  : "mobile-status-idle"
        );
    }

    function autoGrowInput() {
        if (!inputEl) return;

        inputEl.style.height = "auto";

        inputEl.style.height =
            Math.min(
                inputEl.scrollHeight || 44,
                140
            ) + "px";
    }

    function isNearBottom() {
        if (!chatContainer) return true;

        const distance =
            chatContainer.scrollHeight -
            chatContainer.scrollTop -
            chatContainer.clientHeight;

        return distance < 140;
    }

    function scrollBottom(force) {
        if (!chatContainer) return;

        if (
            !force &&
            !isNearBottom()
        ) {
            return;
        }

        chatContainer.scrollTop =
            chatContainer.scrollHeight;
    }

    function setInputText(text) {
        if (!inputEl) return;

        inputEl.value = text || "";

        inputEl.focus();

        autoGrowInput();

        saveDraft();
    }

    function cleanText(text) {
        return String(text || "")
            .replace(
                /Copy|Regen|Speak/g,
                ""
            )
            .trim();
    }

    function isImageUrl(url) {
        const value =
            String(url || "").toLowerCase();

        if (!value) return false;

        if (
            value.includes(
                "/api/uploads/"
            )
        ) {
            return true;
        }

        return /\.(png|jpg|jpeg|gif|webp|bmp|svg)(\?.*)?$/i.test(
            value
        );
    }

    function extractMarkdownImages(text) {
        const matches = [];

        const regex =
            /!\[([^\]]*)\]\(([^)]+)\)/g;

        let match;

        while (
            (
                match = regex.exec(
                    String(text || "")
                )
            ) !== null
        ) {
            matches.push({
                alt:
                    match[1] || "Image",
                url: match[2] || "",
                full: match[0] || ""
            });
        }

        return matches;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll(
                "'",
                "&#39;"
            );
    }

    function renderMarkdown(text) {
        let html =
            escapeHtml(text || "");

        html = html.replace(
            /```([\s\S]*?)```/g,
            function (_, code) {
                return `<pre class="mobile-code-block"><code>${escapeHtml(
                    code.trim()
                )}</code></pre>`;
            }
        );

        html = html.replace(
            /^### (.*)$/gm,
            "<h3>$1</h3>"
        );

        html = html.replace(
            /^## (.*)$/gm,
            "<h2>$1</h2>"
        );

        html = html.replace(
            /^# (.*)$/gm,
            "<h1>$1</h1>"
        );

        html = html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );

        html = html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );

        html = html.replace(
            /^\- (.*)$/gm,
            '<div class="mobile-bullet">• $1</div>'
        );

        html = html.replace(
            /\n/g,
            "<br>"
        );

        return html;
    }

    function getCurrentSessionMessagesKey() {
        return (
            "novaMobileMessages:" +
            (window.__novaActiveSessionId ||
                "default")
        );
    }

    function saveCurrentMessages() {
        if (!chatContainer) return;

        const messages = Array.from(
            chatContainer.querySelectorAll(
                ".mobile-chat-message"
            )
        )
            .map(function (message) {
                const image =
                    message.querySelector(
                        "img.mobile-chat-image"
                    );

                return {
                    role:
                        message.classList.contains(
                            "user"
                        )
                            ? "user"
                            : message.classList.contains(
                                  "assistant"
                              )
                              ? "assistant"
                              : "system",

                    text: image
                        ? ""
                        : cleanText(
                              message.textContent ||
                                  ""
                          ),

                    image: image
                        ? image.src
                        : ""
                };
            })
            .filter(function (message) {
                return (
                    message.text ||
                    message.image
                );
            });

        localStorage.setItem(
            getCurrentSessionMessagesKey(),
            JSON.stringify(
                messages.slice(-80)
            )
        );
    }

function hapticError() {
    if (
        navigator.vibrate &&
        typeof navigator.vibrate === "function"
    ) {
        navigator.vibrate([30, 50, 30]);
    }
}

    function renderEmptyState() {
        if (!chatContainer) return;

        if (
            chatContainer.querySelector(
                ".nova-mobile-empty-state"
            )
        ) {
            return;
        }

        const empty =
            document.createElement("div");

        empty.className =
            "nova-mobile-empty-state";

        empty.innerHTML = `
            <div class="nova-empty-title">Nova is ready.</div>
            <div class="nova-empty-subtitle">
                Ask, build, search, upload, generate, or command.
            </div>
        `;

        chatContainer.appendChild(
            empty
        );
    }

    function updateParallaxDepth() {
        return;
    }

function hapticTap() {
    if (
        navigator.vibrate &&
        typeof navigator.vibrate === "function"
    ) {
        navigator.vibrate(8);
    }
}

function updateHeaderVisibility() {
    return;
}

window.NovaMobileCore = {
    setGeneratingState,
    setConnectionState,
    autoGrowInput,
    isNearBottom,
    scrollBottom,
    setInputText,
    cleanText,
    isImageUrl,
    extractMarkdownImages,
    escapeHtml,
    renderMarkdown,
    getCurrentSessionMessagesKey,
    saveCurrentMessages,
    renderEmptyState,
    updateParallaxDepth,
    hapticTap,
    updateHeaderVisibility,
    hapticError
};

window.scrollBottom = scrollBottom;
window.renderMarkdown = renderMarkdown;
window.saveCurrentMessages =
    saveCurrentMessages;
window.setInputText = setInputText;
window.hapticTap = hapticTap;
window.hapticError = hapticError;

    console.log(
        "[Nova Mobile] core module ready"
    );

})();