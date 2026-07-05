/* NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705 */
(function installNovaMobilePlusMenuReliabilityV1() {
    "use strict";

    if (window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705__ = true;

    const TAG = "[Nova Plus Menu Reliability]";

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

    function findUploadButton() {
        return (
            document.querySelector("[data-mobile-tool='upload']") ||
            Array.from(document.querySelectorAll("button, a, [role='button']")).find(function (el) {
                const text = [
                    el.textContent || "",
                    el.getAttribute("aria-label") || "",
                    el.getAttribute("title") || ""
                ].join(" ");

                return /upload|file|image|photo/i.test(text) && el.id !== "nova-mobile-attach";
            }) ||
            null
        );
    }

    function findMenuFromUploadButton(uploadButton) {
        if (!uploadButton) {
            return null;
        }

        return (
            uploadButton.closest("[data-mobile-tools-menu]") ||
            uploadButton.closest("[data-nova-tools-menu]") ||
            uploadButton.closest(".nova-mobile-tools-menu") ||
            uploadButton.closest(".mobile-tools-menu") ||
            uploadButton.closest(".nova-mobile-attachment-menu") ||
            uploadButton.parentElement
        );
    }

    function showMenu(menu, button) {
        if (!menu) {
            return false;
        }

        menu.hidden = false;
        menu.removeAttribute("hidden");
        menu.setAttribute("aria-hidden", "false");

        menu.style.display = "flex";
        menu.style.visibility = "visible";
        menu.style.opacity = "1";
        menu.style.pointerEvents = "auto";

        menu.classList.add("open", "is-open", "active", "visible", "show");

        if (button) {
            button.setAttribute("aria-expanded", "true");
        }

        return true;
    }

    function handlePlusClick(event) {
        const button = getPlusButton();

        if (!button) {
            return;
        }

        if (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
        }

        const uploadButton = findUploadButton();
        const menu = findMenuFromUploadButton(uploadButton);

        if (showMenu(menu, button)) {
            log(TAG, "opened upload menu");
            return false;
        }

        if (window.NovaMobileUpload && typeof window.NovaMobileUpload.openUploadPicker === "function") {
            log(TAG, "menu missing, opening upload picker directly as fallback");
            window.NovaMobileUpload.openUploadPicker();
            return false;
        }

        log(TAG, "no upload menu or upload picker found");
        return false;
    }

    function bind() {
        const button = getPlusButton();

        if (!button) {
            return false;
        }

        button.disabled = false;
        button.removeAttribute("disabled");
        button.style.pointerEvents = "auto";

        if (button.dataset.novaPlusMenuReliabilityBound === "1") {
            return true;
        }

        button.dataset.novaPlusMenuReliabilityBound = "1";

        button.onclick = handlePlusClick;
        button.addEventListener("pointerdown", handlePlusClick, true);
        button.addEventListener("click", handlePlusClick, true);
        button.addEventListener("touchend", handlePlusClick, true);

        log(TAG, "bound menu opener");
        return true;
    }

    function bindLoop() {
        bind();
        setTimeout(bind, 300);
        setTimeout(bind, 1000);
    }

    bindLoop();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindLoop);
    }

    window.NovaMobilePlusMenuReliabilityV1 = {
        version: "NOVA_MOBILE_PLUS_MENU_RELIABILITY_V1_20260705",
        bind: bind,
        findUploadButton: findUploadButton
    };

    log(TAG, "installed");
})();