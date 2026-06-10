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

    function autoResizeInput() { if (window.__NOVA_FINAL_COMPOSER_LAYOUT_ACTIVE_20260609) { return; }
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

    function lockInputHeight() { if (window.__NOVA_FINAL_COMPOSER_LAYOUT_ACTIVE_20260609) { return; }
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

    function compactInputFinal() { if (window.__NOVA_FINAL_COMPOSER_LAYOUT_ACTIVE_20260609) { return; }
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

    // NOVA_STOP_MESSAGE_BAR_FIGHTING_LOOPS_20260609: disabled compactInputFinal interval

    window.NovaMobileCompactInputFinal = compactInputFinal;

    console.log("[Nova Mobile] compact input final ready");
})();

/* NOVA_MOBILE_UI_UTILS_OWNS_MEDIA_SANITIZER_20260608 */
/* NOVA_MOBILE_UI_MEDIA_SANITIZER_20260607 */
(function () {
    "use strict";

    function sanitizeOversizedMedia() {
        document.querySelectorAll("img, video, iframe").forEach(function (node) {
            var rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;

            if (!rect) {
                return;
            }

            if (rect.width > window.innerWidth * 0.96 || rect.height > 420) {
                node.style.maxWidth = "340px";
                node.style.maxHeight = "280px";
                node.style.objectFit = "contain";
                node.style.borderRadius = "14px";
                node.style.overflow = "hidden";
            }
        });
    }

    var observer = new MutationObserver(function () {
        sanitizeOversizedMedia();
    });

    document.addEventListener("DOMContentLoaded", function () {
        sanitizeOversizedMedia();

        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    });

    window.NovaMobileSanitizeOversizedMedia = sanitizeOversizedMedia;

    console.log("[Nova Mobile UI] media sanitizer ready");
})();


// NOVA_MOBILE_GLOBAL_UTILS_FALLBACK_20260608
(function () {
    "use strict";

    if (typeof window.showToast !== "function") {
        window.showToast = function (message, type) {
            var text = String(message || "").trim();
            var kind = String(type || "info").trim();

            if (!text) return;

            try {
                console.log("[Nova Toast][" + kind + "]", text);
            } catch (error) {
                // no-op
            }

            var existing = document.getElementById("nova-mobile-toast-fallback");
            if (existing) {
                existing.remove();
            }

            var toast = document.createElement("div");
            toast.id = "nova-mobile-toast-fallback";
            toast.textContent = text;
            toast.style.position = "fixed";
            toast.style.left = "50%";
            toast.style.bottom = "88px";
            toast.style.transform = "translateX(-50%)";
            toast.style.zIndex = "999999";
            toast.style.maxWidth = "86vw";
            toast.style.padding = "10px 14px";
            toast.style.borderRadius = "999px";
            toast.style.background = "rgba(20, 20, 28, 0.94)";
            toast.style.color = "#fff";
            toast.style.fontSize = "13px";
            toast.style.lineHeight = "1.3";
            toast.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.28)";
            toast.style.pointerEvents = "none";

            document.body.appendChild(toast);

            window.setTimeout(function () {
                if (toast && toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 2200);
        };
    }

    if (typeof window.copyText !== "function") {
        window.copyText = async function (text) {
            var value = String(text || "");

            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(value);
                    window.showToast("Copied.", "success");
                    return true;
                }
            } catch (error) {
                // fall through to textarea fallback
            }

            try {
                var textarea = document.createElement("textarea");
                textarea.value = value;
                textarea.setAttribute("readonly", "readonly");
                textarea.style.position = "fixed";
                textarea.style.left = "-9999px";
                textarea.style.top = "-9999px";

                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                document.body.removeChild(textarea);

                window.showToast("Copied.", "success");
                return true;
            } catch (error) {
                window.showToast("Copy failed.", "error");
                return false;
            }
        };
    }

    console.log("[Nova Mobile] global utility fallbacks ready");
})();


// NOVA_MOBILE_BUBBLE_ACTIONS_OBSERVER_20260609
(function () {
    "use strict";

    function getChatRoot() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.querySelector(".mobile-chat-container") ||
            document.querySelector("#nova-mobile-messages") ||
            document.querySelector(".nova-mobile-messages")
        );
    }

    function cleanBubbleText(node) {
        if (!node) return "";

        var clone = node.cloneNode(true);

        clone.querySelectorAll(
            ".nova-mobile-message-actions, .mobile-message-actions, button, script, style"
        ).forEach(function (el) {
            el.remove();
        });

        return String(clone.textContent || "").trim();
    }

    function isWebCard(node) {
        if (!node || !node.classList) return false;

        var cls = String(node.className || "").toLowerCase();

        return (
            cls.indexOf("web-card") !== -1 ||
            cls.indexOf("webcard") !== -1 ||
            cls.indexOf("source-card") !== -1 ||
            cls.indexOf("artifact-card") !== -1 ||
            cls.indexOf("mobile-web-card") !== -1 ||
            cls.indexOf("mobile-web-card-title-wrap") !== -1 ||
            node.closest(".mobile-web-card") ||
            node.closest(".nova-web-card") ||
            node.closest(".web-card") ||
            node.closest(".source-card") ||
            node.closest(".artifact-card")
        );
    }

    function looksLikeBubble(node) {
        if (!node || node.nodeType !== 1) return false;

        var root = getChatRoot();
        if (!root || !root.contains(node)) return false;

        if (node === root) return false;
        if (isWebCard(node)) return false;
        if (node.querySelector(".nova-mobile-message-actions")) return false;

        var text = cleanBubbleText(node);
        if (!text || text.length < 2) return false;

        var cls = String(node.className || "").toLowerCase();

        if (
            cls.indexOf("message") !== -1 ||
            cls.indexOf("bubble") !== -1 ||
            cls.indexOf("assistant") !== -1 ||
            cls.indexOf("user") !== -1 ||
            cls.indexOf("chat-row") !== -1
        ) {
            return true;
        }

        var rect = node.getBoundingClientRect();

        return (
            rect.width > 120 &&
            rect.height >= 20 &&
            rect.height < 900 &&
            node.children.length < 12 &&
            !node.querySelector("input, textarea, select")
        );
    }

    function copyTextSafe(text) {
        if (typeof window.copyText === "function") {
            window.copyText(text);
            return;
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(function () {});
        }
    }

    function getLastUserPrompt() {
        try {
            var root = getChatRoot();
            if (!root) return "";

            var nodes = Array.from(root.children);
            for (var i = nodes.length - 1; i >= 0; i -= 1) {
                var node = nodes[i];
                var cls = String(node.className || "").toLowerCase();
                var text = cleanBubbleText(node);

                if (text && (cls.indexOf("user") !== -1 || text.charAt(0) === "/")) {
                    return text;
                }
            }
        } catch (error) {
            // no-op
        }

        return "";
    }

    function triggerRegenerate() {
        var prompt = getLastUserPrompt();

        if (typeof window.showToast === "function") {
            window.showToast("Regenerating...", "info");
        }

        if (typeof window.NovaMobileSendText === "function" && prompt) {
            window.NovaMobileSendText(prompt);
            return;
        }

        var input =
            document.getElementById("nova-mobile-input") ||
            document.getElementById("mobileInput") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']");

        if (input && prompt) {
            input.value = prompt;
            input.dispatchEvent(new Event("input", { bubbles: true }));

            var send =
                document.getElementById("nova-mobile-send") ||
                document.getElementById("mobileSend") ||
                document.querySelector("[data-action='send']") ||
                document.querySelector("button[type='submit']");

            if (send) {
                send.click();
            }
        }
    }

    function attachActions(node) {
        if (!looksLikeBubble(node)) return;

        node.setAttribute("data-nova-bubble-actions", "1");

        var row = document.createElement("div");
        row.className = "nova-mobile-message-actions";

        var copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "nova-mobile-copy-message";
        copyButton.textContent = "Copy";
        copyButton.setAttribute("aria-label", "Copy message");

        copyButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            var text = cleanBubbleText(node);
            copyTextSafe(text);

            if (typeof window.showToast === "function") {
                window.showToast("Copied.", "success");
            }
        });

        var regenButton = document.createElement("button");
        regenButton.type = "button";
        regenButton.className = "nova-mobile-regenerate-message";
        regenButton.textContent = "Regen";
        regenButton.setAttribute("aria-label", "Regenerate response");

        regenButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            triggerRegenerate();
        });

        row.appendChild(copyButton);
        row.appendChild(regenButton);
        node.appendChild(row);
    }

    function scanBubbleActions() {
        var root = getChatRoot();
        if (!root) return;

        Array.from(root.children).forEach(function (node) {
            attachActions(node);
        });

        Array.from(
            root.querySelectorAll(
                ".mobile-message, .nova-mobile-message, .message, .chat-message, .assistant-message, .user-message, [class*='message-bubble']"
            )
        ).forEach(function (node) {
            attachActions(node);
        });
    }

    function startObserver() {
        var root = getChatRoot();
        if (!root) return;

        scanBubbleActions();

        if (window.__novaMobileBubbleActionsObserver) {
            window.__novaMobileBubbleActionsObserver.disconnect();
        }

        window.__novaMobileBubbleActionsObserver = new MutationObserver(function () {
            window.clearTimeout(window.__novaMobileBubbleActionsTimer);
            window.__novaMobileBubbleActionsTimer = window.setTimeout(scanBubbleActions, 80);
        });

        window.__novaMobileBubbleActionsObserver.observe(root, {
            childList: true,
            subtree: true
        });

        console.log("[Nova Mobile] bubble copy/regen observer ready");
    }

    window.NovaMobileScanBubbleActions = scanBubbleActions;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startObserver);
    } else {
        startObserver();
    }

    window.addEventListener("load", function () {
        window.setTimeout(startObserver, 250);
    });
})();


// NOVA_MOBILE_FIX_REGEN_CLICK_20260609
(function () {
    "use strict";

    function toast(message, type) {
        if (typeof window.showToast === "function") {
            window.showToast(message, type || "info");
        } else {
            try {
                console.log("[Nova Mobile]", message);
            } catch (error) {
                // no-op
            }
        }
    }

    function cleanTextFromNode(node) {
        if (!node) return "";

        var clone = node.cloneNode(true);

        clone.querySelectorAll(
            ".nova-mobile-message-actions, .mobile-message-actions, button, script, style"
        ).forEach(function (el) {
            el.remove();
        });

        return String(clone.textContent || "").trim();
    }

    function getChatRoot() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.querySelector(".mobile-chat-container") ||
            document.querySelector("#nova-mobile-messages") ||
            document.querySelector(".nova-mobile-messages")
        );
    }

    function getInput() {
        return (
            document.getElementById("nova-mobile-input") ||
            document.getElementById("mobileInput") ||
            document.getElementById("mobile-chat-input") ||
            document.querySelector("textarea#nova-mobile-input") ||
            document.querySelector("textarea") ||
            document.querySelector("input[type='text']")
        );
    }

    function getSendButton() {
        return (
            document.getElementById("nova-mobile-send") ||
            document.getElementById("mobileSend") ||
            document.getElementById("mobile-send") ||
            document.querySelector("[data-action='send']") ||
            document.querySelector("[data-mobile-action='send']") ||
            document.querySelector("button[type='submit']") ||
            Array.from(document.querySelectorAll("button, [role='button']")).find(function (button) {
                var haystack = [
                    button.id || "",
                    button.className || "",
                    button.getAttribute("aria-label") || "",
                    button.getAttribute("title") || "",
                    button.textContent || ""
                ].join(" ").toLowerCase();

                return (
                    haystack.indexOf("send") !== -1 ||
                    haystack.indexOf("arrow") !== -1
                );
            })
        );
    }

    function findLastUserPrompt() {
        var root = getChatRoot();
        if (!root) return "";

        var nodes = Array.from(root.querySelectorAll("*")).reverse();

        for (var i = 0; i < nodes.length; i += 1) {
            var node = nodes[i];
            var cls = String(node.className || "").toLowerCase();
            var text = cleanTextFromNode(node);

            if (!text || text.length < 1) continue;

            if (
                cls.indexOf("user") !== -1 ||
                cls.indexOf("human") !== -1 ||
                cls.indexOf("outgoing") !== -1
            ) {
                return text;
            }
        }

        var directChildren = Array.from(root.children).reverse();

        for (var j = 0; j < directChildren.length; j += 1) {
            var childText = cleanTextFromNode(directChildren[j]);

            if (
                childText &&
                childText.indexOf("Copy") === -1 &&
                childText.indexOf("Regen") === -1 &&
                childText.length < 2000
            ) {
                return childText;
            }
        }

        return "";
    }

    function sendPrompt(prompt) {
        var text = String(prompt || "").trim();

        if (!text) {
            toast("No previous prompt found.", "error");
            return false;
        }

        if (typeof window.NovaMobileSendText === "function") {
            window.NovaMobileSendText(text);
            return true;
        }

        if (typeof window.sendText === "function") {
            window.sendText(text);
            return true;
        }

        var input = getInput();
        var send = getSendButton();

        if (!input) {
            toast("Input not found.", "error");
            return false;
        }

        input.value = text;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));

        if (send && typeof send.click === "function") {
            send.click();
            return true;
        }

        var enterEvent = new KeyboardEvent("keydown", {
            bubbles: true,
            cancelable: true,
            key: "Enter",
            code: "Enter"
        });

        input.dispatchEvent(enterEvent);
        return true;
    }

    window.NovaMobileRegenerateLast = function () {
        var prompt = findLastUserPrompt();

        toast("Regenerating...", "info");

        return sendPrompt(prompt);
    };

    document.addEventListener(
        "click",
        function (event) {
            var target = event.target;

            if (!target || !target.closest) return;

            var button = target.closest(
                ".nova-mobile-regenerate-message, .nova-mobile-regen-chat, [aria-label='Regenerate response']"
            );

            if (!button) return;

            event.preventDefault();
            event.stopPropagation();

            window.NovaMobileRegenerateLast();
        },
        true
    );

    console.log("[Nova Mobile] regen click fix ready");
})();


// NOVA_MOBILE_REGEN_WRAP_CODE_COPY_20260609
(function(){
    "use strict";

    function applyWrapAndCopy(node){
        if(!node) return;

        // Force wrapping
        node.style.wordBreak = "break-word";
        node.style.overflowWrap = "break-word";
        node.style.whiteSpace = "pre-wrap";
        node.style.maxWidth = "100%";

        // Add copy button for code blocks
        var codes = node.querySelectorAll("pre code");
        codes.forEach(function(code){
            if(code.parentNode.querySelector(".nova-code-copy-btn")) return;

            var btn = document.createElement("button");
            btn.textContent = "Copy";
            btn.className = "nova-code-copy-btn";
            btn.style.position = "absolute";
            btn.style.top = "4px";
            btn.style.right = "4px";
            btn.style.padding = "2px 6px";
            btn.style.fontSize = "11px";
            btn.style.background = "rgba(139,92,246,0.18)";
            btn.style.border = "1px solid rgba(139,92,246,0.38)";
            btn.style.borderRadius = "6px";
            btn.style.cursor = "pointer";
            btn.style.zIndex = "30";

            btn.onclick = function(e){
                e.stopPropagation();
                if(window.copyText){
                    window.copyText(code.innerText || code.textContent || "");
                }
            };

            // Ensure parent <pre> is positioned relative
            if(getComputedStyle(code.parentNode).position === "static"){
                code.parentNode.style.position = "relative";
            }

            code.parentNode.appendChild(btn);
        });
    }

    function scanNewBubbles(){
        var root = document.getElementById("mobileChatMessages") ||
                   document.querySelector(".mobile-chat-container") ||
                   document.querySelector("#nova-mobile-messages");

        if(!root) return;

        Array.from(root.children).forEach(applyWrapAndCopy);
        Array.from(root.querySelectorAll(".mobile-message, .nova-mobile-message, .message, .chat-message, .assistant-message, .user-message, [class*=\"message-bubble\"]"))
             .forEach(applyWrapAndCopy);
    }

    // Mutation observer for regen/new bubbles
    var root = document.getElementById("mobileChatMessages") ||
               document.querySelector(".mobile-chat-container") ||
               document.querySelector("#nova-mobile-messages");

    if(root){
        scanNewBubbles();
        if(window.__novaRegenObserver){
            window.__novaRegenObserver.disconnect();
        }

        window.__novaRegenObserver = new MutationObserver(function(){
            window.clearTimeout(window.__novaRegenTimer);
            window.__novaRegenTimer = window.setTimeout(scanNewBubbles, 80);
        });

        window.__novaRegenObserver.observe(root,{childList:true,subtree:true});
    }

    console.log("[Nova Mobile] regen wrapping + code copy observer ready");
})();


// NOVA_MOBILE_REGEN_CODE_COPY_FULL_20260609
(function(){
    "use strict";

    function applyWrapAndCodeCopy(node){
        if(!node) return;

        // Fix text wrapping
        node.style.wordBreak = "break-word";
        node.style.overflowWrap = "break-word";
        node.style.whiteSpace = "pre-wrap";
        node.style.maxWidth = "100%";

        // Add copy button to code blocks
        node.querySelectorAll("pre code").forEach(function(code){
            if(code.parentNode.querySelector(".nova-code-copy-btn")) return;

            var btn = document.createElement("button");
            btn.textContent = "Copy";
            btn.className = "nova-code-copy-btn";
            btn.style.position = "absolute";
            btn.style.top = "6px";
            btn.style.right = "6px";
            btn.style.zIndex = "40";
            btn.style.padding = "3px 7px";
            btn.style.fontSize = "11px";
            btn.style.background = "rgba(139,92,246,0.18)";
            btn.style.border = "1px solid rgba(139,92,246,0.38)";
            btn.style.borderRadius = "6px";
            btn.style.cursor = "pointer";

            btn.onclick = function(e){
                e.stopPropagation();
                if(window.copyText) window.copyText(code.innerText || code.textContent || "");
            };

            if(getComputedStyle(code.parentNode).position === "static"){
                code.parentNode.style.position = "relative";
            }

            code.parentNode.appendChild(btn);
        });
    }

    function scanAllBubbles(){
        var root = document.getElementById("mobileChatMessages") ||
                   document.querySelector(".mobile-chat-container") ||
                   document.querySelector("#nova-mobile-messages");
        if(!root) return;

        Array.from(root.children).forEach(applyWrapAndCodeCopy);
        Array.from(root.querySelectorAll(".mobile-message, .nova-mobile-message, .message, .assistant-message, .user-message, [class*=\"message-bubble\"]")).forEach(applyWrapAndCodeCopy);
    }

    // Observer for all new bubbles (normal + regenerated)
    var root = document.getElementById("mobileChatMessages") ||
               document.querySelector(".mobile-chat-container") ||
               document.querySelector("#nova-mobile-messages");
    if(root){
        scanAllBubbles();

        if(window.__novaRegenObserver){
            window.__novaRegenObserver.disconnect();
        }

        window.__novaRegenObserver = new MutationObserver(function(){
            window.clearTimeout(window.__novaRegenTimer);
            window.__novaRegenTimer = window.setTimeout(scanAllBubbles, 50);
        });

        window.__novaRegenObserver.observe(root,{childList:true,subtree:true});
    }

    // Patch Regen function to trigger observer
    if(window.NovaMobileRegenerateLast){
        var originalRegen = window.NovaMobileRegenerateLast;
        window.NovaMobileRegenerateLast = function(){
            var result = originalRegen();
            setTimeout(scanAllBubbles, 50);
            return result;
        };
    }

    console.log("[Nova Mobile] full regen + code copy observer ready");
})();


/* NOVA_MOBILE_ALL_PATCHES_20260609 */
/* Combined patch:
   - Regen observer / bubble wrapping
   - Code block copy button
   - Long message scroll
   - Dynamic bubble height
   - Text/block polish
*/

(function(){
    "use strict";

    function applyWrapAndCodeCopy(node){
        if(!node) return;

        // Text wrapping
        node.style.wordBreak = "break-word";
        node.style.overflowWrap = "break-word";
        node.style.whiteSpace = "pre-wrap";
        node.style.maxWidth = "100%";

        // Code block Copy button
        node.querySelectorAll("pre code").forEach(function(code){
            if(code.parentNode.querySelector(".nova-code-copy-btn")) return;

            var btn = document.createElement("button");
            btn.textContent = "Copy";
            btn.className = "nova-code-copy-btn";
            btn.style.position = "absolute";
            btn.style.top = "6px";
            btn.style.right = "6px";
            btn.style.zIndex = "50";
            btn.style.padding = "3px 7px";
            btn.style.fontSize = "11px";
            btn.style.background = "rgba(139,92,246,0.18)";
            btn.style.border = "1px solid rgba(139,92,246,0.38)";
            btn.style.borderRadius = "6px";
            btn.style.cursor = "pointer";

            btn.onclick = function(e){
                e.stopPropagation();
                if(window.copyText) window.copyText(code.innerText || code.textContent || "");
            };

            if(getComputedStyle(code.parentNode).position === "static"){
                code.parentNode.style.position = "relative";
            }

            code.parentNode.appendChild(btn);
        });

        // Limit bubble height and allow scroll
        if(node.className.indexOf("message") !== -1 || node.className.indexOf("bubble") !== -1){
            node.style.maxHeight = "45vh";
            node.style.overflowY = "auto";
        }

        // Ensure code blocks scroll separately
        node.querySelectorAll("pre").forEach(function(pre){
            pre.style.maxHeight = "30vh";
            pre.style.overflowY = "auto";
            pre.style.paddingRight = "4px";
        });
    }

    function scanAllBubbles(){
        var root = document.getElementById("mobileChatMessages") ||
                   document.querySelector(".mobile-chat-container") ||
                   document.querySelector("#nova-mobile-messages");
        if(!root) return;

        Array.from(root.children).forEach(applyWrapAndCodeCopy);
        Array.from(root.querySelectorAll(".mobile-message, .nova-mobile-message, .message, .assistant-message, .user-message, [class*=\"message-bubble\"]")).forEach(applyWrapAndCodeCopy);
    }

    // Mutation observer for all new bubbles (normal + regenerated)
    var root = document.getElementById("mobileChatMessages") ||
               document.querySelector(".mobile-chat-container") ||
               document.querySelector("#nova-mobile-messages");
    if(root){
        scanAllBubbles();

        if(window.__novaRegenObserver){
            window.__novaRegenObserver.disconnect();
        }

        window.__novaRegenObserver = new MutationObserver(function(){
            window.clearTimeout(window.__novaRegenTimer);
            window.__novaRegenTimer = window.setTimeout(scanAllBubbles, 50);
        });

        window.__novaRegenObserver.observe(root,{childList:true,subtree:true});
    }

    // Patch Regen function to trigger observer
    if(window.NovaMobileRegenerateLast){
        var originalRegen = window.NovaMobileRegenerateLast;
        window.NovaMobileRegenerateLast = function(){
            var result = originalRegen();
            setTimeout(scanAllBubbles, 50);
            return result;
        };
    }

    console.log("[Nova Mobile] full regen + code copy + text polish observer ready");
})();


/* NOVA_MOBILE_CONSOLIDATED_PATCH_20260609 */
/* Combined stable patch:
   - Bubble text wrapping
   - Regen observer
   - Code block Copy buttons
   - Long message scroll
   - Full-width stable rows
*/

(function(){
    "use strict";

    function applyWrapAndCodeCopy(node){
        if(!node) return;

        node.style.wordBreak = "break-word";
        node.style.overflowWrap = "break-word";
        node.style.whiteSpace = "pre-wrap";
        node.style.maxWidth = "100%";

        // Limit bubble height
        if(node.className.indexOf("message") !== -1 || node.className.indexOf("bubble") !== -1){
            node.style.maxHeight = "45vh";
            node.style.overflowY = "auto";
        }

        // Code block copy
        node.querySelectorAll("pre code").forEach(function(code){
            if(code.parentNode.querySelector(".nova-code-copy-btn")) return;

            var btn = document.createElement("button");
            btn.textContent = "Copy";
            btn.className = "nova-code-copy-btn";
            btn.style.position = "absolute";
            btn.style.top = "6px";
            btn.style.right = "6px";
            btn.style.zIndex = "50";
            btn.style.padding = "3px 7px";
            btn.style.fontSize = "11px";
            btn.style.background = "rgba(139,92,246,0.18)";
            btn.style.border = "1px solid rgba(139,92,246,0.38)";
            btn.style.borderRadius = "6px";
            btn.style.cursor = "pointer";

            btn.onclick = function(e){
                e.stopPropagation();
                if(window.copyText) window.copyText(code.innerText || code.textContent || "");
            };

            if(getComputedStyle(code.parentNode).position === "static"){
                code.parentNode.style.position = "relative";
            }

            code.parentNode.appendChild(btn);
        });
    }

    function scanAllBubbles(){
        var root = document.getElementById("mobileChatMessages") ||
                   document.querySelector(".mobile-chat-container") ||
                   document.querySelector("#nova-mobile-messages");
        if(!root) return;

        Array.from(root.children).forEach(applyWrapAndCodeCopy);
        Array.from(root.querySelectorAll(".mobile-message, .nova-mobile-message, .message, .assistant-message, .user-message, [class*=\"message-bubble\"]")).forEach(applyWrapAndCodeCopy);
    }

    // Observer for new bubbles
    var root = document.getElementById("mobileChatMessages") ||
               document.querySelector(".mobile-chat-container") ||
               document.querySelector("#nova-mobile-messages");
    if(root){
        scanAllBubbles();
        if(window.__novaRegenObserver) window.__novaRegenObserver.disconnect();

        window.__novaRegenObserver = new MutationObserver(function(){
            window.clearTimeout(window.__novaRegenTimer);
            window.__novaRegenTimer = window.setTimeout(scanAllBubbles, 50);
        });

        window.__novaRegenObserver.observe(root,{childList:true,subtree:true});
    }

    // Patch Regen function to trigger observer
    if(window.NovaMobileRegenerateLast){
        var originalRegen = window.NovaMobileRegenerateLast;
        window.NovaMobileRegenerateLast = function(){
            var result = originalRegen();
            setTimeout(scanAllBubbles, 50);
            return result;
        };
    }

    console.log("[Nova Mobile] consolidated patch ready");
})();

// NOVA_MOBILE_RUNTIME_MESSAGE_BAR_FIX_20260609
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_RUNTIME_MESSAGE_BAR_FIX__) {
        return;
    }

    window.__NOVA_MOBILE_RUNTIME_MESSAGE_BAR_FIX__ = true;

    function findInput() {
        return (
            document.getElementById("nova-mobile-input") ||
            document.querySelector("textarea[placeholder*='message' i]") ||
            document.querySelector("input[placeholder*='message' i]") ||
            document.querySelector("textarea") ||
            document.querySelector("[contenteditable='true']")
        );
    }

    function scoreComposer(el, input) {
        if (!el || !input || el === document.body || el === document.documentElement) {
            return -1;
        }

        var score = 0;
        var id = String(el.id || "").toLowerCase();
        var cls = String(el.className || "").toLowerCase();

        if (id.indexOf("composer") !== -1) score += 50;
        if (cls.indexOf("composer") !== -1) score += 50;
        if (id.indexOf("input") !== -1) score += 20;
        if (cls.indexOf("input") !== -1) score += 20;
        if (id.indexOf("bar") !== -1) score += 20;
        if (cls.indexOf("bar") !== -1) score += 20;
        if (el.querySelector("button")) score += 20;
        if (el.contains(input)) score += 10;

        var rect = el.getBoundingClientRect();
        if (rect.height >= 40 && rect.height <= 180) score += 20;
        if (rect.width > window.innerWidth * 0.7) score += 20;

        return score;
    }

    function findComposer(input) {
        if (!input) return null;

        var best = null;
        var bestScore = -1;
        var node = input.parentElement;
        var steps = 0;

        while (node && steps < 8) {
            var score = scoreComposer(node, input);
            if (score > bestScore) {
                best = node;
                bestScore = score;
            }

            node = node.parentElement;
            steps += 1;
        }

        return best || input.parentElement;
    }

    function fixButton(button) {
        if (!button) return;

        button.style.flex = "0 0 42px";
        button.style.width = "42px";
        button.style.height = "42px";
        button.style.minWidth = "42px";
        button.style.minHeight = "42px";
        button.style.maxWidth = "42px";
        button.style.maxHeight = "42px";
        button.style.display = "inline-flex";
        button.style.alignItems = "center";
        button.style.justifyContent = "center";
        button.style.boxSizing = "border-box";
        button.style.borderRadius = "999px";
        button.style.padding = "0";
        button.style.margin = "0";
        button.style.overflow = "hidden";
    }

    function fixComposer() {
        var input = findInput();
        if (!input) return false;

        var composer = findComposer(input);
        if (!composer) return false;

        composer.id = composer.id || "nova-mobile-runtime-fixed-composer";

        composer.style.position = "fixed";
        composer.style.left = "0";
        composer.style.right = "0";
        composer.style.bottom = "0";
        composer.style.zIndex = "2147483646";
        composer.style.display = "flex";
        composer.style.alignItems = "center";
        composer.style.justifyContent = "center";
        composer.style.gap = "8px";
        composer.style.width = "100vw";
        composer.style.maxWidth = "100vw";
        composer.style.minHeight = "64px";
        composer.style.maxHeight = "84px";
        composer.style.padding = "8px 10px calc(8px + env(safe-area-inset-bottom)) 10px";
        composer.style.boxSizing = "border-box";
        composer.style.background = "#0b0b12";
        composer.style.borderTop = "1px solid rgba(255,255,255,0.12)";
        composer.style.overflow = "hidden";
        composer.style.transform = "none";

        input.style.flex = "1 1 auto";
        input.style.width = "auto";
        input.style.minWidth = "0";
        input.style.maxWidth = "100%";
        input.style.height = "44px";
        input.style.minHeight = "44px";
        input.style.maxHeight = "110px";
        input.style.padding = "10px 12px";
        input.style.boxSizing = "border-box";
        input.style.resize = "none";
        input.style.overflowY = "auto";
        input.style.overflowX = "hidden";
        input.style.lineHeight = "1.25";
        input.style.borderRadius = "18px";
        input.style.margin = "0";
        input.style.transform = "none";

        Array.from(composer.querySelectorAll("button")).forEach(fixButton);

        var chat = (
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-mobile-messages") ||
            document.querySelector(".nova-mobile-chat") ||
            document.querySelector(".nova-mobile-messages") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("main")
        );

        if (chat) {
            chat.style.paddingBottom = "170px";
            chat.style.scrollPaddingBottom = "170px";
            chat.style.boxSizing = "border-box";
        }

        document.body.style.paddingBottom = "100px";
        document.documentElement.style.overflowX = "hidden";
        document.body.style.overflowX = "hidden";

        return true;
    }

    function run() { if (window.__NOVA_FINAL_COMPOSER_LAYOUT_ACTIVE_20260609) { return; }
        fixComposer();
    }

    window.NovaMobileRuntimeFixMessageBar = run;

    window.addEventListener("load", function () {
        setTimeout(run, 0);
        setTimeout(run, 150);
        setTimeout(run, 600);
        setTimeout(run, 1500);
    });

    window.addEventListener("resize", function () {
        setTimeout(run, 50);
    });

    window.addEventListener("focusin", function () {
        setTimeout(run, 50);
        setTimeout(run, 350);
    }, true);

    document.addEventListener("input", function () {
        setTimeout(run, 0);
    }, true);

    // NOVA_STOP_MESSAGE_BAR_FIGHTING_LOOPS_20260609: disabled Runtime Message Bar Fix interval

    console.log("[Nova Mobile Runtime Message Bar Fix] ready");
})();

// NOVA_FINAL_INPUT_HEIGHT_OVERRIDE_20260609
(function () {
    "use strict";

    function forceFinalInputHeight() { window.__NOVA_FINAL_COMPOSER_LAYOUT_ACTIVE_20260609 = true;
        var input = document.getElementById("nova-mobile-input");
        var composer = document.getElementById("nova-mobile-composer") || document.querySelector(".mobile-composer");

        if (!input || !composer) {
            return;
        }

        composer.style.setProperty("height", "132px", "important");
        composer.style.setProperty("min-height", "132px", "important");
        composer.style.setProperty("max-height", "132px", "important");
        composer.style.setProperty("display", "flex", "important");
        composer.style.setProperty("flex-wrap", "wrap", "important");
        composer.style.setProperty("align-items", "center", "important");

        input.style.setProperty("flex", "0 0 100%", "important");
        input.style.setProperty("width", "100%", "important");
        input.style.setProperty("min-width", "100%", "important");
        input.style.setProperty("max-width", "100%", "important");
        input.style.setProperty("height", "68px", "important");
        input.style.setProperty("min-height", "68px", "important");
        input.style.setProperty("max-height", "68px", "important");
        input.style.setProperty("padding", "14px", "important");
        input.style.setProperty("line-height", "21px", "important");
        input.style.setProperty("box-sizing", "border-box", "important");
        input.style.setProperty("resize", "none", "important");

        composer.querySelectorAll("button, .mobile-composer-btn, .mobile-icon-action").forEach(function (button) {
            button.style.setProperty("flex", "0 0 42px", "important");
            button.style.setProperty("width", "42px", "important");
            button.style.setProperty("min-width", "42px", "important");
            button.style.setProperty("max-width", "42px", "important");
            button.style.setProperty("height", "42px", "important");
            button.style.setProperty("min-height", "42px", "important");
            button.style.setProperty("max-height", "42px", "important");
        });

        document.body.style.setProperty("padding-bottom", "148px", "important");
    }

    forceFinalInputHeight();
    setTimeout(forceFinalInputHeight, 50);
    setTimeout(forceFinalInputHeight, 250);
    setTimeout(forceFinalInputHeight, 750);
    setTimeout(forceFinalInputHeight, 1500);

    window.addEventListener("load", forceFinalInputHeight);
    window.addEventListener("resize", function () {
        setTimeout(forceFinalInputHeight, 50);
    });

    window.NovaFinalInputHeightOverride = forceFinalInputHeight;

    console.log("[Nova Final Input Height Override] ready");
})();

// NOVA_STOP_MESSAGE_BAR_FIGHTING_LOOPS_20260609
console.log("[Nova Stop Message Bar Fighting Loops] ready");

// NOVA_GUARD_OLD_COMPOSER_RESIZERS_20260609
console.log("[Nova Guard Old Composer Resizers] ready");
