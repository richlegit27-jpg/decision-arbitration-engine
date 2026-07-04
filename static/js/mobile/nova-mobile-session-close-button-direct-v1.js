(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_BUTTON_DIRECT_V1_20260704__";

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
        }

        if (launcher && typeof launcher.focus === "function") {
            try {
                launcher.focus({ preventScroll: true });
            } catch (err) {
                try {
                    launcher.focus();
                } catch (err2) {}
            }
        }

        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("pointer-events", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");

        panel.setAttribute("aria-hidden", "true");
    }

    function findCloseButton(panel) {
        if (!panel) {
            return null;
        }

        return [...panel.querySelectorAll("button, [role='button']")]
            .find((button) => {
                const label = String(
                    button.getAttribute("aria-label") ||
                    button.textContent ||
                    ""
                ).trim().toLowerCase();

                return label === "close" || label.includes("close");
            });
    }

    function wireCloseButton() {
        const panel = document.getElementById(PANEL_ID);
        const closeButton = findCloseButton(panel);

        if (!panel || !closeButton) {
            return false;
        }

        if (closeButton.dataset.novaDirectCloseWired === "true") {
            return true;
        }

        closeButton.dataset.novaDirectCloseWired = "true";
        closeButton.setAttribute("data-nova-clean-session-close-direct", "true");

        closeButton.onclick = function (event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            hardClosePanel();

            return false;
        };

        closeButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            hardClosePanel();
        }, true);

        console.error("[Nova Session Direct Close] wired close button");

        return true;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaDirectCloseRenderPatched) {
            return true;
        }

        const originalRenderDrawer = api.renderDrawer.bind(api);

        api.renderDrawer = async function () {
            const result = await originalRenderDrawer.apply(api, arguments);

            setTimeout(wireCloseButton, 50);
            setTimeout(wireCloseButton, 250);
            setTimeout(wireCloseButton, 700);

            return result;
        };

        api.__novaDirectCloseRenderPatched = true;

        console.error("[Nova Session Direct Close] patched renderDrawer");

        return true;
    }

    function boot() {
        patchRenderDrawer();
        wireCloseButton();

        setInterval(function () {
            patchRenderDrawer();
            wireCloseButton();
        }, 500);
    }

    window.NovaMobileSessionCloseButtonDirectV1 = {
        version: "session-close-button-direct-v1",
        hardClosePanel,
        wireCloseButton
    };

    boot();

    console.error("[Nova Session Direct Close V1] installed");
})();
