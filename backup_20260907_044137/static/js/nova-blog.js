(function () {
    "use strict";

    if (window.__NOVA_BLOG_PAGE_20260709__) {
        return;
    }

    window.__NOVA_BLOG_PAGE_20260709__ = true;

    function boot() {
        document.documentElement.setAttribute("data-nova-blog-ready", "true");
        console.log("[NOVA BLOG] page ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
