
(function () {
    "use strict";

    if (window.__NOVA_CHAT_COMPOSER_LOCK_FINAL_20260622__) return;
    window.__NOVA_CHAT_COMPOSER_LOCK_FINAL_20260622__ = true;

    function lockComposer() {
        const chatPanel = document.querySelector(".chat-panel");
        const chat = document.getElementById("chat");
        const composer = document.querySelector(".composer");
        const summary = document.getElementById("novaChatSummaryStrip");

        if (chatPanel) {
            chatPanel.style.height = "calc(100vh - 28px)";
            chatPanel.style.maxHeight = "calc(100vh - 28px)";
            chatPanel.style.minHeight = "0";
            chatPanel.style.overflow = "hidden";
            chatPanel.style.display = "grid";
            chatPanel.style.gridTemplateRows = "auto minmax(0, 1fr) auto auto";
        }

        if (chat) {
            chat.style.minHeight = "0";
            chat.style.overflowY = "auto";
            chat.style.overflowX = "hidden";
        }

        if (summary) {
            summary.style.margin = "0";
        }

        if (composer) {
            composer.style.margin = "0";
            composer.style.position = "relative";
            composer.style.zIndex = "20";
        }
    }

    window.NovaLockChatComposer = lockComposer;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", lockComposer);
    } else {
        lockComposer();
    }

    setTimeout(lockComposer, 300);
    setTimeout(lockComposer, 1000);
    window.addEventListener("resize", lockComposer);
})();
