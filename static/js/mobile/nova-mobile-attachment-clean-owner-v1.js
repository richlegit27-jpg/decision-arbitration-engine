(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_CLEAN_OWNER_V1__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_CLEAN_OWNER_V1__ = true;

    const LOG = "[Nova Mobile Attachment Clean Owner]";
    const STORAGE_KEYS = [
        "nova_mobile_upload",
        "nova_mobile_uploads",
        "nova_mobile_upload_queue",
        "nova_mobile_pending_uploads",
        "nova_mobile_pending_attachments",
        "nova_mobile_attachments",
        "nova_pending_uploads",
        "nova_pending_attachments",
        "mobile_upload_queue",
        "mobile_pending_uploads",
        "mobile_pending_attachments",
        "pendingAttachments",
        "NovaMobilePendingAttachments"
    ];

    const PREVIEW_SELECTORS = [
        "#nova-mobile-upload-preview-owner",
        "#nova-mobile-attachment-preview",
        "#mobileAttachmentPreview",
        ".nova-mobile-upload-preview-owner",
        ".nova-mobile-attachment-preview",
        ".mobile-attachment-preview",
        ".nova-mobile-preview-bar",
        ".attachment-preview"
    ];

    const CHIP_SELECTORS = [
        ".nova-mobile-upload-preview-chip",
        ".nova-mobile-attachment-chip",
        ".mobile-attachment-chip",
        ".attachment-chip",
        ".nova-attachment-item",
        "[data-attachment-preview]",
        "[data-nova-upload-preview]"
    ];

    let recentlyCleared = false;

    function safeJsonEmptyStorage(storage) {
        if (!storage) {
            return;
        }

        STORAGE_KEYS.forEach(function (key) {
            try {
                storage.removeItem(key);
                storage.setItem(key, "[]");
            } catch (error) {
                // Ignore storage privacy/quota errors.
            }
        });
    }

    function clearPreviewElement(element) {
        if (!element) {
            return;
        }

        try {
            element.innerHTML = "";
        } catch (error) {
            // Ignore DOM write errors.
        }

        try {
            element.hidden = true;
            element.setAttribute("hidden", "");
            element.dataset.novaCleared = "1";
            element.style.display = "none";
            element.style.visibility = "hidden";
            element.style.pointerEvents = "none";
        } catch (error) {
            // Ignore style errors.
        }
    }

    function clearPreviewDom() {
        PREVIEW_SELECTORS.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(clearPreviewElement);
        });

        CHIP_SELECTORS.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (element) {
                try {
                    element.remove();
                } catch (error) {
                    try {
                        element.innerHTML = "";
                        element.style.display = "none";
                    } catch (innerError) {
                        // Ignore.
                    }
                }
            });
        });
    }

    function clearFileInputs() {
        document.querySelectorAll('input[type="file"]').forEach(function (input) {
            try {
                input.value = "";
            } catch (error) {
                // Ignore protected file input errors.
            }
        });
    }

    function clearWindowQueues() {
        try {
            window.NovaMobilePendingAttachments = [];
        } catch (error) {
            // Ignore.
        }

        try {
            window.NovaMobilePendingUploads = [];
        } catch (error) {
            // Ignore.
        }

        try {
            window.pendingAttachments = [];
        } catch (error) {
            // Ignore.
        }

        try {
            if (window.NovaMobileUpload && typeof window.NovaMobileUpload === "object") {
                if (typeof window.NovaMobileUpload.clear === "function") {
                    window.NovaMobileUpload.clear();
                }

                if (typeof window.NovaMobileUpload.clearQueue === "function") {
                    window.NovaMobileUpload.clearQueue();
                }

                if (typeof window.NovaMobileUpload.clearPendingAttachments === "function" &&
                    !window.NovaMobileUpload.clearPendingAttachments.__novaCleanOwner) {
                    window.NovaMobileUpload.clearPendingAttachments();
                }

                if (typeof window.NovaMobileUpload.setPendingAttachments === "function") {
                    window.NovaMobileUpload.setPendingAttachments([]);
                }

                window.NovaMobileUpload.pendingAttachments = [];
                window.NovaMobileUpload.pendingUploads = [];
                window.NovaMobileUpload.attachments = [];
            }
        } catch (error) {
            // Ignore.
        }
    }

    function clearAll(reason) {
        recentlyCleared = true;

        safeJsonEmptyStorage(window.localStorage);
        safeJsonEmptyStorage(window.sessionStorage);
        clearWindowQueues();
        clearPreviewDom();
        clearFileInputs();

        try {
            window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
                detail: {
                    reason: reason || "unknown",
                    owner: "nova-mobile-attachment-clean-owner-v1"
                }
            }));
        } catch (error) {
            // Ignore CustomEvent issues.
        }

        console.log(LOG, "cleared", reason || "");
    }

    function markNewUploadActivity() {
        recentlyCleared = false;

        PREVIEW_SELECTORS.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (element) {
                try {
                    element.hidden = false;
                    element.removeAttribute("hidden");
                    element.style.visibility = "";
                    element.style.pointerEvents = "";
                    element.style.display = "";
                    delete element.dataset.novaCleared;
                } catch (error) {
                    // Ignore.
                }
            });
        });
    }

    function installFetchCleaner() {
        if (!window.fetch || window.fetch.__novaAttachmentCleanOwner) {
            return;
        }

        const originalFetch = window.fetch;

        function wrappedFetch(input, init) {
            const url = typeof input === "string" ? input : ((input && input.url) || "");
            const method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
            const isUpload = method === "POST" && url.includes("/api/upload");
            const isChat = method === "POST" && (
                url.includes("/api/chat") ||
                url.includes("/api/chat/stream")
            );

            return originalFetch.apply(this, arguments).then(function (response) {
                if (isUpload && response && response.ok) {
                    markNewUploadActivity();
                }

                if (isChat && response && response.ok) {
                    setTimeout(function () {
                        clearAll("chat-fetch-ok");
                    }, 0);

                    setTimeout(function () {
                        clearAll("chat-fetch-ok-followup");
                    }, 350);

                    setTimeout(function () {
                        clearAll("chat-fetch-ok-late");
                    }, 1200);
                }

                return response;
            });
        }

        wrappedFetch.__novaAttachmentCleanOwner = true;
        wrappedFetch.__novaOriginalFetch = originalFetch;
        window.fetch = wrappedFetch;
    }

    function installUploadReceiverCleaner() {
        const originalReceiver = window.NovaMobileReceiveUploadedAttachment;

        if (originalReceiver && originalReceiver.__novaAttachmentCleanOwner) {
            return;
        }

        window.NovaMobileReceiveUploadedAttachment = function () {
            markNewUploadActivity();

            if (typeof originalReceiver === "function") {
                return originalReceiver.apply(this, arguments);
            }

            return undefined;
        };

        window.NovaMobileReceiveUploadedAttachment.__novaAttachmentCleanOwner = true;
        window.NovaMobileReceiveUploadedAttachment.__novaOriginalReceiver = originalReceiver;
    }

    function installUploadFacadePatch() {
        const upload = window.NovaMobileUpload;

        if (!upload || typeof upload !== "object" || upload.__novaAttachmentCleanOwner) {
            return;
        }

        const originalGet = typeof upload.getPendingAttachments === "function"
            ? upload.getPendingAttachments.bind(upload)
            : null;

        upload.getPendingAttachments = function () {
            if (recentlyCleared) {
                return [];
            }

            if (originalGet) {
                const result = originalGet();

                if (Array.isArray(result)) {
                    return result;
                }
            }

            if (Array.isArray(window.NovaMobilePendingAttachments)) {
                return window.NovaMobilePendingAttachments;
            }

            return [];
        };

        upload.clearPendingAttachments = function () {
            clearAll("NovaMobileUpload.clearPendingAttachments");
        };

        upload.__novaAttachmentCleanOwner = true;
    }

    function installEventCleaners() {
        document.addEventListener("change", function (event) {
            if (event.target && event.target.matches && event.target.matches('input[type="file"]')) {
                markNewUploadActivity();
            }
        }, true);

        document.addEventListener("click", function (event) {
            const button = event.target && event.target.closest
                ? event.target.closest("#nova-mobile-send, #mobileSend, [data-action='send'], button")
                : null;

            if (!button) {
                return;
            }

            const text = (button.id || "") + " " + (button.dataset ? Object.values(button.dataset).join(" ") : "") + " " + (button.textContent || "");

            if (!/send|nova-mobile-send|mobileSend/i.test(text)) {
                return;
            }

            setTimeout(function () {
                clearAll("send-click-fallback");
            }, 1800);
        }, true);

        window.addEventListener("nova-mobile-chat-sent", function () {
            clearAll("nova-mobile-chat-sent-event");
        });

        window.addEventListener("nova-mobile-message-sent", function () {
            clearAll("nova-mobile-message-sent-event");
        });
    }

    function boot() {
        installFetchCleaner();
        installUploadReceiverCleaner();
        installUploadFacadePatch();
        installEventCleaners();

        // Kill stale previews from previous sessions/page reloads.
        setTimeout(function () {
            clearAll("boot-stale-preview-clean");
        }, 250);

        setTimeout(function () {
            installUploadFacadePatch();
        }, 1000);

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();