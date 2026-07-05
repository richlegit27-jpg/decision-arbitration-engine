/* NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V5_DELEGATE_UPLOAD_20260705 */
(function installNovaMobileAttachButtonAuthorityV5DelegateUpload() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V5_DELEGATE_UPLOAD_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V5_DELEGATE_UPLOAD_20260705__ = true;
    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V4_SINGLE_CLICK_20260705__ = true;
    window.__NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V1_20260705__ = true;

    let lastOpenAt = 0;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
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

    function findWorkingUploadTrigger() {
        const candidates = Array.from(document.querySelectorAll("button, label, a, [role='button'], [data-nova-upload-trigger], [data-nova-upload-button]"));

        return candidates.find(function (el) {
            if (!el) return false;
            if (el.id === "nova-mobile-attach") return false;
            if (el.matches && el.matches("input[type='file']")) return false;

            const text = textOf(el);

            return /(upload|file|image|photo|attach)/i.test(text);
        }) || null;
    }

    function openPicker(event) {
        const now = Date.now();

        if (now - lastOpenAt < 900) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation?.();
            }

            log("[Nova Attach Button Authority V5] ignored duplicate tap");
            return;
        }

        lastOpenAt = now;

        if (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation?.();
        }

        const uploadTrigger = findWorkingUploadTrigger();

        if (uploadTrigger) {
            log("[Nova Attach Button Authority V5] delegating to working upload trigger", {
                id: uploadTrigger.id || "",
                className: String(uploadTrigger.className || ""),
                text: String(uploadTrigger.textContent || "").trim().slice(0, 80)
            });

            uploadTrigger.click();
            return;
        }

        const input = getFileInput();

        if (input) {
            log("[Nova Attach Button Authority V5] fallback direct file input click");
            input.disabled = false;
            input.removeAttribute("disabled");
            input.click();
            return;
        }

        log("[Nova Attach Button Authority V5] no upload trigger or file input found");
    }

    function cleanButton(button) {
        if (!button) return null;

        if (button.dataset.novaAttachAuthorityV5Clean === "1") {
            return button;
        }

        const clone = button.cloneNode(true);

        clone.id = "nova-mobile-attach";
        clone.dataset.novaAttachAuthorityV5Clean = "1";
        clone.dataset.novaAttachAuthorityBound = "0";

        button.replaceWith(clone);

        log("[Nova Attach Button Authority V5] replaced plus with delegate clone");

        return clone;
    }

    function bind() {
        let button = getAttachButton();

        if (!button) {
            return false;
        }

        button = cleanButton(button);

        if (!button || button.dataset.novaAttachAuthorityBound === "1") {
            return true;
        }

        button.dataset.novaAttachAuthorityBound = "1";
        button.addEventListener("click", openPicker, true);

        log("[Nova Attach Button Authority V5] bound plus to working upload trigger");

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

    window.NovaMobileAttachButtonAuthorityV1 = {
        version: "NOVA_MOBILE_ATTACH_BUTTON_AUTHORITY_V5_DELEGATE_UPLOAD_20260705",
        bind: bind,
        openPicker: openPicker,
        findWorkingUploadTrigger: findWorkingUploadTrigger
    };

    log("[Nova Attach Button Authority V5] installed");
})();
