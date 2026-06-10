// NOVA_MOBILE_QUIET_REMAINING_ATTACHMENT_LOGS_20260608
window.NOVA_MOBILE_ATTACHMENT_DEBUG = window.NOVA_MOBILE_ATTACHMENT_DEBUG === true;

window.NovaMobileAttachmentDebugLog = window.NovaMobileAttachmentDebugLog || function () {
    if (!window.NOVA_MOBILE_ATTACHMENT_DEBUG) return;
    try {
        console.log.apply(console, arguments);
    } catch (e) {}
};

window.NovaMobileAttachmentDebugWarn = window.NovaMobileAttachmentDebugWarn || function () {
    if (!window.NOVA_MOBILE_ATTACHMENT_DEBUG) return;
    try {
        console.warn.apply(console, arguments);
    } catch (e) {}
};
/* NOVA_MOBILE_ATTACHMENT_PAYLOAD_MODULE_20260606 */

/* NOVA_CAPTURE_UPLOAD_FETCH_20260606 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.__novaCaptureUploadFetchInstalled) {
        return;
    }

    window.__novaCaptureUploadFetchInstalled = true;

    const previousFetch = window.fetch.bind(window);

    function normalizeCapturedUpload(data) {
        const source = data && data.file ? data.file : data || {};

        return {
            ok: true,
            filename: source.filename || source.name || source.original_filename || data.filename || data.name || "attachment",
            original_filename: source.original_filename || source.filename || source.name || data.original_filename || data.filename || "attachment",
            mime_type: source.mime_type || source.content_type || data.mime_type || data.content_type || "",
            url: source.url || source.file_url || source.path || data.url || data.file_url || data.path || "",
            file_url: source.file_url || source.url || source.path || data.file_url || data.url || data.path || "",
            size: source.size || data.size || 0
        };
    }

    function storeCapturedAttachment(attachment) {
        if (!attachment || (!attachment.url && !attachment.file_url && !attachment.filename)) {
            window.NovaMobileAttachmentDebugWarn("[Nova Mobile Upload Capture] skipped empty attachment", attachment);
            return;
        }

        window.NovaMobileSharedAttachments = window.NovaMobileSharedAttachments || [];

        const key = String(attachment.url || attachment.file_url || attachment.filename || "");

        const exists = window.NovaMobileSharedAttachments.some(function (item) {
            return String(item.url || item.file_url || item.filename || "") === key;
        });

        if (!exists) {
            window.NovaMobileSharedAttachments.push(attachment);
        }

        try {
            localStorage.setItem(
                "nova_mobile_pending_attachments",
                JSON.stringify(window.NovaMobileSharedAttachments)
            );
        } catch (_) {}

        if (typeof window.NovaMobileReceiveUploadedAttachment === "function") {
            window.NovaMobileReceiveUploadedAttachment(attachment, null);
        }

        window.NovaMobileAttachmentDebugLog("[Nova Mobile Upload Capture] captured /api/upload attachment", attachment);
    }

    window.fetch = async function (input, init) {
        const url = typeof input === "string" ? input : (input && input.url ? input.url : "");

        const response = await previousFetch(input, init);

        try {
            if (url.includes("/api/upload")) {
                const clone = response.clone();
                const data = await clone.json();

                if (Array.isArray(data.files)) {
                    data.files.forEach(function (item) {
                        storeCapturedAttachment(normalizeCapturedUpload(item));
                    });
                } else {
                    storeCapturedAttachment(normalizeCapturedUpload(data));
                }
            }
        } catch (error) {
            window.NovaMobileAttachmentDebugWarn("[Nova Mobile Upload Capture] failed to capture upload response", error);
        }

        return response;
    };

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Upload Capture] active");
})();

/* NOVA_STRONGER_CHAT_ATTACHMENTS_PAYLOAD_20260606 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.__novaStrongerChatAttachmentsInstalled) {
        return;
    }

    window.__novaStrongerChatAttachmentsInstalled = true;

    const previousFetch = window.fetch.bind(window);

    function readStoredAttachments() {
        const live = Array.isArray(window.NovaMobileSharedAttachments)
            ? window.NovaMobileSharedAttachments
            : [];

        let stored = [];

        try {
            stored = JSON.parse(localStorage.getItem("nova_mobile_pending_attachments") || "[]");
        } catch (_) {
            stored = [];
        }

        const merged = [];

        live.concat(Array.isArray(stored) ? stored : []).forEach(function (item) {
            if (!item) return;

            const normalized = {
                ok: item.ok !== false,
                filename: item.filename || item.name || item.original_filename || "attachment",
                original_filename: item.original_filename || item.filename || item.name || "attachment",
                mime_type: item.mime_type || item.content_type || "",
                url: item.url || item.file_url || item.path || "",
                file_url: item.file_url || item.url || item.path || "",
                size: item.size || 0
            };

            const key = String(normalized.url || normalized.file_url || normalized.filename || "");

            if (!key) return;

            const exists = merged.some(function (existing) {
                return String(existing.url || existing.file_url || existing.filename || "") === key;
            });

            if (!exists) {
                merged.push(normalized);
            }
        });

        return merged;
    }

    function shouldPatchChatUrl(url) {
        return (
            url.includes("/api/chat") ||
            url.includes("/api/chat/stream")
        );
    }

    function patchJsonBody(body) {
        const attachments = readStoredAttachments();

        if (!attachments.length) {
            novaAttachmentDebugLog("[Nova Mobile Payload Guard Strong] no pending attachments to force");
            return body;
        }

        let payload = {};

        try {
            payload = JSON.parse(body || "{}");
        } catch (error) {
            novaAttachmentDebugWarn("[Nova Mobile Payload Guard Strong] body was not JSON", error);
            return body;
        }

        const existing = Array.isArray(payload.attachments)
            ? payload.attachments
            : [];

        if (!existing.length) {
            payload.attachments = attachments;
            payload.force_attachments = true;
            payload.attachment_count = attachments.length;

            novaAttachmentDebugLog("[Nova Mobile Payload Guard Strong] forced attachments into chat payload", attachments);
        } else {
            novaAttachmentDebugLog("[Nova Mobile Payload Guard Strong] payload already had attachments", existing);
        }

        return JSON.stringify(payload);
    }

    window.fetch = async function (input, init) {
        let url = "";
        let nextInput = input;
        let nextInit = init ? Object.assign({}, init) : init;

        try {
            url = typeof input === "string"
                ? input
                : (input && input.url ? input.url : "");

            if (shouldPatchChatUrl(url)) {
                if (nextInit && typeof nextInit.body === "string") {
                    nextInit.body = patchJsonBody(nextInit.body);
                } else if (input instanceof Request) {
                    const cloned = input.clone();
                    const bodyText = await cloned.text();
                    const patchedBody = patchJsonBody(bodyText);

                    nextInput = new Request(input, {
                        body: patchedBody
                    });
                } else {
                    novaAttachmentDebugWarn("[Nova Mobile Payload Guard Strong] chat fetch had no patchable body", {
                        url: url,
                        init: nextInit
                    });
                }
            }
        } catch (error) {
            novaAttachmentDebugWarn("[Nova Mobile Payload Guard Strong] failed before fetch", error);
        }

        const response = await previousFetch(nextInput, nextInit);

        try {
            url = typeof nextInput === "string"
                ? nextInput
                : (nextInput && nextInput.url ? nextInput.url : url);

            if (shouldPatchChatUrl(url)) {
                novaAttachmentDebugLog("[Nova Mobile Payload Guard Strong] chat request completed", {
                    pendingAttachments: readStoredAttachments().length
                });
            }
        } catch (_) {}

        return response;
    };

    novaAttachmentDebugLog("[Nova Mobile Payload Guard Strong] active");
})();


/* NOVA_MOBILE_HARD_UPLOAD_TO_CHAT_PAYLOAD_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaMobileHardUploadToChatPayloadInstalled) {
        return;
    }

    window.NovaMobileHardUploadToChatPayloadInstalled = true;

    var PENDING_KEY = "nova_mobile_pending_attachments";
    var LAST_KEY = "nova_mobile_last_uploaded_attachment";

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    }

    function normalizeAttachment(value) {
        if (!value || typeof value !== "object") {
            return null;
        }

        var source = value.attachment || value.result || value.file || value.upload || value;

        var filename = (
            source.filename ||
            source.original_filename ||
            source.name ||
            source.saved_filename ||
            ""
        );

        var url = (
            source.url ||
            source.file_url ||
            source.path ||
            source.href ||
            ""
        );

        if (!filename && url) {
            filename = String(url).split("/").pop();
        }

        if (!filename && !url) {
            return null;
        }

        return {
            filename: filename,
            original_filename: source.original_filename || filename,
            name: filename,
            url: url,
            file_url: source.file_url || url,
            mime_type: source.mime_type || source.type || "",
            size: source.size || 0,
            source: "hard_upload_to_chat_payload"
        };
    }

    function getPendingAttachments() {
        var found = [];

        var fromPending = parseJson(localStorage.getItem(PENDING_KEY) || "[]", []);
        if (Array.isArray(fromPending)) {
            found = found.concat(fromPending);
        }

        var fromLast = parseJson(localStorage.getItem(LAST_KEY) || "null", null);
        if (fromLast) {
            found.push(fromLast);
        }

        if (Array.isArray(window.NovaMobilePendingAttachments)) {
            found = found.concat(window.NovaMobilePendingAttachments);
        }

        if (Array.isArray(window.__novaMobilePendingAttachments)) {
            found = found.concat(window.__novaMobilePendingAttachments);
        }

        var clean = [];
        var seen = {};

        found.forEach(function (item) {
            var normalized = normalizeAttachment(item);
            if (!normalized) {
                return;
            }

            var key = String(normalized.url || normalized.file_url || normalized.filename || "").toLowerCase();
            if (!key || seen[key]) {
                return;
            }

            seen[key] = true;
            clean.push(normalized);
        });

        return clean;
    }

    function storePendingAttachment(value) {
        var normalized = normalizeAttachment(value);

        if (!normalized) {
            window.NovaMobileAttachmentDebugWarn("[Nova Mobile Hard Attachment Payload] upload response could not normalize", value);
            return false;
        }

        var current = getPendingAttachments();
        current.push(normalized);

        var clean = [];
        var seen = {};

        current.forEach(function (item) {
            var key = String(item.url || item.file_url || item.filename || "").toLowerCase();
            if (!key || seen[key]) {
                return;
            }
            seen[key] = true;
            clean.push(item);
        });

        localStorage.setItem(PENDING_KEY, JSON.stringify(clean));
        localStorage.setItem(LAST_KEY, JSON.stringify(normalized));

        window.NovaMobilePendingAttachments = clean;
        window.__novaMobilePendingAttachments = clean;

        window.NovaMobileAttachmentDebugLog("[Nova Mobile Hard Attachment Payload] stored pending attachment", normalized);
        return true;
    }

    var previousFetch = window.fetch;

    window.fetch = function (input, init) {
        var url = typeof input === "string" ? input : (input && input.url ? input.url : "");

        return previousFetch.apply(this, arguments).then(function (response) {
            try {
                if (url.indexOf("/api/upload") !== -1 && response && response.clone) {
                    response.clone().json().then(function (data) {
                        storePendingAttachment(data);
                    }).catch(function (e) {
                        window.NovaMobileAttachmentDebugWarn("[Nova Mobile Hard Attachment Payload] could not read upload json", e);
                    });
                }

                if (url.indexOf("/api/chat") !== -1 && init && init.body) {
                    var payload = parseJson(init.body, null);

                    if (payload && typeof payload === "object") {
                        var text = String(payload.user_text || payload.text || payload.message || "").toLowerCase();
                        var wantsAttachment = (
                            text.indexOf("attachment") !== -1 ||
                            text.indexOf("attach") !== -1 ||
                            text.indexOf("this file") !== -1 ||
                            text.indexOf("summarize this") !== -1 ||
                            text.indexOf("summarise this") !== -1
                        );

                        var existing = Array.isArray(payload.attachments) ? payload.attachments : [];

                        if (wantsAttachment && existing.length === 0) {
                            var pending = getPendingAttachments();

                            if (pending.length > 0) {
                                payload.attachments = pending;
                                init.body = JSON.stringify(payload);
                                window.NovaMobileAttachmentDebugLog("[Nova Mobile Hard Attachment Payload] injected attachments into /api/chat", pending);
                            } else {
                                window.NovaMobileAttachmentDebugWarn("[Nova Mobile Hard Attachment Payload] attachment prompt but pending list is empty");
                            }
                        }
                    }
                }
            } catch (e) {
                window.NovaMobileAttachmentDebugWarn("[Nova Mobile Hard Attachment Payload] fetch bridge failed", e);
            }

            return response;
        });
    };

    window.NovaMobileHardAttachmentPayloadGet = getPendingAttachments;
    window.NovaMobileHardAttachmentPayloadStore = storePendingAttachment;

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Hard Attachment Payload] ready");
})();


/* NOVA_MOBILE_PREFLIGHT_CHAT_ATTACHMENT_INJECT_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaMobilePreflightChatAttachmentInjectInstalled) {
        return;
    }

    window.NovaMobilePreflightChatAttachmentInjectInstalled = true;

    var PENDING_KEY = "nova_mobile_pending_attachments";
    var LAST_KEY = "nova_mobile_last_uploaded_attachment";

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    }

    function getPendingAttachments() {
        var found = [];

        var pending = parseJson(localStorage.getItem(PENDING_KEY) || "[]", []);
        if (Array.isArray(pending)) {
            found = found.concat(pending);
        }

        var last = parseJson(localStorage.getItem(LAST_KEY) || "null", null);
        if (last && typeof last === "object") {
            found.push(last);
        }

        if (Array.isArray(window.NovaMobilePendingAttachments)) {
            found = found.concat(window.NovaMobilePendingAttachments);
        }

        if (Array.isArray(window.__novaMobilePendingAttachments)) {
            found = found.concat(window.__novaMobilePendingAttachments);
        }

        var clean = [];
        var seen = {};

        found.forEach(function (item) {
            if (!item || typeof item !== "object") {
                return;
            }

            var key = String(item.url || item.file_url || item.filename || item.name || "").toLowerCase();

            if (!key || seen[key]) {
                return;
            }

            seen[key] = true;
            clean.push(item);
        });

        return clean;
    }

    var previousFetch = window.fetch;

    window.fetch = function (input, init) {
        try {
            var url = typeof input === "string" ? input : (input && input.url ? input.url : "");

            if (url.indexOf("/api/chat") !== -1 && init && init.body) {
                var payload = parseJson(init.body, null);

                if (payload && typeof payload === "object") {
                    var text = String(payload.user_text || payload.text || payload.message || "").toLowerCase();
                    var wantsAttachment = (
                        text.indexOf("attachment") !== -1 ||
                        text.indexOf("attach") !== -1 ||
                        text.indexOf("image") !== -1 ||
                        text.indexOf("photo") !== -1 ||
                        text.indexOf("picture") !== -1 ||
                        text.indexOf("describe this") !== -1 ||
                        text.indexOf("what is this") !== -1 ||
                        text.indexOf("this file") !== -1 ||
                        text.indexOf("summarize this") !== -1 ||
                        text.indexOf("summarise this") !== -1
                    );

                    var existing = Array.isArray(payload.attachments) ? payload.attachments : [];

                    if (wantsAttachment && existing.length === 0) {
                        var pending = getPendingAttachments();

                        if (pending.length > 0) {
                            payload.attachments = pending;
                            init.body = JSON.stringify(payload);

                            window.NovaMobileAttachmentDebugLog("[Nova Mobile Preflight Attachment Inject] injected before /api/chat", pending);
                        } else {
                            window.NovaMobileAttachmentDebugWarn("[Nova Mobile Preflight Attachment Inject] wanted attachment but pending empty");
                        }
                    }
                }
            }
        } catch (e) {
            window.NovaMobileAttachmentDebugWarn("[Nova Mobile Preflight Attachment Inject] failed", e);
        }

        return previousFetch.apply(this, arguments);
    };

    window.NovaMobilePreflightChatAttachmentGet = getPendingAttachments;

    window.NovaMobileAttachmentDebugLog("[Nova Mobile Preflight Attachment Inject] ready");
})();


/* NOVA_ATTACHMENT_PIPELINE_PROBE_20260607 */
(function () {
    "use strict";

    // NOVA_MOBILE_QUIET_ATTACHMENT_DEBUG_LOGS_20260608
    var NOVA_MOBILE_ATTACHMENT_DEBUG = false;
    function novaAttachmentDebugLog() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.log.apply(console, arguments);
        } catch (e) {}
    }
    function novaAttachmentDebugWarn() {
        if (!NOVA_MOBILE_ATTACHMENT_DEBUG) return;
        try {
            console.warn.apply(console, arguments);
        } catch (e) {}
    }

    if (window.NovaAttachmentPipelineProbeInstalled) {
        return;
    }

    window.NovaAttachmentPipelineProbeInstalled = true;

    function parseJson(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    }

    function readPending() {
        return {
            local_pending: parseJson(localStorage.getItem("nova_mobile_pending_attachments") || "[]", []),
            local_last: parseJson(localStorage.getItem("nova_mobile_last_uploaded_attachment") || "null", null),
            win_pending: Array.isArray(window.NovaMobilePendingAttachments) ? window.NovaMobilePendingAttachments : [],
            win_alt_pending: Array.isArray(window.__novaMobilePendingAttachments) ? window.__novaMobilePendingAttachments : []
        };
    }

    var previousFetch = window.fetch;

    window.fetch = function (input, init) {
        var url = typeof input === "string" ? input : (input && input.url ? input.url : "");

        if (url.indexOf("/api/upload") !== -1) {
            novaAttachmentDebugLog("[NOVA PIPELINE PROBE] /api/upload request starting");
        }

        if (url.indexOf("/api/chat") !== -1) {
            var payload = init && init.body ? parseJson(init.body, {}) : {};
            novaAttachmentDebugLog("[NOVA PIPELINE PROBE] /api/chat BEFORE SEND", {
                text: payload.user_text || payload.text || payload.message || "",
                payload_attachments: payload.attachments || [],
                pending_state: readPending()
            });
        }

        return previousFetch.apply(this, arguments).then(function (response) {
            if (url.indexOf("/api/upload") !== -1 && response && response.clone) {
                response.clone().json().then(function (data) {
                    novaAttachmentDebugLog("[NOVA PIPELINE PROBE] /api/upload response", data);
                    novaAttachmentDebugLog("[NOVA PIPELINE PROBE] pending after upload response", readPending());
                }).catch(function () {});
            }

            if (url.indexOf("/api/chat") !== -1) {
                novaAttachmentDebugLog("[NOVA PIPELINE PROBE] /api/chat response completed");
            }

            return response;
        });
    };

    window.NovaAttachmentPipelineProbeState = readPending;

    novaAttachmentDebugLog("[NOVA PIPELINE PROBE] ready");
})();



// NOVA_MOBILE_ATTACHMENT_STATE_ISOLATION_LOCK_20260609
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ATTACHMENT_STATE_ISOLATION_LOCK__) {
        return;
    }

    window.__NOVA_MOBILE_ATTACHMENT_STATE_ISOLATION_LOCK__ = true;

    var PENDING_KEYS = [
        "nova_mobile_pending_attachments",
        "nova_mobile_latest_attachments",
        "nova_mobile_last_uploaded_attachment",
        "nova_pending_attachments"
    ];

    function parsePayload(body) {
        try {
            return JSON.parse(String(body || "{}"));
        } catch (error) {
            return null;
        }
    }

    function getText(payload) {
        if (!payload) return "";

        return String(
            payload.user_text ||
            payload.text ||
            payload.message ||
            payload.prompt ||
            ""
        ).trim();
    }

    function isChatUrl(url) {
        url = String(url || "");
        return (
            url.indexOf("/api/chat") !== -1 ||
            url.indexOf("/api/chat/stream") !== -1
        );
    }

    function isAttachmentIntent(text) {
        text = String(text || "").toLowerCase();

        return (
            text.indexOf("attachment") !== -1 ||
            text.indexOf("uploaded") !== -1 ||
            text.indexOf("upload") !== -1 ||
            text.indexOf("file") !== -1 ||
            text.indexOf("docx") !== -1 ||
            text.indexOf("pdf") !== -1 ||
            text.indexOf("image") !== -1 ||
            text.indexOf("picture") !== -1 ||
            text.indexOf("photo") !== -1 ||
            text.indexOf("summarize this") !== -1 ||
            text.indexOf("summarise this") !== -1 ||
            text.indexOf("analyze this") !== -1 ||
            text.indexOf("analyse this") !== -1 ||
            text.indexOf("what does this say") !== -1 ||
            text.indexOf("what is this file") !== -1
        );
    }

    function clearAttachmentState(reason) {
        try {
            window.NovaMobileSharedAttachments = [];
            window.NovaMobilePendingAttachments = [];
            window.__novaMobilePendingAttachments = [];
            window.NovaPendingAttachments = [];
            window.__novaPendingAttachments = [];

            if (window.NovaMobileState) {
                window.NovaMobileState.pendingAttachments = [];
            }

            if (window.NovaMobileState && window.NovaMobileState.state) {
                window.NovaMobileState.state.pendingAttachments = [];
            }
        } catch (error) {}

        PENDING_KEYS.forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (error) {}
        });

        try {
            window.dispatchEvent(new CustomEvent("nova-mobile-attachments-cleared", {
                detail: {
                    pendingAttachments: [],
                    reason: reason || "attachment_state_isolation"
                }
            }));
        } catch (error) {}

        try {
            if (typeof window.NovaRenderComposerInlinePreview === "function") {
                window.NovaRenderComposerInlinePreview();
            }

            if (typeof window.NovaMobileCleanAttachmentChipOnlyClear === "function") {
                window.NovaMobileCleanAttachmentChipOnlyClear();
            }
        } catch (error) {}

        console.log("[Nova Mobile Attachment State Isolation] cleared", reason || "");
    }

    function stripAttachmentsFromPayload(payload) {
        if (!payload) return payload;

        payload.attachments = [];
        payload.force_attachments = false;
        payload.attachment_count = 0;

        return payload;
    }

    var previousFetch = window.fetch;

    window.fetch = async function novaAttachmentStateIsolationFetch(input, init) {
        var url = "";

        try {
            if (typeof input === "string") {
                url = input;
            } else if (input && input.url) {
                url = input.url;
            }
        } catch (error) {}

        if (!isChatUrl(url) || !init || !init.body) {
            return previousFetch.apply(this, arguments);
        }

        var payload = parsePayload(init.body);
        var text = getText(payload);
        var wantsAttachment = isAttachmentIntent(text);

        if (!wantsAttachment) {
            clearAttachmentState("normal_chat_or_web_request");

            if (payload) {
                stripAttachmentsFromPayload(payload);
                init = Object.assign({}, init, {
                    body: JSON.stringify(payload)
                });
            }
        }

        var hadAttachmentPayload = Boolean(
            payload &&
            (
                Array.isArray(payload.attachments) && payload.attachments.length ||
                payload.force_attachments ||
                payload.attachment_count
            )
        );

        var response = await previousFetch.call(this, input, init);

        if (wantsAttachment || hadAttachmentPayload) {
            setTimeout(function () {
                clearAttachmentState("attachment_request_completed");
            }, 100);

            setTimeout(function () {
                clearAttachmentState("attachment_request_completed_late");
            }, 750);
        }

        return response;
    };

    window.NovaMobileClearAllAttachmentState = clearAttachmentState;

    console.log("[Nova Mobile Attachment State Isolation] ready");
})();
