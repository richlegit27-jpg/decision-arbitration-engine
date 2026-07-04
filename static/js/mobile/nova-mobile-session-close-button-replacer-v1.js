(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_CLOSE_ANY_DRAWER_V4_20260704__";

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

    function looksSessionRelated(el) {
        if (!el) {
            return false;
        }

        const haystack = String(
            (el.id || "") + " " +
            (el.className || "") + " " +
            (el.getAttribute("role") || "") + " " +
            (el.getAttribute("aria-label") || "") + " " +
            (el.getAttribute("data-nova-session-panel") || "") + " " +
            (el.getAttribute("data-nova-clean-session-panel") || "") + " " +
            (el.textContent || "").slice(0, 500)
        ).toLowerCase();

        return (
            haystack.includes("session") ||
            haystack.includes("sessions") ||
            haystack.includes("drawer")
        );
    }

    function findCandidatePanels() {
        const all = Array.from(document.querySelectorAll("aside, dialog, section, nav, div, [role='dialog'], [role='complementary']"));

        return all
            .filter(isVisible)
            .filter(looksSessionRelated)
            .filter(function (el) {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();

                return (
                    style.position === "fixed" ||
                    style.position === "absolute" ||
                    Number(style.zIndex) >= 10 ||
                    rect.width >= 200
                );
            })
            .sort(function (a, b) {
                const az = Number(getComputedStyle(a).zIndex) || 0;
                const bz = Number(getComputedStyle(b).zIndex) || 0;

                return bz - az;
            });
    }

    function isCloseButtonTarget(target) {
        if (!target || !target.closest) {
            return false;
        }

        const button = target.closest("button, [role='button'], a");

        if (!button) {
            return false;
        }

        const label = textOf(button);

        if (!(label === "close" || label.includes("close") || label === "×" || label === "x")) {
            return false;
        }

        return findCandidatePanels().some(function (panel) {
            return panel.contains(button);
        });
    }

    function hardClosePanel() {
        const panels = findCandidatePanels();

        if (!panels.length) {
            console.error("[Nova Session Close Any Drawer V4] no visible session panel found");
            return false;
        }

        panels.forEach(function (panel) {
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
        });

        console.error("[Nova Session Close Any Drawer V4] hard closed panels", panels.length);

        return true;
    }

    function intercept(event) {
        if (!isCloseButtonTarget(event.target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        hardClosePanel();

        return false;
    }

    function replaceCloseButtons() {
        const panels = findCandidatePanels();
        let replaced = 0;

        panels.forEach(function (panel) {
            const buttons = Array.from(panel.querySelectorAll("button, [role='button'], a"));

            buttons.forEach(function (button) {
                const label = textOf(button);

                if (!(label === "close" || label.includes("close") || label === "×" || label === "x")) {
                    return;
                }

                if (button.dataset.novaCloseAnyDrawerV4 === "true") {
                    return;
                }

                const fresh = button.cloneNode(true);

                fresh.dataset.novaCloseAnyDrawerV4 = "true";

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

                button.replaceWith(fresh);
                replaced += 1;
            });
        });

        if (replaced) {
            console.error("[Nova Session Close Any Drawer V4] replaced close buttons", replaced);
        }

        return replaced;
    }

    function patchRenderDrawer() {
        const api = window.NovaMobileSimpleSessionDrawerV1;

        if (!api || typeof api.renderDrawer !== "function") {
            return false;
        }

        if (api.__novaCloseAnyDrawerV4Patched) {
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

        api.__novaCloseAnyDrawerV4Patched = true;

        console.error("[Nova Session Close Any Drawer V4] patched renderDrawer");

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
            attributeFilter: ["style", "class", "aria-hidden"]
        });

        patchRenderDrawer();
        replaceCloseButtons();

        setInterval(function () {
            patchRenderDrawer();
            replaceCloseButtons();
        }, 250);

        console.error("[Nova Session Close Any Drawer V4] installed");
    }

    window.NovaMobileSessionCloseAnyDrawerV4 = {
        version: "session-close-any-drawer-v4",
        findCandidatePanels: findCandidatePanels,
        hardClosePanel: hardClosePanel,
        replaceCloseButtons: replaceCloseButtons,
        patchRenderDrawer: patchRenderDrawer
    };

    boot();
})();
