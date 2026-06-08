(function () {
    "use strict";

    function installCoreListeners() {
        if (window.sendBtn) {
            window.sendBtn.addEventListener("click", function () {
                sendMessage();
            });
        }

        if (window.inputEl) {
            window.inputEl.addEventListener("keydown", function (event) {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            });

            window.inputEl.addEventListener("input", function () {
                saveDraft();
                window.NovaMobileCore.autoGrowInput();
            });
        }

        if (window.chatContainer) {
            window.chatContainer.addEventListener("scroll", function () {
                window.NovaMobileCore.updateParallaxDepth();
                window.NovaMobileCore.updateHeaderVisibility();
            });
        }

        // NOVA_MOBILE_DUPLICATE_UPLOAD_CLICK_REMOVED_20260608
        // Upload click binding is owned by static/js/mobile/nova-mobile-upload.js.

        // NOVA_MOBILE_DUPLICATE_TTS_CLICK_REMOVED_20260608
        // TTS click and stop-speech binding currently live in nova-mobile-app.js until a dedicated TTS module exists.

        // NOVA_MOBILE_DUPLICATE_VOICE_CLICK_REMOVED_20260608
        // Voice click binding is owned by static/js/mobile/nova-mobile-voice.js.

        if (window.toolsToggleBtn) {
            window.toolsToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(window.toolsPanel);
            });
        }

        if (window.memoryToggleBtn) {
            window.memoryToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(window.memoryPanel);
            });
        }

        if (window.memoryCloseBtn) {
            window.memoryCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(window.memoryPanel);
            });
        }

        if (window.executionCloseBtn) {
            window.executionCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(window.executionPanel);
            });
        }

        if (window.sessionsToggleBtn) {
            window.sessionsToggleBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.togglePanel(window.sessionsPanel);
            });
        }

        if (window.sessionsCloseBtn) {
            window.sessionsCloseBtn.addEventListener("click", function () {
                window.NovaMobileUiUtils.closePanel(window.sessionsPanel);
            });
        }

        if (window.copyChatBtn) {
            window.copyChatBtn.addEventListener(
                "click",
                window.NovaMobileUiUtils.copyWholeChat
            );
        }

        if (window.exportChatBtn) {
            window.exportChatBtn.addEventListener(
                "click",
                window.NovaMobileUiUtils.exportWholeChat
            );
        }

        if (window.clearChatBtn) {
            window.clearChatBtn.addEventListener("click", function () {
                window.speechSynthesis.cancel();
                setStopSpeechActive(false);

                if (window.chatContainer) {
                    window.chatContainer.innerHTML = "";
                }

                localStorage.removeItem(
                    window.NovaMobileCore.getCurrentSessionMessagesKey()
                );

                showToast("Chat cleared.");
            });
        }

        if (window.newChatBtn) {
            window.newChatBtn.addEventListener(
                "click",
                window.NovaMobileSessions.createNewMobileSession
            );
        }

        if (window.stopGenerationBtn) {
            window.stopGenerationBtn.addEventListener(
                "click",
                stopGeneration
            );
        }
    }

    function installDocumentListeners() {
        document.addEventListener("click", function (event) {
            const button = event.target.closest("[data-mobile-tool]");

            if (!button) return;

            window.NovaMobileUiUtils.runTool(
                button.getAttribute("data-mobile-tool")
            );
        });

        document.addEventListener("click", function (event) {
            const isInsideSafeArea =
                event.target.closest(
                    ".mobile-composer, .mobile-header, .mobile-quick-prompts, .mobile-panel, [data-mobile-tool]"
                );

            if (isInsideSafeArea) return;

            window.NovaMobileUiUtils.closeAllPanels();
        });

        document.addEventListener("click", function (event) {
            const promptBtn = event.target.closest("[data-quick-prompt]");

            if (!promptBtn) return;

            window.NovaMobileCore.setInputText(
                promptBtn.getAttribute("data-quick-prompt") || ""
            );
        });

        document.addEventListener("touchstart", function (event) {
            const firstTouch = event.touches?.[0];

            if (firstTouch) {
                window.touchStartY = firstTouch.clientY;
            }

            const promptBtn = event.target.closest("[data-quick-prompt]");

            if (!promptBtn) return;

            const prompt =
                promptBtn.getAttribute("data-quick-prompt") || "";

            window.quickPromptHoldTimer =
                setTimeout(function () {
                    sendMessage(prompt);
                }, 500);
        });

        document.addEventListener("touchend", function (event) {
            clearTimeout(window.quickPromptHoldTimer);

            const changedTouch = event.changedTouches?.[0];

            if (!changedTouch) return;

            const distance =
                changedTouch.clientY - window.touchStartY;

            if (
                distance > 120 &&
                window.chatContainer &&
                window.chatContainer.scrollTop <= 10 &&
                window.inputEl
            ) {
                window.inputEl.focus();
            }
        });

        document.addEventListener("touchcancel", function () {
            clearTimeout(window.quickPromptHoldTimer);
        });

        window.addEventListener("online", function () {
            window.NovaMobileCore.setConnectionState("idle");
            showToast("Back online.");
        });

        window.addEventListener("offline", function () {
            window.NovaMobileCore.setConnectionState("error");
            showToast("Offline.");
        });
    }

    function disableMobileCircleCursor() {
        const selectors = [
            ".cursor",
            ".custom-cursor",
            ".nova-cursor",
            ".cursor-ring",
            ".cursor-dot",
            "#cursor",
            "#customCursor",
            "#novaCursor",
            "#cursorRing",
            "#cursorDot",
            ".nova-stream-cursor",
            ".streaming-cursor",
            ".nova-empty-orb",
            ".mobile-cursor",
            ".nova-mobile-cursor",
            ".circle-cursor",
            "#mobileCursor",
            "#novaMobileCursor"
        ];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                el.remove();
            });
        });

        document.body.style.cursor = "auto";
        document.documentElement.style.cursor = "auto";

        console.log("[Nova Mobile] circle cursor disabled");
    }

    window.NovaMobileListeners = {
        installCoreListeners,
        installDocumentListeners,
        disableMobileCircleCursor
    };

    console.log("[Nova Mobile] listeners module ready");
})();
