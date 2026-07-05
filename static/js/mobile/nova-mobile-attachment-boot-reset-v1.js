/* NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705 */
(function installNovaMobileAttachmentBootResetV1() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705__ = true;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    const KEY_RE = /(attach|attachment|attachments|upload|uploads|preview|pending.*file|pending.*image|pending.*attach)/i;
    const VALUE_RE = /(\/api\/uploads\/|attachment|attachments|filename|preview|pending)/i;

    function clearStorage() {
        [window.localStorage, window.sessionStorage].forEach(function (store) {
            if (!store) return;

            Object.keys(store).forEach(function (key) {
                let value = "";

                try {
                    value = String(store.getItem(key) || "");
                } catch (_) {}

                if (KEY_RE.test(key) || VALUE_RE.test(value)) {
                    try {
                        log("[Nova Attachment Boot Reset] removed stale storage", key);
                        store.removeItem(key);
                    } catch (_) {}
                }
            });
        });
    }

    function clearQueues() {
        window.NovaMobileSharedAttachments = [];
        window.__novaMobilePendingAttachments = [];
        window.NovaMobilePendingAttachments = [];
        window.__NOVA_MOBILE_PENDING_ATTACHMENTS__ = [];
    }

    function clearFileInput() {
        const input =
            document.getElementById("nova-mobile-file-input") ||
            document.querySelector("input[type='file']");

        if (input) {
            try {
                input.value = "";
            } catch (_) {}
        }
    }

    function clearPreviewDom() {
        const selectors = [
            "[data-nova-attachment-preview]",
            "[data-nova-upload-preview]",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-upload-preview",
            ".nova-mobile-preview-chip",
            ".nova-attachment-chip",
            ".attachment-preview",
            ".upload-preview"
        ];

        document.querySelectorAll(selectors.join(",")).forEach(function (el) {
            try {
                el.remove();
            } catch (_) {}
        });
    }

    function reset() {
        clearStorage();
        clearQueues();
        clearFileInput();
        clearPreviewDom();
    }

    reset();

    document.addEventListener("DOMContentLoaded", reset);
    window.addEventListener("load", reset);

    setTimeout(reset, 100);
    setTimeout(reset, 500);
    setTimeout(reset, 1500);

    window.NovaMobileAttachmentBootResetV1 = {
        version: "NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705",
        reset: reset
    };

    log("[Nova Attachment Boot Reset] installed");
})();
