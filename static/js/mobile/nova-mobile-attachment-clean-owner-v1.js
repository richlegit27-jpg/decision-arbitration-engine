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

/* NOVA_MOBILE_ATTACHMENT_CLEAN_OWNER_V2_20260705 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_CLEAN_OWNER_V2__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_CLEAN_OWNER_V2__ = true;

    const LOG = "[Nova Mobile Attachment Clean Owner V2]";
    let suppressUntil = 0;

    const previewSelectors = [
        "#nova-mobile-upload-preview-owner",
        "#nova-mobile-attachment-preview",
        "#mobileAttachmentPreview",
        ".nova-mobile-upload-preview-owner",
        ".nova-mobile-attachment-preview",
        ".mobile-attachment-preview",
        ".nova-mobile-preview-bar",
        ".attachment-preview"
    ];

    const chipSelectors = [
        ".nova-mobile-upload-preview-chip",
        ".nova-mobile-attachment-chip",
        ".mobile-attachment-chip",
        ".attachment-chip",
        ".nova-attachment-item",
        "[data-attachment-preview]",
        "[data-nova-upload-preview]"
    ];

    const storageKeys = [
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

    function now() {
        return Date.now ? Date.now() : new Date().getTime();
    }

    function duringSuppression() {
        return now() < suppressUntil;
    }

    function clearStorage(storage) {
        if (!storage) {
            return;
        }

        storageKeys.forEach(function (key) {
            try {
                storage.removeItem(key);
            } catch (error) {}

            try {
                storage.setItem(key, "[]");
            } catch (error) {}
        });
    }

    function hardHidePreview(el) {
        if (!el) {
            return;
        }

        try {
            el.innerHTML = "";
        } catch (error) {}

        try {
            el.hidden = true;
            el.setAttribute("hidden", "");
            el.setAttribute("aria-hidden", "true");
            el.dataset.novaAttachmentCleared = "1";
            el.style.setProperty("display", "none", "important");
            el.style.setProperty("visibility", "hidden", "important");
            el.style.setProperty("pointer-events", "none", "important");
            el.style.setProperty("height", "0px", "important");
            el.style.setProperty("min-height", "0px", "important");
            el.style.setProperty("padding", "0px", "important");
            el.style.setProperty("margin", "0px", "important");
            el.style.setProperty("overflow", "hidden", "important");
        } catch (error) {}
    }

    function clearDom() {
        previewSelectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(hardHidePreview);
        });

        chipSelectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                try {
                    el.remove();
                } catch (error) {
                    try {
                        el.innerHTML = "";
                        el.style.setProperty("display", "none", "important");
                    } catch (innerError) {}
                }
            });
        });
    }

    function clearGlobals() {
        try { window.NovaMobilePendingAttachments = []; } catch (error) {}
        try { window.NovaMobilePendingUploads = []; } catch (error) {}
        try { window.pendingAttachments = []; } catch (error) {}

        try {
            if (window.NovaMobileUpload && typeof window.NovaMobileUpload === "object") {
                window.NovaMobileUpload.pendingAttachments = [];
                window.NovaMobileUpload.pendingUploads = [];
                window.NovaMobileUpload.attachments = [];

                window.NovaMobileUpload.getPendingAttachments = function () {
                    return duringSuppression() ? [] : [];
                };

                window.NovaMobileUpload.clearPendingAttachments = function () {
                    forceClear("NovaMobileUpload.clearPendingAttachments.v2");
                };

                window.NovaMobileUpload.clear = function () {
                    forceClear("NovaMobileUpload.clear.v2");
                };

                window.NovaMobileUpload.clearQueue = function () {
                    forceClear("NovaMobileUpload.clearQueue.v2");
                };
            }
        } catch (error) {}
    }

    function clearInputs() {
        document.querySelectorAll('input[type="file"]').forEach(function (input) {
            try {
                input.value = "";
            } catch (error) {}
        });
    }

    function forceClear(reason) {
        clearStorage(window.localStorage);
        clearStorage(window.sessionStorage);
        clearGlobals();
        clearInputs();
        clearDom();

        try {
            window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
                detail: {
                    reason: reason || "unknown",
                    owner: "nova-mobile-attachment-clean-owner-v2"
                }
            }));
        } catch (error) {}

        console.log(LOG, "cleared", reason || "");
    }

    function armPostSendSuppression(reason) {
        suppressUntil = now() + 6500;

        forceClear(reason || "post-send");

        [80, 200, 450, 800, 1300, 2200, 3500, 5200, 6500].forEach(function (delay) {
            setTimeout(function () {
                if (duringSuppression()) {
                    forceClear((reason || "post-send") + "-followup-" + delay);
                }
            }, delay);
        });
    }

    function isSendButton(el) {
        if (!el || !el.closest) {
            return false;
        }

        const button = el.closest("button, [role='button'], input[type='submit']");

        if (!button) {
            return false;
        }

        const id = button.id || "";
        const label = button.getAttribute("aria-label") || "";
        const title = button.getAttribute("title") || "";
        const dataAction = button.getAttribute("data-action") || "";
        const text = button.textContent || "";

        return /send|nova-mobile-send|mobileSend/i.test(
            [id, label, title, dataAction, text].join(" ")
        );
    }

    function installSendStartCleaner() {
        document.addEventListener("pointerdown", function (event) {
            if (isSendButton(event.target)) {
                armPostSendSuppression("send-pointerdown");
            }
        }, true);

        document.addEventListener("click", function (event) {
            if (isSendButton(event.target)) {
                armPostSendSuppression("send-click");
            }
        }, true);

        document.addEventListener("submit", function () {
            armPostSendSuppression("composer-submit");
        }, true);

        document.addEventListener("keydown", function (event) {
            const key = event.key || "";

            if (key !== "Enter" || event.shiftKey) {
                return;
            }

            const target = event.target;

            if (!target || !target.matches) {
                return;
            }

            if (target.matches("textarea, input[type='text'], [contenteditable='true']")) {
                armPostSendSuppression("enter-send");
            }
        }, true);
    }

    function installFetchCleaner() {
        if (!window.fetch || window.fetch.__novaAttachmentCleanOwnerV2) {
            return;
        }

        const originalFetch = window.fetch;

        function wrappedFetch(input, init) {
            const url = typeof input === "string" ? input : ((input && input.url) || "");
            const method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
            const isChat = method === "POST" && (
                url.includes("/api/chat") ||
                url.includes("/api/chat/stream")
            );

            const promise = originalFetch.apply(this, arguments);

            if (isChat) {
                armPostSendSuppression("chat-fetch-start");
            }

            return promise.then(function (response) {
                if (isChat) {
                    armPostSendSuppression(response && response.ok ? "chat-fetch-ok" : "chat-fetch-done");
                }

                return response;
            });
        }

        wrappedFetch.__novaAttachmentCleanOwnerV2 = true;
        wrappedFetch.__novaOriginalFetch = originalFetch;
        window.fetch = wrappedFetch;
    }

    function installMutationCleaner() {
        const observer = new MutationObserver(function () {
            if (duringSuppression()) {
                clearDom();
            }
        });

        try {
            observer.observe(document.documentElement || document.body, {
                childList: true,
                subtree: true
            });
        } catch (error) {}
    }

    function installUploadActivityUnhide() {
        document.addEventListener("change", function (event) {
            if (event.target && event.target.matches && event.target.matches('input[type="file"]')) {
                suppressUntil = 0;

                previewSelectors.forEach(function (selector) {
                    document.querySelectorAll(selector).forEach(function (el) {
                        try {
                            el.hidden = false;
                            el.removeAttribute("hidden");
                            el.removeAttribute("aria-hidden");
                            el.style.removeProperty("display");
                            el.style.removeProperty("visibility");
                            el.style.removeProperty("pointer-events");
                            el.style.removeProperty("height");
                            el.style.removeProperty("min-height");
                            el.style.removeProperty("padding");
                            el.style.removeProperty("margin");
                            el.style.removeProperty("overflow");
                        } catch (error) {}
                    });
                });
            }
        }, true);
    }

    function boot() {
        installSendStartCleaner();
        installFetchCleaner();
        installMutationCleaner();
        installUploadActivityUnhide();

        setTimeout(function () {
            forceClear("boot-v2-stale-clean");
        }, 300);

        console.log(LOG, "installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
