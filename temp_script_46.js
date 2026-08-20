
(function () {
    "use strict";

    if (window.__NOVA_HARD_KILL_CHAT_SUMMARY_STRIP_20260622__) return;
    window.__NOVA_HARD_KILL_CHAT_SUMMARY_STRIP_20260622__ = true;

    function kill() {
        [
            "#novaChatSummaryStrip",
            ".nova-chat-summary-main",
            ".nova-chat-summary-text",
            ".nova-chat-summary-actions"
        ].forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (node) {
                node.remove();
            });
        });
    }

    kill();
    setTimeout(kill, 100);
    setTimeout(kill, 400);
    setTimeout(kill, 1000);
    setTimeout(kill, 2000);

    const observer = new MutationObserver(kill);
    observer.observe(document.documentElement, { childList: true, subtree: true });

    console.log("[Nova hard kill chat summary strip] ready");
})();
