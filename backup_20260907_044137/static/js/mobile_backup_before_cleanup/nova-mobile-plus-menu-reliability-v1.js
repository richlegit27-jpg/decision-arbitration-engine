(function () {
    "use strict";

    if (window.__NOVA_MOBILE_PLUS_MENU_HARD_NO_SHAKE_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_PLUS_MENU_HARD_NO_SHAKE_20260705__ = true;

    var lastOpenAt = 0;

    function log() {
        try {
            console.log.apply(console, ["[Nova Plus Menu Hard No Shake]"].concat([].slice.call(arguments)));
        } catch (_) {}
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
        return (
            document.querySelector("[data-mobile-tool='upload']") ||
            [].slice.call(document.querySelectorAll("button, a, [role='button']")).find(function (el) {
                var haystack = [
                    el.id || "",
                    el.className || "",
                    el.getAttribute("aria-label") || "",
                    el.getAttribute("title") || "",
                    el.textContent || ""
                ].join(" ").toLowerCase();

                return /upload|file|image|photo/.test(haystack);
            }) ||
            null
        );
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
            node.style.animation = "none";
            node.style.transitionProperty = "opacity, visibility";
            node.classList.add("open", "is-open", "visible", "is-visible", "active");
        } catch (_) {}
    }

    function calmPlusButton() {
        var plus = findPlusButton();

        if (!plus) {
            return;
        }

        try {
            plus.style.transform = "none";
            plus.style.animation = "none";
            plus.style.transitionProperty = "background-color, color, border-color, opacity";
            plus.classList.remove(
                "shake",
                "shaking",
                "is-shaking",
                "nova-shake",
                "nova-mobile-shake",
                "bounce",
                "bouncing",
                "pulse",
                "pulsing",
                "active"
            );
        } catch (_) {}
    }

    function openMenu() {
        var now = Date.now();

        if (now - lastOpenAt < 180) {
            calmPlusButton();
            return true;
        }

        lastOpenAt = now;

        var uploadButton = findUploadButton();

        if (!uploadButton) {
            calmPlusButton();
            log("upload button not found");
            return false;
        }

        var menu = findMenuFromUploadButton(uploadButton);

        revealNode(menu);
        revealNode(uploadButton);
        calmPlusButton();

        try {
            document.body.classList.add("nova-mobile-plus-menu-open");
        } catch (_) {}

        log("opened menu");
        return true;
    }

    function isPlusTarget(target) {
        var plus = findPlusButton();

        return !!(
            plus &&
            (
                target === plus ||
                plus.contains(target)
            )
        );
    }

    function stopPlusEvent(event) {
        if (!isPlusTarget(event.target)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        calmPlusButton();
        openMenu();

        return false;
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

    function bindHardCapture() {
        if (window.__NOVA_MOBILE_PLUS_HARD_CAPTURE_BOUND_20260705__) {
            return;
        }

        window.__NOVA_MOBILE_PLUS_HARD_CAPTURE_BOUND_20260705__ = true;

        ["pointerdown", "touchstart", "mousedown", "click"].forEach(function (type) {
            document.addEventListener(type, stopPlusEvent, true);
        });

        document.addEventListener("click", function (event) {
            closeMenuIfOutside(event.target);
        }, true);

        log("hard capture bound");
    }

    function boot() {
        calmPlusButton();
        bindHardCapture();
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
        calmPlusButton: calmPlusButton
    };

    log("installed");
})();
