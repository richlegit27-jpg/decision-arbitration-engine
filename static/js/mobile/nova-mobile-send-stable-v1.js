(function () {
    "use strict";

    var VERSION = "mobile-send-stable-v1-20260703";
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

    function appendMessage(role, text) {
        installStyle();

        var container = findMainChatContainer();
        if (!container) return;

        var row = document.createElement("div");
        row.className = "nova-stable-send-message";
        row.setAttribute("data-role", role || "assistant");
        row.textContent = text || "";
        container.appendChild(row);

        try {
            container.scrollTop = container.scrollHeight;
        } catch (_) {}
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
        "";

    var url =
        item.url ||
        item.file_url ||
        item.fileUrl ||
        item.path ||
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
        filename: filename,
        name: filename,
        url: url,
        file_url: url,
        mime_type: mimeType,
        type: mimeType,
        size: size
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

    addAttachmentCandidates(found, window.NovaMobileSharedAttachments);
    addAttachmentCandidates(found, window.__novaMobilePendingAttachments);
    addAttachmentCandidates(found, window.NovaMobilePendingAttachments);
    addAttachmentCandidates(found, window.__NOVA_MOBILE_PENDING_ATTACHMENTS__);
    addAttachmentCandidates(found, window.NovaMobileUploadedAttachments);
    addAttachmentCandidates(found, window.NovaMobileAttachmentQueue);
    addAttachmentCandidates(found, window.NovaMobileUploadQueue);
    addAttachmentCandidates(found, window.pendingAttachments);

    addAttachmentCandidates(found, readJsonArray("nova_mobile_pending_attachments"));

    var seen = {};
    var unique = [];

    found.forEach(function (item) {
        var key = [
            item.filename || "",
            item.url || "",
            item.mime_type || ""
        ].join("|");

        if (!seen[key]) {
            seen[key] = true;
            unique.push(item);
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

        if (input) {
            input.value = "";
            try {
                input.dispatchEvent(new Event("input", { bubbles: true }));
            } catch (_) {}
        }

var pendingAttachments = collectPendingAttachments();

var payload = {
    message: text,
    session_id: sid
};

if (pendingAttachments.length) {
    payload.attachments = pendingAttachments;
    payload.files = pendingAttachments;
    log("sending with attachments", pendingAttachments);
} else {
    log("sending without attachments");
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
        var reply = extractReply(responsePayload) || "[empty response]";

        appendMessage("assistant", reply);

        clearPendingAttachmentsAfterSend();

        log("sent", sid);
    });
}).catch(function (err) {
    appendMessage("system", "Send failed: " + (err && err.message ? err.message : String(err)));
    log("failed", err);
}).finally(function () {
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
            var target = event.target;
            var button = target && target.closest && target.closest("button, a, [role='button']");
            if (!button) return;
            if (button.closest && button.closest("#nova-session-drawer-v2-panel")) return;

            if (looksLikeSendButton(button)) {
                sendNow(event);
            }
        }, true);

        document.addEventListener("keydown", function (event) {
            if (!event) return;
            if (event.key !== "Enter") return;
            if (event.shiftKey) return;

            var target = event.target;
            if (!target) return;
            if (!target.matches || !target.matches("textarea, input[type='text']")) return;
            if (target.closest && target.closest("#nova-session-drawer-v2-panel")) return;

            sendNow(event);
        }, true);
    }

    installCapture();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installCapture);
    }

    window.NovaMobileSendStableV1 = {
        version: VERSION,
        sendNow: sendNow
    };

    log("ready", VERSION);
})();



