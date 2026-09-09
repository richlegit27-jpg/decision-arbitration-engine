(function () {
    "use strict";

    /*
     * V3 rule:
     * Do NOT clean preview on upload, mutation, focus, drawer close, or random DOM change.
     * Only clean after a real /api/chat send finishes, or when called manually.
     */

    window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V3_SEND_ONLY__ = true;

    const LOG = "[Nova Mobile Attachment Postsend Clear V1]";

    function queuedCount() {
        try {
            if (
                window.NovaMobileAttachmentSendBridgeV1 &&
                typeof window.NovaMobileAttachmentSendBridgeV1.getQueuedAttachments === "function"
            ) {
                return (window.NovaMobileAttachmentSendBridgeV1.getQueuedAttachments() || []).length;
            }
        } catch (_) {}

        return 0;
    }

    function removeFallbackPreviewNodes(reason) {
        let removed = 0;

        const selectors = [
            ".nova-mobile-upload-preview",
            ".nova-mobile-attachment-preview",
            ".mobile-upload-preview",
            ".attachment-preview",
            ".upload-preview",
            ".file-preview",
            ".preview-chip",
            ".attachment-chip",
            ".file-chip",
            "[data-preview]",
            "[data-attachment-preview]",
            "[data-upload-preview]",
            "[data-file-preview]"
        ];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                if (el.closest("#mobileChatMessages,.mobile-chat-container,.nova-mobile-visible-message-v1")) {
                    return;
                }

                try {
                    el.remove();
                    removed += 1;
                } catch (_) {
                    el.style.setProperty("display", "none", "important");
                    el.innerHTML = "";
                    removed += 1;
                }
            });
        });

        return removed;
    }

    function clear(reason) {
        let removed = 0;

        try {
            if (
                window.NovaMobileAttachmentPreviewCleanupV1 &&
                typeof window.NovaMobileAttachmentPreviewCleanupV1.clear === "function"
            ) {
                removed += Number(window.NovaMobileAttachmentPreviewCleanupV1.clear(reason || "postsend-v3-clear")) || 0;
            }
        } catch (err) {
            console.warn(LOG, "preview cleanup failed", err);
        }

        removed += removeFallbackPreviewNodes(reason || "postsend-v3-clear");

        console.log(LOG, "clear", {
            reason: reason || "postsend-v3-clear",
            removed: removed,
            queued: queuedCount()
        });

        return removed;
    }

    function scheduleClear(reason) {
        [500, 900, 1400, 2200, 3400, 5200, 7200].forEach(function (delay) {
            setTimeout(function () {
                /*
                 * Only clean once the send bridge has finished with attachments.
                 * This prevents upload preview from disappearing before send.
                 */
                if (queuedCount() === 0) {
                    clear((reason || "postsend-v3") + "-" + delay);
                } else {
                    console.log(LOG, "skip clear; queue not empty", {
                        reason: reason || "postsend-v3",
                        delay: delay,
                        queued: queuedCount()
                    });
                }
            }, delay);
        });
    }

    if (!window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_FETCH_PATCHED_V3__) {
        window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_FETCH_PATCHED_V3__ = true;

        const originalFetch = window.fetch.bind(window);

        window.fetch = async function novaMobileAttachmentPostsendClearFetch(input, init) {
            const url = String(
                (input && input.url) ||
                input ||
                ""
            );

            const isChatSend = /\/api\/chat(?:\?|$)/.test(url);

            const response = await originalFetch(input, init);

            if (isChatSend) {
                scheduleClear("api-chat-finished");
            }

            return response;
        };
    }

    window.NovaMobileAttachmentPostsendClearV1 = {
        version: "v3-send-only",
        clear: clear,
        scheduleClear: scheduleClear,
        queuedCount: queuedCount
    };

    console.log(LOG, "installed v3 send-only");
})();
