/* NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705 */
(function installNovaMobileAttachmentClearAuthorityV1() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705__ = true;

    const STORAGE_RE = /nova.*(attach|attachment|upload|preview|pending|file|image)/i;
    const MARKER_RE = /(attach|attachment|upload|preview|pending|file|image)/i;
    const REMOVE_RE = /(preview|chip|thumb|pending|queue|attachment-list|upload-list|file-list|image-list)/i;

    const MESSAGE_ROOT_SELECTORS = [
        "#mobileChatMessages",
        ".mobile-chat-container",
        "[data-nova-role='messages']"
    ];

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
    }

    function isInsideMessages(el) {
        if (!el || !el.closest) return false;

        for (const selector of MESSAGE_ROOT_SELECTORS) {
            try {
                if (el.closest(selector)) return true;
            } catch (_) {}
        }

        return false;
    }

    function markerFor(el) {
        if (!el) return "";

        return [
            el.id || "",
            String(el.className || ""),
            el.getAttribute && el.getAttribute("data-nova-role"),
            el.getAttribute && el.getAttribute("data-role"),
            el.getAttribute && el.getAttribute("data-attachment-id"),
            el.getAttribute && el.getAttribute("data-upload-id"),
            el.getAttribute && el.getAttribute("data-preview"),
            el.getAttribute && el.getAttribute("aria-label")
        ].filter(Boolean).join(" ");
    }

    function clearStorage() {
        for (const store of [window.localStorage, window.sessionStorage]) {
            if (!store) continue;

            for (const key of Object.keys(store)) {
                if (STORAGE_RE.test(key)) {
                    try {
                        log("[Nova Attachment Clear] removing storage key", key);
                        store.removeItem(key);
                    } catch (_) {}
                }
            }
        }
    }

    function clearFileInputs() {
        for (const input of document.querySelectorAll("input[type='file']")) {
            try {
                input.value = "";
            } catch (_) {}
        }
    }

    function clearWindowQueues() {
        const names = [
            "__novaMobilePendingAttachments",
            "__NOVA_MOBILE_PENDING_ATTACHMENTS__",
            "NovaMobilePendingAttachments",
            "novaMobilePendingAttachments",
            "__novaMobileAttachmentQueue",
            "__NOVA_MOBILE_ATTACHMENT_QUEUE__",
            "NovaMobileAttachmentQueue"
        ];

        for (const name of names) {
            try {
                window[name] = [];
            } catch (_) {}
        }

        const objectNames = [
            "NovaMobileSharedAttachments",
            "NovaMobileUpload",
            "NovaMobileImages",
            "NovaMobileAttachmentState",
            "NovaMobileAttachmentQueue"
        ];

        for (const name of objectNames) {
            const obj = window[name];

            if (!obj || typeof obj !== "object") continue;

            for (const method of ["clear", "reset", "clearAll", "clearQueue", "clearPending", "resetQueue", "removeAll"]) {
                try {
                    if (typeof obj[method] === "function") {
                        obj[method]();
                    }
                } catch (_) {}
            }

            for (const prop of ["pending", "queue", "attachments", "files", "images", "items", "previews"]) {
                try {
                    if (Array.isArray(obj[prop])) {
                        obj[prop].length = 0;
                    }
                } catch (_) {}
            }
        }
    }

    function removePreviewDom() {
        for (const el of Array.from(document.querySelectorAll("*"))) {
            if (!el || isInsideMessages(el)) continue;

            const tag = String(el.tagName || "").toLowerCase();

            if (
                tag === "html" ||
                tag === "head" ||
                tag === "body" ||
                tag === "script" ||
                tag === "style" ||
                tag === "input" ||
                tag === "textarea" ||
                tag === "button" ||
                tag === "form"
            ) {
                continue;
            }

            const marker = markerFor(el);

            if (MARKER_RE.test(marker) && REMOVE_RE.test(marker)) {
                try {
                    log("[Nova Attachment Clear] removing preview-ish element", el);
                    el.remove();
                } catch (_) {}
            }
        }
    }

    function clear(reason) {
        clearFileInputs();
        clearStorage();
        clearWindowQueues();
        removePreviewDom();

        log("[Nova Attachment Clear] cleared", reason || "manual");
    }

    function scheduleClear(reason) {
        setTimeout(function () {
            clear(reason);
        }, 100);

        setTimeout(function () {
            clear(reason + ":late");
        }, 900);
    }

    function installFetchHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V1__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V1__ = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") {
            return;
        }

        window.fetch = function novaMobileAttachmentClearFetchHook(input, init) {
            const url = typeof input === "string" ? input : input && input.url;
            const method = String((init && init.method) || "GET").toUpperCase();

            return originalFetch.apply(this, arguments).then(function (response) {
                try {
                    if (
                        response &&
                        response.ok &&
                        method === "POST" &&
                        /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""))
                    ) {
                        scheduleClear("chat-send-success");
                    }
                } catch (_) {}

                return response;
            });
        };
    }

    window.NovaMobileAttachmentClearAuthorityV1 = {
        version: "NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705",
        clear: clear,
        scheduleClear: scheduleClear
    };

    installFetchHook();

    log("[Nova Attachment Clear] authority installed");
})();
