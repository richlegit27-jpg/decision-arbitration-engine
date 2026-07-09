(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_SEND_CLEANUP_V1__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_SEND_CLEANUP_V1__ = true;

    const LOG = "[Nova Attachment Send Cleanup V1]";

    const STORAGE_KEYS = [
        "nova_mobile_upload",
        "nova_mobile_attachments",
        "nova_mobile_pending_attachments",
        "nova_pending_attachments",
        "novaMobilePendingAttachments",
        "nova_mobile_attachment_queue",
        "NovaMobilePendingAttachments"
    ];

const PREVIEW_SELECTORS = [
    "#nova-main-visible-attachment-preview",
    "#nova-mobile-upload-preview",
    "#nova-mobile-attachment-preview",
    "#nova-mobile-attachment-preview-bar",
    "#nova-mobile-upload-preview-bar",

        "[data-nova-upload-preview]",
        "[data-nova-attachment-preview]",
        "[data-nova-preview]",
        ".nova-mobile-upload-preview",
        ".nova-mobile-attachment-preview",
        ".nova-mobile-upload-chip",
        ".nova-mobile-attachment-chip",
        ".nova-mobile-preview-chip",
        ".nova-attachment-preview-chip",
        "[class*='upload-preview']",
        "[class*='attachment-preview']",
        "[class*='preview-chip']"
    ];

    let suppressUntil = 0;

    function clearStorageQueues() {
        STORAGE_KEYS.forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (error) {}

            try {
                sessionStorage.removeItem(key);
            } catch (error) {}
        });
    }

    function clearGlobals() {
        try {
            window.NovaMobilePendingAttachments = [];
        } catch (error) {}

        try {
            window.NovaMobileAttachments = [];
        } catch (error) {}

        try {
            if (window.NovaMobileUpload) {
                if (Array.isArray(window.NovaMobileUpload.pendingAttachments)) {
                    window.NovaMobileUpload.pendingAttachments.length = 0;
                }

                if (Array.isArray(window.NovaMobileUpload.queue)) {
                    window.NovaMobileUpload.queue.length = 0;
                }

                if (typeof window.NovaMobileUpload.clearPendingAttachments === "function") {
                    window.NovaMobileUpload.clearPendingAttachments();
                }

                if (typeof window.NovaMobileUpload.clearQueue === "function") {
                    window.NovaMobileUpload.clearQueue();
                }

                if (typeof window.NovaMobileUpload.reset === "function") {
                    window.NovaMobileUpload.reset();
                }
            }
        } catch (error) {
            console.warn(LOG, "global clear warning", error);
        }
    }

    function clearFileInputs() {
        document.querySelectorAll('input[type="file"]').forEach(function (input) {
            try {
                input.value = "";
            } catch (error) {}
        });
    }

    function clearPreviewDom() {
        PREVIEW_SELECTORS.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (node) {
                try {
                    node.replaceChildren();
                    node.innerHTML = "";
                    node.style.setProperty("display", "none", "important");
                    node.style.setProperty("visibility", "hidden", "important");
                    node.style.setProperty("opacity", "0", "important");
                    node.dataset.novaClearedAfterSend = "true";
                } catch (error) {
                    try {
                        node.remove();
                    } catch (removeError) {}
                }
            });
        });
    }

    function clearAttachmentsAfterSend() {
        suppressUntil = Date.now() + 2500;

        clearStorageQueues();
        clearGlobals();
        clearFileInputs();
        clearPreviewDom();

        try {
            window.dispatchEvent(new CustomEvent("nova:attachments-cleared-after-send"));
        } catch (error) {}

        console.log(LOG, "cleared attachment queue and preview after send");
    }

function scheduleClearAfterSend() {
    [50, 150, 350, 700, 1200, 2000, 2800].forEach(function (delay) {
        window.setTimeout(clearAttachmentsAfterSend, delay);
    });
}

    function getFetchUrl(input) {
        if (typeof input === "string") {
            return input;
        }

        if (input && typeof input.url === "string") {
            return input.url;
        }

        return "";
    }

    function isChatSend(input, init) {
        const url = getFetchUrl(input);
        const method = String((init && init.method) || "GET").toUpperCase();

        return (
            method === "POST" &&
            (
                url.includes("/api/chat") ||
                url.includes("/api/chat/stream")
            )
        );
    }

    function installFetchHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_SEND_CLEANUP_FETCH_HOOK__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_SEND_CLEANUP_FETCH_HOOK__ = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") {
            return;
        }

        window.fetch = async function novaAttachmentCleanupFetch(input, init) {
            const shouldClear = isChatSend(input, init);
            const response = await originalFetch.apply(this, arguments);

            if (shouldClear && response && response.ok) {
                scheduleClearAfterSend();
            }

            return response;
        };

        console.log(LOG, "fetch hook installed");
    }

    function installDomSuppressor() {
        const observer = new MutationObserver(function () {
            if (Date.now() <= suppressUntil) {
                clearPreviewDom();
            }
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }

    installFetchHook();
    installDomSuppressor();
})();
