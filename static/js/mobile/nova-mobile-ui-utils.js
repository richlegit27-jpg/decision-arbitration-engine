(function () {
    "use strict";

    function byId(id) {
        return document.getElementById(id);
    }

    function cleanText(value) {
        if (window.NovaMobileBridge && typeof window.NovaMobileBridge.cleanText === "function") {
            return window.NovaMobileBridge.cleanText(value);
        }

        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function showToast(message) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        console.log("[Nova Mobile Toast]", message);
    }

    function hapticSuccess() {
        if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
            navigator.vibrate(20);
        }
    }

    async function copyText(text) {
        const value = String(text || "").trim();

        if (!value) {
            showToast("Nothing to copy.");
            return false;
        }

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(value);
                showToast("Copied.");
                hapticSuccess();
                return true;
            }
        } catch (error) {
            console.warn("[Nova Mobile] clipboard failed", error);
        }

        const area = document.createElement("textarea");
        area.value = value;
        area.setAttribute("readonly", "readonly");
        area.style.position = "fixed";
        area.style.left = "-9999px";

        document.body.appendChild(area);
        area.select();

        let copied = false;

        try {
            copied = document.execCommand("copy");
        } catch (error) {
            copied = false;
        }

        area.remove();

        if (copied) {
            showToast("Copied.");
            hapticSuccess();
            return true;
        }

        showToast("Copy failed.");
        return false;
    }

    function setInputText(value) {
        const input =
            byId("mobileMessageInput") ||
            byId("messageInput") ||
            byId("composer-input") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']");

        if (!input) {
            showToast("Input not found.");
            return;
        }

        input.value = String(value || "");
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();
    }

    function togglePanel(panel) {
        if (!panel) {
            return;
        }

        panel.classList.toggle("hidden");
        panel.classList.toggle("open");
        panel.classList.toggle("is-open");

        const isOpen =
            panel.classList.contains("open") ||
            panel.classList.contains("is-open") ||
            !panel.classList.contains("hidden");

        panel.setAttribute("aria-hidden", isOpen ? "false" : "true");
    }

    function closePanel(panel) {
        if (!panel) {
            return;
        }

        panel.classList.add("hidden");
        panel.classList.remove("open");
        panel.classList.remove("is-open");
        panel.setAttribute("aria-hidden", "true");
    }

    function closeAllPanels() {
        const panels = [
            byId("memoryPanel"),
            byId("sessionsPanel"),
            byId("toolsPanel"),
            byId("mobileMemoryPanel"),
            byId("mobileSessionsPanel"),
            byId("mobileToolsPanel"),
            byId("executionPanel"),
            byId("mobileExecutionPanel"),
            document.querySelector("[data-mobile-memory-panel]"),
            document.querySelector("[data-mobile-sessions-panel]"),
            document.querySelector("[data-mobile-tools-panel]"),
            document.querySelector("[data-mobile-execution-panel]")
        ];

        panels.forEach(function (panel) {
            closePanel(panel);
        });
    }

    function getPanelByName(name) {
        const normalized = String(name || "").trim().toLowerCase();

        if (normalized === "memory") {
            return (
                byId("memoryPanel") ||
                byId("mobileMemoryPanel") ||
                document.querySelector("[data-mobile-memory-panel]")
            );
        }

        if (normalized === "sessions") {
            return (
                byId("sessionsPanel") ||
                byId("mobileSessionsPanel") ||
                document.querySelector("[data-mobile-sessions-panel]")
            );
        }

        if (normalized === "tools") {
            return (
                byId("toolsPanel") ||
                byId("mobileToolsPanel") ||
                document.querySelector("[data-mobile-tools-panel]")
            );
        }

        if (normalized === "execution") {
            return (
                byId("executionPanel") ||
                byId("mobileExecutionPanel") ||
                document.querySelector("[data-mobile-execution-panel]")
            );
        }

        return null;
    }

    function runTool(tool) {
        switch (String(tool || "").trim().toLowerCase()) {
            case "web":
                setInputText("Search the web for ");
                return;

            case "image":
                setInputText("/image ");
                return;

            case "upload":
            case "attach":
                if (
                    window.NovaMobileUpload &&
                    typeof window.NovaMobileUpload.openUploadPicker === "function"
                ) {
                    window.NovaMobileUpload.openUploadPicker();
                    return;
                }

                const fileInput =
                    byId("mobileFileInput") ||
                    byId("fileUploadInput") ||
                    byId("file-upload-input") ||
                    document.querySelector("input[type='file']");

                if (fileInput) {
                    fileInput.click();
                    return;
                }

                showToast("Upload picker not found.");
                return;

            case "voice":
                if (
                    window.NovaMobileVoice &&
                    typeof window.NovaMobileVoice.startVoiceInput === "function"
                ) {
                    window.NovaMobileVoice.startVoiceInput();
                    return;
                }

                if (
                    window.NovaMobileVoice &&
                    typeof window.NovaMobileVoice.toggleVoice === "function"
                ) {
                    window.NovaMobileVoice.toggleVoice();
                    return;
                }

                showToast("Voice not ready.");
                return;

            case "memory":
                togglePanel(getPanelByName("memory"));
                return;

            case "sessions":
                togglePanel(getPanelByName("sessions"));
                return;

            case "tools":
                togglePanel(getPanelByName("tools"));
                return;

            case "execution":
                togglePanel(getPanelByName("execution"));
                return;

            default:
                showToast("Tool not found.");
        }
    }

    function getChatContainer() {
        return (
            byId("mobileChatMessages") ||
            byId("messagesContainer") ||
            byId("messages-container") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages")
        );
    }

    function getChatTranscript() {
        const chatContainer = getChatContainer();

        const messages = chatContainer
            ? Array.from(
                  chatContainer.querySelectorAll(
                      ".mobile-chat-message, .mobile-message, [data-message-role]"
                  )
              )
            : [];

        return messages
            .map(function (message) {
                return cleanText(message.textContent || "");
            })
            .filter(Boolean)
            .join("\n\n");
    }

    function copyWholeChat() {
        copyText(getChatTranscript() || "No chat messages.");
    }

    function exportWholeChat() {
        const transcript = getChatTranscript() || "No chat messages.";

        const blob = new Blob([transcript], {
            type: "text/plain"
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "nova-chat-" + Date.now() + ".txt";

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        showToast("Chat exported.");
        hapticSuccess();
    }

    function installCopyButton(button, getText) {
        if (!button || button.dataset.novaCopyWired === "1") {
            return;
        }

        button.dataset.novaCopyWired = "1";

        button.addEventListener("click", function () {
            const text =
                typeof getText === "function"
                    ? getText(button)
                    : "";

            copyText(text);
        });
    }

    function installMessageActionButtons(messageNode) {
        if (!messageNode || messageNode.dataset.novaUiActionsWired === "1") {
            return;
        }

        messageNode.dataset.novaUiActionsWired = "1";

        const copyButton =
            messageNode.querySelector("[data-copy-message]") ||
            messageNode.querySelector(".js-copy-message") ||
            messageNode.querySelector(".nova-copy-message");

        if (copyButton) {
            installCopyButton(copyButton, function () {
                const clone = messageNode.cloneNode(true);
                clone.querySelectorAll("button").forEach(function (button) {
                    button.remove();
                });

                return cleanText(clone.textContent || "");
            });
        }

        const regenButton =
            messageNode.querySelector("[data-regenerate-message]") ||
            messageNode.querySelector(".js-regenerate-message") ||
            messageNode.querySelector(".nova-regenerate-message");

        if (regenButton && regenButton.dataset.novaRegenWired !== "1") {
            regenButton.dataset.novaRegenWired = "1";

            regenButton.addEventListener("click", function () {
                window.dispatchEvent(
                    new CustomEvent("nova-mobile-regenerate-message", {
                        detail: {
                            messageNode: messageNode
                        }
                    })
                );
            });
        }
    }

    function wireExistingMessageActions() {
        const chatContainer = getChatContainer();

        if (!chatContainer) {
            return;
        }

        chatContainer
            .querySelectorAll(".mobile-chat-message, .mobile-message, [data-message-role]")
            .forEach(function (messageNode) {
                installMessageActionButtons(messageNode);
            });
    }

    function observeMessageActions() {
        const chatContainer = getChatContainer();

        if (!chatContainer || chatContainer.dataset.novaUiObserverWired === "1") {
            return;
        }

        chatContainer.dataset.novaUiObserverWired = "1";

        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
                        return;
                    }

                    if (
                        node.matches &&
                        node.matches(".mobile-chat-message, .mobile-message, [data-message-role]")
                    ) {
                        installMessageActionButtons(node);
                    }

                    if (node.querySelectorAll) {
                        node
                            .querySelectorAll(".mobile-chat-message, .mobile-message, [data-message-role]")
                            .forEach(function (messageNode) {
                                installMessageActionButtons(messageNode);
                            });
                    }
                });
            });
        });

        observer.observe(chatContainer, {
            childList: true,
            subtree: true
        });
    }

    function bootUiUtils() {
        wireExistingMessageActions();
        observeMessageActions();

        console.log("[Nova Mobile] ui utils module ready");
    }

    window.NovaMobileUiUtils = {
        togglePanel,
        closePanel,
        closeAllPanels,
        runTool,
        getChatTranscript,
        copyWholeChat,
        exportWholeChat,
        copyText,
        setInputText,
        installMessageActionButtons,
        wireExistingMessageActions,
        observeMessageActions
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootUiUtils);
    } else {
        bootUiUtils();
    }
})();


// MOBILE_QUICK_BUTTON_LISTENER_RESTORE_LOCK
(function () {
    "use strict";

    function getComposerInput() {
        return (
            document.querySelector("[data-mobile-input]") ||
            document.querySelector("#mobileInput") ||
            document.querySelector("#chatInput") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']")
        );
    }

    function setComposerText(value) {
        const input = getComposerInput();

        if (!input) {
            return false;
        }

        input.value = value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.focus();

        return true;
    }

    function clickSend() {
        const sendButton = (
            document.querySelector("[data-mobile-send]") ||
            document.querySelector("#mobileSend") ||
            document.querySelector("#sendButton") ||
            document.querySelector("button[type='submit']")
        );

        if (sendButton) {
            sendButton.click();
            return true;
        }

        const form = getComposerInput()?.closest("form");

        if (form) {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            return true;
        }

        return false;
    }

    document.addEventListener("click", function (event) {
        const button = event.target.closest("[data-quick-prompt]");

        if (!button) {
            return;
        }

        event.preventDefault();

        const action = String(button.getAttribute("data-quick-prompt") || "").trim().toLowerCase();

        const prompts = {
            continue: "continue",
            summarize: "summarize this",
            improve: "improve this",
            next: "next"
        };

        const prompt = prompts[action] || action;

        if (!prompt) {
            return;
        }

        if (setComposerText(prompt)) {
            clickSend();
        }
    });
})();

