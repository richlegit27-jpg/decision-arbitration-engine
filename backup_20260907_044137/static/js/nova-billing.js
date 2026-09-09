(function () {
    "use strict";

    if (window.__NOVA_BILLING_DASHBOARD_20260709__) {
        return;
    }

    window.__NOVA_BILLING_DASHBOARD_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-billing-ready", "true");
        console.log("[NOVA BILLING] dashboard phase 1 ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
