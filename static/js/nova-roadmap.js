(function () {
    "use strict";

    if (window.__NOVA_ROADMAP_PAGE_20260709__) {
        return;
    }

    window.__NOVA_ROADMAP_PAGE_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-roadmap-ready", "true");
        console.log("[NOVA ROADMAP] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
