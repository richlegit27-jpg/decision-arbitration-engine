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

        // NOVA_MOBILE_DUPLICATE_TTS_CLICK_REMOVED_20260608
        // TTS click and stop-speech binding currently live in nova-mobile-app.js until a dedicated TTS module exists.

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

// NOVA_ROUTE_SESSIONS_BUTTON_TO_FINAL_OWNER_20260609
(function () {
    "use strict";

    function isSessionsButton(target) {
        if (!target || !target.closest) return false;

        var button = target.closest("button, a");
        if (!button) return false;

        var text = String(button.textContent || "").trim().toLowerCase();
        var id = String(button.id || "").toLowerCase();
        var cls = String(button.className || "").toLowerCase();
        var aria = String(button.getAttribute("aria-label") || "").toLowerCase();

        return (
            text === "sessions" ||
            id === "nova-mobile-sessions-toggle" ||
            id.includes("sessions") ||
            cls.includes("sessions") ||
            aria.includes("sessions")
        );
    }

})();

// NOVA_MOBILE_RESTORE_QUICK_PROMPTS_20260610
(function () {
    "use strict";

    var PROMPTS = [
        {
            label: "Cont.",
            text: "Continue from where we left off. Keep it direct and tell me the next move."
        },
        {
            label: "Sum.",
            text: "Summarize the current situation in plain English and tell me what matters most."
        },
        {
            label: "Fix",
            text: "Improve this and make it cleaner, more direct, and more useful."
        },
        {
            label: "Next",
            text: "What should I do next? Give me the best next step only."
        }
    ];

    function $(id) {
        return document.getElementById(id);
    }

    function findComposer() {
        return $("nova-mobile-composer")
            || document.querySelector("[data-mobile-composer='true']")
            || document.querySelector(".mobile-composer")
            || document.querySelector(".composer")
            || null;
    }

    function findInput() {
        return $("nova-mobile-input")
            || document.querySelector("textarea#mobileInput")
            || document.querySelector("textarea")
            || document.querySelector("[contenteditable='true']")
            || null;
    }

    function findSendButton() {
        return $("nova-mobile-send")
            || $("mobileSendButton")
            || document.querySelector("[data-mobile-send='true']")
            || document.querySelector("button[aria-label='Send']")
            || Array.from(document.querySelectorAll("button")).find(function (button) {
                var text = String(button.textContent || "").trim().toLowerCase();
                var label = String(button.getAttribute("aria-label") || "").trim().toLowerCase();
                return text === "send" || label === "send" || text === "➤" || text === "↑";
            })
            || null;
    }

    function setInputValue(input, value) {
        if (!input) return;

        if (input.isContentEditable) {
            input.textContent = value;
        } else {
            input.value = value;
        }

        try {
            input.dispatchEvent(new Event("input", { bubbles: true }));
        } catch (error) {}

        try {
            input.focus();
        } catch (error) {}
    }

    function sendPrompt(text) {
        var input = findInput();
        setInputValue(input, text);

        try {
            if (typeof window.NovaMobileSendText === "function") {
                window.NovaMobileSendText(text);
                return;
            }
        } catch (error) {}

        try {
            if (typeof window.sendText === "function") {
                window.sendText(text);
                return;
            }
        } catch (error) {}

        var sendButton = findSendButton();
        if (sendButton) {
            sendButton.click();
        }
    }

    function installStyle() {
        if ($("nova-mobile-quick-prompts-style")) return;

        var style = document.createElement("style");
        style.id = "nova-mobile-quick-prompts-style";
        style.textContent = [
            ".nova-mobile-quick-prompts-clean{",
            "display:flex;",
            "gap:8px;",
            "align-items:center;",
            "justify-content:space-between;",
            "padding:8px 10px 6px;",
            "background:rgba(10,10,18,.92);",
            "border-top:1px solid rgba(255,255,255,.10);",
            "}",
            ".nova-mobile-quick-prompts-clean button{",
            "appearance:none;",
            "border:1px solid rgba(255,255,255,.16);",
            "background:rgba(255,255,255,.08);",
            "color:rgba(255,255,255,.92);",
            "border-radius:999px;",
            "padding:7px 8px;min-width:0;flex:1;max-width:82px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;",
            "font-size:12px;",
            "font-weight:700;",
            "line-height:1;",
            "cursor:pointer;",
            "}",
            ".nova-mobile-quick-prompts-clean button:active{",
            "transform:translateY(1px);",
            "}",
            "@media (max-width:420px){",
            ".nova-mobile-quick-prompts-clean{gap:6px;padding-left:6px;padding-right:6px;}",
            ".nova-mobile-quick-prompts-clean button{font-size:11px;padding:7px 6px;max-width:none;}",
            "}"
        ].join("");

        document.head.appendChild(style);
    }

    function installQuickPrompts() {
        // NOVA_DISABLE_DUPLICATE_QUICK_PROMPTS_20260610
        // Quick prompts are now owned by templates/mobile.html:
        // Go / Sum / Fix / Next with class .mobile-quick-action.
        // Do not inject the duplicate Cont. / Sum. / Fix / Next row.
        return true;
        var composer = findComposer();
        if (!composer) return false;

        if ($("nova-mobile-quick-prompts-clean")) return true;

        installStyle();

        var row = document.createElement("div");
        row.id = "nova-mobile-quick-prompts-clean";
        row.className = "nova-mobile-quick-prompts-clean";
        row.setAttribute("data-nova-quick-prompts-owner", "NOVA_MOBILE_RESTORE_QUICK_PROMPTS_20260610");

        PROMPTS.forEach(function (prompt) {
            var button = document.createElement("button");
            button.type = "button";
            button.textContent = prompt.label;
            button.setAttribute("data-prompt-text", prompt.text);
            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                sendPrompt(prompt.text);
            });
            row.appendChild(button);
        });

        composer.insertBefore(row, composer.firstChild);
        console.log("[Nova Mobile] clean quick prompts restored");
        return true;
    }

    function boot() {
        if (installQuickPrompts()) return;

        var tries = 0;
        var timer = setInterval(function () {
            tries += 1;
            if (installQuickPrompts() || tries >= 30) {
                clearInterval(timer);
            }
        }, 250);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();






