(function () {
    "use strict";

    if (window.__NOVA_LANDING_HOME_SUPERPOWER_20260709__) {
        return;
    }

    window.__NOVA_LANDING_HOME_SUPERPOWER_20260709__ = true;

    function markLoaded() {
        document.documentElement.setAttribute("data-nova-home-loaded", "true");
        console.log("[NOVA LANDING HOME] superpower phase 2 ready");
    }

    function setupReveal() {
        var targets = Array.prototype.slice.call(document.querySelectorAll(
            ".nova-section, .nova-workflow, .nova-builder, .nova-command-card"
        ));

        targets.forEach(function (target) {
            target.setAttribute("data-nova-reveal", "pending");
        });

        if (!("IntersectionObserver" in window)) {
            targets.forEach(function (target) {
                target.setAttribute("data-nova-reveal", "in");
            });
            return;
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) {
                    return;
                }

                entry.target.setAttribute("data-nova-reveal", "in");
                observer.unobserve(entry.target);
            });
        }, {
            root: null,
            threshold: 0.12
        });

        targets.forEach(function (target) {
            observer.observe(target);
        });
    }

    function boot() {
        markLoaded();
        setupReveal();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
