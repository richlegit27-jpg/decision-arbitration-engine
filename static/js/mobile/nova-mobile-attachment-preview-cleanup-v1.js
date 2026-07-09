(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_PREVIEW_CLEANUP_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_PREVIEW_CLEANUP_V1_20260704__ = true;

    const LOG = "[Nova Mobile Attachment Preview Cleanup V1]";

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

    const COMPOSER_SELECTORS = [
        "#mobileComposer",
        "#mobileInputBar",
        "#mobileInputForm",
        "#mobileChatInputForm",
        ".mobile-composer",
        ".mobile-input-bar",
        ".mobile-chat-input",
        "[data-nova-mobile-composer]",
        "footer"
    ];

    function textOf(el) {
        return String(
            (el && (
                (el.id || "") + " " +
                (el.className || "") + " " +
                (el.getAttribute && el.getAttribute("aria-label") || "") + " " +
                (el.getAttribute && el.getAttribute("title") || "") + " " +
                (el.innerText || el.textContent || "")
            )) || ""
        ).replace(/\s+/g, " ").trim();
    }

    function roots() {
        const found = COMPOSER_SELECTORS
            .flatMap(function (selector) {
                return Array.from(document.querySelectorAll(selector));
            })
            .filter(Boolean);

        return found.length ? found : [document.body];
    }

    function isCloseLike(el) {
        const t = textOf(el).toLowerCase();

        if (!t) {
            return false;
        }

        if (/send|stop|voice|speak|tts|session|rename|pin|logout|account|new chat|copy|regen|regenerate/.test(t)) {
            return false;
        }

        return /(^x$)|(^×$)|close|remove|clear|delete|dismiss|cancel/.test(t);
    }

function looksLikePreview(el) {

    if (el && el.id === "nova-mobile-upload-preview-owner") {
        return false;
    }

    if (!el || el === document.body || el === document.documentElement) {
        return false;
    }

    const t = textOf(el).toLowerCase();

    if (/preview|attachment|upload|chip|file|image|photo/.test(String(el.id || "") + " " + String(el.className || ""))) {
        return true;
    }

    if (el.querySelector && el.querySelector("img, video, canvas")) {
        return true;
    }

    if (/\.(png|jpe?g|webp|gif|pdf|txt|md|docx?|csv|json)\b/i.test(t)) {
        return true;
    }
    function findPreviewRoot(start) {
        if (!start || !start.closest) {
            return null;
        }

        const direct = start.closest(PREVIEW_SELECTORS.join(","));

        if (direct) {
            return direct;
        }

        let el = start;
        let best = null;

        for (let i = 0; i < 8 && el && el !== document.body; i++) {
            if (looksLikePreview(el)) {
                best = el;
            }

            el = el.parentElement;
        }

        return best;
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

    function removePreviewNodes() {
        const removed = [];

        roots().forEach(function (root) {
            PREVIEW_SELECTORS.forEach(function (selector) {
                root.querySelectorAll(selector).forEach(function (el) {
                    if (!el || removed.includes(el)) {
                        return;
                    }

                    removed.push(el);

                    try {
                        el.remove();
                    } catch (_) {
                        el.style.setProperty("display", "none", "important");
                        el.innerHTML = "";
                    }
                });
            });

            root.querySelectorAll("div,section,aside,span,label").forEach(function (el) {
                if (!looksLikePreview(el)) {
                    return;
                }

                const rect = el.getBoundingClientRect();

                if (rect.height > 180 || rect.width > window.innerWidth * 0.98) {
                    return;
                }

                if (textOf(el).length > 260) {
                    return;
                }

                if (!removed.includes(el)) {
                    removed.push(el);

                    try {
                        el.remove();
                    } catch (_) {
                        el.style.setProperty("display", "none", "important");
                        el.innerHTML = "";
                    }
                }
            });
        });

        return removed.length;
    }

    function clear(reason) {
        resetQueues();
        clearFileInputs();

        let count = 0;

        for (let i = 0; i < 4; i++) {
            count += removePreviewNodes();
        }

        try {
            document.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
                detail: {
                    reason: reason || "manual",
                    removed: count
                }
            }));
        } catch (_) {}

        console.log(LOG, "cleared", {
            reason: reason || "manual",
            removed: count
        });

        return count;
    }

    function maybeClosePreview(event) {
        const target = event.target;

        if (!target || !target.closest) {
            return;
        }

        const closeEl = target.closest("button,a,[role='button'],span,div");

        if (!isCloseLike(closeEl)) {
            return;
        }

        const root = findPreviewRoot(closeEl);

        if (!root) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }

        clear("preview-close");

        return false;
    }

    ["pointerdown", "pointerup", "touchstart", "touchend", "click"].forEach(function (eventName) {
        document.addEventListener(eventName, maybeClosePreview, true);
    });

    const originalFetch = window.fetch && window.fetch.bind(window);

    if (originalFetch && !window.__NOVA_MOBILE_ATTACHMENT_PREVIEW_CLEANUP_FETCH_PATCHED__) {
        window.__NOVA_MOBILE_ATTACHMENT_PREVIEW_CLEANUP_FETCH_PATCHED__ = true;

        window.fetch = async function novaMobileAttachmentPreviewCleanupFetch(input, init) {
            const url = typeof input === "string" ? input : (input && input.url) || "";
            const response = await originalFetch(input, init);

            if (/\/api\/chat(?:\/stream)?(?:\?|$)/.test(String(url || ""))) {
                try {
                    const cloned = response.clone();

                    cloned.json().then(function (data) {
                        if (response.ok && (!data || data.ok !== false)) {
                            setTimeout(function () {
                                clear("chat-send-success");
                            }, 120);
                            setTimeout(function () {
                                clear("chat-send-success-late");
                            }, 650);
                        }
                    }).catch(function () {
                        if (response.ok) {
                            setTimeout(function () {
                                clear("chat-send-success-nonjson");
                            }, 120);
                            setTimeout(function () {
                                clear("chat-send-success-nonjson-late");
                            }, 650);
                        }
                    });
                } catch (_) {
                    if (response.ok) {
                        setTimeout(function () {
                            clear("chat-send-success-fallback");
                        }, 120);
                    }
                }
            }

            return response;
        };
    }

    window.NovaMobileAttachmentPreviewCleanupV1 = {
        clear: clear,
        removePreviewNodes: removePreviewNodes
    };

    console.log(LOG, "installed");
})();
