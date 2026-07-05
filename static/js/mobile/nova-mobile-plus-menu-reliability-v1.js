/* NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705 */
(function installNovaMobilePlusMenuReliabilityV1() {
    "use strict";

    if (window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705__ = true;

    let fallbackClickInProgress = false;
    let lastRealTapAt = 0;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    function getPlusButton() {
        return (
            document.getElementById("nova-mobile-attach") ||
            document.querySelector(".nova-mobile-attach-action") ||
            document.querySelector(".nova-mobile-attach")
        );
    }

    function textOf(el) {
        return [
            el.id || "",
            el.className || "",
            el.getAttribute("title") || "",
            el.getAttribute("aria-label") || "",
            el.getAttribute("data-action") || "",
            el.getAttribute("data-nova-action") || "",
            el.textContent || ""
        ].join(" ").toLowerCase();
    }

    function isVisible(el) {
        if (!el) return false;

        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || "1") !== 0 &&
            rect.width > 0 &&
            rect.height > 0
        );
    }

    function findVisibleUploadMenuButton() {
        const candidates = Array.from(document.querySelectorAll("button, a, label, [role='button']"));

        return candidates.find(function (el) {
            if (!el) return false;
            if (el.id === "nova-mobile-attach") return false;

            const text = textOf(el);

            return isVisible(el) && /(upload|image|photo|file|attach)/i.test(text);
        }) || null;
    }

    function hardenPlusButton(button) {
        if (!button) return;

        try {
            button.disabled = false;
            button.removeAttribute("disabled");
            button.style.pointerEvents = "auto";
            button.style.touchAction = "manipulation";
            button.style.webkitTapHighlightColor = "transparent";
            button.style.position = button.style.position || "relative";
            button.style.zIndex = "2147483647";
        } catch (_) {}
    }

    function handlePlusClick(event) {
        const button = getPlusButton();

        if (!button) return;

        hardenPlusButton(button);

        if (fallbackClickInProgress) {
            return;
        }

        const now = Date.now();

        if (now - lastRealTapAt < 500) {
            return;
        }

        lastRealTapAt = now;

        setTimeout(function () {
            const visibleUpload = findVisibleUploadMenuButton();

            if (visibleUpload) {
                log("[Nova Plus Menu Reliability] menu opened normally", visibleUpload);
                return;
            }

            const freshButton = getPlusButton();

            if (!freshButton) {
                log("[Nova Plus Menu Reliability] no plus button for fallback");
                return;
            }

            log("[Nova Plus Menu Reliability] first tap did not open menu, firing one fallback click");

            fallbackClickInProgress = true;

            try {
                freshButton.dispatchEvent(new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    view: window
                }));
            } catch (error) {
                console.error("[Nova Plus Menu Reliability] fallback click failed", error);
            }

            setTimeout(function () {
                fallbackClickInProgress = false;
            }, 250);
        }, 140);
    }

    function bind() {
        const button = getPlusButton();

        if (!button) {
            return false;
        }

        hardenPlusButton(button);

        if (button.dataset.novaPlusMenuReliabilityBound === "1") {
            return true;
        }

        button.dataset.novaPlusMenuReliabilityBound = "1";
        button.addEventListener("click", handlePlusClick, false);

        log("[Nova Plus Menu Reliability] bound");

        return true;
    }

    function bindLoop() {
        bind();
        setTimeout(bind, 300);
        setTimeout(bind, 1000);
        setTimeout(bind, 2500);
    }

    document.addEventListener("DOMContentLoaded", bindLoop);
    window.addEventListener("load", bindLoop);

    new MutationObserver(bind).observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
    });

    bindLoop();

    window.NovaMobilePlusMenuReliabilityV1 = {
        version: "NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705",
        bind: bind,
        findVisibleUploadMenuButton: findVisibleUploadMenuButton
    };

    log("[Nova Plus Menu Reliability] installed");
})();
