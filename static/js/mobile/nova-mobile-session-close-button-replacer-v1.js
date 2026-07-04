(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_BUTTON_REPLACER_V1_20260704__";

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

        console.error("[Nova Session Close Replacer] hard closed panel");
    }

    function findCloseButton(panel) {
        if (!panel) {
            return null;
        }

        return [...panel.querySelectorAll("button, [role='button']"]
            .find((button) => {
                const label = String(
                    button.getAttribute("aria-label") ||
                    button.textContent ||
                    ""
                ).trim().toLowerCase();

                return label === "close" || label.includes("close");
            });
    }

    function replaceCloseButton() {
        const panel = document.getElementById(PANEL_ID);
        const oldButton = findCloseButton(panel);

        if (!panel || !oldButton) {
            return false;
        }

        if (oldButton.dataset.novaCloseReplaced === "true") {
            return true;
        }

        const fresh = oldButton.cloneNode(true);

        fresh.dataset.novaCloseReplaced = "true";
        fresh.setAttribute("data-nova-session-close-replacer", "true");

        fresh.onclick = function (event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            hardClosePanel();

            return false;
        };

        ["pointerdown", "touchstart", "mousedown", "click"].forEach((eventName) => {
            fresh.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                hardClosePanel();

                return false;
            }, true);
        });

        oldButton.replaceWith(fresh);

        console.error("[Nova Session Close Replacer] replaced Close button");

        return true;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaCloseReplacerPatched) {
            return true;
        }

        const originalRenderDrawer = api.renderDrawer.bind(api);

        api.renderDrawer = async function () {
            const result = await originalRenderDrawer.apply(api, arguments);

            setTimeout(replaceCloseButton, 10);
            setTimeout(replaceCloseButton, 100);
            setTimeout(replaceCloseButton, 300);
            setTimeout(replaceCloseButton, 800);

            return result;
        };

        api.__novaCloseReplacerPatched = true;

        console.error("[Nova Session Close Replacer] patched renderDrawer");

        return true;
    }

    function boot() {
        patchRenderDrawer();
        replaceCloseButton();

        setInterval(function () {
            patchRenderDrawer();
            replaceCloseButton();
        }, 250);
    }

    window.NovaMobileSessionCloseButtonReplacerV1 = {
        version: "session-close-button-replacer-v1",
        hardClosePanel,
        replaceCloseButton
    };

    boot();

    console.error("[Nova Session Close Button Replacer V1] installed");
})();
