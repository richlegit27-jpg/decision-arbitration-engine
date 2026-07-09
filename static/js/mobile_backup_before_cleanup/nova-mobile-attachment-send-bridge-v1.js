(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_SEND_BRIDGE_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_SEND_BRIDGE_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attachment Send Bridge V1]";
    const QUEUE_KEY = "__NOVA_MOBILE_ATTACHMENT_SEND_QUEUE_V1__";

    function queue() {
        if (!Array.isArray(window[QUEUE_KEY])) {
            window[QUEUE_KEY] = [];
        }
        return window[QUEUE_KEY];
    }

    function normalizeAttachment(raw) {
        if (!raw || typeof raw !== "object") {
            return null;
        }

        const source = raw.attachment && typeof raw.attachment === "object"
            ? raw.attachment
            : raw;

        const filename = source.filename || source.name || source.original_filename || raw.filename || raw.name;
        const url = source.url || source.file_url || source.path || raw.url || raw.file_url || raw.path;
        const mimeType = source.mime_type || source.mimeType || source.type || raw.mime_type || raw.type || "";

        if (!filename && !url) {
            return null;
        }

        return {
            filename: filename || "attachment",
            name: filename || "attachment",
            url: url || "",
            path: source.path || raw.path || url || "",
            mime_type: mimeType,
            type: mimeType,
            size: source.size || source.size_bytes || raw.size || raw.size_bytes || null,
            source: "mobile-upload"
        };
    }

    function rememberAttachment(raw) {
        const attachment = normalizeAttachment(raw);

        if (!attachment) {
            return;
        }

        const q = queue();
        const key = String(attachment.url || attachment.path || attachment.filename);

        const exists = q.some(function (item) {
            return String(item.url || item.path || item.filename) === key;
        });

        if (!exists) {
            q.push(attachment);
        }

        window.NovaMobilePendingAttachments = q;
        window.novaMobilePendingAttachments = q;

        console.log(LOG, "queued attachment", attachment);
    }

    function getQueuedAttachments() {
        const candidates = [
            queue(),
            window.NovaMobilePendingAttachments,
            window.novaMobilePendingAttachments,
            window.NovaMobileSharedAttachments,
            window.novaMobileSharedAttachments,
            window.NovaMobileAttachmentQueue,
            window.novaMobileAttachmentQueue
        ];

        const merged = [];

        candidates.forEach(function (candidate) {
            if (!Array.isArray(candidate)) {
                return;
            }

            candidate.forEach(function (item) {
                const attachment = normalizeAttachment(item);
                if (!attachment) {
                    return;
                }

                const key = String(attachment.url || attachment.path || attachment.filename);
                const exists = merged.some(function (existing) {
                    return String(existing.url || existing.path || existing.filename) === key;
                });

                if (!exists) {
                    merged.push(attachment);
                }
            });
        });

        return merged;
    }

    function clearAttachmentQueues() {
        window[QUEUE_KEY] = [];
        window.NovaMobilePendingAttachments = [];
        window.novaMobilePendingAttachments = [];

        [
            "NovaMobileSharedAttachments",
            "novaMobileSharedAttachments",
            "NovaMobileAttachmentQueue",
            "novaMobileAttachmentQueue"
        ].forEach(function (key) {
            if (Array.isArray(window[key])) {
                window[key].length = 0;
            }
        });
    }

    function clearFileInputs() {
        document.querySelectorAll("input[type='file']").forEach(function (input) {
            try {
                input.value = "";
            } catch (_) {}
        });
    }

    function clearPreviewDom() {
        const composerRoots = [
            document.getElementById("mobileComposer"),
            document.getElementById("mobileInputBar"),
            document.getElementById("mobileInputForm"),
            document.querySelector(".mobile-composer"),
            document.querySelector(".mobile-input-bar"),
            document.querySelector("[data-nova-mobile-composer]")
        ].filter(Boolean);

        const roots = composerRoots.length ? composerRoots : [document.body];

        const selectors = [
            "[data-nova-attachment-preview]",
            "[data-nova-mobile-attachment-preview]",
            "#nova-mobile-attachment-preview",
            "#nova-mobile-attachment-preview-bar",
            "#nova-mobile-preview-bar",
            ".nova-mobile-attachment-preview",
            ".nova-mobile-attachment-preview-bar",
            ".nova-mobile-preview-bar",
            ".nova-mobile-attachment-chip",
            ".mobile-attachment-preview",
            ".mobile-attachment-chip"
        ];

        roots.forEach(function (root) {
            selectors.forEach(function (selector) {
                root.querySelectorAll(selector).forEach(function (el) {
                    try {
                        el.remove();
                    } catch (_) {
                        el.style.setProperty("display", "none", "important");
                        el.innerHTML = "";
                    }
                });
            });
        });
    }

    function clearAfterSuccessfulSend() {
        clearAttachmentQueues();
        clearFileInputs();
        clearPreviewDom();

        try {
            document.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared"));
        } catch (_) {}

        console.log(LOG, "cleared attachments after send");
    }

    function isUploadUrl(url) {
        return /\/api\/upload(?:\?|$)/.test(String(url || ""));
    }

    function isChatUrl(url) {
        return /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""));
    }

    function readBodyJson(init) {
        if (!init || typeof init.body !== "string") {
            return null;
        }

        try {
            return JSON.parse(init.body);
        } catch (_) {
            return null;
        }
    }

    function writeBodyJson(init, payload) {
        init.body = JSON.stringify(payload);

        init.headers = init.headers || {};

        if (init.headers instanceof Headers) {
            init.headers.set("Content-Type", "application/json");
            init.headers.set("Accept", "application/json");
        } else {
            init.headers["Content-Type"] = init.headers["Content-Type"] || "application/json";
            init.headers["Accept"] = init.headers["Accept"] || "application/json";
        }
    }

    const originalFetch = window.fetch.bind(window);

    window.fetch = async function novaMobileAttachmentSendBridgeFetch(input, init) {
        const url = typeof input === "string" ? input : (input && input.url) || "";

        if (isChatUrl(url) && init && typeof init.body === "string") {
            const payload = readBodyJson(init);
            const attachments = getQueuedAttachments();

            if (payload && attachments.length) {
                const existing = Array.isArray(payload.attachments) ? payload.attachments : [];

                payload.attachments = existing.concat(
                    attachments.filter(function (attachment) {
                        const key = String(attachment.url || attachment.path || attachment.filename);
                        return !existing.some(function (item) {
                            return String(item.url || item.path || item.filename) === key;
                        });
                    })
                );

                payload.files = payload.attachments;
                payload.uploads = payload.attachments;

                writeBodyJson(init, payload);

                console.log(LOG, "injected attachments into chat payload", payload.attachments);
            }
        }

        const response = await originalFetch(input, init);

        if (isUploadUrl(url)) {
            try {
                response.clone().json().then(function (data) {
                    if (data && data.ok !== false) {
                        rememberAttachment(data);
                    }
                }).catch(function () {});
            } catch (_) {}
        }

        if (isChatUrl(url)) {
            try {
                const cloned = response.clone();

                cloned.json().then(function (data) {
                    if (response.ok && (!data || data.ok !== false)) {
                        clearAfterSuccessfulSend();
                    }
                }).catch(function () {
                    if (response.ok) {
                        clearAfterSuccessfulSend();
                    }
                });
            } catch (_) {
                if (response.ok) {
                    clearAfterSuccessfulSend();
                }
            }
        }

        return response;
    };

    window.NovaMobileAttachmentSendBridgeV1 = {
        queue: queue,
        remember: rememberAttachment,
        clear: clearAfterSuccessfulSend,
        getQueuedAttachments: getQueuedAttachments
    };

    console.log(LOG, "installed");
})();
