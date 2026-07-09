(function () {
    "use strict";

    if (window.__NOVA_LEGAL_PAGE_20260709__) {
        return;
    }

    window.__NOVA_LEGAL_PAGE_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-legal-ready", "true");
        console.log("[NOVA LEGAL] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
