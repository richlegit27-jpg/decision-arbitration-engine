
(function () {
    "use strict";

    if (window.__NOVA_FRONTEND_SOURCE_CARD_SCOPE_GUARD_20260622__) return;
    window.__NOVA_FRONTEND_SOURCE_CARD_SCOPE_GUARD_20260622__ = true;

    const USER_SELECTORS = [
        ".user",
        ".user-message",
        ".message.user",
        ".chat-message.user",
        ".desktop-user-message",
        "[data-role='user']"
    ].join(",");

    const SOURCE_SELECTORS = [
        ".source-card",
        ".source-cards",
        ".sourceCards",
        ".desktop-source-card",
        ".desktop-source-cards",
        ".nova-source-card",
        ".nova-source-cards",
        ".web-source-card",
        ".web-source-cards",
        ".live-source-card",
        ".live-source-cards",
        "[data-source-card]",
        "[data-source-url]"
    ].join(",");

    function wantsLiveWeb(text) {
        const t = String(text || "").toLowerCase();

        return [
            "latest",
            "today's",
            "todays",
            "current",
            "right now",
            "breaking",
            "news",
            "headline",
            "headlines",
            "look up",
            "lookup",
            "search",
            "web fetch",
            "browse",
            "google",
            "online",
            "recent",
            "source",
            "sources",
            "article",
            "who won",
            "score",
            "weather",
            "stock price"
        ].some(term => t.includes(term));
    }

    function lastUserText() {
        const users = Array.from(document.querySelectorAll(USER_SELECTORS));
        const last = users[users.length - 1];
        return last ? String(last.innerText || last.textContent || "").trim() : "";
    }

    function cleanLeakedSourceCards() {
        const text = lastUserText();

        if (!text || wantsLiveWeb(text)) return;

        document.querySelectorAll(SOURCE_SELECTORS).forEach(el => {
            el.remove();
        });
    }

    cleanLeakedSourceCards();

    const observer = new MutationObserver(() => {
        cleanLeakedSourceCards();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    console.log("[Nova] frontend source-card scope guard ready");
})();
