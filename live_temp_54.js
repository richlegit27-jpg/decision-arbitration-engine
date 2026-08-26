
(function () {
    "use strict";

    if (window.__NOVA_CHAT_SCROLL_VIEWPORT_FORCE_20260622__) return;
    window.__NOVA_CHAT_SCROLL_VIEWPORT_FORCE_20260622__ = true;

    let resizeTimer = null;

    function px(value) {
        return Math.max(0, Math.floor(value || 0));
    }

    function forceChatScrollViewport() {
        const shell = document.querySelector(".shell");
        const panel = document.querySelector(".panel.chat-panel") || document.querySelector(".chat-panel");
        const top = document.querySelector(".chat-top");
        const chat = document.getElementById("chat");
        const summary = document.getElementById("novaChatSummaryStrip");
        const composer = document.querySelector(".composer");

        if (!panel || !chat || !composer) return;

        if (shell) {
            shell.style.height = "100vh";
            shell.style.maxHeight = "100vh";
            shell.style.overflow = "hidden";
        }

        panel.style.height = "calc(100vh - 28px)";
        panel.style.maxHeight = "calc(100vh - 28px)";
        panel.style.minHeight = "0";
        panel.style.overflow = "hidden";
        panel.style.display = "grid";
        panel.style.gridTemplateRows = "auto minmax(0, 1fr) auto auto";

        const panelRect = panel.getBoundingClientRect();
        const topH = top ? top.getBoundingClientRect().height : 0;
        const summaryH = summary ? summary.getBoundingClientRect().height : 0;
        const composerH = composer ? composer.getBoundingClientRect().height : 0;

        const available = px(panelRect.height - topH - summaryH - composerH);

        chat.style.minHeight = "0";
        chat.style.height = available + "px";
        chat.style.maxHeight = available + "px";
        chat.style.overflowY = "auto";
        chat.style.overflowX = "hidden";

        composer.style.flex = "0 0 auto";
        composer.style.margin = "0";
        composer.style.position = "relative";
        composer.style.zIndex = "30";

        if (summary) {
            summary.style.flex = "0 0 auto";
            summary.style.margin = "0";
        }
    }

    function scheduleForce() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(forceChatScrollViewport, 40);
    }

    window.NovaForceChatScrollViewport = forceChatScrollViewport;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", forceChatScrollViewport);
    } else {
        forceChatScrollViewport();
    }

    window.addEventListener("resize", scheduleForce);

    setTimeout(forceChatScrollViewport, 200);
    setTimeout(forceChatScrollViewport, 700);
    setTimeout(forceChatScrollViewport, 1400);

    try {
        const chat = document.getElementById("chat");
        if (chat) {
            const observer = new MutationObserver(function () {
                forceChatScrollViewport();
                chat.scrollTop = chat.scrollHeight;
            });

            observer.observe(chat, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }
    } catch (_) {}

    try {
        const input = document.getElementById("input");
        if (input) {
            input.addEventListener("input", scheduleForce);
        }
    } catch (_) {}
})();
