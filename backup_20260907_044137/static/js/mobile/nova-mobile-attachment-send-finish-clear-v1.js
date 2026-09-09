(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_SEND_FINISH_CLEAR_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_SEND_FINISH_CLEAR_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attachment Send Finish Clear V1]";

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

    function cleanup(reason) {
        let removed = 0;

        try {
            if (
                window.NovaMobileAttachmentPreviewCleanupV1 &&
                typeof window.NovaMobileAttachmentPreviewCleanupV1.clear === "function"
            ) {
                removed += Number(window.NovaMobileAttachmentPreviewCleanupV1.clear(reason || "send-finish-clear")) || 0;
            }
        } catch (err) {
            console.warn(LOG, "preview cleanup failed", err);
        }

        try {
            if (
                window.NovaMobileAttachmentPostsendClearV1 &&
                typeof window.NovaMobileAttachmentPostsendClearV1.clear === "function"
            ) {
                removed += Number(window.NovaMobileAttachmentPostsendClearV1.clear(reason || "send-finish-postsend-clear")) || 0;
            }
        } catch (err) {
            console.warn(LOG, "postsend cleanup failed", err);
        }

        console.log(LOG, "cleanup", {
            reason: reason || "send-finish-clear",
            removed: removed,
            queued: queuedCount()
        });

        return removed;
    }

    function scheduleAfterSend(reason) {
        const startedAt = Date.now();

        [600, 1000, 1600, 2400, 3400, 5000, 7000].forEach(function (delay) {
            setTimeout(function () {
                const q = queuedCount();

                /*
                 * Do not clear too early while the queued attachment may still
                 * need to be injected into /api/chat. Once queue is empty, the
                 * send bridge has finished with it.
                 */
                if (q === 0 || Date.now() - startedAt > 4500) {
                    cleanup((reason || "send-finish") + "-" + delay);
                } else {
                    console.log(LOG, "waiting for queue to empty", {
                        reason: reason || "send-finish",
                        delay: delay,
                        queued: q
                    });
                }
            }, delay);
        });
    }

    function isSendControl(el) {
        if (!el || !el.closest) {
            return false;
        }

        const target = el.closest("button,a,[role='button']");

        if (!target) {
            return false;
        }

        if (target.id === "nova-mobile-send") {
            return true;
        }

        const hay = (
            String(target.id || "") + " " +
            String(target.className || "") + " " +
            String(target.getAttribute("aria-label") || "") + " " +
            String(target.getAttribute("title") || "") + " " +
            String(target.innerText || target.textContent || "")
        ).toLowerCase();

        return /send/.test(hay) && !/stop|voice|tts|speak|attach|session|copy|regen/.test(hay);
    }

    document.addEventListener("pointerup", function (event) {
        if (isSendControl(event.target)) {
            scheduleAfterSend("send-pointerup");
        }
    }, true);

    document.addEventListener("click", function (event) {
        if (isSendControl(event.target)) {
            scheduleAfterSend("send-click");
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        const target = event.target;

        if (
            target &&
            target.matches &&
            target.matches("textarea,input") &&
            event.key === "Enter" &&
            !event.shiftKey
        ) {
            scheduleAfterSend("send-enter");
        }
    }, true);

    window.NovaMobileAttachmentSendFinishClearV1 = {
        cleanup: cleanup,
        scheduleAfterSend: scheduleAfterSend,
        queuedCount: queuedCount
    };

    console.log(LOG, "installed");
})();
