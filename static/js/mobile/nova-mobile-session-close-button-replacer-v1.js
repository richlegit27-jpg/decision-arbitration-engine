(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_BUTTON_CAPTURE_V3_20260704__";

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

    function isCloseButton(node) {
        if (!node || !node.closest) {
            return false;
        }

        const button = node.closest("button, [role='button']");

        if (!button) {
            return false;
        }

        const panel = getPanel();

        if (!panel || !panel.contains(button)) {
            return false;
        }

        const label = String(
            button.getAttribute("aria-label") ||
            button.getAttribute("title") ||
            button.textContent ||
            ""
        ).trim().toLowerCase();

        return label === "close" || label.includes("close");
    }

    function hardClosePanel() {
        const panel = getPanel();
        const launcher = getLauncher();

        if (!panel) {
            return false;
        }

        const active = document.activeElement;

        if (active && panel.contains(active)) {
            try {
                active.blur();
            } catch (err) {}
        }

        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("pointer-events", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");
        panel.style.setProperty("transform", "translateX(-120%)", "important");
        panel.setAttribute("aria-hidden", "true");
        panel.dataset.novaForceClosed = "true";

        if (launcher && typeof launcher.focus === "function") {
            try {
                launcher.focus({ preventScroll: true });
            } catch (err) {
                try {
                    launcher.focus();
                } catch (err2) {}
            }
        }

        console.error("[Nova Session Close Capture V3] hard closed panel");

        return true;
    }

    function interceptClose(event) {
        if (!isCloseButton(event.target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        hardClosePanel();

        return false;
    }

    function findCloseButton() {
        const panel = getPanel();

        if (!panel) {
            return null;
        }

        return Array.from(panel.querySelectorAll("button, [role='button']")).find(function (button) {
            const label = String(
                button.getAttribute("aria-label") ||
                button.getAttribute("title") ||
                button.textContent ||
                ""
            ).trim().toLowerCase();

            return label === "close" || label.includes("close");
        }) || null;
    }

    function replaceCloseButton() {
        const oldButton = findCloseButton();

        if (!oldButton) {
            return false;
        }

        if (oldButton.dataset.novaCloseCaptureV3 === "true") {
            return true;
        }

        const fresh = oldButton.cloneNode(true);

        fresh.dataset.novaCloseCaptureV3 = "true";
        fresh.setAttribute("data-nova-session-close-capture-v3", "true");

        fresh.onclick = function (event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            hardClosePanel();

            return false;
        };

        ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (eventName) {
            fresh.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                hardClosePanel();

                return false;
            }, true);
        });

        oldButton.replaceWith(fresh);

        console.error("[Nova Session Close Capture V3] replaced Close button");

        return true;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaCloseCaptureV3Patched) {
            return true;
        }

        const originalRenderDrawer = api.renderDrawer.bind(api);

        api.renderDrawer = async function () {
            const result = await originalRenderDrawer.apply(api, arguments);

            setTimeout(replaceCloseButton, 0);
            setTimeout(replaceCloseButton, 25);
            setTimeout(replaceCloseButton, 100);
            setTimeout(replaceCloseButton, 300);
            setTimeout(replaceCloseButton, 800);

            return result;
        };

        api.__novaCloseCaptureV3Patched = true;

        console.error("[Nova Session Close Capture V3] patched renderDrawer");

        return true;
    }

    function boot() {
        ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (eventName) {
            document.addEventListener(eventName, interceptClose, true);
            window.addEventListener(eventName, interceptClose, true);
        });

        const observer = new MutationObserver(function () {
            patchRenderDrawer();
            replaceCloseButton();
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });

        patchRenderDrawer();
        replaceCloseButton();

        setInterval(function () {
            patchRenderDrawer();
            replaceCloseButton();
        }, 250);

        console.error("[Nova Session Close Capture V3] installed");
    }

    window.NovaMobileSessionCloseButtonCaptureV3 = {
        version: "session-close-button-capture-v3",
        hardClosePanel: hardClosePanel,
        replaceCloseButton: replaceCloseButton,
        patchRenderDrawer: patchRenderDrawer
    };

    boot();
})();
