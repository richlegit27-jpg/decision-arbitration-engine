(function () {
    "use strict";

    if (window.NovaMobileLayout) {
        return;
    }

    function updateGeometry() {
        const chat =
            document.getElementById("mobileChatMessages");

        const composer =
            document.getElementById("nova-mobile-composer");

        if (!chat || !composer) {
            return;
        }

        const viewportHeight =
            window.visualViewport?.height ||
            window.innerHeight ||
            0;

        const composerRect =
            composer.getBoundingClientRect();

        const composerHeight =
            Math.round(
                composerRect.height || 150
            );

        document.documentElement.style.setProperty(
            "--nova-mobile-composer-live-height",
            composerHeight + "px"
        );

        chat.style.paddingBottom =
            composerHeight + "px";

        window.__novaMobileViewportHeight =
            viewportHeight;
    }

    function init() {
        updateGeometry();

        window.addEventListener(
            "resize",
            updateGeometry,
            { passive: true }
        );

        if (window.visualViewport) {
            window.visualViewport.addEventListener(
                "resize",
                updateGeometry,
                { passive: true }
            );

            window.visualViewport.addEventListener(
                "scroll",
                updateGeometry,
                { passive: true }
            );
        }

        const composer =
            document.getElementById(
                "nova-mobile-composer"
            );

        if (
            composer &&
            window.ResizeObserver
        ) {
            new ResizeObserver(
                updateGeometry
            ).observe(composer);
        }
    }

    window.NovaMobileLayout = {
        init,
        updateGeometry
    };

    document.addEventListener(
        "DOMContentLoaded",
        init,
        { once: true }
    );

})();