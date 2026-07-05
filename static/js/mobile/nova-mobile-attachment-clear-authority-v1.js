/* NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V3_20260705 */
(function installNovaMobileAttachmentClearAuthorityV3() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V3_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V3_20260705__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V2_20260705__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705__ = true;

    const STORAGE_RE = /nova.*(attach|attachment|upload|preview|pending|file|image)/i;
    const MARKER_RE = /(attach|attachment|upload|preview|pending|file|image)/i;
    const REMOVE_RE = /(preview|chip|thumb|pending|queue|attachment-list|upload-list|file-list|image-list|upload-preview)/i;

    const KEEP_IDS = new Set([
        "nova-mobile-file-input",
        "nova-mobile-attach"
    ]);

    const MESSAGE_ROOT_SELECTORS = [
        "#mobileChatMessages",
        ".mobile-chat-container",
        "[data-nova-role='messages']"
    ];

    let lastAttachIntentAt = 0;
    let fallbackSendClearTimer = null;

    function log() {
        try {
            console.log.apply(console, arguments);
        } catch (_) {}
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
            el.getAttribute && el.getAttribute("aria-label"),
            el.getAttribute && el.getAttribute("title")
        ].filter(Boolean).join(" ");
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

    function hasSelectedFile() {
        for (const input of document.querySelectorAll("input[type='file']")) {
            try {
                if (input.files && input.files.length > 0) {
                    return true;
                }
            } catch (_) {}
        }

        return false;
    }

    function previewOwner() {
        return document.getElementById("nova-mobile-upload-preview-owner");
    }

    function unlockPreviewForAttach(reason) {
        lastAttachIntentAt = Date.now();

        const owner = previewOwner();

        if (owner) {
            try {
                owner.hidden = false;
                owner.removeAttribute("hidden");
                owner.removeAttribute("aria-hidden");
                owner.style.removeProperty("display");
                owner.style.removeProperty("visibility");
                owner.style.removeProperty("opacity");
                owner.style.removeProperty("pointer-events");
            } catch (_) {}
        }

        log("[Nova Attachment Clear V3] unlocked preview for attach", reason || "");
    }

    function clearStorage() {
        for (const store of [window.localStorage, window.sessionStorage]) {
            if (!store) continue;

            for (const key of Object.keys(store)) {
                if (STORAGE_RE.test(key)) {
                    try {
                        log("[Nova Attachment Clear V3] removing storage key", key);
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

    function clearKnownQueues() {
        const arrayNames = [
            "__novaMobilePendingAttachments",
            "__NOVA_MOBILE_PENDING_ATTACHMENTS__",
            "NovaMobilePendingAttachments",
            "novaMobilePendingAttachments",
            "__novaMobileAttachmentQueue",
            "__NOVA_MOBILE_ATTACHMENT_QUEUE__",
            "NovaMobileAttachmentQueue",
            "__novaMobileUploadedAttachments",
            "__NOVA_MOBILE_UPLOADED_ATTACHMENTS__",
            "NovaMobileUploadedAttachments"
        ];

        for (const name of arrayNames) {
            try {
                if (Array.isArray(window[name])) {
                    window[name].length = 0;
                }

                window[name] = [];
            } catch (_) {}
        }

        const objectNames = [
            "NovaMobileSharedAttachments",
            "NovaMobileUpload",
            "NovaMobileImages",
            "NovaMobileAttachmentState",
            "NovaMobileAttachmentQueue",
            "NovaMobileUploadState"
        ];

        for (const name of objectNames) {
            const obj = window[name];

            if (!obj || typeof obj !== "object") continue;

            for (const method of [
                "clear",
                "reset",
                "clearAll",
                "clearQueue",
                "clearPending",
                "resetQueue",
                "removeAll",
                "clearAttachments",
                "resetAttachments",
                "clearPreview",
                "clearPreviews"
            ]) {
                try {
                    if (typeof obj[method] === "function") {
                        obj[method]();
                    }
                } catch (_) {}
            }

            for (const prop of [
                "pending",
                "queue",
                "attachments",
                "files",
                "images",
                "items",
                "previews",
                "uploaded",
                "uploadedAttachments",
                "pendingAttachments"
            ]) {
                try {
                    if (Array.isArray(obj[prop])) {
                        obj[prop].length = 0;
                    }
                } catch (_) {}
            }
        }
    }

    function hidePreviewOwner() {
        const owner = previewOwner();

        if (!owner) return;

        try {
            owner.innerHTML = "";
            owner.hidden = true;
            owner.setAttribute("aria-hidden", "true");
            owner.style.setProperty("display", "none", "important");
            owner.style.setProperty("visibility", "hidden", "important");
            owner.style.setProperty("opacity", "0", "important");
            owner.style.setProperty("pointer-events", "none", "important");
        } catch (_) {}
    }

    function shouldRemoveElement(el) {
        if (!el) return false;
        if (isInsideMessages(el)) return false;
        if (KEEP_IDS.has(el.id)) return false;

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
            return false;
        }

        const marker = markerFor(el);

        return MARKER_RE.test(marker) && REMOVE_RE.test(marker);
    }

    function removePreviewDom() {
        hidePreviewOwner();

        for (const el of Array.from(document.querySelectorAll("*"))) {
            if (shouldRemoveElement(el)) {
                try {
                    log("[Nova Attachment Clear V3] removing preview-ish element", el);
                    el.remove();
                } catch (_) {}
            }
        }
    }

    function clearAfterSend(reason) {
        clearFileInputs();
        clearStorage();
        clearKnownQueues();
        removePreviewDom();

        log("[Nova Attachment Clear V3] cleared after send", reason || "");
    }

    function clearAfterSendSweep(reason) {
        const delays = [100, 400, 900, 1800, 3500];

        for (const delay of delays) {
            setTimeout(function () {
                clearAfterSend((reason || "send-success") + ":t+" + delay);
            }, delay);
        }
    }

    function delayedFallbackClear(reason) {
        if (fallbackSendClearTimer) {
            clearTimeout(fallbackSendClearTimer);
        }

        fallbackSendClearTimer = setTimeout(function () {
            clearAfterSendSweep(reason || "send-fallback-delayed");
        }, 2500);
    }

    function installFetchHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V3__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V3__ = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") return;

        window.fetch = function novaMobileAttachmentClearFetchHookV3(input, init) {
            const url = typeof input === "string" ? input : input && input.url;
            const method = String((init && init.method) || "GET").toUpperCase();

            const isChatSend =
                method === "POST" &&
                /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""));

            return originalFetch.apply(this, arguments).then(function (response) {
                try {
                    if (response && response.ok && isChatSend) {
                        clearAfterSendSweep("fetch-chat-send-success");
                    }
                } catch (_) {}

                return response;
            });
        };
    }

    function installXhrHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_XHR_HOOK_V3__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_CLEAR_XHR_HOOK_V3__ = true;

        const OriginalXHR = window.XMLHttpRequest;

        if (typeof OriginalXHR !== "function") return;

        const originalOpen = OriginalXHR.prototype.open;
        const originalSend = OriginalXHR.prototype.send;

        OriginalXHR.prototype.open = function novaAttachmentClearXhrOpenV3(method, url) {
            try {
                this.__novaAttachmentClearMethod = String(method || "GET").toUpperCase();
                this.__novaAttachmentClearUrl = String(url || "");
            } catch (_) {}

            return originalOpen.apply(this, arguments);
        };

        OriginalXHR.prototype.send = function novaAttachmentClearXhrSendV3() {
            try {
                const isChatSend =
                    this.__novaAttachmentClearMethod === "POST" &&
                    /\/api\/chat(?:\/stream)?(?:\?|$)/.test(this.__novaAttachmentClearUrl || "");

                if (isChatSend) {
                    this.addEventListener("loadend", function () {
                        if (this.status >= 200 && this.status < 300) {
                            clearAfterSendSweep("xhr-chat-send-success");
                        }
                    });
                }
            } catch (_) {}

            return originalSend.apply(this, arguments);
        };
    }

    function installInteractionHooks() {
        document.addEventListener("click", function (event) {
            const button = event.target && event.target.closest && event.target.closest("button");

            if (!button) return;

            const marker = markerFor(button);
            const text = (button.textContent || "").trim();

            if (
                button.id === "nova-mobile-attach" ||
                /attach|upload|file/i.test(marker)
            ) {
                unlockPreviewForAttach("attach-click");
                return;
            }

            if (/send/i.test(marker) || /^send$/i.test(text) || /mobile-send/i.test(marker)) {
                delayedFallbackClear("send-click-delayed-fallback");
            }
        }, true);

        document.addEventListener("change", function (event) {
            const target = event.target;

            if (target && target.matches && target.matches("input[type='file']")) {
                unlockPreviewForAttach("file-input-change");
            }
        }, true);

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" || event.shiftKey) return;

            const target = event.target;
            if (!target) return;

            const marker = markerFor(target);

            if (
                /message|composer|chat|input|textarea/i.test(marker) ||
                target.tagName === "TEXTAREA" ||
                target.isContentEditable
            ) {
                delayedFallbackClear("enter-send-delayed-fallback");
            }
        }, true);
    }

    window.NovaMobileAttachmentClearAuthorityV1 = {
        version: "NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V3_20260705",
        clear: function (reason) {
            clearAfterSend(reason || "manual");
        },
        clearAfterSend: clearAfterSend,
        clearAfterSendSweep: clearAfterSendSweep,
        unlockPreviewForAttach: unlockPreviewForAttach
    };

    installFetchHook();
    installXhrHook();
    installInteractionHooks();

    log("[Nova Attachment Clear V3] authority installed");
})();
