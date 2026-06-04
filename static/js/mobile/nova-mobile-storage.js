(function () {
    "use strict";

    function saveDraft(inputEl) {
        if (!inputEl) return;

        localStorage.setItem("novaMobileDraft", inputEl.value || "");
        inputEl.dataset.draftSaved = "1";
    }

    function restoreDraft(inputEl) {
        if (!inputEl) return;

        const saved = localStorage.getItem("novaMobileDraft") || "";

        if (saved.trim()) {
            inputEl.value = saved;
            inputEl.dataset.draftSaved = "1";
        }
    }

    function restoreCurrentMessages() {
        if (!window.chatContainer) return;

        try {
            const messages = JSON.parse(
                localStorage.getItem(
                    window.NovaMobileCore.getCurrentSessionMessagesKey()
                ) || "[]"
            );

            if (!Array.isArray(messages) || !messages.length) {
                window.NovaMobileCore.renderEmptyState();
                return;
            }

            window.chatContainer.innerHTML = "";

            messages.forEach(function (message) {
                if (message.image) {
                    window.NovaMobileImages.appendImage(
                        message.image,
                        "Restored image"
                    );
                }

                if (message.text) {
                    window.NovaMobileChatUI.appendMessage(
                        message.role,
                        message.text
                    );
                }
            });

            window.NovaMobileCore.scrollBottom(true);
        } catch {
            localStorage.removeItem(
                window.NovaMobileCore.getCurrentSessionMessagesKey()
            );
        }
    }

    window.NovaMobileStorage = {
        saveDraft,
        restoreDraft,
        restoreCurrentMessages
    };

    console.log("[Nova Mobile] storage module ready");
})();