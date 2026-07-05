/* NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V4_SINGLE_CLICK_20260705 */
(function installNovaMobileAttachButtonAuthorityV4SingleClick() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V4_SINGLE_CLICK_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V4_SINGLE_CLICK_20260705__ = true;
    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V3_CLEAN_CLONE_20260705__ = true;
    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705__ = true;

    let lastOpenAt = 0;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    function getAttachButton() {
        return (
            document.getElementById("nova-mobile-attach") ||
            document.querySelector(".nova-mobile-attach-action") ||
            document.querySelector(".nova-mobile-attach")
        );
    }

    function getFileInput() {
        return (
            document.getElementById("nova-mobile-file-input") ||
            document.querySelector("input[type='file'][id*='mobile']") ||
            document.querySelector("input[type='file']")
        );
    }

    function ensureInputReady(input) {
        if (!input) return;

        input.disabled = false;
        input.removeAttribute("disabled");

        if (!input.accept) {
            input.accept = "image/*,.txt,.md,.pdf,.doc,.docx";
        }
    }

    function openPicker(event) {
        const now = Date.now();

        if (now - lastOpenAt < 900) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();

                if (typeof event.stopImmediatePropagation === "function") {
                    event.stopImmediatePropagation();
                }
            }

            log("[Nova Attach Button Authority V4] ignored duplicate tap");
            return;
        }

        lastOpenAt = now;

        if (event) {
            event.preventDefault();
            event.stopPropagation();

            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }
        }

        const input = getFileInput();

        if (!input) {
            log("[Nova Attach Button Authority V4] no file input found");
            return;
        }

        ensureInputReady(input);

        log("[Nova Attach Button Authority V4] opening picker once");

        try {
            input.click();
        } catch (error) {
            console.error("[Nova Attach Button Authority V4] input click failed", error);
        }
    }

    function cleanButton(button) {
        if (!button) return null;

        if (button.dataset.novaAttachAuthorityV4Clean === "1") {
            return button;
        }

        const clone = button.cloneNode(true);

        clone.id = "nova-mobile-attach";
        clone.dataset.novaAttachAuthorityV4Clean = "1";
        clone.dataset.novaAttachAuthorityCleanClone = "1";
        clone.dataset.novaAttachAuthorityBound = "0";

        try {
            button.replaceWith(clone);
            log("[Nova Attach Button Authority V4] replaced attach button with single-click clone");
            return clone;
        } catch (error) {
            console.error("[Nova Attach Button Authority V4] clone replace failed", error);
            return button;
        }
    }

    function bind() {
        let button = getAttachButton();
        const input = getFileInput();

        if (!button || !input) {
            return false;
        }

        ensureInputReady(input);

        button = cleanButton(button);

        if (!button || button.dataset.novaAttachAuthorityBound === "1") {
            return true;
        }

        button.dataset.novaAttachAuthorityBound = "1";

        /*
          IMPORTANT:
          Bind only ONE picker event.
          No pointerup.
          No touchend.
          No onclick property.
          This prevents double file picker opens.
        */
        button.addEventListener("click", openPicker, true);

        input.addEventListener("change", function () {
            log("[Nova Attach Button Authority V4] selected files", input.files && input.files.length, input.files && input.files[0]);
        }, true);

        log("[Nova Attach Button Authority V4] bound single-click attach button");

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

    const observer = new MutationObserver(bind);
    observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
    });

    bindLoop();

    window.NovaMobileAttachButtonAuthorityV1 = {
        version: "NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V4_SINGLE_CLICK_20260705",
        bind: bind,
        openPicker: openPicker
    };

    log("[Nova Attach Button Authority V4] installed");
})();
