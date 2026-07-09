(function () {
    "use strict";

    if (window.__NOVA_FAQ_PAGE_20260709__) {
        return;
    }

    window.__NOVA_FAQ_PAGE_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-faq-ready", "true");
        console.log("[NOVA FAQ] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
