(function () {
    "use strict";

    if (window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_NO_SHAKE_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_NO_SHAKE_20260705__ = true;

    function log() {
        try {
            console.log.apply(console, ["[Nova Plus Menu No Shake]"].concat([].slice.call(arguments)));
        } catch (_) {}
    }

    function isVisible(el) {
        if (!el) {
            return false;
        }

        var s = getComputedStyle(el);
        var r = el.getBoundingClientRect();

        return (
            s.display !== "none" &&
            s.visibility !== "hidden" &&
            s.opacity !== "0" &&
            r.width > 0 &&
            r.height > 0
        );
    }

    function findPlusButton() {
        return (
            document.getElementById("nova-mobile-attach") ||
            document.querySelector("[data-mobile-tool='attach']") ||
            document.querySelector("[data-mobile-tool='plus']") ||
            document.querySelector("[aria-label='Attach']") ||
            document.querySelector("[aria-label='Add']")
        );
    }

    function findUploadButton() {
        var direct = document.querySelector("[data-mobile-tool='upload']");

        if (direct) {
            return direct;
        }

        var buttons = [].slice.call(document.querySelectorAll("button, a, [role='button']"));

        return buttons.find(function (el) {
            var haystack = [
                el.id || "",
                el.className || "",
                el.getAttribute("aria-label") || "",
                el.getAttribute("title") || "",
                el.textContent || ""
            ].join(" ").toLowerCase();

            return /upload|file|image|photo|attach/.test(haystack);
        }) || null;
    }

    function looksLikeMenu(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return false;
        }

        var haystack = [
            el.id || "",
            el.className || "",
            el.getAttribute("role") || "",
            el.getAttribute("data-mobile-menu") || "",
            el.getAttribute("data-nova-menu") || "",
            el.getAttribute("data-menu") || ""
        ].join(" ").toLowerCase();

        return /menu|sheet|drawer|popover|popup|tools|attach|upload|composer/.test(haystack);
    }

    function findMenuFromUploadButton(uploadButton) {
        var el = uploadButton;

        while (el && el !== document.body && el !== document.documentElement) {
            if (looksLikeMenu(el)) {
                return el;
            }

            el = el.parentElement;
        }

        return uploadButton ? uploadButton.parentElement : null;
    }

    function revealNode(node) {
        if (!node) {
            return;
        }

        try {
            node.hidden = false;
            node.removeAttribute("hidden");
            node.removeAttribute("aria-hidden");
            node.style.display = node.tagName === "BUTTON" ? "inline-flex" : "flex";
            node.style.visibility = "visible";
            node.style.opacity = "1";
            node.style.pointerEvents = "auto";
            node.style.transform = "none";
            node.classList.add("open", "is-open", "visible", "is-visible", "active");
        } catch (_) {}
    }

    function openMenu() {
        var uploadButton = findUploadButton();

        if (!uploadButton) {
            log("upload button not found");
            return false;
        }

        var menu = findMenuFromUploadButton(uploadButton);

        revealNode(menu);
        revealNode(uploadButton);

        try {
            document.body.classList.add("nova-mobile-plus-menu-open");
        } catch (_) {}

        log("opened menu");
        return true;
    }

    function closeMenuIfOutside(target) {
        var plus = findPlusButton();
        var upload = findUploadButton();
        var menu = findMenuFromUploadButton(upload);

        if (
            target === plus ||
            target === upload ||
            (plus && plus.contains(target)) ||
            (upload && upload.contains(target)) ||
            (menu && menu.contains(target))
        ) {
            return;
        }

        try {
            document.body.classList.remove("nova-mobile-plus-menu-open");
        } catch (_) {}
    }

    function bindPlusButton() {
        var plus = findPlusButton();

        if (!plus || plus.__novaPlusNoShakeBound) {
            return;
        }

        plus.__novaPlusNoShakeBound = true;

        plus.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            openMenu();

            return false;
        }, true);

        log("bound plus button");
    }

    document.addEventListener("click", function (event) {
        closeMenuIfOutside(event.target);
    }, true);

    function boot() {
        bindPlusButton();
    }

    boot();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    }

    window.addEventListener("load", boot);

    setTimeout(boot, 250);
    setTimeout(boot, 750);
    setTimeout(boot, 1500);

    window.NovaMobilePlusMenuReliabilityV1 = {
        findPlusButton: findPlusButton,
        findUploadButton: findUploadButton,
        findMenuFromUploadButton: findMenuFromUploadButton,
        openMenu: openMenu,
        bindPlusButton: bindPlusButton,
        isVisible: isVisible
    };

    log("installed");
})();
