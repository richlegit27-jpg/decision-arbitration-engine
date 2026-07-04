(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_REMOVE_DRAWER_V6_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    function textOf(el) {
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

    function isVisible(el) {
        if (!el) {
            return false;
        }

        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0" &&
            rect.width > 0 &&
            rect.height > 0
        );
    }

    function isExactCloseButton(el) {
        const label = textOf(el);

        return (
            label === "close" ||
            label === "×" ||
            label === "x"
        );
    }

    function looksLikeSessionDrawer(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return false;
        }

        const meta = String(
            (el.id || "") + " " +
            (el.className || "") + " " +
            (el.getAttribute("role") || "") + " " +
            (el.getAttribute("aria-label") || "")
        ).toLowerCase();

        const text = String(el.textContent || "").toLowerCase();

        const hasSessionMeta =
            meta.includes("session") ||
            meta.includes("drawer") ||
            meta.includes("nova-clean");

        const hasSessionActions =
            text.includes("new chat") ||
            text.includes("rename") ||
            text.includes("pin") ||
            text.includes("delete") ||
            text.includes("clean start");

        const hasClose =
            text.includes("close");

        return hasClose && (hasSessionMeta || hasSessionActions);
    }

    function findDrawerForCloseButton(button) {
        let el = button;

        while (el && el !== document.body && el !== document.documentElement) {
            if (looksLikeSessionDrawer(el)) {
                return el;
            }

            el = el.parentElement;
        }

        return null;
    }

    function findCloseButtons() {
        return Array.from(document.querySelectorAll("button, [role='button'], a")).filter(function (button) {
            return isVisible(button) && isExactCloseButton(button) && !!findDrawerForCloseButton(button);
        });
    }

    function removeDrawer(drawer) {
        if (!drawer || !drawer.parentNode) {
            return false;
        }

        try {
            const active = document.activeElement;

            if (active && drawer.contains(active)) {
                active.blur();
            }
        } catch (err) {}

        drawer.remove();

        console.error("[Nova Session Close Remove V6] removed drawer");

        return true;
    }

    function closeFromButton(button) {
        const drawer = findDrawerForCloseButton(button);

        if (!drawer) {
            console.error("[Nova Session Close Remove V6] no drawer found for close button", button);
            return false;
        }

        return removeDrawer(drawer);
    }

    function intercept(event) {
        const button = event.target && event.target.closest
            ? event.target.closest("button, [role='button'], a")
            : null;

        if (!button || !isVisible(button) || !isExactCloseButton(button)) {
            return;
        }

        if (!findDrawerForCloseButton(button)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        closeFromButton(button);

        return false;
    }

    function replaceCloseButtons() {
        let replaced = 0;

        findCloseButtons().forEach(function (button) {
            if (button.dataset.novaCloseRemoveV6 === "true") {
                return;
            }

            const fresh = button.cloneNode(true);

            fresh.dataset.novaCloseRemoveV6 = "true";
            fresh.removeAttribute("onclick");

            fresh.onclick = function (event) {
                if (event) {
                    event.preventDefault();
                    event.stopPropagation();
                }

                closeFromButton(fresh);

                return false;
            };

            ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (eventName) {
                fresh.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();

                    closeFromButton(fresh);

                    return false;
                }, true);
            });

            button.replaceWith(fresh);
            replaced += 1;
        });

        if (replaced) {
            console.error("[Nova Session Close Remove V6] replaced close buttons", replaced);
        }

        return replaced;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaCloseRemoveV6Patched) {
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

        api.__novaCloseRemoveV6Patched = true;

        console.error("[Nova Session Close Remove V6] patched renderDrawer");

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
            subtree: true,
            attributes: true,
            attributeFilter: ["style", "class"]
        });

        patchRenderDrawer();
        replaceCloseButtons();

        setInterval(function () {
            patchRenderDrawer();
            replaceCloseButtons();
        }, 250);

        console.error("[Nova Session Close Remove V6] installed");
    }

    window.NovaMobileSessionCloseRemoveV6 = {
        version: "session-close-remove-v6",
        replaceCloseButtons: replaceCloseButtons,
        findCloseButtons: findCloseButtons
    };

    boot();
})();
