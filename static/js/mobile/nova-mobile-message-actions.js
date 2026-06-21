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

