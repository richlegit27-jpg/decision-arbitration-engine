(function () {
    "use strict";

    var VERSION = "send-single-upload-owner-20260705";
    window.__NOVA_MOBILE_SEND_STABLE_V1_20260703__ = VERSION;

    var inFlight = false;

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile Send Stable V1]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function getSessionId() {
        try {
            var urlId = new URLSearchParams(window.location.search).get("session_id");
            if (urlId) return urlId;
        } catch (_) {}

        try {
            var localId = localStorage.getItem("nova_mobile_active_session_id") || localStorage.getItem("nova_active_session_id");
            if (localId) return localId;
        } catch (_) {}

        return "mobile_" + Date.now() + "_" + Math.random().toString(16).slice(2);
    }

    function findInput() {
        var selectors = [
            "#message-input",
            "#chat-input",
            "#nova-mobile-input",
            "#nova-chat-input",
            "textarea",
            "input[type='text']"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var nodes = Array.from(document.querySelectorAll(selectors[i]));
            for (var j = 0; j < nodes.length; j += 1) {
                var el = nodes[j];
                if (!el) continue;
                if (el.offsetParent === null && el !== document.activeElement) continue;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                return el;
            }
        }

        return null;
    }

    function findMainChatContainer() {
        var restored = document.querySelector("[data-nova-restored-session-id]");
        if (restored) return restored;

        var selectors = [
            "#nova-session-main-restore-fallback",
            "#nova-mobile-chat-messages",
            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#chat-messages",
            "#messages",
            "[data-nova-mobile-messages]",
            ".nova-mobile-chat-messages",
            ".nova-mobile-messages",
            ".chat-messages",
            ".messages"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var nodes = Array.from(document.querySelectorAll(selectors[i]));
            for (var j = 0; j < nodes.length; j += 1) {
                var el = nodes[j];
                if (!el) continue;
                if (el.id === "nova-session-drawer-v2-panel") continue;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                return el;
            }
        }

        var fallback = document.createElement("div");
        fallback.id = "nova-session-main-restore-fallback";
        fallback.setAttribute("data-nova-mobile-messages", "true");
        document.body.appendChild(fallback);
        return fallback;
    }

    function installStyle() {
        var style = document.getElementById("nova-mobile-send-stable-v1-style");
        if (style) return;

        style = document.createElement("style");
        style.id = "nova-mobile-send-stable-v1-style";
        style.textContent = [
            ".nova-stable-send-message{margin:8px 10px!important;padding:10px 12px!important;border-radius:12px!important;color:#fff!important;white-space:pre-wrap!important;word-break:break-word!important;font-size:14px!important;line-height:1.38!important}",
            ".nova-stable-send-message[data-role='user']{background:rgba(139,92,246,.26)!important}",
            ".nova-stable-send-message[data-role='assistant']{background:rgba(255,255,255,.09)!important}",
            ".nova-stable-send-message[data-role='system']{background:rgba(255,255,255,.06)!important;color:rgba(255,255,255,.75)!important}"
        ].join("\\n");
        document.head.appendChild(style);
    }

function appendMessage(role, text, message) {
    if (
        window.NovaMobileChatUI &&
        typeof window.NovaMobileChatUI.appendMessage === "function"
    ) {
        return window.NovaMobileChatUI.appendMessage(
            role,
            text,
            message
        );
    }

    console.warn(
        "[Nova Send] chat renderer unavailable"
    );

    return null;
}
    function forceLatestMessageVisible() {
        function scroll() {
            if (
                window.NovaMobileBridge &&
                typeof window.NovaMobileBridge.scrollBottom ===
                    "function"
            ) {
                window.NovaMobileBridge.scrollBottom(true);
                return;
            }

            if (
                window.NovaMobileCore &&
                typeof window.NovaMobileCore.scrollBottom ===
                    "function"
            ) {
                window.NovaMobileCore.scrollBottom(true);
                return;
            }

            if (window.chatContainer) {
                window.chatContainer.scrollTop =
                    window.chatContainer.scrollHeight;
            }
        }

        scroll();
        requestAnimationFrame(scroll);
        setTimeout(scroll, 120);
        setTimeout(scroll, 350);
    }

    function extractReply(payload) {
        if (!payload) return "";

        return String(
            payload.text ||
            (payload.assistant_message && (payload.assistant_message.text || payload.assistant_message.content)) ||
            payload.content ||
            payload.message ||
            ""
        );
    }

function normalizeAttachmentForSend(item) {
    if (!item || typeof item !== "object") {
        return null;
    }

    var filename =
        item.filename ||
        item.name ||
        item.file_name ||
        item.original_name ||
        item.original_filename ||
        "";

    var url =
        item.url ||
        item.file_url ||
        item.fileUrl ||
        item.path ||
        item.upload_path ||
        item.saved_path ||
        item.file_path ||
        item.upload_url ||
        item.uploadUrl ||
        "";

    var mimeType =
        item.mime_type ||
        item.mimeType ||
        item.type ||
        item.content_type ||
        "";

    var size =
        item.size ||
        item.size_bytes ||
        item.sizeBytes ||
        null;

    if (!filename && !url) {
        return null;
    }

    return {
        id: item.id || item.attachment_id || item.file_id || "",
        attachment_id: item.attachment_id || item.id || item.file_id || "",
        filename: filename,
        name: filename,
        url: url,
        file_url: url,
        path: item.path || item.upload_path || item.saved_path || item.file_path || url,
        mime_type: mimeType,
        type: mimeType,
        content_type: mimeType,
        size: size,
        size_bytes: size
    };
}

function addAttachmentCandidates(out, value) {
    if (!value) {
        return;
    }

    if (Array.isArray(value)) {
        value.forEach(function (item) {
            var clean = normalizeAttachmentForSend(item);
            if (clean) {
                out.push(clean);
            }
        });
        return;
    }

    if (typeof value === "object") {
        [
            "attachments",
            "files",
            "queue",
            "items",
            "uploaded",
            "uploadedFiles",
            "pending",
            "pendingAttachments"
        ].forEach(function (key) {
            if (Array.isArray(value[key])) {
                addAttachmentCandidates(out, value[key]);
            }
        });

        var cleanSingle = normalizeAttachmentForSend(value);
        if (cleanSingle) {
            out.push(cleanSingle);
        }
    }
}

function readJsonArray(key) {
    try {
        var raw = localStorage.getItem(key);
        if (!raw) {
            return [];
        }

        var parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
        return [];
    }
}

function collectPendingAttachments() {
    var found = [];

    function safeAdd(value) {
        try {
            addAttachmentCandidates(found, value);
        } catch (_) {}
    }

    function safeJson(raw) {
        try {
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (_) {
            return null;
        }
    }

    try {
        safeAdd(window.NovaMobileUpload?.getPendingAttachments?.());
    } catch (_) {}

    safeAdd(window.NovaMobileUpload);
    safeAdd(window.NovaMobileSharedAttachments);
    safeAdd(window.__novaMobilePendingAttachments);
    safeAdd(window.NovaMobilePendingAttachments);
    safeAdd(window.__NOVA_MOBILE_PENDING_ATTACHMENTS__);
    safeAdd(window.NovaMobileUploadedAttachments);
    safeAdd(window.NovaMobileAttachmentQueue);
    safeAdd(window.NovaMobileUploadQueue);
    safeAdd(window.pendingAttachments);

    [
        "nova_mobile_pending_attachments",
        "nova_mobile_upload",
        "nova_mobile_uploads",
        "nova_mobile_attachment_queue",
        "nova_mobile_uploaded_attachments",
        "nova_pending_attachments",
        "pending_attachments",
        "nova_mobile_last_uploaded_attachment",
        "nova_mobile_pending_attachment",
        "nova_mobile_attachment",
        "nova_pending_attachment",
        "pending_attachment"
    ].forEach(function (key) {
        try {
            safeAdd(safeJson(localStorage.getItem(key)));
            safeAdd(safeJson(sessionStorage.getItem(key)));
        } catch (_) {}
    });

    try {
        Object.keys(window).forEach(function (key) {
            if (!/(upload|attach|attachment|file)/i.test(key)) {
                return;
            }

            if (!/^Nova|^nova|pending|upload|attach|file/i.test(key)) {
                return;
            }

            try {
                safeAdd(window[key]);
            } catch (_) {}
        });
    } catch (_) {}

    var seen = {};
    var unique = [];

    found.forEach(function (item) {
        var clean = normalizeAttachmentForSend(item);
        if (!clean) return;

        var key = [
            clean.filename || clean.name || "",
            clean.url || clean.file_url || clean.path || "",
            clean.mime_type || clean.type || "",
            clean.size || ""
        ].join("|");

        if (!seen[key]) {
            seen[key] = true;
            unique.push(clean);
        }
    });

    return unique;
}

function clearPendingAttachmentsAfterSend() {
    window.NovaMobileSharedAttachments = [];
    window.__novaMobilePendingAttachments = [];
    window.NovaMobilePendingAttachments = [];
    window.__NOVA_MOBILE_PENDING_ATTACHMENTS__ = [];
    window.NovaMobileUploadedAttachments = [];
    window.NovaMobileAttachmentQueue = [];
    window.NovaMobileUploadQueue = [];
    window.pendingAttachments = [];

    try {
        [
            "nova_mobile_pending_attachments",
            "nova_mobile_last_uploaded_attachment",
            "nova_mobile_pending_attachment",
            "nova_mobile_attachment",
            "nova_mobile_upload",
            "nova_pending_attachment",
            "pending_attachment"
        ].forEach(function (key) {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });
    } catch (_) {}

    var selectors = [
        "#nova-mobile-upload-preview-owner",
        ".nova-mobile-upload-preview-owner",
        ".nova-mobile-upload-preview-chip",
        "[data-nova-role='attachment-preview-chip']",

        "#nova-mobile-attachment-preview",
        ".nova-mobile-attachment-preview",
        "#mobileAttachmentPreview",
        ".mobile-attachment-preview",
        "[data-mobile-attachment-preview]",

        "#nova-mobile-preview-bar",
        ".nova-mobile-preview-bar",
        ".nova-mobile-preview-strip",
        ".nova-mobile-upload-preview",
        ".nova-mobile-attachment-chip",
        ".nova-mobile-upload-chip",

        "[data-nova-attachment-preview]",
        "[data-nova-upload-preview]",
        "[data-nova-attachment-chip]",
        "[data-upload-preview]",
        "[data-attachment-preview]"
    ];

    document.querySelectorAll(selectors.join(",")).forEach(function (node) {
        try {
            node.innerHTML = "";
            node.hidden = true;
            node.style.display = "none";
            node.style.visibility = "hidden";
            node.style.opacity = "0";
            node.classList.remove(
                "open",
                "is-open",
                "active",
                "visible",
                "show",
                "has-attachment",
                "is-visible"
            );
            node.removeAttribute("data-has-attachment");
        } catch (_) {}

        try {
            if (
                node.id !== "nova-mobile-upload-preview-owner" &&
                node.id !== "nova-mobile-preview-bar"
            ) {
                node.remove();
            }
        } catch (_) {}
    });

    document.querySelectorAll("input[type='file']").forEach(function (input) {
        try {
            input.value = "";
        } catch (_) {}
    });

    try {
        if (window.NovaMobileUploadPreviewOwner && typeof window.NovaMobileUploadPreviewOwner.clear === "function") {
            window.NovaMobileUploadPreviewOwner.clear();
        }
    } catch (_) {}

    try {
        document.body.classList.remove(
            "nova-has-attachment",
            "nova-mobile-has-attachment",
            "nova-upload-active",
            "nova-attachment-active"
        );
    } catch (_) {}

    log("cleared attachments after send");
}

    function sendNow(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        if (inFlight) {
            log("ignored duplicate send");
            return;
        }

var input = findInput();
var text = input ? String(input.value || "").trim() : "";

if (!text) {

            log("empty send ignored");
            return;
        }

        var sid = getSessionId();

        try {
            localStorage.setItem("nova_mobile_active_session_id", sid);
            localStorage.setItem("nova_active_session_id", sid);
        } catch (_) {}

        inFlight = true;

        appendMessage("user", text);
        forceLatestMessageVisible();

        if (input) {
            input.value = "";
            try {
                input.dispatchEvent(new Event("input", { bubbles: true }));
            } catch (_) {}
        }

var bridgeAttachments = [];

try {
    bridgeAttachments = window.NovaMobileUpload?.getPendingAttachments?.() || [];
} catch (_) {
    bridgeAttachments = [];
}

var pendingAttachments = collectPendingAttachments();

console.log("[Nova Send Stable] ATTACHMENT SOURCES", {
    bridgeCount: Array.isArray(bridgeAttachments) ? bridgeAttachments.length : -1,
    collectCount: Array.isArray(pendingAttachments) ? pendingAttachments.length : -1,
    bridgeAttachments: bridgeAttachments,
    collectedAttachments: pendingAttachments,
    novaMobileUpload: window.NovaMobileUpload,
    pendingA: window.NovaMobilePendingAttachments,
    pendingB: window.__novaMobilePendingAttachments,
    pendingC: window.NovaMobileSharedAttachments,
    localUpload: localStorage.getItem("nova_mobile_upload"),
    localPending: localStorage.getItem("nova_mobile_pending_attachments")
});

if (
    Array.isArray(bridgeAttachments) &&
    bridgeAttachments.length &&
    (!Array.isArray(pendingAttachments) || !pendingAttachments.length)
) {
    pendingAttachments = bridgeAttachments.map(function (item) {
        return normalizeAttachmentForSend(item) || item;
    }).filter(Boolean);
}

var payload = {
    message: text,
    session_id: sid
};

console.log("[Nova Send Stable] BEFORE CHAT SEND", {
    text: text,
    session_id: sid,
    attachmentCount: pendingAttachments.length,
    attachments: pendingAttachments
});

console.log("[Nova Send Stable] FINAL PAYLOAD BEFORE CHAT", {
    attachmentCount: Array.isArray(pendingAttachments) ? pendingAttachments.length : 0,
    payload: payload
});

console.log("[Nova Send Stable] FINAL ATTACHMENT CHECK", {
    attachmentCount: pendingAttachments.length,
    attachments: pendingAttachments,
    novaMobileUpload: window.NovaMobileUpload,
    uploadGetter: (function () {
        try {
            return window.NovaMobileUpload?.getPendingAttachments?.();
        } catch (_) {
            return null;
        }
    })(),
    localUpload: localStorage.getItem("nova_mobile_upload"),
    localPending: localStorage.getItem("nova_mobile_pending_attachments")
});

if (pendingAttachments.length) {
    payload.attachments = pendingAttachments;
    payload.files = pendingAttachments;
    payload.uploads = pendingAttachments;
    payload.uploaded_files = pendingAttachments;
    payload.attachment = pendingAttachments[0];
    log("sending with attachments", pendingAttachments);
} else {
    log("sending without attachments");
}

if (
    window.NovaMobileRuntime &&
    typeof window.NovaMobileRuntime.setGeneratingState === "function"
) {
    window.NovaMobileRuntime.setGeneratingState(true);
}

fetch("/api/chat", {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    body: JSON.stringify(payload)
}).then(function (response) {
    return response.text().then(function (raw) {
        if (!response.ok) {
            throw new Error("HTTP " + response.status + ": " + raw.slice(0, 500));
        }

        var responsePayload = JSON.parse(raw);
        var reply =
            extractReply(responsePayload) ||
            "[empty response]";

        var assistantMessage =
            responsePayload.assistant_message &&
            typeof responsePayload.assistant_message ===
                "object"
                ? Object.assign(
                    {},
                    responsePayload.assistant_message
                )
                : {
                    role: "assistant",
                    text: reply
                };

        if (
            responsePayload.image_url &&
            !assistantMessage.image_url
        ) {
            assistantMessage.image_url =
                responsePayload.image_url;
        }

        if (
            Array.isArray(responsePayload.attachments) &&
            !Array.isArray(
                assistantMessage.attachments
            )
        ) {
            assistantMessage.attachments =
                responsePayload.attachments;
        }

        appendMessage(
            "assistant",
            reply,
            assistantMessage
        );
        forceLatestMessageVisible();

try {
    window.NovaMobileUpload?.clearPendingAttachments?.();
} catch (_) {}

try {
    window.NovaMobileUpload?.clear?.();
} catch (_) {}

clearPendingAttachmentsAfterSend();

log("sent", sid);
    });

}).catch(function (err) {

    appendMessage(
        "system",
        "Send failed: " + (err && err.message ? err.message : String(err))
    );

    log("failed", err);

}).finally(function () {

    if (
        window.NovaMobileRuntime &&
        typeof window.NovaMobileRuntime.setGeneratingState === "function"
    ) {
        window.NovaMobileRuntime.setGeneratingState(false);
    }

    inFlight = false;
});

    }

    function looksLikeSendButton(el) {
        if (!el) return false;

        var text = String(el.textContent || "").trim().toLowerCase();
        var aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        var title = String(el.getAttribute("title") || "").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var klass = String(el.className || "").toLowerCase();

        var haystack = [text, aria, title, id, klass].join(" ");

        if (haystack.indexOf("session") >= 0) return false;
        if (haystack.indexOf("stop") >= 0) return false;
        if (haystack.indexOf("voice") >= 0) return false;
        if (haystack.indexOf("attach") >= 0) return false;

        return (
            text === "send" ||
            text === "âž¤" ||
            text === "â†‘" ||
            haystack.indexOf("send") >= 0
        );
    }
function installCapture() {
    if (window.__NOVA_MOBILE_SEND_STABLE_V1_CAPTURE_INSTALLED_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SEND_STABLE_V1_CAPTURE_INSTALLED_20260703__ = true;

document.addEventListener("click", function (event) {
    var button = event.target && event.target.closest
        ? event.target.closest("#nova-mobile-send")
        : null;

    if (!button) return;

if (button.classList.contains("is-stop-mode")) {
    if (
        window.NovaMobileRuntime &&
        typeof window.NovaMobileRuntime.stopGeneration === "function"
    ) {
        window.NovaMobileRuntime.stopGeneration();
    } else if (window.NovaMobileAbortController) {
        window.NovaMobileAbortController.abort();
    } else {
        console.warn("[Nova Stop] stop handler unavailable");
    }

    return;
}

    sendNow(event);
}, true);

    document.addEventListener("keydown", function (event) {
        if (!event) return;
        if (event.key !== "Enter") return;
        if (event.shiftKey) return;

        var target = event.target;

        if (!target) return;
        if (!target.matches || !target.matches("textarea, input[type='text']")) return;

        if (target.closest && target.closest("#nova-session-drawer-v2-panel")) {
            return;
        }

         sendNow(event);
    }, true);
}

installCapture();

})();


