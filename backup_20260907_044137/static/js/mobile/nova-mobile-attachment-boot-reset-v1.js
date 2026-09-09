/* NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705 */
(function installNovaMobileAttachmentBootResetV1() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705__ = true;

    let userPickedFile = false;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
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

    function clearStorage() {
        const keyRe = /(attach|attachment|attachments|upload|uploads|preview|pending.*file|pending.*image|pending.*attach)/i;
        const valueRe = /(\/api\/uploads\/|attachment|attachments|filename|preview|pending)/i;

        [window.localStorage, window.sessionStorage].forEach(function (store) {
            if (!store) return;

            Object.keys(store).forEach(function (key) {
                let value = "";

                try {
                    value = String(store.getItem(key) || "");
                } catch (_) {}

                if (keyRe.test(key) || valueRe.test(value)) {
                    try {
                        log("[Nova Attachment Boot Reset] removed stale storage", key);
                        store.removeItem(key);
                    } catch (_) {}
                }
            });
        });
    }

    function reset(reason) {
        if (userPickedFile) {
            log("[Nova Attachment Boot Reset] skipped after user file pick", reason);
            return;
        }

        clearStorage();
        clearQueues();
        clearFileInput();
        clearPreviewDom();

        log("[Nova Attachment Boot Reset] cleared stale attachment state", reason);
    }

    document.addEventListener("change", function (event) {
        const target = event.target;

        if (target && target.matches && target.matches("input[type='file']")) {
            userPickedFile = true;
            log("[Nova Attachment Boot Reset] user picked file, boot reset disabled");
        }
    }, true);

    reset("install");

    document.addEventListener("DOMContentLoaded", function () {
        reset("dom-ready");
    });

    window.addEventListener("load", function () {
        reset("load");
    });

    setTimeout(function () {
        reset("late-250");
    }, 250);

    setTimeout(function () {
        reset("late-1000");
    }, 1000);

    window.NovaMobileAttachmentBootResetV1 = {
        version: "NOVA_MOBILE_ATTACHMENT_BOOT_RESET_V1_20260705",
        reset: reset
    };

    log("[Nova Attachment Boot Reset] installed");
})();
