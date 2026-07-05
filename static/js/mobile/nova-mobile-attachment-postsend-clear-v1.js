(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704__ = true;

    function clearAttachmentPreviewDom() {
        const selectors = [
            "[data-nova-attachment-preview]",
            "[data-nova-upload-preview]",
            ".nova-mobile-attachment-preview",
            ".nova-attachment-preview",
            ".mobile-attachment-preview",
            "#nova-mobile-attachment-preview",
            "#novaAttachmentPreview",
            "#attachmentPreview"
        ];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                el.remove();
            });
        });
    }

    function clearAttachmentState() {
        try {
            if (window.NovaMobileAttachmentSendBridgeV1?.clearQueuedAttachments) {
                window.NovaMobileAttachmentSendBridgeV1.clearQueuedAttachments();
            }
        } catch (_) {}

        try {
            if (window.NovaMobileAttachmentSendBridgeV1?.setQueuedAttachments) {
                window.NovaMobileAttachmentSendBridgeV1.setQueuedAttachments([]);
            }
        } catch (_) {}

        try {
            window.NovaMobileQueuedAttachments = [];
            window.novaMobileQueuedAttachments = [];
            window.__nova_mobile_queued_attachments = [];
        } catch (_) {}
    }

    function clear() {
        clearAttachmentState();
        clearAttachmentPreviewDom();
        console.log("[NOVA ATTACHMENT POSTSEND CLEAR] cleared");
    }

    window.NovaMobileAttachmentPostsendClearV1 = {
        clear: clear
    };

    window.addEventListener("nova:message-sent", clear);
    window.addEventListener("nova-mobile:message-sent", clear);
    window.addEventListener("nova:send-complete", clear);

    console.log("[NOVA_MOBILE_ATTACHMENT_POSTSEND_CLEAR_V1_20260704] ready");
})();
