/* NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V4_VISUAL_ONLY_20260705 */
(function installNovaMobileAttachmentClearAuthorityV4VisualOnly() {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V4_VISUAL_ONLY_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V4_VISUAL_ONLY_20260705__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V3_20260705__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V2_20260705__ = true;
    window.__NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V1_20260705__ = true;

    const MESSAGE_ROOT_SELECTORS = [
        "#mobileChatMessages",
        ".mobile-chat-container",
        "[data-nova-role='messages']"
    ];

    const KEEP_IDS = new Set([
        "nova-mobile-file-input",
        "nova-mobile-attach"
    ]);

    const MARKER_RE = /(attach|attachment|upload|preview|pending|file|image)/i;
    const REMOVE_RE = /(preview|chip|thumb|attachment-list|upload-list|file-list|image-list|upload-preview)/i;

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

    function shouldRemoveVisualPreview(el) {
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

    function showPreviewOwner(reason) {
        const owner = document.getElementById("nova-mobile-upload-preview-owner");

        if (!owner) return;

        try {
            owner.hidden = false;
            owner.removeAttribute("hidden");
            owner.removeAttribute("aria-hidden");
            owner.style.removeProperty("display");
            owner.style.removeProperty("visibility");
            owner.style.removeProperty("opacity");
            owner.style.removeProperty("pointer-events");
        } catch (_) {}

        log("[Nova Attachment Clear V4] preview owner unlocked", reason || "");
    }

    function hideVisualPreview(reason) {
        const owner = document.getElementById("nova-mobile-upload-preview-owner");

        if (owner) {
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

        for (const el of Array.from(document.querySelectorAll("*"))) {
            if (shouldRemoveVisualPreview(el)) {
                try {
                    log("[Nova Attachment Clear V4] removing visual preview", el);
                    el.remove();
                } catch (_) {}
            }
        }

        log("[Nova Attachment Clear V4] visual preview hidden", reason || "");
    }

    function hideVisualPreviewSweep(reason) {
        const delays = [500, 1200, 2500, 4500, 7000];

        for (const delay of delays) {
            setTimeout(function () {
                hideVisualPreview((reason || "sweep") + ":t+" + delay);
            }, delay);
        }
    }

    function installFetchHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V4_VISUAL_ONLY__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_CLEAR_FETCH_HOOK_V4_VISUAL_ONLY__ = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") return;

        window.fetch = function novaMobileAttachmentClearFetchHookV4(input, init) {
            const url = typeof input === "string" ? input : input && input.url;
            const method = String((init && init.method) || "GET").toUpperCase();

            const isChatSend =
                method === "POST" &&
                /\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""));

            return originalFetch.apply(this, arguments).then(function (response) {
                try {
                    if (response && response.ok && isChatSend) {
                        hideVisualPreviewSweep("fetch-chat-send-success");
                    }
                } catch (_) {}

                return response;
            });
        };
    }

    function installXhrHook() {
        if (window.__NOVA_MOBILE_ATTACHMENT_CLEAR_XHR_HOOK_V4_VISUAL_ONLY__) {
            return;
        }

        window.__NOVA_MOBILE_ATTACHMENT_CLEAR_XHR_HOOK_V4_VISUAL_ONLY__ = true;

        const OriginalXHR = window.XMLHttpRequest;

        if (typeof OriginalXHR !== "function") return;

        const originalOpen = OriginalXHR.prototype.open;
        const originalSend = OriginalXHR.prototype.send;

        OriginalXHR.prototype.open = function novaAttachmentClearXhrOpenV4(method, url) {
            try {
                this.__novaAttachmentClearMethod = String(method || "GET").toUpperCase();
                this.__novaAttachmentClearUrl = String(url || "");
            } catch (_) {}

            return originalOpen.apply(this, arguments);
        };

        OriginalXHR.prototype.send = function novaAttachmentClearXhrSendV4() {
            try {
                const isChatSend =
                    this.__novaAttachmentClearMethod === "POST" &&
                    /\/api\/chat(?:\/stream)?(?:\?|$)/.test(this.__novaAttachmentClearUrl || "");

                if (isChatSend) {
                    this.addEventListener("loadend", function () {
                        if (this.status >= 200 && this.status < 300) {
                            hideVisualPreviewSweep("xhr-chat-send-success");
                        }
                    });
                }
            } catch (_) {}

            return originalSend.apply(this, arguments);
        };
    }

    function installAttachUnlockHook() {
        document.addEventListener("click", function (event) {
            const button = event.target && event.target.closest && event.target.closest("button");

            if (!button) return;

            const marker = markerFor(button);

            if (
                button.id === "nova-mobile-attach" ||
                /attach|upload|file/i.test(marker)
            ) {
                showPreviewOwner("attach-click");
            }
        }, true);

        document.addEventListener("change", function (event) {
            const target = event.target;

            if (target && target.matches && target.matches("input[type='file']")) {
                showPreviewOwner("file-input-change");
            }
        }, true);
    }

    window.NovaMobileAttachmentClearAuthorityV1 = {
        version: "NOVA_MOBILE_ATTACHMENT_CLEAR_AUTHORITY_V4_VISUAL_ONLY_20260705",
        hideVisualPreview,
        hideVisualPreviewSweep,
        showPreviewOwner,
        clear: hideVisualPreview
    };

    installFetchHook();
    installXhrHook();
    installAttachUnlockHook();

    log("[Nova Attachment Clear V4] visual-only authority installed");
})();
