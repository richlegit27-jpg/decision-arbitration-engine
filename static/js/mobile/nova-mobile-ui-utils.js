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

/* NOVA_MOBILE_UI_UTILS_OWNS_RUNTIME_UI_BLOCKS_20260608 */
/* NOVA_MOBILE_COMPOSER_AUTORE_SIZE_JS_20260607 */
(function () {
    "use strict";

    var inputEl = document.getElementById("nova-mobile-input") || document.querySelector(".nova-mobile-input");

    if (!inputEl) return;

    function autoResizeInput() {
        inputEl.style.height = "36px";
        inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + "px";
    }

    inputEl.addEventListener("input", autoResizeInput, false);
    inputEl.addEventListener("focus", autoResizeInput, false);
    inputEl.addEventListener("blur", autoResizeInput, false);

    window.NovaMobileAutoResizeComposer = autoResizeInput;

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(autoResizeInput, 0);
    });

    console.log("[Nova Mobile] composer auto-resize ready");
})();


/* NOVA_MOBILE_SEND_BUTTON_STATE_LOCK_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileSendButtonStateInstalled) {
        return;
    }

    window.NovaMobileSendButtonStateInstalled = true;

    function safeJson(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            return fallback;
        }
    }

    function getInput() {
        return document.getElementById("nova-mobile-input") ||
            document.querySelector(".nova-mobile-input") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']");
    }

    function getSendButton() {
        return document.getElementById("nova-mobile-send") ||
            document.getElementById("mobileSendBtn") ||
            document.querySelector("[data-mobile-send]") ||
            document.querySelector(".nova-mobile-send") ||
            document.querySelector(".send-button");
    }

    function getPendingAttachmentCount() {
        if (window.NovaMobileState && Array.isArray(window.NovaMobileState.pendingAttachments)) {
            return window.NovaMobileState.pendingAttachments.length;
        }

        var stored = safeJson(localStorage.getItem("nova_mobile_pending_attachments"), []);
        return Array.isArray(stored) ? stored.length : 0;
    }

    function updateSendButtonState() {
        var input = getInput();
        var send = getSendButton();

        if (!send) {
            return;
        }

        var text = input ? String(input.value || "").trim() : "";
        var hasAttachments = getPendingAttachmentCount() > 0;
        var canSend = Boolean(text || hasAttachments);

        send.disabled = !canSend;
        send.classList.toggle("nova-mobile-send-disabled", !canSend);
        send.setAttribute("aria-disabled", canSend ? "false" : "true");
    }

    function bind() {
        var input = getInput();

        if (input && input.getAttribute("data-send-state-bound") !== "true") {
            input.setAttribute("data-send-state-bound", "true");
            input.addEventListener("input", updateSendButtonState);
            input.addEventListener("keyup", updateSendButtonState);
            input.addEventListener("change", updateSendButtonState);
        }

        updateSendButtonState();
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(bind, 0);
        setTimeout(bind, 250);
    });

    window.addEventListener("nova-mobile-upload-complete", updateSendButtonState);
    window.addEventListener("nova-mobile-attachments-changed", updateSendButtonState);
    window.addEventListener("nova-mobile-attachments-cleared", updateSendButtonState);

    document.addEventListener("click", function () {
        setTimeout(updateSendButtonState, 0);
    }, true);

    window.NovaMobileUpdateSendButtonState = updateSendButtonState;

    console.log("[Nova Mobile] send button state lock ready");
})();


/* NOVA_MOBILE_WHITE_BLOB_CLEANUP_JS_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileWhiteBlobCleanupInstalled) {
        return;
    }

    window.NovaMobileWhiteBlobCleanupInstalled = true;

    function looksLikeGiantBlankMedia(node) {
        if (!node || !node.getBoundingClientRect) {
            return false;
        }

        var rect = node.getBoundingClientRect();
        var tag = String(node.tagName || "").toLowerCase();

        if (!["img", "video", "canvas", "iframe"].includes(tag)) {
            return false;
        }

        if (rect.width > window.innerWidth * 0.95 || rect.height > 420) {
            return true;
        }

        return false;
    }

    function cleanupWhiteBlobs() {
        document.querySelectorAll("img, video, canvas, iframe").forEach(function (node) {
            if (!looksLikeGiantBlankMedia(node)) {
                return;
            }

            node.style.maxWidth = "320px";
            node.style.maxHeight = "240px";
            node.style.width = "auto";
            node.style.height = "auto";
            node.style.objectFit = "contain";
            node.style.borderRadius = "12px";
            node.style.overflow = "hidden";
        });

        document.querySelectorAll("[class*='blob'], [class*='glow'], [class*='orb'], [class*='splash']").forEach(function (node) {
            if (!node || !node.getBoundingClientRect) {
                return;
            }

            var rect = node.getBoundingClientRect();

            if (rect.width > window.innerWidth * 1.2 || rect.height > window.innerHeight * 1.2) {
                node.style.maxWidth = "100vw";
                node.style.maxHeight = "100vh";
                node.style.overflow = "hidden";
                node.style.pointerEvents = "none";
                node.style.zIndex = "0";
            }
        });
    }

    var observer = new MutationObserver(function () {
        window.requestAnimationFrame(cleanupWhiteBlobs);
    });

    document.addEventListener("DOMContentLoaded", function () {
        cleanupWhiteBlobs();

        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["style", "class", "src"]
            });
        }

        setInterval(cleanupWhiteBlobs, 1200);
    });

    window.NovaMobileCleanupWhiteBlobs = cleanupWhiteBlobs;

    console.log("[Nova Mobile UI] white blob cleanup ready");
})();


/* NOVA_MOBILE_RUNTIME_INPUT_HEIGHT_LOCK_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileRuntimeInputHeightLockInstalled) {
        return;
    }

    window.NovaMobileRuntimeInputHeightLockInstalled = true;

    function lockInputHeight() {
        var inputs = Array.from(document.querySelectorAll(
            "#mobileInput, " +
            "#mobileMessageInput, " +
            "#nova-mobile-input, " +
            "textarea#nova-mobile-input, " +
            "input#nova-mobile-input, " +
            ".mobile-composer textarea, " +
            ".mobile-composer input, " +
            ".nova-mobile-composer textarea, " +
            ".nova-mobile-composer input, " +
            ".composer textarea, " +
            ".composer input, " +
            ".chat-composer textarea, " +
            ".chat-composer input, " +
            "textarea[placeholder], " +
            "input[placeholder], " +
            "[contenteditable='true']"
        ));

        inputs.forEach(function (el) {
            el.style.setProperty("min-height", "44px", "important");
            el.style.setProperty("height", "44px", "important");
            el.style.setProperty("max-height", "110px", "important");
            el.style.setProperty("padding", "10px 14px", "important");
            el.style.setProperty("line-height", "1.35", "important");
            el.style.setProperty("font-size", "16px", "important");
            el.style.setProperty("border-radius", "16px", "important");
            el.style.setProperty("box-sizing", "border-box", "important");
            el.style.setProperty("resize", "none", "important");
        });

        var rows = Array.from(document.querySelectorAll(
            ".mobile-composer-inner, " +
            ".nova-mobile-composer-inner, " +
            ".composer-row, " +
            ".mobile-composer-actions, " +
            ".mobile-composer-buttons, " +
            "#nova-mobile-composer, " +
            ".mobile-composer, " +
            ".nova-mobile-composer, " +
            ".composer, " +
            ".chat-composer"
        ));

        rows.forEach(function (el) {
            el.style.setProperty("min-height", "54px", "important");
        });

        var buttons = Array.from(document.querySelectorAll(
            ".mobile-composer-btn, " +
            ".mobile-composer button, " +
            ".nova-mobile-composer button, " +
            "#nova-mobile-composer button, " +
            ".composer button, " +
            ".chat-composer button"
        ));

        buttons.forEach(function (button) {
            button.style.setProperty("width", "42px", "important");
            button.style.setProperty("min-width", "42px", "important");
            button.style.setProperty("max-width", "42px", "important");
            button.style.setProperty("height", "42px", "important");
            button.style.setProperty("min-height", "42px", "important");
            button.style.setProperty("max-height", "42px", "important");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(lockInputHeight, 0);
        setTimeout(lockInputHeight, 250);
        setTimeout(lockInputHeight, 750);
    });

    document.addEventListener("input", function () {
        setTimeout(lockInputHeight, 0);
    }, true);

    window.addEventListener("resize", function () {
        setTimeout(lockInputHeight, 0);
    });

    window.NovaMobileLockInputHeight = lockInputHeight;

    console.log("[Nova Mobile] runtime input height lock ready");
})();


/* NOVA_MOBILE_RUNTIME_ICON_REPAIR_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileRuntimeIconRepairInstalled) {
        return;
    }

    window.NovaMobileRuntimeIconRepairInstalled = true;

    function setButtonIcon(id, html, label) {
        var button = document.getElementById(id);
        if (!button) {
            return;
        }

        button.innerHTML = html;
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
    }

    function repairIcons() {
        setButtonIcon("nova-mobile-send", "&#10148;", "Send");
        setButtonIcon("nova-mobile-voice", "&#127908;", "Voice");
        setButtonIcon("nova-mobile-tts", "&#128266;", "Speak");
        setButtonIcon("nova-mobile-attach", "&#65291;", "Attach");
        setButtonIcon("nova-mobile-tools-toggle", "&#8943;", "Tools");

        var stopGeneration = document.getElementById("nova-mobile-stop-generation");
        if (stopGeneration) {
            stopGeneration.textContent = "Stop";
            stopGeneration.setAttribute("aria-label", "Stop generation");
            stopGeneration.setAttribute("title", "Stop generation");
        }

        var stopSpeech = document.getElementById("nova-mobile-stop-speech");
        if (stopSpeech) {
            stopSpeech.textContent = "Stop";
            stopSpeech.setAttribute("aria-label", "Stop speech");
            stopSpeech.setAttribute("title", "Stop speech");
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(repairIcons, 0);
        setTimeout(repairIcons, 250);
        setTimeout(repairIcons, 750);
    });

    window.addEventListener("load", function () {
        setTimeout(repairIcons, 0);
    });

    window.NovaMobileRepairIcons = repairIcons;

    console.log("[Nova Mobile] runtime icon repair ready");
})();


/* NOVA_MOBILE_COMPACT_INPUT_FINAL_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileCompactInputFinalInstalled) {
        return;
    }

    window.NovaMobileCompactInputFinalInstalled = true;

    function compactInputFinal() {
        var input = document.getElementById("nova-mobile-input");

        if (input) {
            input.style.setProperty("height", "40px", "important");
            input.style.setProperty("min-height", "40px", "important");
            input.style.setProperty("max-height", "90px", "important");
            input.style.setProperty("padding", "8px 12px", "important");
            input.style.setProperty("line-height", "1.25", "important");
            input.style.setProperty("font-size", "16px", "important");
            input.style.setProperty("border-radius", "14px", "important");
            input.style.setProperty("box-sizing", "border-box", "important");
            input.style.setProperty("resize", "none", "important");
            input.style.setProperty("overflow-y", "auto", "important");
        }

        [
            "nova-mobile-send",
            "nova-mobile-stop-generation",
            "nova-mobile-voice",
            "nova-mobile-stop-speech",
            "nova-mobile-tts",
            "nova-mobile-attach",
            "nova-mobile-tools-toggle"
        ].forEach(function (id) {
            var button = document.getElementById(id);
            if (!button) {
                return;
            }

            button.style.setProperty("width", "40px", "important");
            button.style.setProperty("min-width", "40px", "important");
            button.style.setProperty("max-width", "40px", "important");
            button.style.setProperty("height", "40px", "important");
            button.style.setProperty("min-height", "40px", "important");
            button.style.setProperty("max-height", "40px", "important");
            button.style.setProperty("flex", "0 0 40px", "important");
            button.style.setProperty("padding", "0", "important");
        });

        Array.from(document.querySelectorAll(
            ".mobile-composer-inner, .nova-mobile-composer-inner, .composer-row, .mobile-composer-actions, .mobile-composer-buttons"
        )).forEach(function (row) {
            row.style.setProperty("height", "48px", "important");
            row.style.setProperty("min-height", "48px", "important");
            row.style.setProperty("max-height", "48px", "important");
            row.style.setProperty("align-items", "center", "important");
        });

        Array.from(document.querySelectorAll(
            "#nova-mobile-composer, .mobile-composer, .nova-mobile-composer, .chat-composer, .composer"
        )).forEach(function (bar) {
            bar.style.setProperty("min-height", "52px", "important");
            bar.style.setProperty("max-height", "64px", "important");
            bar.style.setProperty("padding-top", "4px", "important");
            bar.style.setProperty("padding-bottom", "4px", "important");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(compactInputFinal, 0);
        setTimeout(compactInputFinal, 250);
        setTimeout(compactInputFinal, 750);
        setTimeout(compactInputFinal, 1500);
    });

    document.addEventListener("input", function () {
        setTimeout(compactInputFinal, 0);
        setTimeout(compactInputFinal, 50);
    }, true);

    window.addEventListener("resize", function () {
        setTimeout(compactInputFinal, 0);
    });

    setInterval(compactInputFinal, 1000);

    window.NovaMobileCompactInputFinal = compactInputFinal;

    console.log("[Nova Mobile] compact input final ready");
})();

