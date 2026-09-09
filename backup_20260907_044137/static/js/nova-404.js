(function () {
    "use strict";

    if (window.__NOVA_PUBLIC_404_20260709__) {
        return;
    }

    window.__NOVA_PUBLIC_404_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-404-ready", "true");
        console.log("[NOVA 404] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
