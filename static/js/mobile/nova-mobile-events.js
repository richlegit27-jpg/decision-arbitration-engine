(function () {
    "use strict";

    function installCoreListeners(options) {
        options = options || {};

        const sendMessage = options.sendMessage;
        const speakLastAssistant = options.speakLastAssistant;
        const stopGeneration = options.stopGeneration;
        const saveDraft = options.saveDraft;
        const setStopSpeechActive = options.setStopSpeechActive || function () {};

        const inputEl = document.getElementById("nova-mobile-input");
        const sendBtn = document.getElementById("nova-mobile-send");
        const stopGenerationBtn = document.getElementById("nova-mobile-stop-generation");
        const attachBtn = document.getElementById("nova-mobile-attach");
        const voiceBtn = document.getElementById("nova-mobile-voice");
        const ttsBtn = document.getElementById("nova-mobile-tts");
        const stopSpeechBtn = document.getElementById("nova-mobile-stop-speech");

        const toolsToggleBtn = document.getElementById("nova-mobile-tools-toggle");
        const toolsPanel = document.getElementById("nova-mobile-tools-panel");
        const memoryToggleBtn = document.getElementById("nova-mobile-memory-toggle");
        const memoryPanel = document.getElementById("nova-mobile-memory-panel");
        const memoryCloseBtn = document.getElementById("nova-mobile-memory-close");
        const executionPanel = document.getElementById("nova-mobile-execution-panel");
        const executionCloseBtn = document.getElementById("nova-mobile-execution-close");
        const sessionsToggleBtn = document.getElementById("nova-mobile-sessions-toggle");
        const sessionsPanel = document.getElementById("nova-mobile-sessions-panel");
        const sessionsCloseBtn = document.getElementById("nova-mobile-sessions-close");

        const newChatBtn = document.getElementById("nova-mobile-new-chat");
        const clearChatBtn = document.getElementById("nova-mobile-clear-chat");
        const copyChatBtn = document.getElementById("nova-mobile-copy-chat");
        const exportChatBtn = document.getElementById("nova-mobile-export-chat");

        if (sendBtn && typeof sendMessage === "function") {
            sendBtn.addEventListener("click", function () {
                sendMessage();
            });
        }

        if (inputEl && typeof sendMessage === "function") {
            inputEl.addEventListener("keydown", function (event) {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            });

            inputEl.addEventListener("input", function () {
                if (typeof saveDraft === "function") {
                    saveDraft();
                }

                if (window.NovaMobileCore) {
                    window.NovaMobileCore.autoGrowInput();
                }
            });
        }

        if (window.chatContainer) {
            let mobileScrollTicking = false;

            window.chatContainer.addEventListener("scroll", function () {
                if (mobileScrollTicking) return;

                mobileScrollTicking = true;

                requestAnimationFrame(function () {
                    if (window.NovaMobileCore) {
                        window.NovaMobileCore.updateParallaxDepth();
                        window.NovaMobileCore.updateHeaderVisibility();
                    }

                    mobileScrollTicking = false;
                });
            });
        }

        // NOVA_MOBILE_DUPLICATE_UPLOAD_CLICK_REMOVED_20260608
        // Upload click binding is owned by static/js/mobile/nova-mobile-upload.js.

        if (ttsBtn && typeof speakLastAssistant === "function") {
            ttsBtn.addEventListener("click", speakLastAssistant);
        }

        if (stopSpeechBtn) {
            stopSpeechBtn.addEventListener("click", function () {
                window.speechSynthesis.cancel();
                setStopSpeechActive(false);

                if (ttsBtn) {
                    ttsBtn.classList.remove("speaking");
                }

                if (typeof window.showToast === "function") {
                    window.showToast("Speech stopped.");
                }
            });
        }

        // NOVA_MOBILE_DUPLICATE_VOICE_CLICK_REMOVED_20260608
        // Voice click binding is owned by static/js/mobile/nova-mobile-voice.js.

        if (toolsToggleBtn && window.NovaMobileUiUtils) {
            toolsToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(toolsPanel);
            });
        }

        if (memoryToggleBtn && window.NovaMobileUiUtils) {
            memoryToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(memoryPanel);
            });
        }

        if (memoryCloseBtn && window.NovaMobileUiUtils) {
            memoryCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(memoryPanel);
            });
        }

        if (executionCloseBtn && window.NovaMobileUiUtils) {
            executionCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(executionPanel);
            });
        }

        if (sessionsToggleBtn && window.NovaMobileUiUtils) {
            sessionsToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(sessionsPanel);
            });
        }

        if (sessionsCloseBtn && window.NovaMobileUiUtils) {
            sessionsCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(sessionsPanel);
            });
        }

        if (
            copyChatBtn &&
            window.NovaMobileUiUtils &&
            typeof window.NovaMobileUiUtils.copyWholeChat === "function"
        ) {
            copyChatBtn.addEventListener("click", window.NovaMobileUiUtils.copyWholeChat);
        }

        if (
            exportChatBtn &&
            window.NovaMobileUiUtils &&
            typeof window.NovaMobileUiUtils.exportWholeChat === "function"
        ) {
            exportChatBtn.addEventListener("click", window.NovaMobileUiUtils.exportWholeChat);
        }

        if (clearChatBtn) {
            clearChatBtn.addEventListener("click", function () {
                window.speechSynthesis.cancel();
                setStopSpeechActive(false);

                if (window.chatContainer) {
                    window.chatContainer.innerHTML = "";
                }

                if (window.NovaMobileCore) {
                    localStorage.removeItem(
                        window.NovaMobileCore.getCurrentSessionMessagesKey()
                    );
                }

                if (typeof window.showToast === "function") {
                    window.showToast("Chat cleared.");
                }
            });
        }

        if (
            newChatBtn &&
            window.NovaMobileSessions &&
            typeof window.NovaMobileSessions.createNewMobileSession === "function"
        ) {
            newChatBtn.addEventListener(
                "click",
                window.NovaMobileSessions.createNewMobileSession
            );
        }

        if (stopGenerationBtn && typeof stopGeneration === "function") {
            stopGenerationBtn.addEventListener("click", stopGeneration);
        }

        console.log("[Nova Mobile] events module listeners installed");
    }

    window.NovaMobileEvents = {
        installCoreListeners
    };

    console.log("[Nova Mobile] events module ready");
})();
