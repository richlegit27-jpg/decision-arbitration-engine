/* NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705 */
(function installNovaMobileAttachButtonAuthorityV1() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705__ = true;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    function getAttachButton() {
        return (
            document.getElementById("nova-mobile-attach") ||
            document.querySelector(".nova-mobile-attach") ||
            document.querySelector(".nova-mobile-attach-action")
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

        try {
            input.disabled = false;
            input.removeAttribute("disabled");
            input.setAttribute("type", "file");
        } catch (_) {}

        try {
            if (!input.accept) {
                input.accept = "image/*,.png,.jpg,.jpeg,.webp,.gif,.txt,.md,.json,.pdf,.docx";
            }
        } catch (_) {}
    }

    function openPicker(event) {
        const input = getFileInput();

        if (!input) {
            log("[Nova Attach Button Authority] no file input found");
            return;
        }

        if (event) {
            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
            }
        }

        ensureInputReady(input);

        log("[Nova Attach Button Authority] opening picker");

        try {
            input.click();
        } catch (error) {
            console.error("[Nova Attach Button Authority] input click failed", error);
        }
    }

    function bind() {
        const button = getAttachButton();
        const input = getFileInput();

        if (!button || !input) {
            return false;
        }

        ensureInputReady(input);

        if (button.dataset.novaAttachAuthorityBound === "1") {
            return true;
        }

        button.dataset.novaAttachAuthorityBound = "1";

        button.addEventListener("click", openPicker, true);

        input.addEventListener("change", function () {
            log("[Nova Attach Button Authority] selected files", input.files && input.files.length, input.files && input.files[0]);
        }, true);

        log("[Nova Attach Button Authority] bound", { button: button.id || button.className, input: input.id || input.className });

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
        version: "NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705",
        bind,
        openPicker
    };

    log("[Nova Attach Button Authority] installed");
})();
