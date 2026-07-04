(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_HARD_CLOSE_OVERRIDE_V2_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    const PANEL_ID = "nova-clean-session-panel-v2";
    const BUTTON_ID = "nova-clean-session-launcher-v2";

    function getPanel() {
        return document.getElementById(PANEL_ID);
    }

    function getLauncher() {
        return document.getElementById(BUTTON_ID);
    }

    function hardClosePanel() {
        const panel = getPanel();
        const launcher = getLauncher();

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

    function normalizeOpenPanel() {
        const panel = getPanel();

        if (!panel) {
            return;
        }

        const style = getComputedStyle(panel);
        const isVisible =
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0";

        if (!isVisible) {
            return;
        }

        if (panel.getAttribute("aria-hidden") === "true") {
            const active = document.activeElement;

            if (active && panel.contains(active)) {
                hardClosePanel();
                return;
            }

            panel.removeAttribute("aria-hidden");
            panel.removeAttribute("inert");
        }
    }

    function isCloseClickTarget(target) {
        const panel = getPanel();

        if (!panel || !target || !target.closest) {
            return false;
        }

        const button = target.closest("button, [role='button'], [aria-label]");

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
            label.includes("close")
        );
    }

    document.addEventListener("click", function (event) {
        if (!isCloseClickTarget(event.target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        hardClosePanel();
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            hardClosePanel();
        }
    }, true);

    function bootObserver() {
        const panel = getPanel();

        if (!panel) {
            setTimeout(bootObserver, 250);
            return;
        }

        const observer = new MutationObserver(function () {
            normalizeOpenPanel();
        });

        observer.observe(panel, {
            attributes: true,
            attributeFilter: ["style", "aria-hidden", "inert"]
        });

        setInterval(normalizeOpenPanel, 500);
    }

    bootObserver();

    window.NovaMobileSessionHardCloseOverrideV2 = {
        version: "session-hard-close-override-v2",
        hardClosePanel: hardClosePanel
    };

    console.error("[Nova Session Hard Close Override V2] installed");
})();
