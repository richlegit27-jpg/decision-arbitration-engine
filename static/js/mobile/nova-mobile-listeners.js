(function () {
    "use strict";

    function installCoreListeners() {
        // NOVA_MOBILE_LISTENERS_CORE_DELEGATED_TO_EVENTS_20260608
        // Core button/input listeners are owned by static/js/mobile/nova-mobile-events.js.
        // This function remains as a safe no-op so older boot calls do not break.
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

