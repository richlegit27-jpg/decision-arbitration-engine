(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attachment Postsend Clear V1]";

    function isChatUrl(url) {
        return /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""));
    }

    function clear(reason) {
        try {
            if (
                window.NovaMobileAttachmentPreviewCleanupV1 &&
                typeof window.NovaMobileAttachmentPreviewCleanupV1.clear === "function"
            ) {
                return window.NovaMobileAttachmentPreviewCleanupV1.clear(reason || "postsend-clear");
            }
        } catch (err) {
            console.warn(LOG, "cleanup owner failed", err);
        }

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

        document.querySelectorAll("input[type='file']").forEach(function (input) {
            try {
                input.value = "";
            } catch (_) {}
        });

        const selectors = [
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

        let removed = 0;

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
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

        console.log(LOG, "fallback cleared", {
            reason: reason || "postsend-clear",
            removed: removed
        });

        return removed;
    }

    function scheduleClear(reason) {
        [80, 250, 700, 1200, 2200, 4000].forEach(function (delay) {
            setTimeout(function () {
                const removed = clear((reason || "postsend-clear") + "-" + delay);
                console.log(LOG, "sweep", {
                    delay: delay,
                    removed: removed
                });
            }, delay);
        });
    }

    const previousFetch = window.fetch && window.fetch.bind(window);

    if (previousFetch) {
        window.fetch = async function novaMobileAttachmentPostsendClearFetch(input, init) {
            const url = typeof input === "string" ? input : (input && input.url) || "";
            const response = await previousFetch(input, init);

            if (isChatUrl(url)) {
                scheduleClear("chat-response");
            }

            return response;
        };
    }

    window.NovaMobileAttachmentPostsendClearV1 = {
        clear: clear,
        scheduleClear: scheduleClear
    };

    console.log(LOG, "installed");
})();
