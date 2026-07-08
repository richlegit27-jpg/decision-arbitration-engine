(function () {
    "use strict";

    function notifyMessageCopied() {
        if (typeof showToast === "function") {
            showToast("Copied");
            return;
        }

        console.log("[Nova Mobile] Copied");
    }

    function notifyRegenerating() {
        showToast("Rebuilding answer...");
        vibrate(10);
    }

    function notifySpeaking() {
        showToast("Speaking response...");
        vibrate(10);
    }

    function hasMessageText(text) {
        if (text) return true;

        showToast("No message text to copy.");
        vibrate(20);

        return false;
    }

    function hasLastUserPrompt() {
        if (lastUserPrompt) return true;

        showToast("No prompt to regenerate.");
        vibrate(20);

        return false;
    }

    function hasSpeakableText(text) {
        if (text) return true;

        showToast("No message text to speak.");
        vibrate(20);

        return false;
    }

    function flashButtonState(
        button,
        activeText,
        restoreText
    ) {
        if (!button) return;

        button.textContent = activeText;

        setTimeout(function () {
            button.textContent = restoreText;
        }, 1200);
    }

    function addAssistantActions(wrapper, text) {
        if (!wrapper) return;

        const actions =
            document.createElement("div");

        actions.className =
            "mobile-message-actions";

        const content =
            wrapper.querySelector(
                ".mobile-message-content"
            );

        if (
            content &&
            text &&
            text.length > 1200
        ) {
            content.classList.add(
                "mobile-message-collapsed"
            );

            const collapseBtn =
                document.createElement(
                    "button"
                );

            collapseBtn.type = "button";

            collapseBtn.className =
                "mobile-inline-action";

            collapseBtn.textContent =
                "Expand";

            collapseBtn.addEventListener(
                "click",
                function () {
                    vibrate(8);

                    content.classList.toggle(
                        "mobile-message-collapsed"
                    );

                    collapseBtn.textContent =
                        content.classList.contains(
                            "mobile-message-collapsed"
                        )
                            ? "Expand"
                            : "Collapse";
                }
            );

            actions.appendChild(
                collapseBtn
            );
        }

        const copyBtn =
            document.createElement(
                "button"
            );

        copyBtn.type = "button";
        copyBtn.className =
            "mobile-inline-action";
        copyBtn.textContent = "Copy";

        copyBtn.addEventListener(
            "click",
            function () {
                if (!hasMessageText(text)) {
                    return;
                }

                copyText(text);
                notifyMessageCopied();
                flashButtonState(
                    copyBtn,
                    "Copied",
                    "Copy"
                );
            }
        );

        const regenBtn =
            document.createElement(
                "button"
            );

        regenBtn.type = "button";
        regenBtn.className =
            "mobile-inline-action";
        regenBtn.textContent = "Regen";

        regenBtn.addEventListener(
            "click",
            function () {
                if (!hasLastUserPrompt()) {
                    return;
                }

                notifyRegenerating();

                flashButtonState(
                    regenBtn,
                    "Working",
                    "Regen"
                );

                sendMessage({
                    text: lastUserPrompt,
                    regenerate: true,
                    attachments: []
                });
            }
        );

        actions.appendChild(copyBtn);
        actions.appendChild(regenBtn);

        wrapper.appendChild(actions);
    }

    window.NovaMobileMessageActions = {
        notifyMessageCopied,
        notifyRegenerating,
        notifySpeaking,
        hasMessageText,
        hasLastUserPrompt,
        hasSpeakableText,
        flashButtonState,
        addAssistantActions
    };

})();

// NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630
// Adds stable Copy / Regenerate buttons under mobile chat messages.
// Copy works for any text message.
// Regenerate re-sends the previous user message into the current active session.
(() => {
    "use strict";

    if (window.__NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630__) return;
    window.__NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630__ = true;

    function clean(value) {
        return String(value || "").trim();
    }

    function getChatContainer() {
        return (
            document.querySelector("#mobile-chat-messages") ||
            document.querySelector("#nova-mobile-chat-messages") ||
            document.querySelector("#chat-messages") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("main")
        );
    }

    function isMessageNode(node) {
        if (!node || !node.classList) return false;

        const cls = String(node.className || "").toLowerCase();

        return (
            cls.includes("mobile-chat-message") ||
            cls.includes("chat-message") ||
            cls.includes("message")
        );
    }

    function getRole(node) {
        const cls = String(node?.className || "").toLowerCase();
        const dataRole = clean(node?.dataset?.role || node?.getAttribute?.("data-role") || "").toLowerCase();

        if (dataRole) return dataRole;
        if (cls.includes("user")) return "user";
        if (cls.includes("assistant")) return "assistant";

        return "";
    }

    function getMessageText(node) {
        if (!node) return "";

        const clone = node.cloneNode(true);

        clone.querySelectorAll(
            ".nova-mobile-message-actions," +
            ".nova-mobile-copy-regen-actions," +
            "button," +
            ".nova-mobile-generated-image-card," +
            ".nova-direct-generated-image-card," +
            ".nova-mobile-session-restored-image-card"
        ).forEach((item) => item.remove());

        return clean(clone.textContent || "");
    }

    function normalizeResponseText(text) {
        return clean(text)
            .replace(/^Generated image for:\s*of\s+/i, "Generated image: ")
            .replace(/^Generated image for:\s*/i, "Generated image: ")
            .replace(/^Generated image:\s*of\s+/i, "Generated image: ");
    }

    function getAllMessages() {
        const container = getChatContainer();
        if (!container) return [];

        return Array.from(container.querySelectorAll(
            ".mobile-chat-message, .chat-message, .message, [data-role='user'], [data-role='assistant']"
        )).filter(isMessageNode);
    }

    function previousUserTextFor(node) {
        const messages = getAllMessages();
        const index = messages.indexOf(node);

        for (let i = index - 1; i >= 0; i -= 1) {
            if (getRole(messages[i]) === "user") {
                const text = getMessageText(messages[i]);
                if (text) return text;
            }
        }

        for (let i = messages.length - 1; i >= 0; i -= 1) {
            if (getRole(messages[i]) === "user") {
                const text = getMessageText(messages[i]);
                if (text) return text;
            }
        }

        return "";
    }

    function activeSessionId() {
        return (
            clean(window.NovaMobileActiveSessionId) ||
            clean(window.__novaMobileActiveSessionId) ||
            clean(localStorage.getItem("nova_mobile_active_session_id")) ||
            clean(localStorage.getItem("nova_active_session_id")) ||
            clean(sessionStorage.getItem("nova_mobile_active_session_id")) ||
            ""
        );
    }

    function setActiveSessionId(id) {
        const value = clean(id);
        if (!value) return;

        window.NovaMobileActiveSessionId = value;
        window.__novaMobileActiveSessionId = value;

        localStorage.setItem("nova_mobile_active_session_id", value);
        localStorage.setItem("nova_active_session_id", value);
        sessionStorage.setItem("nova_mobile_active_session_id", value);
    }

    function toast(message, kind) {
        const fn =
            window.NovaMobileToast ||
            window.showToast ||
            window.toast ||
            null;

        if (typeof fn === "function") {
            try {
                fn(message, kind || "info");
                return;
            } catch (_) {}
        }

        console.log("[NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630]", message);
    }

    async function copyText(text) {
        const value = clean(text);
        if (!value) return false;

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(value);
                return true;
            }
        } catch (_) {}

        try {
            const area = document.createElement("textarea");
            area.value = value;
            area.setAttribute("readonly", "readonly");
            area.style.position = "fixed";
            area.style.left = "-9999px";
            area.style.top = "-9999px";

            document.body.appendChild(area);
            area.select();

            const ok = document.execCommand("copy");
            area.remove();

            return ok;
        } catch (_) {
            return false;
        }
    }

    function appendAssistantMessage(text) {
        const container = getChatContainer();
        if (!container) return null;

        const wrapper = document.createElement("div");
        wrapper.className = "mobile-chat-message assistant";
        wrapper.dataset.role = "assistant";

        const body = document.createElement("div");
        body.className = "mobile-chat-message-text";
        body.textContent = normalizeResponseText(text);

        wrapper.appendChild(body);
        container.appendChild(wrapper);

        try {
            container.scrollTop = container.scrollHeight;
        } catch (_) {}

        setTimeout(installActions, 80);

        return wrapper;
    }

    function replaceMessageText(node, text) {
        if (!node) {
            appendAssistantMessage(text);
            return;
        }

        let body =
            node.querySelector(".mobile-chat-message-text") ||
            node.querySelector(".message-text") ||
            node.querySelector(".content");

        if (!body) {
            body = document.createElement("div");
            body.className = "mobile-chat-message-text";
            node.insertBefore(body, node.firstChild);
        }

        body.textContent = normalizeResponseText(text);
        setTimeout(installActions, 80);
    }

    function extractAssistantText(payload) {
        const data = payload && typeof payload === "object" ? payload : {};
        const assistant = data.assistant_message && typeof data.assistant_message === "object"
            ? data.assistant_message
            : {};

        const artifact = data.saved_artifact && typeof data.saved_artifact === "object"
            ? data.saved_artifact
            : {};

        return normalizeResponseText(
            assistant.content ||
            assistant.text ||
            data.content ||
            data.text ||
            artifact.summary ||
            "Regenerated."
        );
    }

    async function regenerateFromMessage(node) {
        const prompt = previousUserTextFor(node);

        if (!prompt) {
            toast("No previous user message to regenerate.", "error");
            return;
        }

        if (/^\s*(generate|create|make|draw|render)\s+image\b/i.test(prompt)) {
            toast("Image regenerate skipped. Use a new image prompt instead.", "info");
            return;
        }

        const sessionId = activeSessionId();

        replaceMessageText(node, "Regenerating...");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: prompt,
                    session_id: sessionId,
                    active_session_id: sessionId,
                    attachments: []
                })
            });

            const payload = await response.json();

            if (payload.session_id || payload.active_session_id || payload.session?.id) {
                setActiveSessionId(payload.session_id || payload.active_session_id || payload.session?.id);
            }

            replaceMessageText(node, extractAssistantText(payload));

            if (typeof window.NovaMobileRestoreSessionMessages === "function") {
                setTimeout(() => window.NovaMobileRestoreSessionMessages(activeSessionId()), 500);
            }

            toast("Regenerated", "success");
        } catch (error) {
            console.warn("[NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630] regenerate failed", error);
            replaceMessageText(node, "Regenerate failed.");
            toast("Regenerate failed", "error");
        }
    }

    function makeButton(label, className, onClick) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = className;
        button.textContent = label;

        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            onClick();
        });

        return button;
    }

    function installActions() {
        const messages = getAllMessages();

        for (const message of messages) {
            if (message.dataset.novaCopyRegenActions === "1") continue;

            const text = getMessageText(message);
            const role = getRole(message);

            if (!text && role !== "assistant") continue;

            const bar = document.createElement("div");
            bar.className = "nova-mobile-copy-regen-actions";

            const copyButton = makeButton("Copy", "nova-mobile-action-btn nova-mobile-copy-btn", async () => {
                const ok = await copyText(getMessageText(message));
                toast(ok ? "Copied" : "Copy failed", ok ? "success" : "error");
            });

            bar.appendChild(copyButton);

            if (role === "assistant") {
                const regenButton = makeButton("Regenerate", "nova-mobile-action-btn nova-mobile-regen-btn", () => {
                    regenerateFromMessage(message);
                });

                bar.appendChild(regenButton);
            }

            message.appendChild(bar);
            message.dataset.novaCopyRegenActions = "1";
        }
    }

    const observer = new MutationObserver(() => {
        installActions();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    setTimeout(installActions, 100);
    setTimeout(installActions, 600);
    setTimeout(installActions, 1500);

    window.NovaMobileInstallCopyRegenerateActions = installActions;

    console.log("[NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630] ready");
})();