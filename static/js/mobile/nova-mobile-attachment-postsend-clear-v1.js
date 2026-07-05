(function () {
    "use strict";

    window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attachment Postsend Clear V1]";
    let lastChatSendAt = 0;

    const PREVIEW_SELECTORS = [
        "[data-nova-attachment-preview]",
        "[data-nova-mobile-attachment-preview]",
        "[data-nova-upload-preview]",
        "[data-attachment-preview]",
        "[data-upload-preview]",
        "#nova-mobile-attachment-preview",
        "#nova-mobile-attachment-preview-bar",
        "#nova-mobile-preview-bar",
        ".nova-mobile-attachment-preview",
        ".nova-mobile-attachment-preview-bar",
        ".nova-mobile-preview-bar",
        ".nova-mobile-attachment-chip",
        ".mobile-attachment-preview",
        ".mobile-attachment-chip",
        ".attachment-preview",
        ".attachment-chip",
        ".upload-preview",
        ".upload-chip",
        ".preview-chip"
    ];

    function queueItems() {
        try {
            if (
                window.NovaMobileAttachmentSendBridgeV1 &&
                typeof window.NovaMobileAttachmentSendBridgeV1.getQueuedAttachments === "function"
            ) {
                return window.NovaMobileAttachmentSendBridgeV1.getQueuedAttachments() || [];
            }
        } catch (_) {}

        return [];
    }

    function resetQueues() {
        [
            "__NOVA_MOBILE_ATTACHMENT_SEND_QUEUE_V1__",
            "NovaMobilePendingAttachments",
            "novaMobilePendingAttachments",
            "NovaMobileSharedAttachments",
            "novaMobileSharedAttachments",
            "NovaMobileAttachmentQueue",
            "novaMobileAttachmentQueue"
        ].forEach(function (key) {
            try {
                if (Array.isArray(window[key])) {
                    window[key].length = 0;
                } else {
                    window[key] = [];
                }
            } catch (_) {}
        });
    }

    function clearFileInputs() {
        document.querySelectorAll("input[type='file']").forEach(function (input) {
            try {
                input.value = "";
            } catch (_) {}
        });
    }

    function removeBySelectors() {
        let removed = 0;

        PREVIEW_SELECTORS.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                try {
                    el.remove();
                } catch (_) {
                    el.style.setProperty("display", "none", "important");
                    el.innerHTML = "";
                }

                removed += 1;
            });
        });

        return removed;
    }

    function removeLikelyPreviewNodes() {
        let removed = 0;

        document.querySelectorAll("div,section,aside,span,label").forEach(function (el) {
            if (!el || !el.getBoundingClientRect) {
                return;
            }

            const rect = el.getBoundingClientRect();
            const text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
            const hay = (
                String(el.id || "") + " " +
                String(el.className || "") + " " +
                text
            ).toLowerCase();

            if (rect.width < 10 || rect.height < 10) {
                return;
            }

            if (rect.height > 180 || rect.width > window.innerWidth * 0.98) {
                return;
            }

            if (text.length > 260) {
                return;
            }

            if (!/(attachment|preview|upload|chip|rich_.*\.jpg|\.jpg|\.jpeg|\.png|\.webp|\.gif)/i.test(hay)) {
                return;
            }

            if (el.closest("#mobileChatMessages,.mobile-chat-container,.nova-mobile-visible-message-v1")) {
                return;
            }

            try {
                el.remove();
            } catch (_) {
                el.style.setProperty("display", "none", "important");
                el.innerHTML = "";
            }

            removed += 1;
        });

        return removed;
    }

    function clear(reason) {
        resetQueues();
        clearFileInputs();

        let removed = 0;

        try {
            if (
                window.NovaMobileAttachmentPreviewCleanupV1 &&
                typeof window.NovaMobileAttachmentPreviewCleanupV1.clear === "function"
            ) {
                removed += Number(window.NovaMobileAttachmentPreviewCleanupV1.clear(reason || "postsend-clear-owner")) || 0;
            }
        } catch (err) {
            console.warn(LOG, "preview cleanup owner failed", err);
        }

        removed += removeBySelectors();
        removed += removeLikelyPreviewNodes();

        console.log(LOG, "cleared", {
            reason: reason || "postsend-clear",
            removed: removed,
            queued: queueItems().length
        });

        return removed;
    }

    function scheduleClear(reason) {
        [0, 80, 200, 450, 800, 1200, 1800, 2600, 4000, 6500].forEach(function (delay) {
            setTimeout(function () {
                clear((reason || "scheduled") + "-" + delay);
            }, delay);
        });
    }

    function isChatUrl(url) {
        return /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""));
    }

    if (window.fetch && !window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_FETCH_PATCHED_V2__) {
        window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_FETCH_PATCHED_V2__ = true;

        const previousFetch = window.fetch.bind(window);

        window.fetch = async function novaMobileAttachmentPostsendClearFetch(input, init) {
            const url = typeof input === "string" ? input : (input && input.url) || "";
            const isChat = isChatUrl(url);

            if (isChat) {
                lastChatSendAt = Date.now();
                scheduleClear("chat-before-response");
            }

            const response = await previousFetch(input, init);

            if (isChat) {
                lastChatSendAt = Date.now();
                scheduleClear("chat-after-response");
            }

            return response;
        };
    }

    const observer = new MutationObserver(function () {
        if (!lastChatSendAt) {
            return;
        }

        if (Date.now() - lastChatSendAt > 9000) {
            return;
        }

        if (queueItems().length === 0) {
            scheduleClear("mutation-after-send");
        }
    });

    try {
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (_) {}

    window.NovaMobileAttachmentPostsendClearV1 = {
        clear: clear,
        scheduleClear: scheduleClear,
        removeBySelectors: removeBySelectors,
        removeLikelyPreviewNodes: removeLikelyPreviewNodes
    };

    console.log(LOG, "installed v2");
})();
