(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_REMOVE_DRAWER_V5_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    function labelOf(el) {
        return String(
            (el && (
                el.getAttribute("aria-label") ||
                el.getAttribute("title") ||
                el.textContent ||
                ""
            )) ||
            ""
        ).trim().toLowerCase();
    }

    function metaOf(el) {
        return String(
            (el && (
                (el.id || "") + " " +
                (el.className || "") + " " +
                (el.getAttribute("role") || "") + " " +
                (el.getAttribute("aria-label") || "") + " " +
                (el.getAttribute("data-nova-session-panel") || "") + " " +
                (el.getAttribute("data-nova-clean-session-panel") || "")
            )) ||
            ""
        ).toLowerCase();
    }

    function isCloseLike(button) {
        const label = labelOf(button);
        return label === "close" || label.includes("close") || label === "×" || label === "x";
    }

    function isSessionPanelLike(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return false;
        }

        const meta = metaOf(el);
        const text = String(el.textContent || "").toLowerCase().slice(0, 1000);
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        const namedLikePanel =
            meta.includes("session") ||
            meta.includes("drawer") ||
            meta.includes("panel");

        const contentLikePanel =
            text.includes("session") &&
            (
                text.includes("new chat") ||
                text.includes("rename") ||
                text.includes("pin") ||
                text.includes("delete") ||
                text.includes("close")
            );

        const positionedLikeDrawer =
            style.position === "fixed" ||
            style.position === "absolute" ||
            style.position === "sticky" ||
            Number(style.zIndex) >= 10 ||
            el.getAttribute("role") === "dialog";

        return (
            rect.width > 0 &&
            rect.height > 0 &&
            positionedLikeDrawer &&
            (namedLikePanel || contentLikePanel)
        );
    }

    function findPanelForButton(button) {
        let el = button;

        while (el && el !== document.body && el !== document.documentElement) {
            if (isSessionPanelLike(el)) {
                return el;
            }

            el = el.parentElement;
        }

        return null;
    }

    function findCloseButtons() {
        return Array.from(document.querySelectorAll("button, [role='button'], a")).filter(function (button) {
            if (!isCloseLike(button)) {
                return false;
            }

            return !!findPanelForButton(button);
        });
    }

    function removePanel(panel) {
        if (!panel || !panel.parentNode) {
            return false;
        }

        try {
            const active = document.activeElement;

            if (active && panel.contains(active)) {
                active.blur();
            }
        } catch (err) {}

        panel.remove();

        console.error("[Nova Session Close Remove V5] removed drawer panel");

        return true;
    }

    function hardClosePanelFromTarget(target) {
        const button = target && target.closest
            ? target.closest("button, [role='button'], a")
            : null;

        const panel = button ? findPanelForButton(button) : null;

        if (panel) {
            return removePanel(panel);
        }

        const buttons = findCloseButtons();

        if (buttons.length) {
            const fallbackPanel = findPanelForButton(buttons[0]);
            return removePanel(fallbackPanel);
        }

        console.error("[Nova Session Close Remove V5] no close panel found");
        return false;
    }

    function intercept(event) {
        const button = event.target && event.target.closest
            ? event.target.closest("button, [role='button'], a")
            : null;

        if (!button || !isCloseLike(button) || !findPanelForButton(button)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        hardClosePanelFromTarget(button);

        return false;
    }

    function replaceCloseButtons() {
        let replaced = 0;

        findCloseButtons().forEach(function (button) {
            if (button.dataset.novaCloseRemoveV5 === "true") {
                return;
            }

            const fresh = button.cloneNode(true);

            fresh.dataset.novaCloseRemoveV5 = "true";

            fresh.onclick = function (event) {
                if (event) {
                    event.preventDefault();
                    event.stopPropagation();
                }

                hardClosePanelFromTarget(fresh);

                return false;
            };

            ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (eventName) {
                fresh.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();

                    hardClosePanelFromTarget(fresh);

                    return false;
                }, true);
            });

            button.replaceWith(fresh);
            replaced += 1;
        });

        if (replaced) {
            console.error("[Nova Session Close Remove V5] replaced close buttons", replaced);
        }

        return replaced;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaCloseRemoveV5Patched) {
            return true;
        }

        const originalRenderDrawer = api.renderDrawer.bind(api);

        api.renderDrawer = async function () {
            const result = await originalRenderDrawer.apply(api, arguments);

            setTimeout(replaceCloseButtons, 0);
            setTimeout(replaceCloseButtons, 25);
            setTimeout(replaceCloseButtons, 100);
            setTimeout(replaceCloseButtons, 300);
            setTimeout(replaceCloseButtons, 800);

            return result;
        };

        api.__novaCloseRemoveV5Patched = true;

        console.error("[Nova Session Close Remove V5] patched renderDrawer");

        return true;
    }

    function boot() {
        ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (eventName) {
            document.addEventListener(eventName, intercept, true);
            window.addEventListener(eventName, intercept, true);
        });

        const observer = new MutationObserver(function () {
            patchRenderDrawer();
            replaceCloseButtons();
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });

        patchRenderDrawer();
        replaceCloseButtons();

        setInterval(function () {
            patchRenderDrawer();
            replaceCloseButtons();
        }, 250);

        console.error("[Nova Session Close Remove V5] installed");
    }

    window.NovaMobileSessionCloseRemoveV5 = {
        version: "session-close-remove-v5",
        replaceCloseButtons: replaceCloseButtons,
        patchRenderDrawer: patchRenderDrawer
    };

    boot();
})();
