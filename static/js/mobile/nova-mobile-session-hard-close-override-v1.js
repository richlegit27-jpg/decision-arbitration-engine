(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_HARD_CLOSE_OVERRIDE_V1_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    const PANEL_ID = "nova-clean-session-panel-v2";
    const BUTTON_ID = "nova-clean-session-launcher-v2";

    function hardClosePanel() {
        const panel = document.getElementById(PANEL_ID);
        const launcher = document.getElementById(BUTTON_ID);

        if (!panel) {
            return;
        }

        const active = document.activeElement;

        if (active && panel.contains(active)) {
            try {
                active.blur();
            } catch (err) {}

            if (launcher && typeof launcher.focus === "function") {
                try {
                    launcher.focus({ preventScroll: true });
                } catch (err) {
                    try {
                        launcher.focus();
                    } catch (err2) {}
                }
            }
        }

        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("pointer-events", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");

        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("inert", "");
    }

    function isCloseTarget(target) {
        const panel = document.getElementById(PANEL_ID);

        if (!panel || !target || !target.closest) {
            return false;
        }

        const button = target.closest(
            "button, [role='button'], [aria-label], [data-nova-clean-session-close-v3]"
        );

        if (!button || !panel.contains(button)) {
            return false;
        }

        const label = String(
            button.getAttribute("aria-label") ||
            button.textContent ||
            ""
        ).trim().toLowerCase();

        return (
            label === "close" ||
            label === "x" ||
            label === "×" ||
            label.includes("close") ||
            button.getAttribute("data-nova-clean-session-close-v3") === "true"
        );
    }

    document.addEventListener("click", function (event) {
        if (!isCloseTarget(event.target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        hardClosePanel();
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }

        const panel = document.getElementById(PANEL_ID);

        if (!panel) {
            return;
        }

        const style = getComputedStyle(panel);

        if (style.display === "none") {
            return;
        }

        hardClosePanel();
    }, true);

    function watchPanel() {
        const panel = document.getElementById(PANEL_ID);

        if (!panel) {
            setTimeout(watchPanel, 250);
            return;
        }

        const observer = new MutationObserver(function () {
            const style = getComputedStyle(panel);

            if (
                panel.getAttribute("aria-hidden") === "true" &&
                style.display !== "none"
            ) {
                hardClosePanel();
            }
        });

        observer.observe(panel, {
            attributes: true,
            attributeFilter: ["aria-hidden"]
        });
    }

    watchPanel();

    window.NovaMobileSessionHardCloseOverrideV1 = {
        version: "session-hard-close-override-v1",
        hardClosePanel
    };

    console.error("[Nova Session Hard Close Override V1] installed");
})();