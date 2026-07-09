(function () {
    "use strict";

    if (window.__NOVA_LANDING_HOME_20260709__) {
        return;
    }

    window.__NOVA_LANDING_HOME_20260709__ = true;

    function markLoaded() {
        document.documentElement.setAttribute("data-nova-home-loaded", "true");
        console.log("[NOVA LANDING HOME] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", markLoaded, { once: true });
    } else {
        markLoaded();
    }
})();
